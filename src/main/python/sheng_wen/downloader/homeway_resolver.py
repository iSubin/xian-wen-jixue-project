from __future__ import annotations

import json
import os
import random
import re
import sqlite3
import tempfile
import shutil
import sys
import zlib
from dataclasses import dataclass
from typing import Any, Callable, Dict
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

from ..utils.logger import logger


HOMEWAY_DEFAULT_BIGVID = "41"
HOMEWAY_API_BASE = "https://tydsapi.homeway.com.cn"
VHALL_WATCH_BASE = "https://hexun.vhall.homeway.com.cn"
VHALL_SDK_BASE = "https://api.vhallyun.com/sdk"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
SENSITIVE_QUERY_PATTERN = re.compile(
    r"([?&](?:token|access_token|auth|authorization|sign|secret|web_qtstr|t|us)=)[^&#\s]+",
    re.IGNORECASE,
)


class HomewayResolveError(RuntimeError):
    pass


@dataclass(frozen=True)
class HomewayResolvedVideo:
    media_url: str
    title: str
    source_url: str
    vhall_id: str


def redact_sensitive_url(value: str) -> str:
    return SENSITIVE_QUERY_PATTERN.sub(r"\1<redacted>", str(value or ""))


def is_homeway_graphic_video_url(video_url: str) -> bool:
    try:
        parsed = urlparse(str(video_url or ""))
    except Exception:
        return False
    host = (parsed.hostname or "").lower()
    if host != "tyds.homeway.com.cn":
        return False
    fragment_path, fragment_params = _parse_fragment_route(parsed.fragment)
    if fragment_path != "/GraphicVideo":
        return False
    return bool(fragment_params.get("key"))


def resolve_homeway_graphic_video(video_url: str, web_qtstr: str | None = None) -> HomewayResolvedVideo:
    token = _sanitize_cookie_value(web_qtstr)
    if token:
        return HomewayVideoResolver(token_provider=lambda: token).resolve(video_url)
    return HomewayVideoResolver().resolve(video_url)


def transform_vhall_play_token(origin_token: str) -> str:
    token = str(origin_token or "").strip()
    if "_" not in token:
        return token
    prefix, suffix = token.split("_", 1)
    if not prefix or not suffix:
        return token
    checksum = zlib.crc32(prefix[::-1].encode("utf-8")) & 0xFFFFFFFF
    return f"{checksum:X}_{suffix}"


def _parse_fragment_route(fragment: str) -> tuple[str, Dict[str, list[str]]]:
    route = (fragment or "").strip()
    if route.startswith("#"):
        route = route[1:]
    if not route.startswith("/"):
        route = f"/{route}" if route else ""
    if "?" not in route:
        return route, {}
    route_path, route_query = route.split("?", 1)
    return route_path, parse_qs(route_query)


def _first_query_value(values: Dict[str, list[str]], key: str) -> str:
    raw = values.get(key) or []
    return str(raw[0]).strip() if raw else ""


def _extract_homeway_params(video_url: str) -> tuple[str, str, str]:
    parsed = urlparse(video_url)
    page_query = parse_qs(parsed.query)
    _, fragment_query = _parse_fragment_route(parsed.fragment)

    video_id = _first_query_value(fragment_query, "key") or _first_query_value(page_query, "key")
    token = _first_query_value(fragment_query, "token") or _first_query_value(page_query, "token")
    big_vid = (
        _first_query_value(fragment_query, "bigVId")
        or _first_query_value(page_query, "bigVId")
        or os.getenv("HOMEWAY_BIGVID")
        or HOMEWAY_DEFAULT_BIGVID
    )
    return video_id, token, big_vid


def _sanitize_cookie_value(value: str | None) -> str:
    return (value or "").strip().replace("\r", "").replace("\n", "")


def _read_homeway_token_from_browser_cookie3() -> tuple[str, str]:
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
    for browser_key, browser_name in browsers_to_try:
        try:
            browser_func = getattr(browser_cookie3, browser_key, None)
            if browser_func is None:
                continue
            cookies = browser_func(domain_name="homeway.com.cn")
            for cookie in cookies:
                if cookie.name == "web_qtstr" and cookie.value:
                    token = _sanitize_cookie_value(cookie.value)
                    if token:
                        return token, browser_name
        except Exception:
            continue
    return "", ""


def _read_homeway_token_from_macos_chrome() -> tuple[str, str]:
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
        logger.debug(f"[HomewayResolver] 读取 Chrome Safe Storage 失败: {e}")
        return "", ""

    for cookie_file in cookie_files:
        temp_path = ""
        try:
            fd, temp_path = tempfile.mkstemp(prefix="shengwen-homeway-cookies-", suffix=".sqlite")
            os.close(fd)
            shutil.copy2(cookie_file, temp_path)
            with sqlite3.connect(temp_path) as con:
                rows = con.execute(
                    """
                    SELECT host_key, name, value, encrypted_value
                    FROM cookies
                    WHERE host_key LIKE ? AND name = ?
                    ORDER BY expires_utc DESC
                    """,
                    ("%homeway.com.cn%", "web_qtstr"),
                ).fetchall()

            for host_key, _name, value, encrypted_value in rows:
                token = _sanitize_cookie_value(
                    _decrypt_macos_chrome_v10_cookie(host_key, value, encrypted_value, password)
                )
                if token:
                    return token, "Google Chrome"
        except Exception as e:
            logger.debug(f"[HomewayResolver] Chrome Cookie 兜底读取失败: {e}")
        finally:
            if temp_path:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    return "", ""


def resolve_homeway_login_token() -> str:
    env_token = _sanitize_cookie_value(os.getenv("HOMEWAY_TOKEN") or os.getenv("HOMEWAY_WEB_QTSTR"))
    if env_token:
        return env_token

    token, browser_name = _read_homeway_token_from_browser_cookie3()
    if token:
        logger.info(f"[HomewayResolver] 已从 {browser_name} 读取投研大师 web_qtstr")
        return token

    token, browser_name = _read_homeway_token_from_macos_chrome()
    if token:
        logger.info(f"[HomewayResolver] 已通过 macOS {browser_name} 读取投研大师 web_qtstr")
        return token

    return ""


class HomewayVideoResolver:
    def __init__(
        self,
        token_provider: Callable[[], str] | None = None,
        random_int_provider: Callable[[], int] | None = None,
    ):
        self.token_provider = token_provider or resolve_homeway_login_token
        self.random_int_provider = random_int_provider or (lambda: random.randint(100000000, 999999999))

    def resolve(self, video_url: str) -> HomewayResolvedVideo:
        if not is_homeway_graphic_video_url(video_url):
            raise HomewayResolveError("不是支持的投研大师图文视频链接。")

        video_id, url_token, big_vid = _extract_homeway_params(video_url)
        if not video_id:
            raise HomewayResolveError("投研大师链接缺少 key 参数。")

        token = _sanitize_cookie_value(url_token or self.token_provider())
        if not token:
            raise HomewayResolveError(
                "未找到投研大师登录态 web_qtstr。请先在 Chrome 登录并打开一次投研大师页面，"
                "或设置 HOMEWAY_TOKEN/HOMEWAY_WEB_QTSTR 后重试。"
            )

        video_info = self._fetch_video_info(video_id=video_id, token=token, big_vid=big_vid)
        video_block = ((video_info.get("data") or {}).get("video") or {})
        title = str(video_block.get("title") or "投研大师视频")
        vhall_id = str(video_block.get("vh_live_id") or "").strip()
        if not vhall_id:
            raise HomewayResolveError("投研大师 videoInfo 未返回 vh_live_id。")

        watch_init = self._fetch_vhall_watch_init(vhall_id)
        watch_data = watch_init.get("data") or {}
        record_info = self._fetch_vhall_record_info(watch_data)
        media_url = self._dispatch_vhall_replay(watch_data, record_info)

        return HomewayResolvedVideo(
            media_url=media_url,
            title=title,
            source_url=video_url,
            vhall_id=vhall_id,
        )

    def _fetch_video_info(self, video_id: str, token: str, big_vid: str) -> Dict[str, Any]:
        query = urlencode({"id": video_id, "token": token, "bigVId": big_vid})
        url = f"{HOMEWAY_API_BASE}/lecturers/video/videoInfo?{query}"
        data = self._get_json(url, headers={"Referer": "https://tyds.homeway.com.cn/"})
        if str(data.get("code")) != "1000":
            raise HomewayResolveError(f"投研大师 videoInfo 请求失败: {data.get('msg') or data.get('code')}")
        return data

    def _fetch_vhall_watch_init(self, vhall_id: str) -> Dict[str, Any]:
        query = urlencode({
            "webinar_id": vhall_id,
            "clientType": "embed",
            "live_type": "0",
            "embed": "video",
        })
        url = f"{VHALL_WATCH_BASE}/v3/webinars/watch/init?{query}"
        data = self._get_json(
            url,
            headers={"Referer": f"{VHALL_WATCH_BASE}/v3/lives/watch/{vhall_id}?embed=video"},
        )
        if str(data.get("code")) != "200":
            raise HomewayResolveError(f"Vhall watch/init 请求失败: {data.get('msg') or data.get('code')}")
        return data

    def _fetch_vhall_record_info(self, watch_data: Dict[str, Any]) -> Dict[str, Any]:
        interact = watch_data.get("interact") or {}
        join_info = watch_data.get("join_info") or {}
        record = watch_data.get("record") or {}

        app_id = str(interact.get("paas_app_id") or "").strip()
        access_token = str(interact.get("paas_access_token") or "").strip()
        third_party_user_id = str(
            join_info.get("third_party_user_id") or join_info.get("join_id") or ""
        ).strip()
        record_id = str(record.get("paas_record_id") or watch_data.get("paas_record_id") or "").strip()
        if not all([app_id, access_token, third_party_user_id, record_id]):
            raise HomewayResolveError("Vhall watch/init 返回数据不完整，无法请求点播记录。")

        form_data = {
            "app_id": app_id,
            "third_party_user_id": third_party_user_id,
            "client": "pc_browser",
            "access_token": access_token,
            "package_check": "peter",
            "record_id": record_id,
        }
        data = self._post_form(
            f"{VHALL_SDK_BASE}/v2/demand/get-record-watch-info",
            form_data,
            headers={"Referer": f"{VHALL_WATCH_BASE}/v3/lives/watch/{watch_data.get('webinar_id', '')}"},
        )
        if str(data.get("code")) != "200":
            raise HomewayResolveError(f"Vhall 点播信息请求失败: {data.get('msg') or data.get('code')}")
        return data.get("data") or {}

    def _dispatch_vhall_replay(self, watch_data: Dict[str, Any], record_info: Dict[str, Any]) -> str:
        interact = watch_data.get("interact") or {}
        join_info = watch_data.get("join_info") or {}
        record = watch_data.get("record") or {}
        record_id = str(record.get("paas_record_id") or watch_data.get("paas_record_id") or "").strip()
        default_server = record_info.get("default_server") or {}
        dispatch_server = str(record_info.get("dispatch_server") or "").strip()
        log_info = record_info.get("log_info") or {}

        app_id = str(interact.get("paas_app_id") or "").strip()
        uid = str(
            join_info.get("third_party_user_id")
            or log_info.get("uid")
            or log_info.get("third_party_user_id")
            or ""
        ).strip()
        uri = str(default_server.get("uri") or "").strip()
        if not all([dispatch_server, app_id, record_id, uid, uri]):
            media_url = self._select_hls_url(default_server)
            token = transform_vhall_play_token(str(default_server.get("token") or "").strip())
            if media_url:
                return self._append_token(media_url, token)
            raise HomewayResolveError("Vhall 调度信息不完整，无法生成 HLS 地址。")

        query = urlencode({
            "app_id": app_id,
            "webinar_id": record_id,
            "uid": uid,
            "bu": "1",
            "rand": str(self.random_int_provider()),
            "app_custom_line": "1",
            "uri": uri,
            "quality": '["a","same"]',
        })
        dispatch_url = f"{dispatch_server.rstrip('/')}/api/dispatch_replay?{query}"
        dispatch_data = self._get_json(dispatch_url, headers={"Referer": VHALL_WATCH_BASE})
        if str(dispatch_data.get("code")) != "200":
            raise HomewayResolveError(
                f"Vhall dispatch_replay 请求失败: {dispatch_data.get('msg') or dispatch_data.get('code')}"
            )

        data = dispatch_data.get("data") or {}
        media_url = self._select_hls_url(data) or self._select_hls_url(default_server)
        token = transform_vhall_play_token(
            str(default_server.get("token") or data.get("token") or "").strip()
        )
        if not media_url:
            raise HomewayResolveError("Vhall dispatch_replay 未返回 HLS 地址。")
        return self._append_token(media_url, token)

    @staticmethod
    def _select_hls_url(data: Dict[str, Any]) -> str:
        hls_domainnames = data.get("hls_domainnames")
        if isinstance(hls_domainnames, dict):
            for quality in ("same", "a", "origin"):
                items = hls_domainnames.get(quality)
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and item.get("hls_domainname"):
                            return str(item["hls_domainname"])
            for items in hls_domainnames.values():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and item.get("hls_domainname"):
                            return str(item["hls_domainname"])

        if isinstance(hls_domainnames, list):
            for item in hls_domainnames:
                if isinstance(item, dict) and item.get("hls_domainname"):
                    return str(item["hls_domainname"])

        direct = data.get("hls_domainname") or data.get("uri")
        return str(direct or "")

    @staticmethod
    def _append_token(media_url: str, token: str) -> str:
        if not token:
            return media_url
        parsed = urlparse(media_url)
        query = parse_qs(parsed.query)
        if query.get("token"):
            return media_url
        new_query = urlencode({**{k: v[-1] for k, v in query.items()}, "token": token})
        return urlunparse(parsed._replace(query=new_query))

    def _get_json(self, url: str, headers: Dict[str, str] | None = None) -> Dict[str, Any]:
        request_headers = {"User-Agent": USER_AGENT}
        if headers:
            request_headers.update(headers)
        request = Request(url, headers=request_headers)
        try:
            with urlopen(request, timeout=20) as response:
                raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw)
        except Exception as exc:
            raise HomewayResolveError(f"请求失败: {redact_sensitive_url(url)}") from exc

    def _post_form(
        self,
        url: str,
        form_data: Dict[str, str],
        headers: Dict[str, str] | None = None,
    ) -> Dict[str, Any]:
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
        try:
            with urlopen(request, timeout=20) as response:
                raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw)
        except Exception as exc:
            raise HomewayResolveError(f"请求失败: {redact_sensitive_url(url)}") from exc
