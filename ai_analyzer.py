import json
import os
import time
from typing import List, Dict, Any, Optional, Set, Tuple

import requests

from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_API_URL,
    DEEPSEEK_MODEL,
    ARTICLE_GENERATION_PROMPT_TEMPLATE,
)
from utils import logger, save_article_to_file

# 已发布文章记录文件
PUBLISHED_RECORDS_FILE = "published_articles.json"


def call_deepseek_api(prompt: str, max_tokens=4096, temperature=0.7) -> str:
    """
    调用 DeepSeek API 生成文本。
    :param prompt: 用户提示词
    :param max_tokens: 生成文本的最大长度（默认4096，足够生成1200-1500字的文章）
    :param temperature: 控制生成文本的随机性
    :return: 生成的文本
    """
    logger.info("DeepSeek API Running...")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    }

    data = {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        response = requests.post(
            DEEPSEEK_API_URL, headers=headers, data=json.dumps(data), timeout=60
        )
        response.raise_for_status()
        result = response.json()

        if "choices" in result and len(result["choices"]) > 0:
            generated_content = result["choices"][0]["message"]["content"].strip()
            logger.info("DeepSeek API success。")
            return generated_content
        else:
            logger.error(f"DeepSeek API 返回格式不正确: {result}")
            return ""

    except requests.exceptions.RequestException as e:
        logger.error(f"DeepSeek API fail: {e}")
        if e.response is not None:
            logger.error(f"API 错误详情: {e.response.text}")
        return ""


def extract_title_and_content(article_text: str) -> Tuple[str, str]:
    """
    从生成的文章中提取标题和正文内容。
    文章格式应为：标题：xxx\n\n正文内容...

    :param article_text: 完整的文章文本
    :return: (标题, 正文内容) 元组
    """
    lines = article_text.strip().split("\n")

    # 查找标题行（以"标题："开头）
    title = None
    content_start_idx = 0

    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith("标题："):
            title = line.replace("标题：", "").strip()
            content_start_idx = i + 1
            break
        elif line.startswith("标题:"):
            title = line.replace("标题:", "").strip()
            content_start_idx = i + 1
            break

    # 如果没有找到标题，尝试使用第一行作为标题
    if not title and lines:
        # 如果第一行看起来像标题（长度适中，没有太多标点）
        first_line = lines[0].strip()
        if len(first_line) > 5 and len(first_line) < 50:
            title = first_line
            content_start_idx = 1

    # 如果还是没有标题，使用默认格式
    if not title:
        # 尝试从正文第一段提取关键词作为标题
        if lines:
            title = lines[0].strip()[:30]  # 使用第一行前30字作为标题
            content_start_idx = 0

    # 提取正文内容
    content_lines = lines[content_start_idx:]
    # 跳过空行
    while content_lines and not content_lines[0].strip():
        content_lines = content_lines[1:]

    content = "\n".join(content_lines).strip()

    return title, content


def generate_article_draft(
    topic: str, source_url: Optional[str] = None
) -> Tuple[str, str]:
    """
    根据话题生成文章初稿，返回标题和正文。
    :param topic: 热点话题
    :param source_url: 参考链接（可选）
    :return: (标题, 正文内容) 元组
    """
    prompt = ARTICLE_GENERATION_PROMPT_TEMPLATE.format(topic=topic)
    if source_url:
        prompt += (
            "\n参考链接：{url}\n"
            "请结合该链接可能涉及的事实背景，输出一篇具有洞察力的文章。"
        ).format(url=source_url)

    full_article = call_deepseek_api(prompt)
    title, content = extract_title_and_content(full_article)

    return title, content


def load_published_records(records_file: str = PUBLISHED_RECORDS_FILE) -> Set[str]:
    """
    加载已发布文章的记录（使用URL作为唯一标识）。

    :param records_file: 记录文件路径
    :return: 已发布文章的URL集合
    """
    if not os.path.exists(records_file):
        return set()

    try:
        with open(records_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return set(data)
        elif isinstance(data, dict) and "urls" in data:
            return set(data["urls"])
        else:
            logger.warning(f"已发布记录文件格式不正确: {records_file}")
            return set()
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(f"读取已发布记录失败: {exc}")
        return set()


def save_published_record(url: str, records_file: str = PUBLISHED_RECORDS_FILE) -> None:
    """
    保存已发布文章的记录。

    :param url: 文章URL
    :param records_file: 记录文件路径
    """
    published = load_published_records(records_file)
    published.add(url)

    try:
        with open(records_file, "w", encoding="utf-8") as f:
            json.dump(list(published), f, ensure_ascii=False, indent=2)
        logger.debug(f"已记录已发布文章: {url}")
    except OSError as exc:
        logger.warning(f"保存已发布记录失败: {exc}")


def load_hot_searches(json_path: str) -> List[Dict[str, Any]]:
    """
    读取热搜 JSON 文件。
    :param json_path: JSON 文件路径
    :return: 热搜数据列表
    """
    if not os.path.exists(json_path):
        logger.error(f"未找到热搜数据文件: {json_path}")
        return []

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            logger.error("热搜文件格式不正确，预期为列表。")
            return []
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.error(f"读取热搜文件失败: {exc}")
        return []


def process_hot_searches(
    json_path: str = "filtered_hot_searches.json",
    limit: Optional[int] = None,
    delay_seconds: float = 1.5,
    publisher=None,
    publish_config: Optional[Dict[str, Any]] = None,
    skip_published: bool = False,
) -> None:
    """
    依次处理热搜话题并生成文章，可选择立即发布。
    :param json_path: 热搜数据文件
    :param limit: 限制处理的话题数量
    :param delay_seconds: 调用 API 之间的间隔，避免触发限流
    :param publisher: ToutiaoPublisher 实例，如果提供则每生成一篇文章就发布
    :param publish_config: 发布配置字典，包含 cover_mode, cover_style 等参数
    :param skip_published: 是否跳过已发布的文章（用于恢复中断的任务）
    """
    hot_searches = load_hot_searches(json_path)
    if not hot_searches:
        logger.error("热搜数据为空，无法生成文章。")
        return

    # 如果需要跳过已发布的文章，加载已发布记录
    published_urls = set()
    if skip_published:
        published_urls = load_published_records()
        logger.info(f"已加载 {len(published_urls)} 条已发布记录，将跳过这些文章。")

    # 过滤已发布的文章
    if skip_published and published_urls:
        original_count = len(hot_searches)
        hot_searches = [
            item for item in hot_searches if item.get("url") not in published_urls
        ]
        skipped_count = original_count - len(hot_searches)
        if skipped_count > 0:
            logger.info(
                f"已跳过 {skipped_count} 篇已发布的文章，剩余 {len(hot_searches)} 篇待处理。"
            )

    if limit:
        hot_searches = hot_searches[:limit]

    if not hot_searches:
        logger.info("没有待处理的文章，所有文章都已发布。")
        return

    logger.info(f"开始处理 {len(hot_searches)} 条热搜话题。")

    # 如果需要发布，导入相关模块
    if publisher:
        from image_generator import generate_cover_image
        from config import (
            IMAGE_DEFAULT_STYLE,
            IMAGE_DEFAULT_RESOLUTION,
            IMAGE_DEFAULT_LOGO_ADD,
        )
        from publisher import markdown_to_html
        import os

        publish_config = publish_config or {}
        cover_mode = publish_config.get("cover_mode", "generate")
        cover_style = publish_config.get("cover_style")
        cover_resolution = publish_config.get("cover_resolution")
        cover_negative_prompt = publish_config.get("cover_negative_prompt", "")
        cover_logo_add = publish_config.get("cover_logo_add")
        publish_delay = publish_config.get("delay_seconds", 8.0)

    for idx, item in enumerate(hot_searches, start=1):
        topic = item.get("title")
        url = item.get("url")

        if not topic or not url:
            logger.warning(f"第 {idx} 条数据缺少必要信息，已跳过: {item}")
            continue

        logger.info(f"[{idx}/{len(hot_searches)}] 正在生成话题文章: {topic}")
        result = generate_article_draft(topic, url)
        if not result or not result[1]:
            logger.warning(f"话题《{topic}》生成失败，跳过保存。")
            continue

        title, article_content = result
        if not title:
            title = topic  # 如果提取标题失败，使用原话题作为标题

        logger.info(f"生成标题: {title}")

        # 如果需要发布，立即发布
        if publisher:
            try:
                content_html = markdown_to_html(article_content)
                cover_path = None

                # 生成封面（必须成功才能发布）
                if cover_mode == "generate":
                    max_retries = 3
                    cover_generated = False
                    for attempt in range(1, max_retries + 1):
                        try:
                            logger.info(
                                f"尝试生成封面（第 {attempt}/{max_retries} 次）..."
                            )
                            cover_path = generate_cover_image(
                                title=title,
                                article_text=article_content[:100],
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
                                time.sleep(2)
                            else:
                                logger.error(
                                    f"封面生成失败（已重试 {max_retries} 次），跳过该文章：{title}"
                                )
                                cover_generated = False

                    # 如果封面生成失败，跳过该文章
                    if not cover_generated:
                        logger.warning(f"《{title}》因封面生成失败，已跳过发布")
                        continue

                # 发布文章（必须有封面）
                publisher.publish(
                    title, content_html, cover_path=cover_path, use_cover=True
                )
                logger.info(f"《{title}》发布完成。")

                # 记录已发布的文章（使用URL作为唯一标识）
                # 总是记录，以便 mode publish 模式下可以跳过已发布的文章
                save_published_record(url)

                # 删除封面图片
                if cover_path and os.path.exists(cover_path):
                    try:
                        os.remove(cover_path)
                        logger.info(f"已删除临时封面图片：{cover_path}")
                    except Exception as exc:
                        logger.warning(f"删除封面图片失败：{exc}")

                # 等待15分钟（900秒）后再处理下一篇文章
                wait_minutes = publish_delay / 60
                logger.info(
                    f"《{title}》发布完成，等待 {wait_minutes:.1f} 分钟后处理下一篇文章..."
                )
                time.sleep(publish_delay)
            except Exception as exc:
                logger.error(f"发布文章失败：{exc}")
        else:
            # 不需要发布，只保存文件
            save_article_to_file(
                topic=topic, article_content=article_content, title=title
            )
            time.sleep(delay_seconds)

    logger.info("全部热搜话题处理完毕。")


# --- 使用示例 ---
if __name__ == "__main__":
    process_hot_searches()
