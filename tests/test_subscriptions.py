import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.main.python.xianwen.db import TaskDB
from src.main.python.xianwen.homeway_subscription import (
    HomewayCapturedItem,
    HomewayLecturerPreview,
    HomewayListItem,
    parse_homeway_datetime,
)
from src.main.python.xianwen.git_sync import build_library_files
from src.main.python.xianwen.subscriptions import SubscriptionService


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

    def test_poll_captures_text_image_locked_metadata_and_daily_digest(self):
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
        self.assertIn("/task-assets/homeway-digest-", captured["raw_markdown"])

        image_path = self.root / "data" / "assets" / captured["image_manifest"][0]["relative_path"]
        self.assertEqual(image_path.read_bytes(), b"png-data")
        self.assertEqual(len(result["digest_task_ids"]), 1)
        task = self.store.get_task(result["digest_task_ids"][0])
        self.assertEqual(task["source_type"], "homeway_daily_digest")
        self.assertEqual(task["title"], "枪大侠｜2026-08-14")
        self.assertIn("公开正文", task["transcript"])
        self.assertIn("来源 ID：`public-1`", task["transcript"])
        self.assertNotIn("需要会员的内容", task["transcript"])
        self.assertEqual(task["folder_id"], subscription["folder_id"])
        self.assertEqual([folder["name"] for folder in self.store.list_folders()], ["订阅", "投研大师", "枪大侠"])

        generated, document_count = build_library_files(self.store, project_root=self.root)
        content_dir = "内容/枪大侠｜2026-08-14"
        self.assertEqual(document_count, 1)
        self.assertIn(f"{content_dir}/枪大侠｜2026-08-14.md", generated)
        self.assertIn(f"{content_dir}/原始正文.md", generated)
        self.assertNotIn(f"{content_dir}/assets/homeway/public-1/image_01.png", generated)
        raw_export = generated[f"{content_dir}/原始正文.md"].content.decode("utf-8")
        self.assertNotIn("/task-assets/", raw_export)
        main = generated[f"{content_dir}/枪大侠｜2026-08-14.md"].content.decode("utf-8")
        raw = generated[f"{content_dir}/原始正文.md"].content.decode("utf-8")
        self.assertIn("[[原始正文]]", main)
        self.assertNotIn("assets/homeway/public-1/image_01.png", raw)
        self.assertNotIn(str(self.root), main + raw)

    def test_repeated_poll_is_idempotent_and_keeps_digest_timestamp_stable(self):
        subscription = self.create_subscription()
        first = self.service.poll_subscription(subscription["id"], trigger="manual", build_digest=True)
        task_id = first["digest_task_ids"][0]
        first_task = self.store.get_task(task_id)

        second = self.service.poll_subscription(subscription["id"], trigger="manual", build_digest=True)
        second_task = self.store.get_task(task_id)

        self.assertEqual(second["run"]["captured_count"], 0)
        self.assertEqual(second["run"]["updated_count"], 0)
        self.assertEqual(len(self.store.list_subscription_items(subscription["id"])), 2)
        self.assertEqual(first_task["latest_modified_at"], second_task["latest_modified_at"])

    def test_next_reconciliation_archives_items_published_after_prior_digest(self):
        subscription = self.create_subscription()
        first = self.service.poll_subscription(
            subscription["id"],
            trigger="scheduled",
            build_digest=False,
        )
        self.assertEqual(first["digest_task_ids"], [])

        self.now = datetime(2026, 8, 15, 4, 0, tzinfo=timezone.utc)
        second = self.service.poll_subscription(
            subscription["id"],
            trigger="reconciliation",
            reconciliation=True,
            build_digest=True,
        )
        self.assertEqual(len(second["digest_task_ids"]), 1)
        task = self.store.get_task(second["digest_task_ids"][0])
        self.assertEqual(task["title"], "枪大侠｜2026-08-14")

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

    def test_cancel_stops_future_runs_but_preserves_content(self):
        subscription = self.create_subscription()
        result = self.service.poll_subscription(subscription["id"], trigger="manual", build_digest=True)
        task_id = result["digest_task_ids"][0]

        self.assertTrue(self.store.cancel_content_subscription(subscription["id"], "local-user"))
        self.assertEqual(self.store.list_content_subscriptions("local-user"), [])
        self.assertEqual(len(self.store.list_subscription_items(subscription["id"])), 2)
        self.assertIsNotNone(self.store.get_task(task_id))


if __name__ == "__main__":
    unittest.main()
