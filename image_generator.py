import hashlib
import hmac
import json
import os
import textwrap
import time
from datetime import datetime

import requests

from config import (
    IMAGE_API_ENDPOINT,
    IMAGE_API_REGION,
    IMAGE_API_SECRET_ID,
    IMAGE_API_SECRET_KEY,
    IMAGE_DEFAULT_LOGO_ADD,
    IMAGE_DEFAULT_RESOLUTION,
    IMAGE_DEFAULT_STYLE,
    IMAGE_MODEL,
    IMAGE_OUTPUT_DIR,
    IMAGE_PROMPT_TEMPLATE,
)
from utils import ensure_directory_exists, logger


def build_image_prompt(title: str, article_text: str) -> str:
    """
    根据标题与正文生成图像提示词。
    """
    summary = textwrap.shorten(
        article_text.replace("\n", " "), width=400, placeholder="…"
    )
    prompt = IMAGE_PROMPT_TEMPLATE.format(title=title.strip(), summary=summary.strip())
    logger.debug(f"图像 Prompt：{prompt}")
    return prompt


def call_hunyuan_image_api(
    prompt: str,
    negative_prompt: str = "",
    style: str = IMAGE_DEFAULT_STYLE,
    resolution: str = IMAGE_DEFAULT_RESOLUTION,
    logo_add: int = IMAGE_DEFAULT_LOGO_ADD,
) -> bytes:
    """
    调用腾讯混元 TextToImageLite API，返回图片二进制。
    """
    if "你的" in IMAGE_API_SECRET_ID or "你的" in IMAGE_API_SECRET_KEY:
        raise RuntimeError("请在 config.py 中配置混元 API 的 SecretId/SecretKey。")

    payload = {
        "Prompt": prompt,
        "RspImgType": "url",
    }
    if negative_prompt:
        payload["NegativePrompt"] = negative_prompt
    if style:
        payload["Style"] = style
    if resolution:
        payload["Resolution"] = resolution
    if logo_add is not None:
        payload["LogoAdd"] = logo_add

    body = json.dumps(payload)
    timestamp = int(time.time())
    date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
    service = "hunyuan"
    host = IMAGE_API_ENDPOINT
    content_type = "application/json; charset=utf-8"

    hashed_body = hashlib.sha256(body.encode("utf-8")).hexdigest()
    canonical_request = (
        "POST\n/\n\n"
        f"content-type:{content_type}\n"
        f"host:{host}\n\n"
        "content-type;host\n"
        f"{hashed_body}"
    )
    hashed_canonical = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    credential_scope = f"{date}/{service}/tc3_request"
    string_to_sign = (
        "TC3-HMAC-SHA256\n"
        f"{timestamp}\n"
        f"{credential_scope}\n"
        f"{hashed_canonical}"
    )

    secret_date = hmac.new(
        ("TC3" + IMAGE_API_SECRET_KEY).encode("utf-8"),
        date.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    secret_service = hmac.new(
        secret_date, service.encode("utf-8"), hashlib.sha256
    ).digest()
    secret_signing = hmac.new(
        secret_service, "tc3_request".encode("utf-8"), hashlib.sha256
    ).digest()
    signature = hmac.new(
        secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    authorization = (
        "TC3-HMAC-SHA256 "
        f"Credential={IMAGE_API_SECRET_ID}/{credential_scope}, "
        "SignedHeaders=content-type;host, "
        f"Signature={signature}"
    )

    headers = {
        "Authorization": authorization,
        "Content-Type": content_type,
        "Host": host,
        "X-TC-Timestamp": str(timestamp),
        "X-TC-Action": "TextToImageLite",
        "X-TC-Version": "2023-09-01",
        "X-TC-Region": IMAGE_API_REGION,
    }

    response = requests.post(
        f"https://{host}",
        headers=headers,
        data=body.encode("utf-8"),
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    image_url = data.get("Response", {}).get("ResultImage")
    if not image_url:
        raise RuntimeError(f"混元返回异常: {data}")

    image_resp = requests.get(image_url, timeout=120)
    image_resp.raise_for_status()
    return image_resp.content


def generate_cover_image(
    title: str,
    article_text: str,
    output_dir: str = IMAGE_OUTPUT_DIR,
    *,
    negative_prompt: str = "",
    style: str = IMAGE_DEFAULT_STYLE,
    resolution: str = IMAGE_DEFAULT_RESOLUTION,
    logo_add: int = IMAGE_DEFAULT_LOGO_ADD,
) -> str:
    """
    根据标题与正文生成配图，并保存到本地，返回文件路径。
    """
    ensure_directory_exists(output_dir)
    prompt = build_image_prompt(title, article_text)

    image_bytes = call_hunyuan_image_api(
        prompt,
        negative_prompt=negative_prompt,
        style=style,
        resolution=resolution,
        logo_add=logo_add,
    )

    safe_title = (
        "".join(c for c in title if c.isalnum() or c in (" ", "-", "_"))
        .strip()
        .replace(" ", "_")
    )
    filename = (
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_title or 'article'}.png"
    )
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "wb") as f:
        f.write(image_bytes)

    logger.info(f"文章《{title}》配图已保存：{filepath}")
    return filepath


if __name__ == "__main__":
    sample_title = "杭州宣布取消灵隐寺门票"
    sample_body = "杭州正式宣布取消灵隐寺门票，引发网友热议..."
    try:
        image_path = generate_cover_image(sample_title, sample_body)
        print(f"示例图片已生成：{image_path}")
    except Exception as err:
        print(f"生成失败：{err}")
