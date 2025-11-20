#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主程序：整合热点爬取、文章生成和发布功能
支持三种模式：
1. 只爬取过滤热点
2. 只写文发文（从已有热搜数据生成并立即发布，每生成一篇就发布一篇）
3. 完整流程（爬取过滤 -> 生成并立即发布）
"""

import argparse
import sys

from ai_analyzer import process_hot_searches
from config import DEEPSEEK_API_KEY, OUTPUT_DIR
from hot_topic_finder import HotSearchCrawler
from publisher import ToutiaoPublisher, load_cookies
from utils import logger


def crawl_and_filter_hot_searches(
    max_count: int = 100,
    filter_political: bool = True,
    json_output: str = "filtered_hot_searches.json",
) -> bool:
    """
    爬取热点并过滤政治敏感内容。

    :param max_count: 最大爬取数量
    :param filter_political: 是否过滤政治敏感内容
    :param json_output: 输出JSON文件路径
    :return: 是否成功
    """
    logger.info("=" * 60)
    logger.info("步骤 1: 开始爬取热点话题...")
    logger.info("=" * 60)

    try:
        crawler = HotSearchCrawler(DEEPSEEK_API_KEY)

        # 获取所有热搜
        all_hot_searches = crawler.fetch_hot_searches(max_tokens=max_count)
        if not all_hot_searches:
            logger.error("没有获取到热搜数据，程序结束")
            return False

        # 过滤政治敏感内容
        if filter_political:
            logger.info("开始过滤政治敏感内容...")
            filtered_searches = crawler.filter_with_deepseek(all_hot_searches)
        else:
            filtered_searches = all_hot_searches

        if not filtered_searches:
            logger.error("所有话题都被过滤掉了，没有可保存的内容")
            return False

        # 保存结果
        crawler.save_results(
            filtered_searches, max_count=max_count, json_filename=json_output
        )
        logger.info(
            f"已保存 {len(filtered_searches)} 个过滤后的热搜话题到 {json_output}"
        )

        return True

    except Exception as exc:
        logger.error(f"爬取和过滤热点失败: {exc}", exc_info=True)
        return False


def generate_and_publish_articles(
    json_path: str = "filtered_hot_searches.json",
    cookie_file: str = "cookies/toutiao.json",
    limit: int = None,
    generate_delay: float = 1.5,
    publish_delay: float = 8.0,
    headless: bool = False,
    cover_mode: str = "generate",
    cover_style: str = None,
    cover_resolution: str = None,
    cover_negative_prompt: str = "",
    cover_logo_add: int = 0,
    skip_published: bool = False,
) -> bool:
    """
    生成文章并立即发布（每生成一篇就发布一篇，然后等待指定时间）。

    :param json_path: 热搜数据JSON文件路径
    :param cookie_file: Cookie文件路径
    :param limit: 限制处理的话题数量
    :param generate_delay: 生成文章时的API调用间隔
    :param publish_delay: 发布文章后的等待间隔（秒，默认900秒即15分钟）
    :param headless: 是否使用无头浏览器
    :param cover_mode: 封面模式（none/generate）
    :param cover_style: 封面风格
    :param cover_resolution: 封面分辨率
    :param cover_negative_prompt: 封面反向提示词
    :param cover_logo_add: 封面是否加水印
    :param skip_published: 是否跳过已发布的文章（用于恢复中断的任务）
    :return: 是否成功
    """
    logger.info("=" * 60)
    logger.info(
        f"开始生成文章并立即发布（每生成一篇就发布一篇，然后等待 {publish_delay/60:.1f} 分钟）..."
    )
    if skip_published:
        logger.info("将跳过已发布的文章，从未发布的开始继续处理。")
    logger.info("=" * 60)

    try:
        cookies = load_cookies(cookie_file)
        publish_config = {
            "cover_mode": cover_mode,
            "cover_style": cover_style,
            "cover_resolution": cover_resolution,
            "cover_negative_prompt": cover_negative_prompt,
            "cover_logo_add": cover_logo_add,
            "delay_seconds": publish_delay,
        }

        with ToutiaoPublisher(cookies=cookies, headless=headless) as publisher:
            # 只登录一次
            publisher.ensure_login()

            # 生成并发布文章
            process_hot_searches(
                json_path=json_path,
                limit=limit,
                delay_seconds=generate_delay,
                publisher=publisher,
                publish_config=publish_config,
                skip_published=skip_published,  # 根据参数决定是否跳过已发布的文章
            )

        logger.info("文章生成和发布完成")
        return True

    except Exception as exc:
        logger.error(f"生成和发布文章失败: {exc}", exc_info=True)
        return False


def publish_existing_articles(
    directory: str = None,
    cookie_file: str = "cookies/toutiao.json",
    limit: int = None,
    delay_seconds: float = 8.0,
    headless: bool = False,
    cover_mode: str = "generate",
    cover_style: str = None,
    cover_resolution: str = None,
    cover_negative_prompt: str = "",
    cover_logo_add: int = 0,
) -> bool:
    """
    发布已有的文章文件。

    :param directory: 文章目录
    :param cookie_file: Cookie文件路径
    :param limit: 限制发布数量
    :param delay_seconds: 发布间隔
    :param headless: 是否使用无头浏览器
    :param cover_mode: 封面模式（none/generate）
    :param cover_style: 封面风格
    :param cover_resolution: 封面分辨率
    :param cover_negative_prompt: 封面反向提示词
    :param cover_logo_add: 封面是否加水印
    :return: 是否成功
    """
    logger.info("=" * 60)
    logger.info("开始发布已有文章...")
    logger.info("=" * 60)

    if directory is None:
        directory = OUTPUT_DIR

    try:
        from publisher import publish_directory

        publish_directory(
            directory=directory,
            cookie_file=cookie_file,
            limit=limit,
            delay_seconds=delay_seconds,
            headless=headless,
            cover_mode=cover_mode,
            cover_style=cover_style,
            cover_resolution=cover_resolution,
            cover_negative_prompt=cover_negative_prompt,
            cover_logo_add=cover_logo_add,
        )
        logger.info("文章发布完成")
        return True

    except Exception as exc:
        logger.error(f"发布文章失败: {exc}", exc_info=True)
        return False


def main():
    """主函数：根据模式执行相应流程。"""
    parser = argparse.ArgumentParser(
        description="今日头条自动化发布系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 模式1：只爬取过滤热点
  python main.py --mode crawl

  # 模式2：只写文发文（从已有热搜数据生成并立即发布）
  python main.py --mode publish

  # 模式3：完整流程（爬取过滤 -> 生成并立即发布）
  python main.py --mode full
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["crawl", "publish", "full"],
        default="full",
        help="运行模式：crawl=只爬取过滤, publish=生成并立即发布, full=完整流程（默认：full）",
    )

    # 爬取参数
    parser.add_argument(
        "--crawl-limit",
        type=int,
        default=100,
        help="爬取热点的最大数量（默认：100）",
    )
    parser.add_argument(
        "--hot-searches-file",
        default="filtered_hot_searches.json",
        help="热搜数据JSON文件路径（默认：filtered_hot_searches.json）",
    )

    # 生成和发布参数
    parser.add_argument(
        "--generate-limit",
        type=int,
        default=None,
        help="限制生成的文章数量（默认：不限制）",
    )
    parser.add_argument(
        "--generate-delay",
        type=float,
        default=1.5,
        help="生成文章时的API调用间隔秒数（默认：1.5）",
    )
    parser.add_argument(
        "--publish-delay",
        type=float,
        default=900.0,
        help="发布文章时的间隔秒数（默认：900.0，即15分钟）",
    )
    parser.add_argument(
        "--article-dir",
        default=None,
        help=f"文章目录（默认：{OUTPUT_DIR}）",
    )
    parser.add_argument(
        "--cookies",
        default="cookies/toutiao.json",
        help="Cookie文件路径（默认：cookies/toutiao.json）",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="使用无头浏览器模式",
    )
    parser.add_argument(
        "--cover-mode",
        choices=["none", "generate"],
        default="generate",
        help="封面处理方式：none 不上传，generate 自动生成上传（默认：generate）",
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
        help="封面是否加水印：1 加，0 不加（默认：0）",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("今日头条自动化发布系统启动")
    logger.info(f"运行模式: {args.mode}")
    logger.info("=" * 60)

    success = True

    # 模式1：只爬取过滤
    if args.mode == "crawl":
        if not crawl_and_filter_hot_searches(
            max_count=args.crawl_limit, json_output=args.hot_searches_file
        ):
            success = False
            sys.exit(1)

    # 模式2：只写文发文（从已有热搜数据生成并立即发布）
    elif args.mode == "publish":
        if not generate_and_publish_articles(
            json_path=args.hot_searches_file,
            cookie_file=args.cookies,
            limit=args.generate_limit,
            generate_delay=args.generate_delay,
            publish_delay=args.publish_delay,
            headless=args.headless,
            cover_mode=args.cover_mode,
            cover_style=args.cover_style,
            cover_resolution=args.cover_resolution,
            cover_negative_prompt=args.cover_negative,
            cover_logo_add=args.cover_logo,
            skip_published=True,  # mode publish 跳过已发布的文章，从未发布的开始
        ):
            success = False
            logger.error("生成和发布文章失败，程序终止")
            sys.exit(1)

    # 模式3：完整流程
    elif args.mode == "full":
        # 步骤1：爬取和过滤热点
        if not crawl_and_filter_hot_searches(
            max_count=args.crawl_limit, json_output=args.hot_searches_file
        ):
            success = False
            logger.error("爬取和过滤热点失败，程序终止")
            sys.exit(1)

        # 步骤2：生成并立即发布文章（mode full 不跳过已发布的文章，因为热点是重新爬取的）
        if not generate_and_publish_articles(
            json_path=args.hot_searches_file,
            cookie_file=args.cookies,
            limit=args.generate_limit,
            generate_delay=args.generate_delay,
            publish_delay=args.publish_delay,
            headless=args.headless,
            cover_mode=args.cover_mode,
            cover_style=args.cover_style,
            cover_resolution=args.cover_resolution,
            cover_negative_prompt=args.cover_negative,
            cover_logo_add=args.cover_logo,
            skip_published=False,  # mode full 不跳过，因为热点是重新爬取的
        ):
            success = False
            logger.error("生成和发布文章失败，程序终止")
            sys.exit(1)

    if success:
        logger.info("=" * 60)
        logger.info("所有步骤执行完成！")
        logger.info("=" * 60)
    else:
        logger.warning("部分步骤执行失败，请检查日志")
        sys.exit(1)


if __name__ == "__main__":
    main()
