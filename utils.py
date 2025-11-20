import os
import logging
from datetime import datetime
from config import LOG_LEVEL, OUTPUT_DIR


def setup_logger():
    """设置日志记录器"""
    logger = logging.getLogger(__name__)
    logger.setLevel(LOG_LEVEL)

    # 避免重复添加 handler
    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # 控制台输出 handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 文件输出 handler
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_file = os.path.join(log_dir, f'app_{datetime.now().strftime("%Y%m%d")}.log')
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def ensure_directory_exists(directory):
    """确保目录存在，如果不存在则创建"""
    if not os.path.exists(directory):
        os.makedirs(directory)


def save_article_to_file(topic, article_content, title=None):
    """将生成的文章保存到本地文件"""
    ensure_directory_exists(OUTPUT_DIR)

    safe_topic = (
        "".join(c for c in topic if c.isalnum() or c in (" ", "-", "_"))
        .strip()
        .replace(" ", "_")
    )
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_topic}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        if title:
            f.write(f"# {title}\n\n")
        f.write(article_content)

    logger = setup_logger()
    logger.info(f"文章已保存到本地: {filepath}")
    return filepath


# 初始化logger
logger = setup_logger()
