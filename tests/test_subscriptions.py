import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.main.python.xianwen.db import TaskDB, TaskStatus
from src.main.python.xianwen.homeway_subscription import (
    HomewayCapturedItem,
    HomewayLecturerPreview,
    HomewayListItem,
    parse_homeway_datetime,
)
from src.main.python.xianwen.git_sync import build_library_files
from src.main.python.xianwen.subscriptions import SubscriptionService, _digest_task_id


IMAGE_URL = "https://tyds-cos.homeway.com.cn/article/source.png"


class FakeHomewayAdapter:
    def preview_subscription(self, source_url, token=None):
        if token != "account-token":
            raise AssertionError("connected account token was not forwarded")
        return HomewayLecturerPreview(
            lecturer_id="1669029704",
            display_name="枪大侠",
            source_url="https://tyds.homeway.com.cn/#/GraphicLecturer?lecturerId=1669029704",
            text_menu_name="观点",
        )

    def list_items(self, lecturer_id, *, cursor=None, token=None):
        if lecturer_id != "1669029704" or token != "account-token":
            raise AssertionError("subscription identity was not forwarded")
        if cursor:
            return []
        return [
            HomewayListItem(
                external_item_id="public-1",
                lecturer_id=lecturer_id,
                lecturer_name="枪大侠",
                published_at=parse_homeway_datetime("2026-08-14 09:20:00"),
                published_at_text="2026-08-14 09:20:00",
                preview_text="【短线】公开市场观察",
                image_urls=[IMAGE_URL],
                is_charge=False,
                tag_name="实战圈·机会点评",
            ),
            HomewayListItem(
                external_item_id="paid-1",
                lecturer_id=lecturer_id,
                lecturer_name="枪大侠",
                published_at=parse_homeway_datetime("2026-08-14 09:25:00"),
                published_at_text="2026-08-14 09:25:00",
                preview_text="需要会员的内容",
                image_urls=[],
                is_charge=True,
            ),
        ]

    def capture_item(self, item, *, token=None):
        if token != "account-token":
            raise AssertionError("token missing")
        if item.external_item_id == "paid-1":
            return HomewayCapturedItem(
                external_item_id=item.external_item_id,
                capture_status="LOCKED",
                access_scope="locked",
                source_meta={
                    "lecturer_name": "枪大侠",
                    "published_at_source": item.published_at_text,
                    "is_charge": True,
                },
                failure_code="ENTITLEMENT_REQUIRED",
                failure_detail="当前账号没有得到站点明确的全文阅读授权",
            )
        return HomewayCapturedItem(
            external_item_id=item.external_item_id,
            capture_status="CAPTURED",
            access_scope="public",
            raw_html=f'<p>公开正文<img src="{IMAGE_URL}"></p>',
            image_urls=[IMAGE_URL],
            source_meta={
                "lecturer_name": "枪大侠",
                "published_at_source": item.published_at_text,
                "tag_name": item.tag_name,
                "signature": "仅供学习交流，不构成投资建议。",
                "is_charge": False,
            },
        )


class FakeImageResponse:
    headers = {"Content-Type": "image/png", "Content-Length": "8"}

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size=8192):
        yield b"png-data"


class FakeImageSession:
    def __init__(self):
        self.headers = {}

    def get(self, url, **kwargs):
        if url != IMAGE_URL:
            raise AssertionError("unexpected image URL")
        return FakeImageResponse()


class SubscriptionServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.previous_secret = os.environ.get("XIANWEN_CREDENTIAL_SECRET")
        os.environ["XIANWEN_CREDENTIAL_SECRET"] = "subscription-test-secret"
        self.addCleanup(self._restore_secret)
        self.root = Path(self.temp_dir.name)
        self.store = TaskDB(sqlite_path=str(self.root / "test.db"))
        self.account = self.store.upsert_connected_account(
            user_id="local-user",
            provider="homeway",
            credential_type="web_qtstr",
            secret_payload={"web_qtstr": "account-token"},
            display_name="投研大师",
            domain_scope="homeway.com.cn",
        )
        self.now = datetime(2026, 8, 14, 4, 0, tzinfo=timezone.utc)
        self.service = SubscriptionService(
            self.store,
            self.root / "data" / "assets",
            adapter_factory=FakeHomewayAdapter,
            image_session_factory=FakeImageSession,
            now_provider=lambda: self.now,
        )

    def _restore_secret(self):
        if self.previous_secret is None:
            os.environ.pop("XIANWEN_CREDENTIAL_SECRET", None)
        else:
            os.environ["XIANWEN_CREDENTIAL_SECRET"] = self.previous_secret

    def create_subscription(self):
        return self.service.create_subscription(
            "local-user",
            "https://tyds.homeway.com.cn/#/GraphicLecturer?lecturerId=1669029704",
            connected_account_id=self.account["id"],
            initial_sync_mode="today",
        )

    def test_poll_captures_text_image_locked_metadata_and_one_document_per_post(self):
        subscription = self.create_subscription()
        result = self.service.poll_subscription(
            subscription["id"],
            trigger="manual",
            build_digest=True,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["run"]["status"], "SUCCESS")
        self.assertEqual(result["run"]["captured_count"], 1)
        self.assertEqual(result["run"]["locked_count"], 1)
        items = self.store.list_subscription_items(subscription["id"])
        captured = next(item for item in items if item["external_item_id"] == "public-1")
        locked = next(item for item in items if item["external_item_id"] == "paid-1")
        self.assertEqual(captured["capture_status"], "CAPTURED")
        self.assertEqual(locked["capture_status"], "LOCKED")
        self.assertIsNone(locked["raw_markdown"])
        self.assertIn("/task-assets/homeway-post-", captured["raw_markdown"])

        image_path = self.root / "data" / "assets" / captured["image_manifest"][0]["relative_path"]
        self.assertEqual(image_path.read_bytes(), b"png-data")
        self.assertEqual(len(result["content_task_ids"]), 1)
        task = self.store.get_task(result["content_task_ids"][0])
        self.assertEqual(task["source_type"], "homeway_post")
        self.assertEqual(task["title"], "2026-08-14 09:20｜【短线】公开市场观察")
        self.assertIn("公开正文", task["transcript"])
        self.assertNotIn("需要会员的内容", task["transcript"])
        date_folder = self.store.get_folder(task["folder_id"])
        month_folder = self.store.get_folder(date_folder["parent_id"])
        year_folder = self.store.get_folder(month_folder["parent_id"])
        self.assertEqual(date_folder["name"], "14日")
        self.assertEqual(month_folder["name"], "08月")
        self.assertEqual(year_folder["name"], "2026")
        self.assertEqual(year_folder["parent_id"], subscription["folder_id"])

        generated, document_count = build_library_files(self.store, project_root=self.root)
        content_dir = "内容/2026-08-14 09-20｜【短线】公开市场观察"
        self.assertEqual(document_count, 1)
        self.assertIn(f"{content_dir}/2026-08-14 09-20｜【短线】公开市场观察.md", generated)
        self.assertNotIn(f"{content_dir}/原始正文.md", generated)
        self.assertNotIn(f"{content_dir}/assets/homeway/public-1/image_01.png", generated)
        main = generated[f"{content_dir}/2026-08-14 09-20｜【短线】公开市场观察.md"].content.decode("utf-8")
        self.assertIn("## 正文", main)
        self.assertIn("公开正文", main)
        self.assertNotIn("/task-assets/", main)
        self.assertNotIn("assets/homeway/public-1/image_01.png", main)
        self.assertNotIn(str(self.root), main)
        daily_index = "藏经阁/订阅/投研大师/枪大侠/2026/08月/14日/_目录.md"
        self.assertIn(daily_index, generated)
        self.assertIn("公开市场观察", generated[daily_index].content.decode("utf-8"))

    def test_repeated_poll_is_idempotent_and_keeps_digest_timestamp_stable(self):
        subscription = self.create_subscription()
        first = self.service.poll_subscription(subscription["id"], trigger="manual", build_digest=True)
        task_id = first["content_task_ids"][0]
        first_task = self.store.get_task(task_id)

        second = self.service.poll_subscription(subscription["id"], trigger="manual", build_digest=True)
        second_task = self.store.get_task(task_id)

        self.assertEqual(second["run"]["captured_count"], 0)
        self.assertEqual(second["run"]["updated_count"], 0)
        self.assertEqual(len(self.store.list_subscription_items(subscription["id"])), 2)
        self.assertEqual(first_task["latest_modified_at"], second_task["latest_modified_at"])
        self.assertEqual(second["content_task_ids"], [])

    def test_organize_existing_daily_digest_removes_replaced_images_and_is_idempotent(self):
        subscription = self.create_subscription()
        digest_date = "2026-08-14"
        legacy_task_id = _digest_task_id(subscription["id"], digest_date)
        old_relative = f"{legacy_task_id}/homeway/public-1/image_01.png"
        old_image = self.root / "data" / "assets" / old_relative
        old_image.parent.mkdir(parents=True, exist_ok=True)
        old_image.write_bytes(b"legacy-image")
        self.store.upsert_content_asset(
            {
                "task_id": legacy_task_id,
                "role": "original",
                "asset_type": "image",
                "relative_path": f"assets/{old_relative}",
                "sha256": "legacy-image-sha",
                "size_bytes": len(b"legacy-image"),
                "status": "available",
            }
        )
        legacy_original = self.root / "data" / "originals" / "homeway" / "2026" / "legacy" / "article.html"
        legacy_original.parent.mkdir(parents=True, exist_ok=True)
        legacy_original.write_text("<p>原始响应</p>", encoding="utf-8")
        self.store.upsert_content_asset(
            {
                "task_id": legacy_task_id,
                "role": "original",
                "asset_type": "article_html",
                "relative_path": "originals/homeway/2026/legacy/article.html",
                "sha256": "legacy-original-sha",
                "size_bytes": legacy_original.stat().st_size,
                "status": "available",
            }
        )
        old_markdown_path = f"/task-assets/{old_relative}"
        self.store.upsert_subscription_item(
            subscription["id"],
            {
                "provider": "homeway",
                "external_item_id": "public-1",
                "source_url": "https://tyds.homeway.com.cn/#/GraphicView?key=public-1",
                "published_at": datetime(2026, 8, 14, 1, 20),
                "content_hash": "legacy-hash",
                "preview_text": "【短线】公开市场观察",
                "raw_html": "<p>公开正文</p>",
                "raw_markdown": f"公开正文\n\n![原文图片]({old_markdown_path})",
                "image_manifest": [
                    {
                        "original_url": IMAGE_URL,
                        "status": "downloaded",
                        "relative_path": old_relative,
                        "markdown_path": old_markdown_path,
                        "size": len(b"legacy-image"),
                    }
                ],
                "source_meta": {"published_at_source": "2026-08-14 09:20:00"},
                "access_scope": "public",
                "capture_status": "CAPTURED",
                "digest_date": digest_date,
                "digest_task_id": legacy_task_id,
            },
        )
        self.store.save_task(
            legacy_task_id,
            {
                "video_url": subscription["source_url"],
                "source_url": subscription["source_url"],
                "source_type": "homeway_daily_digest",
                "status": TaskStatus.COMPLETED,
                "progress": 1.0,
                "title": "枪大侠｜2026-08-14",
                "summary": "旧日报",
                "transcript": "旧日报正文",
                "folder_id": subscription["folder_id"],
                "library_visible": True,
            },
        )

        first = self.service.organize_captured_content(subscription["id"])
        item = self.store.get_subscription_item(subscription["id"], "public-1")
        post_task_id = item["source_meta"]["content_task_id"]
        new_relative = item["image_manifest"][0]["relative_path"]

        self.assertEqual(first["created_count"], 1)
        self.assertFalse(old_image.exists())
        self.assertTrue((self.root / "data" / "assets" / new_relative).is_file())
        self.assertNotIn(legacy_task_id, item["raw_markdown"])
        self.assertIn(post_task_id, item["raw_markdown"])
        self.assertIsNone(self.store.get_task(legacy_task_id))
        self.assertTrue(self.store.get_task(post_task_id)["library_visible"])
        remaining_legacy_assets = self.store.list_content_assets(legacy_task_id, status=None)
        self.assertEqual([asset["asset_type"] for asset in remaining_legacy_assets], ["article_html"])
        self.assertTrue(legacy_original.is_file())

        second = self.service.organize_captured_content(subscription["id"])
        self.assertEqual(second["created_count"], 0)
        self.assertEqual(second["updated_count"], 0)

    def test_next_reconciliation_archives_items_published_after_prior_digest(self):
        subscription = self.create_subscription()
        first = self.service.poll_subscription(
            subscription["id"],
            trigger="scheduled",
            build_digest=False,
        )
        self.assertEqual(first["content_task_ids"], [])

        self.now = datetime(2026, 8, 15, 4, 0, tzinfo=timezone.utc)
        second = self.service.poll_subscription(
            subscription["id"],
            trigger="reconciliation",
            reconciliation=True,
            build_digest=True,
        )
        self.assertEqual(len(second["content_task_ids"]), 1)
        task = self.store.get_task(second["content_task_ids"][0])
        self.assertEqual(task["source_type"], "homeway_post")

    def test_reconciliation_catches_up_to_durable_cursor_after_multi_day_gap(self):
        subscription = self.create_subscription()
        self.store.update_content_subscription(
            subscription["id"],
            {
                "last_success_at": datetime(2026, 8, 14, 2, 0),
                "last_cursor": "2026-08-14 09:00:00",
            },
        )
        watermark = HomewayListItem(
            external_item_id="item-14",
            lecturer_id="1669029704",
            lecturer_name="枪大侠",
            published_at=parse_homeway_datetime("2026-08-14 09:00:00"),
            published_at_text="2026-08-14 09:00:00",
            preview_text="已采集的水位内容",
            image_urls=[],
            is_charge=False,
        )
        self.store.upsert_subscription_item(
            subscription["id"],
            {
                "provider": "homeway",
                "external_item_id": watermark.external_item_id,
                "source_url": watermark.source_url,
                "published_at": watermark.published_at.replace(tzinfo=None),
                "preview_text": watermark.preview_text,
                "raw_html": "<p>旧正文</p>",
                "raw_markdown": "旧正文",
                "content_hash": "existing-hash",
                "source_meta": {},
                "access_scope": "public",
                "capture_status": "CAPTURED",
                "digest_date": "2026-08-14",
            },
        )

        def item(day):
            published_at_text = f"2026-08-{day:02d} 09:00:00"
            return HomewayListItem(
                external_item_id=f"item-{day}",
                lecturer_id="1669029704",
                lecturer_name="枪大侠",
                published_at=parse_homeway_datetime(published_at_text),
                published_at_text=published_at_text,
                preview_text=f"{day} 日内容",
                image_urls=[],
                is_charge=False,
            )

        pages = {
            None: [item(21), item(20)],
            "2026-08-20 09:00:00": [item(19), item(18)],
            "2026-08-18 09:00:00": [item(17), watermark],
        }

        class CatchUpAdapter:
            def __init__(self):
                self.cursors = []

            def list_items(adapter_self, lecturer_id, *, cursor=None, token=None):
                adapter_self.cursors.append(cursor)
                return pages.get(cursor, [])

            def capture_item(adapter_self, list_item, *, token=None):
                return HomewayCapturedItem(
                    external_item_id=list_item.external_item_id,
                    capture_status="CAPTURED",
                    access_scope="public",
                    raw_html=f"<p>{list_item.preview_text}</p>",
                    source_meta={"published_at_source": list_item.published_at_text},
                )

        adapter = CatchUpAdapter()
        self.service.adapter_factory = lambda: adapter
        self.now = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        result = self.service.poll_subscription(
            subscription["id"],
            trigger="reconciliation",
            reconciliation=True,
            build_digest=False,
        )

        self.assertEqual(
            adapter.cursors,
            [None, "2026-08-20 09:00:00", "2026-08-18 09:00:00"],
        )
        self.assertEqual(result["run"]["captured_count"], 5)
        self.assertEqual(
            {entry["external_item_id"] for entry in self.store.list_subscription_items(subscription["id"])},
            {"item-14", "item-17", "item-18", "item-19", "item-20", "item-21"},
        )

    def test_manual_digest_does_not_finalize_day_and_stale_early_marker_is_repaired(self):
        subscription = self.create_subscription()
        self.service.poll_subscription(subscription["id"], trigger="manual", build_digest=True)
        current = self.store.get_content_subscription(subscription["id"])
        self.assertIsNone(current["last_digest_date"])

        self.store.update_content_subscription(
            subscription["id"],
            {
                "last_digest_date": "2026-08-14",
                "last_digest_at": datetime(2026, 8, 14, 4, 0),
            },
        )
        self.now = datetime(2026, 8, 14, 12, 31, tzinfo=timezone.utc)
        stale = self.store.get_content_subscription(subscription["id"])
        self.assertTrue(self.service.should_finalize_today(stale))

        self.service.poll_subscription(
            subscription["id"],
            trigger="reconciliation",
            reconciliation=True,
            build_digest=True,
        )
        repaired = self.store.get_content_subscription(subscription["id"])
        self.assertEqual(repaired["last_digest_date"], "2026-08-14")
        self.assertFalse(self.service.should_finalize_today(repaired))

    def test_database_lease_prevents_two_scheduler_owners(self):
        subscription = self.create_subscription()
        now_naive = self.now.replace(tzinfo=None)
        first = self.store.claim_due_content_subscriptions("owner-a", now_naive)
        second = self.store.claim_due_content_subscriptions("owner-b", now_naive)
        self.assertEqual([item["id"] for item in first], [subscription["id"]])
        self.assertEqual(second, [])

        self.store.release_content_subscription_lease(subscription["id"], "owner-a")
        third = self.store.claim_due_content_subscriptions("owner-b", now_naive)
        self.assertEqual([item["id"] for item in third], [subscription["id"]])

    def test_backfill_resumes_from_cursor_and_stops_at_requested_start_date(self):
        subscription = self.create_subscription()

        def item(day):
            published_at_text = f"2026-08-{day:02d} 09:00:00"
            return HomewayListItem(
                external_item_id=f"history-{day}",
                lecturer_id="1669029704",
                lecturer_name="枪大侠",
                published_at=parse_homeway_datetime(published_at_text),
                published_at_text=published_at_text,
                preview_text=f"{day} 日历史内容",
                image_urls=[],
                is_charge=False,
            )

        pages = {
            None: [item(14)],
            "2026-08-14 09:00:00": [item(13), item(1)],
        }

        class BackfillAdapter(FakeHomewayAdapter):
            def __init__(adapter_self):
                adapter_self.cursors = []

            def list_items(adapter_self, lecturer_id, *, cursor=None, token=None):
                adapter_self.cursors.append(cursor)
                return pages.get(cursor, [])

            def capture_item(adapter_self, list_item, *, token=None):
                return HomewayCapturedItem(
                    external_item_id=list_item.external_item_id,
                    capture_status="CAPTURED",
                    access_scope="public",
                    raw_html=f"<p>{list_item.preview_text}</p>",
                    source_meta={"published_at_source": list_item.published_at_text},
                )

        adapter = BackfillAdapter()
        self.service.adapter_factory = lambda: adapter
        first = self.service.poll_subscription(
            subscription["id"],
            trigger="backfill",
            build_digest=True,
            backfill_from=datetime(2026, 8, 2, tzinfo=timezone.utc),
            backfill_to=datetime(2026, 8, 14, 23, 59, tzinfo=timezone.utc),
            page_limit=1,
        )
        self.assertFalse(first["scan_complete"])
        self.assertEqual(first["next_cursor"], "2026-08-14 09:00:00")

        second = self.service.poll_subscription(
            subscription["id"],
            trigger="backfill",
            build_digest=True,
            backfill_from=datetime(2026, 8, 2, tzinfo=timezone.utc),
            backfill_to=datetime(2026, 8, 14, 23, 59, tzinfo=timezone.utc),
            start_cursor=first["next_cursor"],
            page_limit=1,
        )
        self.assertTrue(second["scan_complete"])
        self.assertIsNone(second["next_cursor"])
        self.assertEqual(adapter.cursors, [None, "2026-08-14 09:00:00"])
        self.assertEqual(
            {entry["external_item_id"] for entry in self.store.list_subscription_items(subscription["id"])},
            {"history-13", "history-14"},
        )
        coverage = self.service.backfill_view(
            {
                "id": "history-job",
                "subscription_id": subscription["id"],
                "start_date": "2026-01-01",
                "end_date": "2026-08-14",
                "status": "SUCCESS",
            }
        )
        self.assertEqual(coverage["coverage_start_date"], "2026-08-13")
        self.assertEqual(coverage["coverage_end_date"], "2026-08-14")
        self.assertTrue(coverage["source_exhausted_before_start"])

    def test_backfill_job_state_is_durable_and_only_one_active_job_is_created(self):
        subscription = self.create_subscription()
        first = self.store.create_subscription_backfill(subscription["id"], "2026-01-01", "2026-08-14")
        duplicate = self.store.create_subscription_backfill(subscription["id"], "2025-01-01", "2025-12-31")
        self.assertEqual(first["id"], duplicate["id"])
        updated = self.store.update_subscription_backfill(
            first["id"],
            {"status": "PAUSED", "cursor": "2026-07-01 00:00:00", "processed_pages": 3},
        )
        self.assertEqual(updated["status"], "PAUSED")
        self.assertEqual(self.store.latest_subscription_backfill(subscription["id"])["processed_pages"], 3)

    def test_cancel_stops_future_runs_but_preserves_content(self):
        subscription = self.create_subscription()
        result = self.service.poll_subscription(subscription["id"], trigger="manual", build_digest=True)
        task_id = result["content_task_ids"][0]

        self.assertTrue(self.store.cancel_content_subscription(subscription["id"], "local-user"))
        self.assertEqual(self.store.list_content_subscriptions("local-user"), [])
        self.assertEqual(len(self.store.list_subscription_items(subscription["id"])), 2)
        self.assertIsNotNone(self.store.get_task(task_id))


if __name__ == "__main__":
    unittest.main()
