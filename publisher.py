import argparse
import json
import os
import time
from typing import List, Optional, Tuple

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from config import (
    IMAGE_DEFAULT_LOGO_ADD,
    IMAGE_DEFAULT_RESOLUTION,
    IMAGE_DEFAULT_STYLE,
    OUTPUT_DIR,
    TOUTIA_DEFAULT_USER_AGENT,
    TOUTIA_WEB_HOME_URL,
    TOUTIA_WEB_PUBLISH_URL,
)
from image_generator import generate_cover_image
from utils import logger

DEFAULT_ARTICLE_DIR = OUTPUT_DIR
DEFAULT_USER_AGENT = TOUTIA_DEFAULT_USER_AGENT
SELECTOR_CACHE_FILE = "selector_cache.json"


def list_article_files(directory: str) -> List[str]:
    """列出待发布的 Markdown 文件，按文件名排序。"""
    if not os.path.isdir(directory):
        logger.error(f"文章目录不存在: {directory}")
        return []

    files = [
        os.path.join(directory, name)
        for name in os.listdir(directory)
        if name.lower().endswith(".md")
    ]
    files.sort()
    logger.info(f"在 {directory} 中找到 {len(files)} 篇文章。")
    return files


def extract_article(file_path: str) -> Optional[Tuple[str, str, str]]:
    """从 Markdown 文件中提取标题、正文 HTML 和原始文本。"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw = f.read().strip()
    except OSError as exc:
        logger.error(f"读取文件失败 {file_path}: {exc}")
        return None

    if not raw:
        logger.warning(f"文件为空: {file_path}")
        return None

    lines = raw.splitlines()
    title = None
    body_lines: List[str] = []
    for line in lines:
        stripped = line.strip()
        if title is None and stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            continue
        body_lines.append(line)

    if not title:
        title = os.path.splitext(os.path.basename(file_path))[0]

    body = "\n".join(body_lines).strip() or raw
    return title, markdown_to_html(body), raw


def markdown_to_html(markdown_text: str) -> str:
    """将简单 Markdown 文本转为 HTML，确保发布编辑器识别。"""
    html_parts: List[str] = []
    for block in markdown_text.split("\n\n"):
        stripped = block.strip()
        if not stripped:
            continue
        if stripped.startswith("### "):
            html_parts.append(f"<h3>{stripped[4:].strip()}</h3>")
        elif stripped.startswith("## "):
            html_parts.append(f"<h2>{stripped[3:].strip()}</h2>")
        elif stripped.startswith("# "):
            html_parts.append(f"<h1>{stripped[2:].strip()}</h1>")
        elif stripped.startswith(">"):
            html_parts.append(
                f"<blockquote>{stripped.lstrip('> ').strip()}</blockquote>"
            )
        elif stripped.startswith("**") and stripped.endswith("**"):
            html_parts.append(f"<strong>{stripped.strip('*')}</strong>")
        else:
            safe_block = stripped.replace("\n", "<br>")
            html_parts.append(f"<p>{safe_block}</p>")
    return "\n".join(html_parts)


def load_cookies(cookie_file: str) -> List[dict]:
    """加载登录 Cookie。"""
    if not os.path.exists(cookie_file):
        raise FileNotFoundError(f"Cookie 文件不存在: {cookie_file}")
    with open(cookie_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Cookie 文件应为列表结构。")
    logger.info(f"已加载 {len(data)} 条 Cookie。")
    return data


def load_selector_cache() -> dict:
    """加载选择器缓存。"""
    if os.path.exists(SELECTOR_CACHE_FILE):
        try:
            with open(SELECTOR_CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
                logger.info(f"已加载选择器缓存：{len(cache)} 个记录")
                return cache
        except Exception as exc:
            logger.warning(f"加载选择器缓存失败：{exc}，将使用默认选择器")
    return {}


def save_selector_cache(cache: dict):
    """保存选择器缓存。"""
    try:
        with open(SELECTOR_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        logger.debug(f"已保存选择器缓存：{len(cache)} 个记录")
    except Exception as exc:
        logger.warning(f"保存选择器缓存失败：{exc}")


def find_element_with_cache(
    driver,
    cache_key: str,
    selectors: List[str],
    cache: dict,
    timeout: int = 10,
    element_type: str = "element",
    clickable: bool = False,
) -> Optional[Tuple[object, str]]:
    """
    使用缓存优先查找元素。
    返回: (元素对象, 使用的选择器) 或 None
    """
    # 优先使用缓存的选择器
    cached_selector = cache.get(cache_key)
    if cached_selector and cached_selector in selectors:
        try:
            wait = WebDriverWait(driver, timeout)
            if clickable:
                element = wait.until(
                    EC.element_to_be_clickable((By.XPATH, cached_selector))
                )
            else:
                element = wait.until(
                    EC.presence_of_element_located((By.XPATH, cached_selector))
                )
            logger.debug(f"使用缓存选择器成功定位{element_type}：{cache_key}")
            return element, cached_selector
        except Exception:
            logger.debug(f"缓存选择器失败，尝试其他方式：{cache_key}")

    # 尝试所有选择器
    for selector in selectors:
        try:
            wait = WebDriverWait(driver, timeout)
            if clickable:
                element = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
            else:
                element = wait.until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
            # 记录成功的选择器
            cache[cache_key] = selector
            save_selector_cache(cache)
            logger.info(
                f"成功定位{element_type}并已缓存：{cache_key} -> {selector[:50]}..."
            )
            return element, selector
        except Exception:
            continue

    return None


class ToutiaoPublisher:
    def __init__(
        self,
        cookies: List[dict],
        headless: bool = True,
        user_agent: str = DEFAULT_USER_AGENT,
    ):
        self.cookies = cookies
        self.headless = headless
        self.user_agent = user_agent
        self.driver: Optional[webdriver.Chrome] = None
        self.selector_cache = load_selector_cache()
        self._logged_in = False  # 标记是否已登录

    def __enter__(self):
        self._init_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def _init_browser(self):
        logger.info("正在启动浏览器...")
        options = ChromeOptions()
        if self.headless:
            options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.add_argument("--start-maximized")
        options.add_argument(f"user-agent={self.user_agent}")

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as exc:
            logger.error(f"自动安装 ChromeDriver 失败: {exc}")
            self.driver = webdriver.Chrome(options=options)

        self.driver.set_page_load_timeout(40)
        self.driver.set_script_timeout(40)

    def ensure_login(self):
        """通过注入 Cookie 自动登录（只执行一次）。"""
        if self._logged_in:
            logger.info("已登录，跳过登录步骤。")
            return

        if not self.driver:
            raise RuntimeError("浏览器尚未启动。")
        logger.info("正在尝试设置 Cookie 登录...")
        driver = self.driver
        driver.get(TOUTIA_WEB_HOME_URL)
        time.sleep(2)
        driver.delete_all_cookies()
        for cookie in self.cookies:
            cookie = cookie.copy()
            cookie.pop("expiry", None)
            driver.add_cookie(cookie)
        driver.refresh()
        time.sleep(5)

        if "login" in driver.current_url.lower():
            screenshot = f"login_failed_{int(time.time())}.png"
            driver.save_screenshot(screenshot)
            raise RuntimeError("Cookie 已失效，请重新获取。")

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".username, .user-name")
                )
            )
            logger.info("账号登录成功。")
        except TimeoutException:
            logger.warning("未能定位账号信息，但页面已进入后台。")

        self._logged_in = True  # 标记已登录

    def publish(
        self,
        title: str,
        content_html: str,
        cover_path: Optional[str] = None,
        use_cover: bool = True,
    ):
        if not self.driver:
            raise RuntimeError("浏览器尚未启动。")
        driver = self.driver

        logger.info("进入发布页面...")
        driver.get(TOUTIA_WEB_PUBLISH_URL)
        time.sleep(4)

        wait = WebDriverWait(driver, 20)
        self._fill_title(wait, title)
        self._fill_content(driver, wait, content_html)
        if cover_path and use_cover:
            self._upload_cover_image(driver, cover_path)
        elif not use_cover:
            self._ensure_no_cover_mode(driver)
        self._submit(driver, wait)

    def _fill_title(self, wait: WebDriverWait, title: str):
        title = title.strip()
        # safe_title = re.sub(r"[^\w\u4e00-\u9fa5·，。？！【】“”《》\-—— ]", "", title)[
        #     :30
        # ]
        safe_title = title
        logger.info(f"输入标题: {safe_title}")
        title_area = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "textarea[placeholder*='请输入文章标题']")
            )
        )
        title_area.clear()
        title_area.send_keys(safe_title)

    def _fill_content(self, driver, wait: WebDriverWait, content_html: str):
        logger.info("写入文章内容...")
        editor = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".ProseMirror"))
        )
        driver.execute_script(
            "arguments[0].innerHTML = arguments[1];", editor, content_html
        )
        time.sleep(2)

    def _ensure_single_cover_mode(self, driver):
        """选择"单图"封面模式。"""
        candidates = [
            "//label[@class='byte-radio']//input[@type='radio' and @value='2']/ancestor::label[1]",
            "//span[contains(@class,'byte-radio-inner-text') and text()='单图']/ancestor::label[1]",
        ]
        result = find_element_with_cache(
            driver,
            "single_cover_mode",
            candidates,
            self.selector_cache,
            timeout=5,
            element_type="单图封面选项",
        )
        if result:
            option, _ = result
            driver.execute_script("arguments[0].click();", option)
            time.sleep(1)
            logger.info("已切换为单图封面。")
        else:
            logger.warning("未能自动切换为单图封面，可能界面已调整。")

    def _ensure_no_cover_mode(self, driver):
        """选择"无封面"模式。"""
        candidates = [
            "//label[@class='byte-radio']//input[@type='radio' and @value='1']/ancestor::label[1]",
            "//span[contains(@class,'byte-radio-inner-text') and text()='无封面']/ancestor::label[1]",
            "//label[contains(@class,'byte-radio')]//span[text()='无封面']/ancestor::label[1]",
        ]
        result = find_element_with_cache(
            driver,
            "no_cover_mode",
            candidates,
            self.selector_cache,
            timeout=5,
            element_type="无封面选项",
        )
        if result:
            option, _ = result
            driver.execute_script("arguments[0].click();", option)
            time.sleep(1)
            logger.info("已切换为无封面模式。")
        else:
            logger.warning("未能自动切换为无封面模式，可能界面已调整。")

    def _upload_cover_image(self, driver, image_path: str):
        abs_path = os.path.abspath(image_path)
        logger.info(f"尝试上传封面：{abs_path}")
        self._ensure_single_cover_mode(driver)
        time.sleep(1)

        selectors = [
            "//div[contains(@class,'article-cover-add')]//input[@type='file']",
            "//div[contains(@class,'article-cover')]//input[@type='file']",
            "//input[@type='file' and contains(@accept,'image')]",
        ]

        result = find_element_with_cache(
            driver,
            "cover_upload_input",
            selectors,
            self.selector_cache,
            timeout=5,
            element_type="封面上传输入框",
        )

        if result:
            input_el, _ = result
            try:
                # 确保元素可见和可交互
                driver.execute_script(
                    """
                    arguments[0].style.display = 'block';
                    arguments[0].style.visibility = 'visible';
                    arguments[0].style.opacity = '1';
                    arguments[0].style.position = 'static';
                    arguments[0].style.width = 'auto';
                    arguments[0].style.height = 'auto';
                    """,
                    input_el,
                )
                input_el.send_keys(abs_path)
                time.sleep(3)
                logger.info("封面上传成功。")
                self._confirm_cover_upload(driver)
                return
            except Exception as exc:
                logger.warning(f"使用缓存选择器上传失败，尝试其他方式: {exc}")

        # 如果找不到file input，尝试点击上传区域触发
        try:
            upload_area = driver.find_element(
                By.XPATH, "//div[contains(@class,'article-cover-add')]"
            )
            driver.execute_script("arguments[0].click();", upload_area)
            time.sleep(1)
            # 再次尝试查找file input
            file_input = driver.find_element(By.XPATH, "//input[@type='file']")
            file_input.send_keys(abs_path)
            time.sleep(3)
            logger.info("封面上传成功（通过点击上传区域）。")
            self._confirm_cover_upload(driver)
            return
        except Exception as exc:
            logger.warning(f"通过点击上传区域也失败: {exc}")

        logger.warning("未找到可用的封面上传控件，封面上传已跳过。")

    def _confirm_cover_upload(self, driver):
        """上传封面后点击确认按钮。"""
        time.sleep(2)
        confirm_selectors = [
            "//span[contains(text(),'确定')]/ancestor::button[1]",
            "//button[contains(text(),'确定')]",
            "//button[contains(@class,'primary')]",
        ]

        result = find_element_with_cache(
            driver,
            "cover_upload_confirm",
            confirm_selectors,
            self.selector_cache,
            timeout=3,
            element_type="封面上传确认按钮",
            clickable=True,
        )

        if result:
            confirm_btn, _ = result
            driver.execute_script("arguments[0].click();", confirm_btn)
            time.sleep(1)
            logger.info("已点击封面上传确认按钮。")
        else:
            logger.debug("未找到封面上传确认按钮，可能不需要确认或界面已变化。")

    def _submit(self, driver, wait: WebDriverWait):
        """两步发布流程：1. 预览并发布 2. 确认发布"""
        logger.info("开始发布流程...")

        # 第一步：点击"预览并发布"按钮
        logger.info("第一步：点击'预览并发布'按钮...")
        preview_publish_selectors = [
            "//span[contains(text(),'预览并发布')]/ancestor::button[1]",
            "//button[contains(text(),'预览并发布')]",
            "//button[contains(@class,'publish-btn')]",
        ]

        result = find_element_with_cache(
            driver,
            "preview_publish_btn",
            preview_publish_selectors,
            self.selector_cache,
            timeout=20,
            element_type="预览并发布按钮",
            clickable=True,
        )

        if result:
            preview_btn, _ = result
            driver.execute_script("arguments[0].click();", preview_btn)
            logger.info("已点击'预览并发布'按钮。")
        else:
            raise RuntimeError("未找到'预览并发布'按钮，发布失败。")

        time.sleep(3)  # 等待确认对话框出现

        # 第二步：点击"确认发布"按钮
        logger.info("第二步：点击'确认发布'按钮...")
        confirm_publish_selectors = [
            "//span[contains(text(),'确认发布')]/ancestor::button[1]",
            "//button[contains(text(),'确认发布')]",
            "//div[contains(@class,'modal')]//button[contains(@class,'primary')]",
        ]

        result = find_element_with_cache(
            driver,
            "confirm_publish_btn",
            confirm_publish_selectors,
            self.selector_cache,
            timeout=10,
            element_type="确认发布按钮",
            clickable=True,
        )

        if result:
            confirm_btn, _ = result
            driver.execute_script("arguments[0].click();", confirm_btn)
            logger.info("已点击'确认发布'按钮。")
        else:
            logger.warning("未找到'确认发布'按钮，可能已自动发布或界面已变化。")

        time.sleep(3)
        logger.info("发布流程完成。")

    def cleanup(self):
        if self.driver:
            logger.info("关闭浏览器。")
            self.driver.quit()
            self.driver = None


def publish_directory(
    directory: str,
    cookie_file: str,
    limit: Optional[int],
    delay_seconds: float,
    headless: bool,
    cover_mode: str,
    cover_style: Optional[str],
    cover_resolution: Optional[str],
    cover_negative_prompt: str,
    cover_logo_add: Optional[int],
):
    files = list_article_files(directory)
    if limit:
        files = files[:limit]
    if not files:
        logger.warning("没有可发布的文章。")
        return

    cookies = load_cookies(cookie_file)

    with ToutiaoPublisher(cookies=cookies, headless=headless) as publisher:
        publisher.ensure_login()
        for idx, file_path in enumerate(files, start=1):
            logger.info(f"[{idx}/{len(files)}] 处理 {file_path}")
            article = extract_article(file_path)
            if not article:
                continue

            title, content_html, raw_text = article
            cover_path = None
            use_cover = True

            if cover_mode == "generate":
                max_retries = 3
                cover_generated = False
                for attempt in range(1, max_retries + 1):
                    try:
                        logger.info(f"尝试生成封面（第 {attempt}/{max_retries} 次）...")
                        cover_path = generate_cover_image(
                            title=title,
                            article_text=raw_text[:100],
                            style=cover_style or IMAGE_DEFAULT_STYLE,
                            resolution=cover_resolution or IMAGE_DEFAULT_RESOLUTION,
                            negative_prompt=cover_negative_prompt,
                            logo_add=(
                                cover_logo_add
                                if cover_logo_add is not None
                                else IMAGE_DEFAULT_LOGO_ADD
                            ),
                        )
                        logger.info(f"封面生成成功：{cover_path}")
                        cover_generated = True
                        break
                    except Exception as exc:
                        logger.warning(f"第 {attempt} 次生成封面失败：{exc}")
                        if attempt < max_retries:
                            time.sleep(2)  # 重试前等待2秒
                        else:
                            logger.error(
                                f"封面生成失败（已重试 {max_retries} 次），跳过该文章：{title}"
                            )
                            cover_generated = False

                # 如果封面生成失败，跳过该文章
                if not cover_generated:
                    logger.warning(f"《{title}》因封面生成失败，已跳过发布")
                    continue

            try:
                publisher.publish(
                    title, content_html, cover_path=cover_path, use_cover=True
                )
                logger.info(f"《{title}》发布完成。")
                # 发布成功后删除封面图片
                if cover_path and os.path.exists(cover_path):
                    try:
                        os.remove(cover_path)
                        logger.info(f"已删除临时封面图片：{cover_path}")
                    except Exception as exc:
                        logger.warning(f"删除封面图片失败：{exc}")
            except Exception as exc:
                logger.error(f"发布失败：{exc}")
                # 即使发布失败，也尝试删除图片
                if cover_path and os.path.exists(cover_path):
                    try:
                        os.remove(cover_path)
                        logger.info(f"已删除临时封面图片：{cover_path}")
                    except Exception:
                        pass
            time.sleep(delay_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="使用 Selenium 将文章发布到今日头条。")
    parser.add_argument("--directory", default=DEFAULT_ARTICLE_DIR, help="文章目录")
    parser.add_argument(
        "--cookies",
        default="cookies/toutiao.json",
        help="包含今日头条 Cookie 的 JSON 文件路径",
    )
    parser.add_argument("--limit", type=int, default=None, help="限定发布数量")
    parser.add_argument("--delay", type=float, default=8.0, help="每次发布后的等待秒数")
    parser.add_argument("--headless", action="store_true", help="启用无头浏览器")
    parser.add_argument(
        "--cover-mode",
        choices=["none", "generate"],
        default="generate",
        help="封面处理方式：none 不上传，generate 自动生成上传",
    )
    parser.add_argument(
        "--cover-style",
        type=str,
        default=None,
        help="封面风格编号（参考混元文生图轻量版 Style 参数）",
    )
    parser.add_argument(
        "--cover-resolution",
        type=str,
        default=None,
        help="封面分辨率，如 1024:1024",
    )
    parser.add_argument(
        "--cover-negative",
        type=str,
        default="",
        help="封面反向提示词（NegativePrompt）",
    )
    parser.add_argument(
        "--cover-logo",
        type=int,
        default=0,
        help="封面是否加水印：1 加，0 不加，不填使用配置默认值",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    publish_directory(
        directory=args.directory,
        cookie_file=args.cookies,
        limit=args.limit,
        delay_seconds=args.delay,
        headless=args.headless,
        cover_mode=args.cover_mode,
        cover_style=args.cover_style,
        cover_resolution=args.cover_resolution,
        cover_negative_prompt=args.cover_negative,
        cover_logo_add=args.cover_logo,
    )


if __name__ == "__main__":
    main()
