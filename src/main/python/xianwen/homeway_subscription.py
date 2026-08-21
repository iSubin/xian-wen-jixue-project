from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import re
from typing import Any, Dict, Iterable
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as html_to_markdown

from .downloader.homeway_resolver import HOMEWAY_API_BASE, USER_AGENT


HOMEWAY_SITE_HOST = "tyds.homeway.com.cn"
HOMEWAY_SOURCE_TIMEZONE = ZoneInfo("Asia/Shanghai")


class HomewaySubscriptionError(RuntimeError):
    pass


class HomewayAuthenticationError(HomewaySubscriptionError):
    pass


@dataclass(frozen=True)
class HomewayLecturerPreview:
    lecturer_id: str
    display_name: str
    source_url: str
    avatar_url: str = ""
    intro: str = ""
    text_menu_name: str = "观点"
    menu: list[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": "homeway",
            "source_type": "homeway_lecturer",
            "external_source_id": self.lecturer_id,
            "display_name": self.display_name,
            "source_url": self.source_url,
            "avatar_url": self.avatar_url,
            "intro": self.intro,
            "text_menu_name": self.text_menu_name,
            "menu": self.menu,
        }


@dataclass(frozen=True)
class HomewayListItem:
    external_item_id: str
    lecturer_id: str
    lecturer_name: str
    published_at: datetime
    published_at_text: str
    preview_text: str
    image_urls: list[str]
    is_charge: bool
    tag_id: str = ""
    tag_name: str = ""
    top: bool = False

    @property
    def source_url(self) -> str:
        return f"https://{HOMEWAY_SITE_HOST}/#/GraphicView?key={self.external_item_id}"


@dataclass(frozen=True)
class HomewayCapturedItem:
    external_item_id: str
    capture_status: str
    access_scope: str
    raw_html: str = ""
    image_urls: list[str] = field(default_factory=list)
    source_meta: Dict[str, Any] = field(default_factory=dict)
    failure_code: str | None = None
    failure_detail: str | None = None


def _sanitize_token(value: Any) -> str:
    return str(value or "").strip().replace("\r", "").replace("\n", "").replace(";", "")


def _truthy(value: Any) -> bool:
    if value is True or value == 1:
        return True
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "allowed"}


def _homeway_id_set(value: Any) -> set[str]:
    if isinstance(value, (list, tuple, set)):
        values = value
    else:
        values = re.split(r"[,\s]+", str(value or "").strip())
    return {str(item).strip() for item in values if str(item).strip()}


def _parse_fragment_query(fragment: str) -> tuple[str, Dict[str, list[str]]]:
    route = str(fragment or "").strip()
    if route.startswith("#"):
        route = route[1:]
    if not route.startswith("/"):
        route = f"/{route}" if route else ""
    if "?" not in route:
        return route, {}
    path, query = route.split("?", 1)
    return path, parse_qs(query)


def parse_homeway_lecturer_url(value: str) -> str:
    try:
        parsed = urlparse(str(value or "").strip())
    except ValueError as exc:
        raise HomewaySubscriptionError("请输入有效的投研大师讲师主页") from exc
    if (parsed.hostname or "").lower() != HOMEWAY_SITE_HOST:
        raise HomewaySubscriptionError("请输入投研大师 tyds.homeway.com.cn 的讲师主页")

    fragment_path, fragment_query = _parse_fragment_query(parsed.fragment)
    page_query = parse_qs(parsed.query)
    lecturer_id = str(
        (fragment_query.get("lecturerId") or page_query.get("lecturerId") or [""])[0]
    ).strip()
    if fragment_path != "/GraphicLecturer" or not lecturer_id:
        raise HomewaySubscriptionError("请输入包含 lecturerId 的投研大师讲师主页")
    if not lecturer_id.isdigit():
        raise HomewaySubscriptionError("投研大师 lecturerId 格式不正确")
    return lecturer_id


def canonical_homeway_lecturer_url(lecturer_id: str) -> str:
    return f"https://{HOMEWAY_SITE_HOST}/#/GraphicLecturer?lecturerId={lecturer_id}"


def parse_homeway_datetime(value: Any) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise HomewaySubscriptionError("投研大师内容缺少发布时间")
    try:
        local_value = datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=HOMEWAY_SOURCE_TIMEZONE)
    except ValueError as exc:
        raise HomewaySubscriptionError("投研大师内容发布时间格式不正确") from exc
    return local_value.astimezone(timezone.utc)


def is_allowed_homeway_image_url(value: str) -> bool:
    try:
        parsed = urlparse(str(value or "").strip())
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (host == "homeway.com.cn" or host.endswith(".homeway.com.cn"))


def collect_homeway_image_urls(raw_html: str) -> list[str]:
    soup = BeautifulSoup(raw_html or "", "lxml")
    result: list[str] = []
    seen: set[str] = set()
    for image in soup.find_all("img"):
        src = str(image.get("data-src") or image.get("src") or "").strip()
        if not src or src in seen or not is_allowed_homeway_image_url(src):
            continue
        seen.add(src)
        result.append(src)
    return result


def render_homeway_markdown(raw_html: str, image_paths: Dict[str, str] | None = None) -> str:
    soup = BeautifulSoup(raw_html or "", "lxml")
    for element in soup.find_all(["script", "style", "iframe"]):
        element.decompose()
    replacements = image_paths or {}
    for image in soup.find_all("img"):
        src = str(image.get("data-src") or image.get("src") or "").strip()
        if src in replacements:
            image["src"] = replacements[src]
        image.attrs.pop("data-src", None)
        if not str(image.get("alt") or "").strip():
            image["alt"] = "原文图片"
    markdown = html_to_markdown(str(soup), heading_style="ATX").replace("\xa0", " ").strip()
    return markdown


class HomewaySubscriptionAdapter:
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self._vip_entitlement_cache: Dict[tuple[str, str], bool] = {}
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "application/json, text/plain, */*",
                "Referer": f"https://{HOMEWAY_SITE_HOST}/",
            }
        )

    def recognize_subscription_url(self, value: str) -> str:
        return parse_homeway_lecturer_url(value)

    def preview_subscription(self, value: str, token: str | None = None) -> HomewayLecturerPreview:
        lecturer_id = self.recognize_subscription_url(value)
        base = self._request_json(
            "/lecturers/info/baseinfo",
            {"lecturer_id": lecturer_id},
            token=token,
        )
        menu_payload = self._request_json(
            "/lecturers/info/lecturersMenu",
            {"lecturer_id": lecturer_id},
            token=token,
        )
        lecturer = ((base.get("data") or {}).get("lecturer") or {})
        if str(lecturer.get("id") or "") != lecturer_id:
            raise HomewaySubscriptionError("投研大师没有返回对应讲师信息")
        menu_data = (menu_payload.get("data") or {}).get("lecturersMenu") or {}
        submenus = menu_data.get("allSubMenu") or []
        text_menu = next(
            (str(item.get("name") or "观点") for item in submenus if str(item.get("id")) == "1"),
            "观点",
        )
        return HomewayLecturerPreview(
            lecturer_id=lecturer_id,
            display_name=str(lecturer.get("name") or f"讲师 {lecturer_id}").strip(),
            source_url=canonical_homeway_lecturer_url(lecturer_id),
            avatar_url=str(lecturer.get("full_avatar_url") or "").strip(),
            intro=str(lecturer.get("intro") or "").strip(),
            text_menu_name=text_menu,
            menu=[item for item in submenus if isinstance(item, dict)],
        )

    def list_items(
        self,
        lecturer_id: str,
        *,
        cursor: str | None = None,
        token: str | None = None,
    ) -> list[HomewayListItem]:
        params: Dict[str, Any] = {
            "lecturer_id": lecturer_id,
            "mainMenuId": 10,
            "subMenuId": 1,
        }
        if cursor:
            params["published_at"] = cursor
        payload = self._request_json("/lecturers/info/list", params, token=token)
        data = payload.get("data") or {}
        raw_items: list[Dict[str, Any]] = []
        if isinstance(data, dict):
            for value in data.values():
                if isinstance(value, list):
                    raw_items.extend(item for item in value if isinstance(item, dict))

        result: list[HomewayListItem] = []
        seen: set[str] = set()
        for raw in raw_items:
            external_item_id = str(raw.get("id") or "").strip()
            if not external_item_id or external_item_id in seen:
                continue
            if str(raw.get("content_type") or "lecturer_feed") != "lecturer_feed":
                continue
            if str(raw.get("data_type") or "outlook") != "outlook":
                continue
            seen.add(external_item_id)
            published_at_text = str(raw.get("published_at") or "").strip()
            image_urls = [
                str(url).strip()
                for url in (raw.get("get_imgs") or [])
                if is_allowed_homeway_image_url(str(url or ""))
            ]
            result.append(
                HomewayListItem(
                    external_item_id=external_item_id,
                    lecturer_id=str(raw.get("lecturer_id") or lecturer_id),
                    lecturer_name=str(raw.get("lecturer_name") or "").strip(),
                    published_at=parse_homeway_datetime(published_at_text),
                    published_at_text=published_at_text,
                    preview_text=str(raw.get("real_content") or "").strip(),
                    image_urls=image_urls,
                    is_charge=_truthy(raw.get("is_charge")),
                    tag_id=str(raw.get("tag_id") or ""),
                    tag_name=str(raw.get("tag_name") or "").strip(),
                    top=_truthy(raw.get("top")),
                )
            )
        result.sort(key=lambda item: (item.published_at, item.external_item_id), reverse=True)
        return result

    def capture_item(self, item: HomewayListItem, *, token: str | None = None) -> HomewayCapturedItem:
        if item.is_charge and not self._has_vip_entitlement(item.lecturer_id, token=token):
            return HomewayCapturedItem(
                external_item_id=item.external_item_id,
                capture_status="LOCKED",
                access_scope="locked",
                source_meta=self._source_meta(item, {}, {}),
                failure_code="ENTITLEMENT_REQUIRED",
                failure_detail="当前账号没有得到站点明确的会员文字阅读授权",
            )

        payload = self._request_json(
            "/lecturers/info/topicDetail",
            {"lecturer_feed_id": item.external_item_id},
            token=token,
        )
        data = payload.get("data") or {}
        lecturer = data.get("lecturer") or {}
        feed = data.get("lecturer_feed") or {}
        if str(feed.get("id") or "") != item.external_item_id:
            raise HomewaySubscriptionError("投研大师没有返回对应文字详情")

        blocked = _truthy(feed.get("is_blocked"))
        if blocked:
            return HomewayCapturedItem(
                external_item_id=item.external_item_id,
                capture_status="LOCKED",
                access_scope="locked",
                source_meta=self._source_meta(item, lecturer, feed),
                failure_code="ENTITLEMENT_REQUIRED",
                failure_detail="当前账号没有得到站点明确的全文阅读授权",
            )

        public_html = str(feed.get("content") or "").strip()
        entitled_html = str(feed.get("vip_content") or "").strip() if item.is_charge else ""
        raw_html = "\n".join(part for part in (public_html, entitled_html) if part).strip()
        if not raw_html:
            raise HomewaySubscriptionError("投研大师文字详情为空")
        detail_image_urls = collect_homeway_image_urls(raw_html)
        image_urls = list(dict.fromkeys([*detail_image_urls, *item.image_urls]))
        missing_images = [url for url in item.image_urls if url not in detail_image_urls]
        if missing_images:
            raw_html = "\n".join(
                [
                    raw_html,
                    *(
                        f'<p><img src="{escape(url, quote=True)}" alt="原文图片"></p>'
                        for url in missing_images
                    ),
                ]
            ).strip()
        return HomewayCapturedItem(
            external_item_id=item.external_item_id,
            capture_status="CAPTURED",
            access_scope="entitled" if item.is_charge else "public",
            raw_html=raw_html,
            image_urls=image_urls,
            source_meta=self._source_meta(item, lecturer, feed),
        )

    def _has_vip_entitlement(self, lecturer_id: str, *, token: str | None) -> bool:
        clean_token = _sanitize_token(token)
        if not clean_token:
            return False
        cache_key = (sha256(clean_token.encode("utf-8")).hexdigest(), str(lecturer_id))
        if cache_key in self._vip_entitlement_cache:
            return self._vip_entitlement_cache[cache_key]

        payload = self._request_json(
            "/lecturers/order/queryUserEvaluationInfo",
            {},
            token=clean_token,
        )
        data = payload.get("data") or {}
        lecturer_value = str(lecturer_id)
        has_permission = lecturer_value in _homeway_id_set(data.get("vipPermissionLecIds"))
        needs_signature = lecturer_value in _homeway_id_set(data.get("vipNeedSignLecturerIds"))
        needs_resign = lecturer_value in _homeway_id_set(data.get("vipReSignLecturerIds"))
        entitled = has_permission and not needs_signature and not needs_resign
        self._vip_entitlement_cache[cache_key] = entitled
        return entitled

    @staticmethod
    def _source_meta(
        item: HomewayListItem,
        lecturer: Dict[str, Any],
        feed: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "lecturer_id": item.lecturer_id,
            "lecturer_name": str(lecturer.get("name") or item.lecturer_name).strip(),
            "published_at_source": item.published_at_text,
            "tag_id": str(feed.get("tag_id") or item.tag_id or ""),
            "tag_name": str(feed.get("tag_name") or item.tag_name or "").strip(),
            "product_name": str(feed.get("product_name") or "").strip(),
            "signature": str(feed.get("signature") or "").strip(),
            "is_charge": item.is_charge,
        }

    def _request_json(
        self,
        path: str,
        params: Dict[str, Any],
        *,
        token: str | None = None,
    ) -> Dict[str, Any]:
        request_params = dict(params)
        clean_token = _sanitize_token(token)
        if clean_token:
            request_params["token"] = clean_token
        try:
            response = self.session.get(
                f"{HOMEWAY_API_BASE}{path}",
                params=request_params,
                timeout=25,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise HomewaySubscriptionError("投研大师接口请求失败，请稍后重试") from exc
        if not isinstance(payload, dict):
            raise HomewaySubscriptionError("投研大师接口返回格式异常")
        if str(payload.get("code")) != "1000":
            message = str(payload.get("msg") or "投研大师接口返回错误").strip()
            if any(keyword in message.lower() for keyword in ("登录", "token", "失效", "过期", "未授权")):
                raise HomewayAuthenticationError("投研大师登录态已失效，请重新导入账号")
            raise HomewaySubscriptionError(message)
        return payload


def oldest_homeway_cursor(items: Iterable[HomewayListItem]) -> str | None:
    values = [item.published_at_text for item in items if item.published_at_text and not item.top]
    return min(values) if values else None
