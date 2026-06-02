from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as html_to_markdown


class WechatArticleCaptureError(RuntimeError):
    pass


@dataclass
class CapturedImage:
    original_url: str
    local_path: str | None = None
    markdown_path: str | None = None
    status: str = "skipped"


@dataclass
class CapturedArticle:
    source_type: str
    source_url: str
    title: str
    author: str | None
    publish_time: str | None
    description: str | None
    raw_markdown: str
    plain_text: str
    images: list[CapturedImage] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def is_wechat_article_url(url: str) -> bool:
    try:
        parsed = urlparse(str(url or "").strip())
    except Exception:
        return False
    return parsed.scheme == "https" and (parsed.hostname or "").lower() == "mp.weixin.qq.com"


def _meta_content(soup: BeautifulSoup, property_name: str) -> str | None:
    tag = soup.find("meta", property=property_name)
    value = tag.get("content") if tag else None
    value = str(value or "").strip()
    return value or None


def _extract_create_time(html: str) -> str | None:
    match = re.search(r"var\s+createTime\s*=\s*['\"]([^'\"]+)['\"]", html or "")
    return match.group(1).strip() if match else None


def _collect_images(content_div) -> list[CapturedImage]:
    images: list[CapturedImage] = []
    for img in content_div.find_all("img"):
        src = str(img.get("data-src") or img.get("src") or "").strip()
        if not src or src.startswith("data:"):
            continue
        images.append(CapturedImage(original_url=src, status="skipped"))
    return images


def _image_extension(url: str, content_type: str) -> str:
    content_type = (content_type or "").lower()
    if "png" in content_type:
        return ".png"
    if "webp" in content_type:
        return ".webp"
    if "gif" in content_type:
        return ".gif"

    path = urlparse(url).path.lower()
    for ext in (".png", ".webp", ".gif", ".jpeg", ".jpg"):
        if ext in path:
            return ".jpg" if ext == ".jpeg" else ext
    return ".jpg"


def _download_images(content_div, images: list[CapturedImage], output_dir: str | None) -> None:
    if not output_dir:
        return
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    session = requests.Session()
    session.headers.update({"Referer": "https://mp.weixin.qq.com/"})

    index = 0
    for img in content_div.find_all("img"):
        src = str(img.get("data-src") or img.get("src") or "").strip()
        if not src or src.startswith("data:"):
            continue
        index += 1
        image_record = images[index - 1]
        try:
            response = session.get(src, timeout=20, stream=True)
            response.raise_for_status()
            filename = f"wechat_{index:02d}{_image_extension(src, response.headers.get('Content-Type', ''))}"
            local_path = os.path.join(images_dir, filename)
            with open(local_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            markdown_path = f"images/{filename}"
            img["src"] = markdown_path
            img.attrs.pop("data-src", None)
            image_record.local_path = local_path
            image_record.markdown_path = markdown_path
            image_record.status = "downloaded"
        except Exception:
            image_record.status = "failed"


def capture_wechat_article_from_html(
    url: str,
    html: str,
    *,
    output_dir: str | None = None,
    download_images: bool = True,
) -> CapturedArticle:
    if not is_wechat_article_url(url):
        raise WechatArticleCaptureError("请输入有效的微信公众号文章链接")

    soup = BeautifulSoup(html or "", "lxml")
    title = _meta_content(soup, "og:title") or "未知标题"
    author = _meta_content(soup, "og:article:author")
    description = _meta_content(soup, "og:description")
    publish_time = _meta_content(soup, "og:article:published_time") or _extract_create_time(html)

    content_div = soup.find("div", id="js_content")
    if not content_div:
        raise WechatArticleCaptureError("无法找到文章正文，文章可能需要登录、已删除、私密或被微信限制")

    images = _collect_images(content_div)
    if download_images:
        _download_images(content_div, images, output_dir)

    markdown = html_to_markdown(str(content_div), heading_style="ATX").strip()
    if not markdown:
        raise WechatArticleCaptureError("文章正文为空，无法生成笔记")

    plain_text = BeautifulSoup(str(content_div), "lxml").get_text("\n", strip=True)
    metadata = {
        "author": author,
        "account": author,
        "publish_time": publish_time,
        "description": description,
        "image_count": len(images),
    }

    return CapturedArticle(
        source_type="wechat_article",
        source_url=url,
        title=title,
        author=author,
        publish_time=publish_time,
        description=description,
        raw_markdown=markdown,
        plain_text=plain_text,
        images=images,
        metadata=metadata,
    )


def capture_wechat_article(url: str, *, output_dir: str | None = None) -> CapturedArticle:
    if not is_wechat_article_url(url):
        raise WechatArticleCaptureError("请输入有效的微信公众号文章链接")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://mp.weixin.qq.com/",
    })
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise WechatArticleCaptureError("公众号文章下载失败，请确认链接可访问后重试") from exc

    return capture_wechat_article_from_html(url, response.text, output_dir=output_dir)
