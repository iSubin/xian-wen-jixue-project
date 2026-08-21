from __future__ import annotations

import html as html_lib
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
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
    raw_html: str = ""
    images: list[CapturedImage] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class WechatAccountIdentity:
    biz: str | None
    account_name: str | None
    appmsg_token: str | None = None


@dataclass
class WechatHistoryArticle:
    source_url: str
    title: str
    digest: str | None
    publish_time: str | None
    cover_url: str | None
    item_index: int


@dataclass
class WechatAccountHistory:
    account_name: str
    source_url: str
    biz: str | None
    items: list[WechatHistoryArticle] = field(default_factory=list)
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


def _decode_js_string(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        text = json.loads(f'"{text}"')
    except Exception:
        text = text.replace("\\/", "/")
    return html_lib.unescape(str(text)).strip()


def _extract_js_string(html: str, name: str) -> str | None:
    patterns = [
        rf"(?<![\w$-])(?:var\s+)?{re.escape(name)}\s*=\s*(['\"])(.*?)\1",
        rf"(?<![\w$-]){re.escape(name)}\s*:\s*(['\"])(.*?)\1",
    ]
    for pattern in patterns:
        match = re.search(pattern, html or "", re.DOTALL)
        if match:
            value = _decode_js_string(match.group(2))
            return value or None
    return None


def _extract_query_value(url: str, key: str) -> str | None:
    parsed = urlparse(str(url or ""))
    query = parsed.query or ""
    match = re.search(rf"(?:^|&){re.escape(key)}=([^&]+)", query)
    return html_lib.unescape(match.group(1)).strip() if match else None


def extract_wechat_account_identity_from_html(url: str, html: str) -> WechatAccountIdentity:
    if not is_wechat_article_url(url):
        raise WechatArticleCaptureError("请输入有效的微信公众号文章链接")

    soup = BeautifulSoup(html or "", "lxml")
    biz = _extract_js_string(html, "biz") or _extract_query_value(url, "__biz")
    account_name = (
        _extract_js_string(html, "nickname")
        or _meta_content(soup, "og:article:author")
        or _meta_content(soup, "og:site_name")
    )
    appmsg_token = _extract_js_string(html, "appmsg_token")
    return WechatAccountIdentity(
        biz=biz,
        account_name=account_name,
        appmsg_token=appmsg_token,
    )


def _format_wechat_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        text = str(value or "").strip()
        return text or None
    if timestamp <= 0:
        return None
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def _normalize_wechat_history_url(value: Any) -> str:
    url = _decode_js_string(value)
    if not url:
        return ""
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("/"):
        return f"https://mp.weixin.qq.com{url}"
    return url


def _coerce_history_payload(payload: Any) -> dict:
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise WechatArticleCaptureError("公众号历史列表返回内容不是有效 JSON") from exc
    if not isinstance(payload, dict):
        raise WechatArticleCaptureError("公众号历史列表返回内容格式不正确")
    return payload


def parse_wechat_history_payload(payload: Any) -> list[WechatHistoryArticle]:
    payload_dict = _coerce_history_payload(payload)
    ret = payload_dict.get("ret")
    if ret not in (None, 0, "0"):
        raise WechatArticleCaptureError(f"公众号历史列表接口返回异常：{ret}")

    general_msg_list = payload_dict.get("general_msg_list")
    if isinstance(general_msg_list, str):
        try:
            general_msg_list = json.loads(general_msg_list)
        except json.JSONDecodeError as exc:
            raise WechatArticleCaptureError("公众号历史列表内容解析失败") from exc

    raw_messages = []
    if isinstance(general_msg_list, dict):
        raw_messages = list(general_msg_list.get("list") or [])
    elif isinstance(payload_dict.get("app_msg_list"), list):
        raw_messages = list(payload_dict.get("app_msg_list") or [])

    items: list[WechatHistoryArticle] = []
    seen_urls: set[str] = set()

    def add_article(raw_article: dict, publish_time: str | None) -> None:
        title = str(raw_article.get("title") or "").strip()
        source_url = _normalize_wechat_history_url(
            raw_article.get("content_url") or raw_article.get("link") or raw_article.get("url")
        )
        if not title or not source_url or source_url in seen_urls:
            return
        seen_urls.add(source_url)
        items.append(
            WechatHistoryArticle(
                source_url=source_url,
                title=title,
                digest=str(raw_article.get("digest") or "").strip() or None,
                publish_time=publish_time,
                cover_url=_normalize_wechat_history_url(raw_article.get("cover") or raw_article.get("cover_url")) or None,
                item_index=len(items),
            )
        )

    for message in raw_messages:
        if not isinstance(message, dict):
            continue
        publish_time = _format_wechat_timestamp(
            (message.get("comm_msg_info") or {}).get("datetime")
            or message.get("create_time")
            or message.get("datetime")
        )
        app_msg = message.get("app_msg_ext_info") if "app_msg_ext_info" in message else message
        if not isinstance(app_msg, dict):
            continue
        add_article(app_msg, publish_time)
        for sub_item in app_msg.get("multi_app_msg_item_list") or []:
            if isinstance(sub_item, dict):
                add_article(sub_item, publish_time)

    return items


def build_wechat_account_history_from_payload(
    source_url: str,
    html: str,
    payload: Any,
    *,
    limit: int = 30,
) -> WechatAccountHistory:
    identity = extract_wechat_account_identity_from_html(source_url, html)
    items = parse_wechat_history_payload(payload)
    if limit > 0:
        items = items[:limit]
    if not items:
        raise WechatArticleCaptureError("未获取到公众号历史文章列表，请使用单篇公众号采集或稍后重试")

    account_name = identity.account_name or "微信公众号"
    return WechatAccountHistory(
        account_name=account_name,
        source_url=source_url,
        biz=identity.biz,
        items=items,
        metadata={
            "account": account_name,
            "biz": identity.biz,
            "source_url": source_url,
            "item_count": len(items),
        },
    )


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


def _download_images(
    content_div,
    images: list[CapturedImage],
    output_dir: str | None,
    markdown_image_base: str | None = None,
) -> None:
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
            if markdown_image_base:
                markdown_path = f"{markdown_image_base.rstrip('/')}/{markdown_path}"
            img["src"] = markdown_path
            img.attrs.pop("data-src", None)
            image_record.local_path = local_path
            image_record.markdown_path = markdown_path
            image_record.status = "downloaded"
        except Exception:
            image_record.status = "failed"


def _sanitize_cookie_piece(value: Any) -> str:
    return str(value or "").strip().replace("\r", "").replace("\n", "").replace(";", "")


def _cookie_items_to_header(items: list[tuple[str, str]]) -> str:
    pairs: list[str] = []
    seen: set[str] = set()
    for name, value in items:
        clean_name = _sanitize_cookie_piece(name)
        clean_value = _sanitize_cookie_piece(value)
        if not clean_name or not clean_value or clean_name in seen:
            continue
        seen.add(clean_name)
        pairs.append(f"{clean_name}={clean_value}")
    return "; ".join(pairs)


def _read_wechat_cookie_from_browser_cookie3() -> tuple[str, str]:
    try:
        import browser_cookie3  # type: ignore
    except Exception:
        return "", ""

    browsers_to_try = [
        ("chrome", "Google Chrome"),
        ("edge", "Microsoft Edge"),
        ("firefox", "Firefox"),
        ("chromium", "Chromium"),
        ("brave", "Brave"),
    ]
    for browser_key, browser_name in browsers_to_try:
        try:
            browser_func = getattr(browser_cookie3, browser_key, None)
            if browser_func is None:
                continue
            cookies = browser_func(domain_name="mp.weixin.qq.com")
            cookie_header = _cookie_items_to_header(
                [(cookie.name, cookie.value) for cookie in cookies if cookie.value]
            )
            if cookie_header:
                return cookie_header, browser_name
        except Exception:
            continue
    return "", ""


def _read_wechat_cookie_from_macos_chrome() -> tuple[str, str]:
    if sys.platform != "darwin":
        return "", ""

    try:
        from .transcriber.settings_manager import (
            _decrypt_macos_chrome_v10_cookie,
            _get_macos_chrome_safe_storage_password,
            _iter_macos_chrome_cookie_files,
        )
    except Exception:
        return "", ""

    try:
        password = _get_macos_chrome_safe_storage_password()
    except Exception:
        return "", ""

    for cookie_file in _iter_macos_chrome_cookie_files():
        temp_path = ""
        try:
            fd, temp_path = tempfile.mkstemp(prefix="shengwen-wechat-cookies-", suffix=".sqlite")
            os.close(fd)
            shutil.copy2(cookie_file, temp_path)
            with sqlite3.connect(temp_path) as con:
                rows = con.execute(
                    """
                    SELECT host_key, name, value, encrypted_value
                    FROM cookies
                    WHERE host_key LIKE ?
                    ORDER BY length(host_key) DESC, expires_utc DESC
                    """,
                    ("%mp.weixin.qq.com%",),
                ).fetchall()

            cookie_items: list[tuple[str, str]] = []
            for host_key, name, value, encrypted_value in rows:
                cookie_value = _decrypt_macos_chrome_v10_cookie(host_key, value, encrypted_value, password)
                if cookie_value:
                    cookie_items.append((name, cookie_value))
            cookie_header = _cookie_items_to_header(cookie_items)
            if cookie_header:
                return cookie_header, "Google Chrome"
        except Exception:
            continue
        finally:
            if temp_path:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
    return "", ""


def read_wechat_cookie_header_from_browser() -> tuple[str, str]:
    cookie_header, browser_name = _read_wechat_cookie_from_browser_cookie3()
    if cookie_header:
        return cookie_header, browser_name
    return _read_wechat_cookie_from_macos_chrome()


def _build_wechat_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://mp.weixin.qq.com/",
    })
    cookie_header, _browser_name = read_wechat_cookie_header_from_browser()
    if cookie_header:
        session.headers.update({"Cookie": cookie_header})
    return session


def capture_wechat_article_from_html(
    url: str,
    html: str,
    *,
    output_dir: str | None = None,
    download_images: bool = True,
    markdown_image_base: str | None = None,
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
        _download_images(content_div, images, output_dir, markdown_image_base=markdown_image_base)

    markdown = html_to_markdown(str(content_div), heading_style="ATX").strip()
    if not markdown:
        raise WechatArticleCaptureError("文章正文为空，无法生成笔记")

    plain_text = BeautifulSoup(str(content_div), "lxml").get_text("\n", strip=True)
    metadata = {
        "author": author,
        "account": author,
        "biz": _extract_js_string(html, "biz") or _extract_query_value(url, "__biz"),
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
        raw_html=html,
        images=images,
        metadata=metadata,
    )


def capture_wechat_article(
    url: str,
    *,
    output_dir: str | None = None,
    markdown_image_base: str | None = None,
) -> CapturedArticle:
    if not is_wechat_article_url(url):
        raise WechatArticleCaptureError("请输入有效的微信公众号文章链接")

    session = _build_wechat_session()
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise WechatArticleCaptureError("公众号文章下载失败，请确认链接可访问后重试") from exc

    return capture_wechat_article_from_html(
        url,
        response.text,
        output_dir=output_dir,
        markdown_image_base=markdown_image_base,
    )


def preview_wechat_account_history(url: str, *, limit: int = 30) -> WechatAccountHistory:
    if not is_wechat_article_url(url):
        raise WechatArticleCaptureError("请输入有效的微信公众号文章链接")

    session = _build_wechat_session()
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise WechatArticleCaptureError("公众号文章下载失败，请确认链接可访问后重试") from exc

    html = response.text
    identity = extract_wechat_account_identity_from_html(url, html)
    if not identity.biz or not identity.appmsg_token:
        raise WechatArticleCaptureError(
            "当前文章正文可访问，但微信没有向桌面网页暴露公众号历史列表授权信息。"
            "请继续使用单篇公众号采集；如需导入历史文章，需要从微信客户端或已授权的公众号历史页提供可访问会话。"
        )

    try:
        history_response = session.get(
            "https://mp.weixin.qq.com/mp/profile_ext",
            params={
                "action": "getmsg",
                "__biz": identity.biz,
                "f": "json",
                "offset": "0",
                "count": str(limit),
                "is_ok": "1",
                "scene": "124",
                "uin": "777",
                "key": "777",
                "pass_ticket": "",
                "wxtoken": "",
                "appmsg_token": identity.appmsg_token,
                "x5": "0",
            },
            headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Referer": url,
            },
            timeout=30,
        )
        history_response.raise_for_status()
        payload = history_response.json()
    except requests.RequestException as exc:
        raise WechatArticleCaptureError("公众号历史列表获取失败，请确认当前文章可访问后重试") from exc
    except ValueError as exc:
        raise WechatArticleCaptureError("公众号历史列表返回内容不是有效 JSON") from exc

    return build_wechat_account_history_from_payload(url, html, payload, limit=limit)
