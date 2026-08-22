from __future__ import annotations

import hashlib
import json
import re
import shutil
import uuid
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests

from .db import TaskStatus
from .downloader.homeway_resolver import USER_AGENT
from .homeway_subscription import (
    HomewayAuthenticationError,
    HomewayCapturedItem,
    HomewayListItem,
    HomewaySubscriptionAdapter,
    HomewaySubscriptionError,
    is_allowed_homeway_image_url,
    oldest_homeway_cursor,
    render_homeway_markdown,
)
from .storage import get_task_assets_root, preserve_article_source


CAPTURED_ITEM_STATUSES = {"CAPTURED", "CAPTURED_UPDATED"}
INITIAL_SYNC_MODES = {"from_now", "today", "last_7_days"}
SUBSCRIPTION_STATUSES = {"ACTIVE", "PAUSED", "AUTH_REQUIRED", "DEGRADED", "ERROR"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _stored_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or "").strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_clock(value: str, fallback: time) -> time:
    try:
        return datetime.strptime(str(value or ""), "%H:%M").time()
    except ValueError:
        return fallback


def _safe_asset_component(value: str, fallback: str) -> str:
    clean = re.sub(r"[^0-9A-Za-z._-]+", "-", str(value or "").strip()).strip(".-")
    return (clean or fallback)[:80]


def _image_extension(url: str, content_type: str) -> str:
    normalized_type = str(content_type or "").lower()
    for marker, extension in (
        ("png", ".png"),
        ("webp", ".webp"),
        ("gif", ".gif"),
        ("jpeg", ".jpg"),
        ("jpg", ".jpg"),
    ):
        if marker in normalized_type:
            return extension
    path = urlparse(url).path.lower()
    for extension in (".png", ".webp", ".gif", ".jpeg", ".jpg"):
        if path.endswith(extension):
            return ".jpg" if extension == ".jpeg" else extension
    return ".jpg"


def _digest_task_id(subscription_id: str, digest_date: str) -> str:
    compact_date = digest_date.replace("-", "")
    return f"homeway-digest-{subscription_id[:12]}-{compact_date}"


def _post_task_id(subscription_id: str, external_item_id: str) -> str:
    external_value = str(external_item_id or "").strip()
    digest = hashlib.sha256(external_value.encode("utf-8")).hexdigest()[:8]
    component = _safe_asset_component(external_value, digest)[:48]
    return f"homeway-post-{subscription_id[:12]}-{component}-{digest}"


def _post_title(item: Dict[str, Any], timezone_value: ZoneInfo) -> str:
    published = _stored_datetime(item.get("published_at")) or _utc_now()
    local_published = published.astimezone(timezone_value)
    preview = re.sub(r"\s+", " ", str(item.get("preview_text") or "")).strip()
    if not preview:
        preview = "讲师观点"
    if len(preview) > 68:
        preview = f"{preview[:67].rstrip()}…"
    return f"{local_published.strftime('%Y-%m-%d %H:%M')}｜{preview}"


def _item_content_hash(markdown: str, image_manifest: list[Dict[str, Any]], source_meta: Dict[str, Any]) -> str:
    upstream_meta = {
        key: value
        for key, value in (source_meta or {}).items()
        if key
        not in {
            "content_task_id",
            "content_version",
            "digest_date",
            "external_item_id",
            "provider",
            "subscription_id",
        }
    }
    return hashlib.sha256(
        json.dumps(
            {
                "markdown": markdown,
                "images": [entry.get("original_url") for entry in image_manifest],
                "meta": upstream_meta,
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


class SubscriptionService:
    def __init__(
        self,
        task_db: Any,
        asset_root: str | Path,
        *,
        adapter_factory: Callable[[], HomewaySubscriptionAdapter] = HomewaySubscriptionAdapter,
        image_session_factory: Callable[[], requests.Session] = requests.Session,
        now_provider: Callable[[], datetime] = _utc_now,
    ):
        self.db = task_db
        self.asset_root = Path(asset_root)
        self.adapter_factory = adapter_factory
        self.image_session_factory = image_session_factory
        self.now_provider = now_provider
        try:
            self.manage_originals = self.asset_root.resolve().is_relative_to(
                get_task_assets_root().resolve()
            )
        except (OSError, ValueError):
            self.manage_originals = False

    def now(self) -> datetime:
        value = self.now_provider()
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

    def preview_subscription(
        self,
        user_id: str,
        source_url: str,
        *,
        connected_account_id: str | None = None,
    ) -> Dict[str, Any]:
        account, token = self._resolve_homeway_account(
            user_id,
            connected_account_id,
            required=False,
        )
        preview = self.adapter_factory().preview_subscription(source_url, token=token)
        result = preview.to_dict()
        result["account_required"] = account is None
        result["connected_account"] = account
        return result

    def create_subscription(
        self,
        user_id: str,
        source_url: str,
        *,
        connected_account_id: str | None = None,
        folder_id: str | None = None,
        initial_sync_mode: str = "from_now",
        poll_interval_minutes: int = 15,
        active_window_start: str = "08:30",
        active_window_end: str = "18:30",
        digest_time: str = "20:30",
        timezone_name: str = "Asia/Shanghai",
    ) -> Dict[str, Any]:
        if initial_sync_mode not in INITIAL_SYNC_MODES:
            raise ValueError("首次同步范围不正确")
        self._validate_timezone(timezone_name)
        self._validate_clock(active_window_start, "活跃开始时间")
        self._validate_clock(active_window_end, "活跃结束时间")
        self._validate_clock(digest_time, "每日内容包时间")
        interval = max(5, min(int(poll_interval_minutes), 360))

        account, token = self._resolve_homeway_account(
            user_id,
            connected_account_id,
            required=True,
        )
        preview = self.adapter_factory().preview_subscription(source_url, token=token)
        if folder_id:
            if not self.db.get_folder(folder_id):
                raise ValueError("目标藏经阁目录不存在")
        else:
            folder_id = self.db.ensure_folder_path(
                ["订阅", "投研大师", preview.display_name],
                folder_type="auto",
                source_url=preview.source_url,
            )

        subscription = self.db.create_content_subscription(
            {
                "id": uuid.uuid4().hex,
                "user_id": user_id,
                "provider": "homeway",
                "source_type": "homeway_lecturer",
                "source_url": preview.source_url,
                "external_source_id": preview.lecturer_id,
                "display_name": preview.display_name,
                "connected_account_id": str((account or {}).get("id") or ""),
                "folder_id": folder_id,
                "status": "ACTIVE",
                "poll_interval_minutes": interval,
                "active_window_start": active_window_start,
                "active_window_end": active_window_end,
                "digest_time": digest_time,
                "timezone": timezone_name,
                "initial_sync_mode": initial_sync_mode,
                "next_poll_at": _naive_utc(self.now()),
            }
        )
        return self.subscription_view(subscription)

    def subscription_view(self, subscription: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(subscription)
        timezone_name = str(result.get("timezone") or "Asia/Shanghai")
        local_today = self.now().astimezone(ZoneInfo(timezone_name)).date().isoformat()
        result["today_item_count"] = self.db.count_subscription_items(
            str(result["id"]),
            digest_date=local_today,
        )
        result["locked_item_count"] = self.db.count_subscription_items(
            str(result["id"]),
            capture_statuses=["LOCKED"],
        )
        result["captured_item_count"] = self.db.count_subscription_items(
            str(result["id"]),
            capture_statuses=sorted(CAPTURED_ITEM_STATUSES),
        )
        return result

    def list_subscriptions(self, user_id: str) -> list[Dict[str, Any]]:
        return [self.subscription_view(item) for item in self.db.list_content_subscriptions(user_id)]

    def should_finalize_today(self, subscription: Dict[str, Any]) -> bool:
        timezone_name = str(subscription.get("timezone") or "Asia/Shanghai")
        local_now = self.now().astimezone(ZoneInfo(timezone_name))
        digest_clock = _parse_clock(str(subscription.get("digest_time") or "20:30"), time(20, 30))
        return (
            local_now.time() >= digest_clock
            and not self._digest_finalized_for_local_date(
                subscription,
                local_now=local_now,
                digest_clock=digest_clock,
            )
        )

    def poll_due_subscription(self, subscription_id: str) -> Dict[str, Any]:
        subscription = self.db.get_content_subscription(subscription_id)
        if not subscription:
            raise ValueError("订阅不存在")
        finalize = self.should_finalize_today(subscription)
        return self.poll_subscription(
            subscription_id,
            trigger="reconciliation" if finalize else "scheduled",
            reconciliation=finalize,
            build_digest=finalize,
        )

    def poll_subscription(
        self,
        subscription_id: str,
        *,
        trigger: str = "manual",
        reconciliation: bool = False,
        build_digest: bool = True,
        backfill_from: datetime | None = None,
    ) -> Dict[str, Any]:
        subscription = self.db.get_content_subscription(subscription_id)
        if not subscription:
            raise ValueError("订阅不存在")
        if subscription.get("status") == "PAUSED" and trigger != "manual":
            raise ValueError("订阅已暂停")

        run = self.db.create_subscription_run(
            subscription_id,
            trigger,
            cursor_before=subscription.get("last_cursor"),
        )
        run_id = str(run["id"])
        counts = {
            "discovered_count": 0,
            "captured_count": 0,
            "updated_count": 0,
            "locked_count": 0,
            "failed_count": 0,
        }
        affected_dates: set[str] = set()
        content_task_ids: list[str] = []
        partial = False
        newest_cursor = str(subscription.get("last_cursor") or "")

        try:
            account, token = self._resolve_homeway_account(
                str(subscription["user_id"]),
                str(subscription.get("connected_account_id") or ""),
                required=True,
            )
            adapter = self.adapter_factory()
            lower_bound = self._poll_lower_bound(subscription, backfill_from=backfill_from)
            prior_cursor = str(subscription.get("last_cursor") or "").strip()
            cursor_watermark = prior_cursor if lower_bound is None else ""
            reconciliation_lower_bound = self.now() - timedelta(days=2) if reconciliation else None
            cursor: str | None = None
            cursor_history: set[str] = set()
            seen_external_ids: set[str] = set()

            for _page_index in range(50):
                page = adapter.list_items(
                    str(subscription["external_source_id"]),
                    cursor=cursor,
                    token=token,
                )
                if not page:
                    break

                page_existing_overlap = False
                page_has_older = False
                page_reached_watermark = False
                for list_item in page:
                    if list_item.external_item_id in seen_external_ids:
                        continue
                    seen_external_ids.add(list_item.external_item_id)
                    counts["discovered_count"] += 1
                    if not newest_cursor or list_item.published_at_text > newest_cursor:
                        newest_cursor = list_item.published_at_text
                    if (
                        cursor_watermark
                        and not list_item.top
                        and list_item.published_at_text <= cursor_watermark
                    ):
                        page_reached_watermark = True
                    if lower_bound and list_item.published_at < lower_bound:
                        page_has_older = True
                        continue

                    digest_date = self._digest_date(subscription, list_item.published_at)
                    existing = self.db.get_subscription_item(
                        subscription_id,
                        list_item.external_item_id,
                    )
                    if existing and not list_item.top:
                        page_existing_overlap = True
                    existing_status = str((existing or {}).get("capture_status") or "")
                    reconcile_existing = bool(
                        reconciliation_lower_bound
                        and list_item.published_at >= reconciliation_lower_bound
                    )
                    should_capture = (
                        existing is None
                        or reconcile_existing
                        or existing_status in {"FAILED", "DISCOVERED"}
                        or (
                            (trigger == "manual" or backfill_from is not None)
                            and existing_status == "LOCKED"
                        )
                    )
                    if not should_capture:
                        continue

                    try:
                        captured = adapter.capture_item(list_item, token=token)
                        item_result, image_partial = self._store_captured_item(
                            subscription,
                            list_item,
                            captured,
                            digest_date,
                            existing,
                        )
                        partial = partial or image_partial
                        stored_item = item_result["item"]
                        if stored_item.get("capture_status") == "LOCKED":
                            counts["locked_count"] += 1
                        elif stored_item.get("capture_status") in CAPTURED_ITEM_STATUSES:
                            if item_result["created"]:
                                counts["captured_count"] += 1
                            elif item_result["changed"]:
                                counts["updated_count"] += 1
                            if item_result["changed"]:
                                affected_dates.add(digest_date)
                    except HomewayAuthenticationError:
                        raise
                    except Exception as exc:
                        partial = True
                        counts["failed_count"] += 1
                        self.db.upsert_subscription_item(
                            subscription_id,
                            {
                                "provider": "homeway",
                                "external_item_id": list_item.external_item_id,
                                "source_url": list_item.source_url,
                                "published_at": _naive_utc(list_item.published_at),
                                "last_seen_at": _naive_utc(self.now()),
                                "preview_text": list_item.preview_text,
                                "access_scope": "unknown",
                                "capture_status": "FAILED",
                                "failure_code": "CAPTURE_FAILED",
                                "failure_detail": self._safe_error(exc),
                                "digest_date": digest_date,
                                "source_meta": {
                                    "published_at_source": list_item.published_at_text,
                                    "tag_id": list_item.tag_id,
                                    "tag_name": list_item.tag_name,
                                    "is_charge": list_item.is_charge,
                                },
                            },
                        )

                if lower_bound and page_has_older:
                    break
                if cursor_watermark and page_reached_watermark:
                    break
                if lower_bound is None and not cursor_watermark and page_existing_overlap:
                    break
                next_cursor = oldest_homeway_cursor(page)
                if not next_cursor or next_cursor == cursor or next_cursor in cursor_history:
                    break
                cursor_history.add(next_cursor)
                cursor = next_cursor

            timezone_value = ZoneInfo(str(subscription.get("timezone") or "Asia/Shanghai"))
            local_now = self.now().astimezone(timezone_value)
            local_today = local_now.date().isoformat()
            if build_digest:
                captured_items = [
                    item
                    for item in self.db.list_subscription_items(subscription_id)
                    if item.get("capture_status") in CAPTURED_ITEM_STATUSES
                    and str(item.get("raw_markdown") or "").strip()
                ]
                affected_dates.update(
                    item["digest_date"]
                    for item in captured_items
                    if not self.db.get_task(
                        _post_task_id(subscription_id, str(item["external_item_id"]))
                    )
                )
                if reconciliation:
                    affected_dates.add(local_today)
                for digest_date in sorted(affected_dates):
                    content_task_ids.extend(
                        self.organize_subscription_date(subscription_id, digest_date)["task_ids"]
                    )

            now = self.now()
            last_digest_date = subscription.get("last_digest_date")
            last_digest_at = _stored_datetime(subscription.get("last_digest_at"))
            digest_clock = _parse_clock(
                str(subscription.get("digest_time") or "20:30"),
                time(20, 30),
            )
            if build_digest and reconciliation and local_now.time() >= digest_clock:
                last_digest_date = local_today
                last_digest_at = now
            updates = {
                "status": "ACTIVE",
                "last_cursor": newest_cursor or None,
                "last_polled_at": _naive_utc(now),
                "last_success_at": _naive_utc(now),
                "last_digest_date": last_digest_date,
                "last_digest_at": _naive_utc(last_digest_at) if last_digest_at else None,
                "last_error": None,
                "consecutive_failures": 0,
            }
            projected = {**subscription, **updates}
            updates["next_poll_at"] = _naive_utc(self.calculate_next_poll_at(projected, now))
            updated_subscription = self.db.update_content_subscription(subscription_id, updates) or projected
            if account:
                self.db.update_connected_account_runtime(
                    str(subscription["user_id"]),
                    str(account["id"]),
                    status="connected",
                    last_error=None,
                    used=True,
                )
            run_status = "PARTIAL" if partial or counts["failed_count"] else "SUCCESS"
            finished_run = self.db.update_subscription_run(
                run_id,
                {
                    "status": run_status,
                    "finished_at": _naive_utc(now),
                    "cursor_after": newest_cursor or None,
                    **counts,
                },
            )
            return {
                "success": True,
                "subscription": self.subscription_view(updated_subscription),
                "run": finished_run,
                "content_task_ids": content_task_ids,
                # 兼容旧客户端；值已经是一帖一文稿的任务，而不是每日合并稿。
                "digest_task_ids": content_task_ids,
            }
        except HomewayAuthenticationError as exc:
            self._record_poll_failure(subscription, run_id, exc, auth_required=True, counts=counts)
            raise
        except Exception as exc:
            self._record_poll_failure(subscription, run_id, exc, auth_required=False, counts=counts)
            raise

    def organize_captured_content(self, subscription_id: str) -> Dict[str, Any]:
        subscription = self.db.get_content_subscription(subscription_id)
        if not subscription:
            raise ValueError("订阅不存在")
        dates = sorted(
            {
                str(item.get("digest_date") or "")
                for item in self.db.list_subscription_items(subscription_id)
                if item.get("capture_status") in CAPTURED_ITEM_STATUSES
                and str(item.get("raw_markdown") or "").strip()
                and str(item.get("digest_date") or "")
            }
        )
        task_ids: list[str] = []
        created_count = 0
        updated_count = 0
        for digest_date in dates:
            result = self.organize_subscription_date(subscription_id, digest_date)
            task_ids.extend(result["task_ids"])
            created_count += int(result["created_count"])
            updated_count += int(result["updated_count"])
        return {
            "success": True,
            "subscription_id": subscription_id,
            "dates": dates,
            "date_count": len(dates),
            "post_count": len(task_ids),
            "created_count": created_count,
            "updated_count": updated_count,
            "task_ids": task_ids,
        }

    def organize_subscription_date(self, subscription_id: str, digest_date: str) -> Dict[str, Any]:
        subscription = self.db.get_content_subscription(subscription_id)
        if not subscription:
            raise ValueError("订阅不存在")
        items = [
            item
            for item in self.db.list_subscription_items(subscription_id, digest_date=digest_date)
            if item.get("capture_status") in CAPTURED_ITEM_STATUSES and str(item.get("raw_markdown") or "").strip()
        ]
        if not items:
            return {
                "digest_date": digest_date,
                "task_ids": [],
                "created_count": 0,
                "updated_count": 0,
            }

        timezone_name = str(subscription.get("timezone") or "Asia/Shanghai")
        timezone_value = ZoneInfo(timezone_name)
        source_url = str(subscription.get("source_url") or "")
        parent_folder_id = str(subscription.get("folder_id") or "")
        if not parent_folder_id or not self.db.get_folder(parent_folder_id):
            parent_folder_id = str(
                self.db.ensure_folder_path(
                    ["订阅", "投研大师", str(subscription.get("display_name") or "投研大师")],
                    folder_type="auto",
                    source_url=source_url,
                )
                or ""
            )
            self.db.update_content_subscription(subscription_id, {"folder_id": parent_folder_id})
        sort_order = -int(re.sub(r"\D", "", digest_date) or "0")
        date_folder_id = self.db.ensure_child_folder(
            parent_folder_id,
            digest_date,
            folder_type="auto",
            source_url=source_url,
            sort_order=sort_order,
        )

        task_ids: list[str] = []
        created_count = 0
        updated_count = 0
        migration_ready = True
        for item in items:
            published = _stored_datetime(item.get("published_at")) or self.now()
            local_published = published.astimezone(timezone_value)
            task_id = _post_task_id(subscription_id, str(item["external_item_id"]))
            title = _post_title(item, timezone_value)
            raw_markdown, image_manifest = self._adopt_item_assets(
                item,
                task_id=task_id,
            )
            meta = dict(item.get("source_meta") or {})
            meta.update(
                {
                    "subscription_id": subscription_id,
                    "provider": "homeway",
                    "external_item_id": str(item["external_item_id"]),
                    "digest_date": digest_date,
                    "content_task_id": task_id,
                }
            )
            tag_name = str(meta.get("tag_name") or "").strip()
            signature = str(meta.get("signature") or "").strip()
            transcript = raw_markdown.strip()
            if signature and signature not in transcript:
                transcript = f"{transcript}\n\n## 来源声明\n\n> {signature}".strip()
            meta["published_at"] = local_published.isoformat()
            meta["content_version"] = _item_content_hash(raw_markdown, image_manifest, meta)
            summary_lines = [
                "### 内容信息",
                "",
                f"- 发布时间：{local_published.strftime('%Y-%m-%d %H:%M:%S')}",
                f"- 原始链接：[{item['source_url']}]({item['source_url']})",
            ]
            if tag_name:
                summary_lines.append(f"- 标签：{tag_name}")
            task_payload = {
                "video_url": str(item.get("source_url") or source_url),
                "source_url": str(item.get("source_url") or source_url),
                "source_type": "homeway_post",
                "status": TaskStatus.COMPLETED,
                "progress": 1.0,
                "title": title,
                "topic": title,
                "author_name": str(subscription.get("display_name") or ""),
                "author_url": source_url,
                "summary": "\n".join(summary_lines).strip(),
                "transcript": transcript,
                "source_meta": json.dumps(meta, ensure_ascii=False),
                "folder_id": date_folder_id,
                "library_visible": True,
            }
            existing_task = self.db.get_task(task_id)
            comparable_keys = (
                "video_url",
                "source_url",
                "source_type",
                "title",
                "topic",
                "author_name",
                "author_url",
                "summary",
                "transcript",
                "source_meta",
                "folder_id",
                "library_visible",
            )
            if existing_task:
                if any(existing_task.get(key) != task_payload.get(key) for key in comparable_keys):
                    self.db.update_task(task_id, task_payload)
                    updated_count += 1
            else:
                task_payload["created_at"] = _naive_utc(
                    _stored_datetime(item.get("captured_at")) or published
                )
                task_payload["latest_modified_at"] = _naive_utc(self.now())
                self.db.save_task(task_id, task_payload)
                created_count += 1
            content_hash = _item_content_hash(raw_markdown, image_manifest, meta)
            item_changed = any(
                (
                    str(item.get("raw_markdown") or "") != raw_markdown,
                    (item.get("image_manifest") or []) != image_manifest,
                    (item.get("source_meta") or {}) != meta,
                    str(item.get("content_hash") or "") != content_hash,
                )
            )
            if item_changed:
                self.db.upsert_subscription_item(
                    subscription_id,
                    {
                        "external_item_id": str(item["external_item_id"]),
                        "raw_markdown": raw_markdown,
                        "image_manifest": image_manifest,
                        "source_meta": meta,
                        "content_hash": content_hash,
                    },
                )
            if item_changed or not self.db.list_content_assets(task_id):
                self._preserve_item_source(
                    item,
                    task_id=task_id,
                    title=title,
                    raw_markdown=raw_markdown,
                    image_manifest=image_manifest,
                )
            saved_task = self.db.get_task(task_id)
            if (
                not saved_task
                or saved_task.get("source_type") != "homeway_post"
                or saved_task.get("status") != TaskStatus.COMPLETED
            ):
                migration_ready = False
            for entry in image_manifest:
                if entry.get("status") != "downloaded":
                    continue
                relative_path = str(entry.get("relative_path") or "")
                if not relative_path.startswith(f"{task_id}/") or not (self.asset_root / relative_path).is_file():
                    migration_ready = False
            task_ids.append(task_id)

        legacy_task_id = _digest_task_id(subscription_id, digest_date)
        migration_ready = migration_ready and len(task_ids) == len(items)
        if migration_ready:
            self._remove_legacy_digest(legacy_task_id)
        return {
            "digest_date": digest_date,
            "folder_id": date_folder_id,
            "task_ids": task_ids,
            "created_count": created_count,
            "updated_count": updated_count,
        }

    def _remove_legacy_digest(self, legacy_task_id: str) -> None:
        """在一帖一文稿迁移完整后，清除旧日报及其重复图片副本。"""
        delete_assets = getattr(self.db, "delete_content_assets", None)
        if callable(delete_assets):
            delete_assets(
                legacy_task_id,
                relative_path_prefix=f"assets/{legacy_task_id}/",
            )
        if self.db.get_task(legacy_task_id):
            self.db.delete_task(legacy_task_id)
        legacy_asset_dir = self.asset_root / legacy_task_id
        if legacy_asset_dir.is_dir():
            shutil.rmtree(legacy_asset_dir)

    def build_daily_digest(self, subscription_id: str, digest_date: str) -> str | None:
        """Backward-compatible entry point; daily archives now contain one task per post."""
        task_ids = self.organize_subscription_date(subscription_id, digest_date)["task_ids"]
        return task_ids[0] if task_ids else None

    def calculate_next_poll_at(self, subscription: Dict[str, Any], now: datetime | None = None) -> datetime:
        current = now or self.now()
        timezone_value = ZoneInfo(str(subscription.get("timezone") or "Asia/Shanghai"))
        local_now = current.astimezone(timezone_value)
        interval = max(5, min(int(subscription.get("poll_interval_minutes") or 15), 360))
        start_clock = _parse_clock(str(subscription.get("active_window_start") or "08:30"), time(8, 30))
        end_clock = _parse_clock(str(subscription.get("active_window_end") or "18:30"), time(18, 30))
        digest_clock = _parse_clock(str(subscription.get("digest_time") or "20:30"), time(20, 30))

        if local_now.time() < start_clock:
            poll_local = datetime.combine(local_now.date(), start_clock, timezone_value)
        elif local_now.time() <= end_clock:
            poll_local = local_now + timedelta(minutes=interval)
            if poll_local.time() > end_clock:
                poll_local = datetime.combine(local_now.date() + timedelta(days=1), start_clock, timezone_value)
        else:
            poll_local = datetime.combine(local_now.date() + timedelta(days=1), start_clock, timezone_value)

        candidates = [poll_local]
        if not self._digest_finalized_for_local_date(
            subscription,
            local_now=local_now,
            digest_clock=digest_clock,
        ):
            digest_local = datetime.combine(local_now.date(), digest_clock, timezone_value)
            if digest_local <= local_now:
                digest_local = local_now + timedelta(seconds=5)
            candidates.append(digest_local)
        return min(candidates).astimezone(timezone.utc)

    def _adopt_item_assets(
        self,
        item: Dict[str, Any],
        *,
        task_id: str,
    ) -> tuple[str, list[Dict[str, Any]]]:
        """Copy legacy day-bucket images into the post bucket before verified cleanup."""
        raw_markdown = str(item.get("raw_markdown") or "")
        external_item_id = str(item.get("external_item_id") or "")
        item_component = _safe_asset_component(external_item_id, "item")
        target_root = self.asset_root / task_id / "homeway" / item_component
        manifest: list[Dict[str, Any]] = []
        for raw_entry in item.get("image_manifest") or []:
            entry = dict(raw_entry or {})
            if entry.get("status") != "downloaded":
                manifest.append(entry)
                continue
            old_relative = str(entry.get("relative_path") or "").strip()
            old_markdown_path = str(entry.get("markdown_path") or "").strip()
            source_path = self.asset_root / old_relative if old_relative else None
            filename = Path(old_relative).name if old_relative else ""
            if not filename:
                manifest.append(entry)
                continue
            target_path = target_root / filename
            if source_path and source_path.is_file() and source_path.resolve() != target_path.resolve():
                target_path.parent.mkdir(parents=True, exist_ok=True)
                if not target_path.exists() or target_path.stat().st_size != source_path.stat().st_size:
                    shutil.copy2(source_path, target_path)
            if target_path.is_file():
                new_relative = target_path.relative_to(self.asset_root).as_posix()
                new_markdown_path = f"/task-assets/{new_relative}"
                if old_markdown_path:
                    raw_markdown = raw_markdown.replace(old_markdown_path, new_markdown_path)
                entry["relative_path"] = new_relative
                entry["markdown_path"] = new_markdown_path
                entry["size"] = target_path.stat().st_size
            manifest.append(entry)
        return raw_markdown, manifest

    def _preserve_item_source(
        self,
        item: Dict[str, Any],
        *,
        task_id: str,
        title: str,
        raw_markdown: str,
        image_manifest: list[Dict[str, Any]],
    ) -> None:
        if not self.manage_originals:
            return
        image_files = [
            self.asset_root / str(entry.get("relative_path") or "")
            for entry in image_manifest
            if entry.get("status") == "downloaded" and entry.get("relative_path")
        ]
        records = preserve_article_source(
            task_id=task_id,
            content_id=f"homeway-{item['external_item_id']}",
            title=title,
            source_url=str(item.get("source_url") or ""),
            source_type="homeway_article",
            raw_html=str(item.get("raw_html") or ""),
            raw_markdown=raw_markdown,
            asset_paths=image_files,
        )
        upsert_asset = getattr(self.db, "upsert_content_asset", None)
        if callable(upsert_asset):
            for record in records:
                upsert_asset(record)

    def _store_captured_item(
        self,
        subscription: Dict[str, Any],
        list_item: HomewayListItem,
        captured: HomewayCapturedItem,
        digest_date: str,
        existing: Dict[str, Any] | None,
    ) -> tuple[Dict[str, Any], bool]:
        now_naive = _naive_utc(self.now())
        if captured.capture_status == "LOCKED":
            return (
                self.db.upsert_subscription_item(
                    str(subscription["id"]),
                    {
                        "provider": "homeway",
                        "external_item_id": list_item.external_item_id,
                        "source_url": list_item.source_url,
                        "published_at": _naive_utc(list_item.published_at),
                        "last_seen_at": now_naive,
                        "preview_text": list_item.preview_text,
                        "raw_html": None,
                        "raw_markdown": None,
                        "image_manifest": [],
                        "source_meta": captured.source_meta,
                        "access_scope": captured.access_scope,
                        "capture_status": "LOCKED",
                        "failure_code": captured.failure_code,
                        "failure_detail": captured.failure_detail,
                        "digest_date": digest_date,
                    },
                ),
                False,
            )

        task_id = _post_task_id(str(subscription["id"]), list_item.external_item_id)
        image_manifest, image_paths = self._download_images(
            captured.image_urls,
            task_id=task_id,
            external_item_id=list_item.external_item_id,
        )
        raw_markdown = render_homeway_markdown(captured.raw_html, image_paths)
        if not raw_markdown:
            raise HomewaySubscriptionError("投研大师文字详情无法转换为 Markdown")
        source_meta = dict(captured.source_meta or {})
        source_meta.update(
            {
                "subscription_id": str(subscription["id"]),
                "provider": "homeway",
                "external_item_id": list_item.external_item_id,
                "digest_date": digest_date,
                "content_task_id": task_id,
            }
        )
        content_hash = _item_content_hash(raw_markdown, image_manifest, source_meta)
        capture_status = "CAPTURED"
        if existing and existing.get("content_hash"):
            if existing.get("content_hash") != content_hash:
                capture_status = "CAPTURED_UPDATED"
            elif existing.get("capture_status") in CAPTURED_ITEM_STATUSES:
                capture_status = str(existing["capture_status"])
        result = self.db.upsert_subscription_item(
            str(subscription["id"]),
            {
                "provider": "homeway",
                "external_item_id": list_item.external_item_id,
                "source_url": list_item.source_url,
                "published_at": _naive_utc(list_item.published_at),
                "last_seen_at": now_naive,
                "captured_at": now_naive,
                "content_hash": content_hash,
                "preview_text": list_item.preview_text,
                "raw_html": captured.raw_html,
                "raw_markdown": raw_markdown,
                "image_manifest": image_manifest,
                "source_meta": source_meta,
                "access_scope": captured.access_scope,
                "capture_status": capture_status,
                "failure_code": "IMAGE_PARTIAL" if any(entry["status"] == "failed" for entry in image_manifest) else None,
                "failure_detail": "部分原文图片下载失败" if any(entry["status"] == "failed" for entry in image_manifest) else None,
                "digest_date": digest_date,
            },
        )
        self._preserve_item_source(
            {
                "external_item_id": list_item.external_item_id,
                "source_url": list_item.source_url,
                "raw_html": captured.raw_html,
            },
            task_id=task_id,
            title=_post_title(result["item"], ZoneInfo(str(subscription.get("timezone") or "Asia/Shanghai"))),
            raw_markdown=raw_markdown,
            image_manifest=image_manifest,
        )
        return result, any(entry["status"] == "failed" for entry in image_manifest)

    def _download_images(
        self,
        image_urls: list[str],
        *,
        task_id: str,
        external_item_id: str,
    ) -> tuple[list[Dict[str, Any]], Dict[str, str]]:
        if not image_urls:
            return [], {}
        item_component = _safe_asset_component(external_item_id, "item")
        relative_root = Path("homeway") / item_component
        target_dir = self.asset_root / task_id / relative_root
        target_dir.mkdir(parents=True, exist_ok=True)
        session = self.image_session_factory()
        session.headers.update({"User-Agent": USER_AGENT, "Referer": "https://tyds.homeway.com.cn/"})
        manifest: list[Dict[str, Any]] = []
        markdown_paths: Dict[str, str] = {}
        max_bytes = 20 * 1024 * 1024
        for index, url in enumerate(dict.fromkeys(image_urls), start=1):
            record: Dict[str, Any] = {"original_url": url, "status": "failed"}
            if not is_allowed_homeway_image_url(url):
                record["error"] = "图片来源不在投研大师域名范围"
                manifest.append(record)
                continue
            target: Path | None = None
            try:
                response = session.get(url, timeout=25, stream=True)
                response.raise_for_status()
                content_length = int(response.headers.get("Content-Length") or 0)
                if content_length > max_bytes:
                    raise ValueError("图片超过 20MB 限制")
                extension = _image_extension(url, response.headers.get("Content-Type", ""))
                filename = f"image_{index:02d}{extension}"
                target = target_dir / filename
                size = 0
                with target.open("wb") as file:
                    for chunk in response.iter_content(chunk_size=64 * 1024):
                        if not chunk:
                            continue
                        size += len(chunk)
                        if size > max_bytes:
                            raise ValueError("图片超过 20MB 限制")
                        file.write(chunk)
                markdown_path = f"/task-assets/{task_id}/{relative_root.as_posix()}/{filename}"
                markdown_paths[url] = markdown_path
                record.update(
                    {
                        "status": "downloaded",
                        "relative_path": f"{task_id}/{relative_root.as_posix()}/{filename}",
                        "markdown_path": markdown_path,
                        "size": size,
                    }
                )
            except Exception as exc:
                if target and target.exists():
                    target.unlink()
                record["error"] = self._safe_error(exc)
            manifest.append(record)
        return manifest, markdown_paths

    def _resolve_homeway_account(
        self,
        user_id: str,
        connected_account_id: str | None,
        *,
        required: bool,
    ) -> tuple[Dict[str, Any] | None, str]:
        accounts = [
            account
            for account in self.db.list_connected_accounts(user_id)
            if account.get("provider") == "homeway" and account.get("credential_type") == "web_qtstr"
        ]
        account = None
        if connected_account_id:
            account = next(
                (item for item in accounts if str(item.get("id") or "") == connected_account_id),
                None,
            )
            if account is None:
                raise HomewayAuthenticationError("所选投研大师账号不存在或不属于当前用户")
        elif accounts:
            account = accounts[-1]
        if account is None:
            if required:
                raise HomewayAuthenticationError("请先在设置中导入投研大师登录态 web_qtstr")
            return None, ""
        secret = self.db.get_connected_account_secret(user_id, str(account["id"])) or {}
        token = str(secret.get("web_qtstr") or "").strip()
        if not token:
            if required:
                raise HomewayAuthenticationError("投研大师账号没有可用的 web_qtstr，请重新导入")
            return account, ""
        return account, token

    @staticmethod
    def _digest_finalized_for_local_date(
        subscription: Dict[str, Any],
        *,
        local_now: datetime,
        digest_clock: time,
    ) -> bool:
        if str(subscription.get("last_digest_date") or "") != local_now.date().isoformat():
            return False
        finalized_at = _stored_datetime(subscription.get("last_digest_at"))
        if finalized_at is None:
            return False
        local_finalized_at = finalized_at.astimezone(local_now.tzinfo or timezone.utc)
        return (
            local_finalized_at.date() == local_now.date()
            and local_finalized_at.time() >= digest_clock
        )

    def _poll_lower_bound(
        self,
        subscription: Dict[str, Any],
        *,
        backfill_from: datetime | None = None,
    ) -> datetime | None:
        now = self.now()
        if backfill_from is not None:
            if backfill_from.tzinfo is None:
                return backfill_from.replace(tzinfo=timezone.utc)
            return backfill_from.astimezone(timezone.utc)
        if subscription.get("last_success_at"):
            return None
        timezone_value = ZoneInfo(str(subscription.get("timezone") or "Asia/Shanghai"))
        local_now = now.astimezone(timezone_value)
        mode = str(subscription.get("initial_sync_mode") or "from_now")
        if mode == "today":
            return datetime.combine(local_now.date(), time.min, timezone_value).astimezone(timezone.utc)
        if mode == "last_7_days":
            return datetime.combine(
                local_now.date() - timedelta(days=6),
                time.min,
                timezone_value,
            ).astimezone(timezone.utc)
        created_at = _stored_datetime(subscription.get("created_at"))
        return created_at or now

    @staticmethod
    def _digest_date(subscription: Dict[str, Any], published_at: datetime) -> str:
        timezone_value = ZoneInfo(str(subscription.get("timezone") or "Asia/Shanghai"))
        return published_at.astimezone(timezone_value).date().isoformat()

    def _record_poll_failure(
        self,
        subscription: Dict[str, Any],
        run_id: str,
        error: Exception,
        *,
        auth_required: bool,
        counts: Dict[str, int],
    ) -> None:
        now = self.now()
        failures = int(subscription.get("consecutive_failures") or 0) + 1
        detail = self._safe_error(error)
        if auth_required:
            status = "AUTH_REQUIRED"
            next_poll_at = None
            account_id = str(subscription.get("connected_account_id") or "")
            if account_id:
                self.db.update_connected_account_runtime(
                    str(subscription["user_id"]),
                    account_id,
                    status="error",
                    last_error=detail,
                )
        else:
            status = "DEGRADED" if failures < 3 else "ERROR"
            delay_minutes = min(15 * (2 ** (failures - 1)), 360)
            next_poll_at = _naive_utc(now + timedelta(minutes=delay_minutes))
        self.db.update_content_subscription(
            str(subscription["id"]),
            {
                "status": status,
                "last_polled_at": _naive_utc(now),
                "last_error": detail,
                "consecutive_failures": failures,
                "next_poll_at": next_poll_at,
            },
        )
        self.db.update_subscription_run(
            run_id,
            {
                "status": "FAILED",
                "finished_at": _naive_utc(now),
                "error_code": "AUTH_REQUIRED" if auth_required else "POLL_FAILED",
                "error_detail": detail,
                **counts,
            },
        )

    @staticmethod
    def _safe_error(error: Exception) -> str:
        message = str(error or "").strip() or error.__class__.__name__
        message = re.sub(
            r"([?&](?:token|web_qtstr|access_token|sign)=)[^&#\s]+",
            r"\1<redacted>",
            message,
            flags=re.IGNORECASE,
        )
        return message[:1000]

    @staticmethod
    def _validate_clock(value: str, label: str) -> None:
        try:
            datetime.strptime(str(value or ""), "%H:%M")
        except ValueError as exc:
            raise ValueError(f"{label}必须使用 HH:MM 格式") from exc

    @staticmethod
    def _validate_timezone(value: str) -> None:
        try:
            ZoneInfo(str(value or ""))
        except Exception as exc:
            raise ValueError("订阅时区不正确") from exc
