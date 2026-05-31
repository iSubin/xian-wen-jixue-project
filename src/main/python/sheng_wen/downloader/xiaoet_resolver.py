from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from ..utils.logger import logger


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
XIAOET_QUALITY_ORDER = (
    "4k_hls",
    "2k_hls",
    "1080p_hls",
    "720p_hls",
    "480p_hls",
    "360p_hls",
)


class XiaoetResolveError(RuntimeError):
    pass


@dataclass(frozen=True)
class XiaoetResolvedVideo:
    media_url: str
    title: str
    source_url: str
    resource_id: str
    product_id: str
    quality: str


@dataclass(frozen=True)
class XiaoetVideoParams:
    app_id: str
    host: str
    base_url: str
    resource_id: str
    product_id: str


def is_xiaoet_video_url(video_url: str) -> bool:
    try:
        parsed = urlparse(str(video_url or ""))
    except Exception:
        return False
    host = (parsed.hostname or "").lower()
    if not _is_supported_xiaoet_host(host):
        return False
    return bool(_extract_resource_id(parsed.path) and _extract_product_id(parsed.query))


def resolve_xiaoet_video(video_url: str) -> XiaoetResolvedVideo:
    return XiaoetVideoResolver().resolve(video_url)


def _is_supported_xiaoet_host(host: str) -> bool:
    return host.endswith(".h5.xiaoeknow.com") or host.endswith(".xet.citv.cn")


def _extract_app_id(host: str) -> str:
    if host.endswith(".h5.xiaoeknow.com"):
        return host[: -len(".h5.xiaoeknow.com")]
    if host.endswith(".xet.citv.cn"):
        return host[: -len(".xet.citv.cn")]
    return ""


def _extract_resource_id(path: str) -> str:
    parts = [part for part in str(path or "").split("/") if part]
    if len(parts) >= 4 and parts[:3] == ["p", "course", "video"]:
        return parts[3].strip()
    return ""


def _first_query_value(values: Dict[str, list[str]], key: str) -> str:
    raw = values.get(key) or []
    return str(raw[0]).strip() if raw else ""


def _extract_product_id(query: str) -> str:
    values = parse_qs(query)
    return _first_query_value(values, "product_id") or _first_query_value(values, "course_id")


def _sanitize_cookie_header(value: str | None) -> str:
    return (value or "").strip().replace("\r", "").replace("\n", "")


def _domain_candidates_for_host(host: str) -> list[str]:
    candidates = [host]
    if host.endswith(".h5.xiaoeknow.com"):
        candidates.append("xiaoeknow.com")
    if host.endswith(".xet.citv.cn"):
        candidates.append("xet.citv.cn")
    return list(dict.fromkeys(candidates))


def _cookie_items_to_header(items: Iterable[tuple[str, str]]) -> str:
    pairs: list[str] = []
    seen: set[str] = set()
    for name, value in items:
        clean_name = str(name or "").strip()
        clean_value = _sanitize_cookie_header(str(value or ""))
        if not clean_name or not clean_value or clean_name in seen:
            continue
        seen.add(clean_name)
        pairs.append(f"{clean_name}={clean_value}")
    return "; ".join(pairs)


def _read_xiaoet_cookie_from_browser_cookie3(host: str) -> tuple[str, str]:
    try:
        import browser_cookie3  # type: ignore
    except Exception:
        return "", ""

    browsers_to_try = [
        ("edge", "Microsoft Edge"),
        ("chrome", "Google Chrome"),
        ("firefox", "Firefox"),
        ("chromium", "Chromium"),
        ("brave", "Brave"),
    ]
    for domain in _domain_candidates_for_host(host):
        for browser_key, browser_name in browsers_to_try:
            try:
                browser_func = getattr(browser_cookie3, browser_key, None)
                if browser_func is None:
                    continue
                cookies = browser_func(domain_name=domain)
                cookie_header = _cookie_items_to_header(
                    (cookie.name, cookie.value) for cookie in cookies if cookie.value
                )
                if cookie_header:
                    return cookie_header, browser_name
            except Exception:
                continue
    return "", ""


def _read_xiaoet_cookie_from_macos_chrome(host: str) -> tuple[str, str]:
    if sys.platform != "darwin":
        return "", ""

    try:
        from ..transcriber.settings_manager import (
            _decrypt_macos_chrome_v10_cookie,
            _get_macos_chrome_safe_storage_password,
            _iter_macos_chrome_cookie_files,
        )
    except Exception:
        return "", ""

    cookie_files = _iter_macos_chrome_cookie_files()
    if not cookie_files:
        return "", ""

    try:
        password = _get_macos_chrome_safe_storage_password()
    except Exception as e:
        logger.debug(f"[XiaoetResolver] 读取 Chrome Safe Storage 失败: {e}")
        return "", ""

    like_patterns = [f"%{domain}%" for domain in _domain_candidates_for_host(host)]
    for cookie_file in cookie_files:
        temp_path = ""
        try:
            fd, temp_path = tempfile.mkstemp(prefix="shengwen-xiaoet-cookies-", suffix=".sqlite")
            os.close(fd)
            shutil.copy2(cookie_file, temp_path)
            rows = []
            with sqlite3.connect(temp_path) as con:
                for pattern in like_patterns:
                    rows.extend(
                        con.execute(
                            """
                            SELECT host_key, name, value, encrypted_value
                            FROM cookies
                            WHERE host_key LIKE ?
                            ORDER BY length(host_key) DESC, expires_utc DESC
                            """,
                            (pattern,),
                        ).fetchall()
                    )

            cookie_items: list[tuple[str, str]] = []
            for host_key, name, value, encrypted_value in rows:
                cookie_value = _sanitize_cookie_header(
                    _decrypt_macos_chrome_v10_cookie(host_key, value, encrypted_value, password)
                )
                if cookie_value:
                    cookie_items.append((name, cookie_value))
            cookie_header = _cookie_items_to_header(cookie_items)
            if cookie_header:
                return cookie_header, "Google Chrome"
        except Exception as e:
            logger.debug(f"[XiaoetResolver] Chrome Cookie 兜底读取失败: {e}")
        finally:
            if temp_path:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
    return "", ""


def resolve_xiaoet_cookie_header(host: str) -> str:
    env_cookie = _sanitize_cookie_header(os.getenv("XIAOET_COOKIE") or os.getenv("XIAOETONG_COOKIE"))
    if env_cookie:
        return env_cookie

    cookie_header, browser_name = _read_xiaoet_cookie_from_browser_cookie3(host)
    if cookie_header:
        logger.info(f"[XiaoetResolver] 已从 {browser_name} 读取小鹅通 Cookie")
        return cookie_header

    cookie_header, browser_name = _read_xiaoet_cookie_from_macos_chrome(host)
    if cookie_header:
        logger.info(f"[XiaoetResolver] 已通过 macOS {browser_name} 读取小鹅通 Cookie")
        return cookie_header

    return ""


class XiaoetVideoResolver:
    def __init__(self, cookie_provider: Callable[[str], str] | None = None):
        self.cookie_provider = cookie_provider or resolve_xiaoet_cookie_header

    def resolve(self, video_url: str) -> XiaoetResolvedVideo:
        params = self._extract_params(video_url)
        cookie_header = _sanitize_cookie_header(self.cookie_provider(params.host))
        if not cookie_header:
            raise XiaoetResolveError(
                "未找到小鹅通 Cookie。请先在 Chrome 登录并打开一次小鹅通视频页，"
                "或设置 XIAOET_COOKIE/XIAOETONG_COOKIE 后重试。"
            )

        common_headers = {
            "Cookie": cookie_header,
            "Referer": video_url,
            "Origin": params.base_url,
        }
        navigation = self._fetch_navigation(params, common_headers)
        user_id = str(navigation.get("user_id") or "").strip()
        if not user_id:
            raise XiaoetResolveError("小鹅通导航接口未返回 user_id。")

        video_info = self._fetch_video_info(params, common_headers)
        play_sign = str(video_info.get("play_sign") or "").strip()
        if not play_sign:
            raise XiaoetResolveError("小鹅通视频详情接口未返回 play_sign。")

        title = str(
            video_info.get("title")
            or video_info.get("resource_title")
            or video_info.get("video_name")
            or video_info.get("file_name")
            or "小鹅通视频"
        )
        play_list = self._fetch_play_list(params, user_id, play_sign, common_headers)
        media_url, quality = self._select_best_play_url(play_list)
        if not media_url:
            raise XiaoetResolveError("小鹅通播放接口未返回可用 HLS 地址。")

        return XiaoetResolvedVideo(
            media_url=media_url,
            title=title,
            source_url=video_url,
            resource_id=params.resource_id,
            product_id=params.product_id,
            quality=quality,
        )

    def _extract_params(self, video_url: str) -> XiaoetVideoParams:
        if not is_xiaoet_video_url(video_url):
            raise XiaoetResolveError("不是支持的小鹅通视频链接。")
        parsed = urlparse(video_url)
        host = (parsed.hostname or "").lower()
        app_id = _extract_app_id(host)
        resource_id = _extract_resource_id(parsed.path)
        product_id = _extract_product_id(parsed.query)
        if not all([app_id, host, resource_id, product_id]):
            raise XiaoetResolveError("小鹅通链接缺少 app_id、resource_id 或 product_id。")
        return XiaoetVideoParams(
            app_id=app_id,
            host=host,
            base_url=f"{parsed.scheme or 'https'}://{host}",
            resource_id=resource_id,
            product_id=product_id,
        )

    def _fetch_navigation(self, params: XiaoetVideoParams, headers: Dict[str, str]) -> Dict[str, Any]:
        url = f"{params.base_url}/xe.micro_page.navigation.get/1.0.0"
        data = self._post_json(
            url,
            {
                "app_id": params.app_id,
                "agent_type": 1,
                "app_version": 0,
            },
            headers=headers,
        )
        return self._extract_data(data, "小鹅通导航接口")

    def _fetch_video_info(self, params: XiaoetVideoParams, headers: Dict[str, str]) -> Dict[str, Any]:
        url = f"{params.base_url}/xe.course.business.video.detail_info.get/2.0.0"
        data = self._post_form(
            url,
            {
                "bizData[resource_id]": params.resource_id,
                "bizData[product_id]": params.product_id,
                "bizData[opr_sys]": "MacIntel",
            },
            headers=headers,
        )
        return self._extract_data(data, "小鹅通视频详情接口").get("video_info") or {}

    def _fetch_play_list(
        self,
        params: XiaoetVideoParams,
        user_id: str,
        play_sign: str,
        headers: Dict[str, str],
    ) -> Dict[str, Any]:
        url = f"{params.base_url}/xe.material-center.play/getPlayUrl"
        data = self._post_json(
            url,
            {
                "org_app_id": params.app_id,
                "app_id": params.app_id,
                "user_id": user_id,
                "play_sign": [play_sign],
                "play_line": "A",
                "opr_sys": "MacIntel",
            },
            headers=headers,
        )
        play_data = self._extract_data(data, "小鹅通播放接口")
        return ((play_data.get(play_sign) or {}).get("play_list") or {})

    @staticmethod
    def _select_best_play_url(play_list: Dict[str, Any]) -> tuple[str, str]:
        for quality in XIAOET_QUALITY_ORDER:
            item = play_list.get(quality) or {}
            play_url = str(item.get("play_url") or "").strip() if isinstance(item, dict) else ""
            if play_url:
                return play_url, quality

        for quality, item in play_list.items():
            play_url = str(item.get("play_url") or "").strip() if isinstance(item, dict) else ""
            if play_url:
                return play_url, str(quality)
        return "", ""

    @staticmethod
    def _extract_data(payload: Dict[str, Any], label: str) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise XiaoetResolveError(f"{label}响应格式异常。")
        code = str(payload.get("code", "0"))
        if code not in ("0", "200"):
            raise XiaoetResolveError(f"{label}请求失败: {payload.get('msg') or payload.get('message') or code}")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise XiaoetResolveError(f"{label}未返回有效 data。")
        return data

    def _post_json(self, url: str, payload: Dict[str, Any], headers: Dict[str, str] | None = None) -> Dict[str, Any]:
        request_headers = {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
        }
        if headers:
            request_headers.update(headers)
        request = Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=request_headers,
            method="POST",
        )
        return self._send_json_request(request, url)

    def _post_form(self, url: str, form_data: Dict[str, str], headers: Dict[str, str] | None = None) -> Dict[str, Any]:
        request_headers = {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        if headers:
            request_headers.update(headers)
        request = Request(
            url,
            data=urlencode(form_data).encode("utf-8"),
            headers=request_headers,
            method="POST",
        )
        return self._send_json_request(request, url)

    @staticmethod
    def _send_json_request(request: Request, url: str) -> Dict[str, Any]:
        try:
            with urlopen(request, timeout=20) as response:
                raw = response.read().decode("utf-8", errors="replace")
            if not raw.strip():
                raise XiaoetResolveError("空响应")
            return json.loads(raw)
        except XiaoetResolveError:
            raise
        except Exception as exc:
            raise XiaoetResolveError(f"请求失败: {url}") from exc
