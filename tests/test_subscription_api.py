import asyncio
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.main.python.xianwen import api as api_module
from src.main.python.xianwen.db import TaskDB
from src.main.python.xianwen.homeway_subscription import (
    HomewayCapturedItem,
    HomewayLecturerPreview,
    HomewayListItem,
    parse_homeway_datetime,
)
from src.main.python.xianwen.subscriptions import SubscriptionService


SOURCE_URL = "https://tyds.homeway.com.cn/#/GraphicLecturer?lecturerId=1669029704"


class ApiFakeHomewayAdapter:
    def preview_subscription(self, source_url, token=None):
        if token != "account-token":
            raise AssertionError("connected account token was not forwarded")
        return HomewayLecturerPreview(
            lecturer_id="1669029704",
            display_name="枪大侠",
            source_url=SOURCE_URL,
            text_menu_name="观点",
        )

    def list_items(self, lecturer_id, *, cursor=None, token=None):
        if token != "account-token":
            raise AssertionError("connected account token was not forwarded")
        if cursor:
            return []
        return [
            HomewayListItem(
                external_item_id="public-api-1",
                lecturer_id=lecturer_id,
                lecturer_name="枪大侠",
                published_at=parse_homeway_datetime("2026-08-14 09:20:00"),
                published_at_text="2026-08-14 09:20:00",
                preview_text="公开市场观察",
                image_urls=[],
                is_charge=False,
            )
        ]

    def capture_item(self, item, *, token=None):
        if token != "account-token":
            raise AssertionError("connected account token was not forwarded")
        return HomewayCapturedItem(
            external_item_id=item.external_item_id,
            capture_status="CAPTURED",
            access_scope="public",
            raw_html="<p>公开正文</p>",
            source_meta={
                "lecturer_name": "枪大侠",
                "published_at_source": item.published_at_text,
                "is_charge": False,
            },
        )


class SubscriptionApiTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.previous_secret = os.environ.get("XIANWEN_CREDENTIAL_SECRET")
        os.environ["XIANWEN_CREDENTIAL_SECRET"] = "subscription-api-test-secret"
        self.addCleanup(self._restore_secret)

        self.original_db = api_module.db
        api_module.db = TaskDB(sqlite_path=str(self.root / "test.db"))
        self.addCleanup(lambda: setattr(api_module, "db", self.original_db))
        api_module._subscription_poll_locks.clear()

        account = api_module.db.upsert_connected_account(
            user_id="local-user",
            provider="homeway",
            credential_type="web_qtstr",
            secret_payload={"web_qtstr": "account-token"},
            display_name="投研大师",
            domain_scope="homeway.com.cn",
        )
        self.account_id = account["id"]
        self.service = SubscriptionService(
            api_module.db,
            self.root / "temp" / "task-assets",
            adapter_factory=ApiFakeHomewayAdapter,
            now_provider=lambda: datetime(2026, 8, 14, 4, 0, tzinfo=timezone.utc),
        )
        self.service_patch = patch.object(
            api_module,
            "get_subscription_service",
            return_value=self.service,
        )
        self.service_patch.start()
        self.addCleanup(self.service_patch.stop)
        self.notify_patch = patch.object(api_module, "notify_task_update", new=AsyncMock())
        self.notify = self.notify_patch.start()
        self.addCleanup(self.notify_patch.stop)
        self.client = TestClient(api_module.app)

    def _restore_secret(self):
        if self.previous_secret is None:
            os.environ.pop("XIANWEN_CREDENTIAL_SECRET", None)
        else:
            os.environ["XIANWEN_CREDENTIAL_SECRET"] = self.previous_secret

    def test_subscription_api_and_persistent_scheduler_flow(self):
        preview = self.client.post(
            "/subscriptions/preview",
            json={"source_url": SOURCE_URL, "connected_account_id": self.account_id},
        )
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.json()["display_name"], "枪大侠")
        self.assertNotIn("account-token", preview.text)

        created = self.client.post(
            "/subscriptions",
            json={
                "source_url": SOURCE_URL,
                "connected_account_id": self.account_id,
                "initial_sync_mode": "today",
            },
        )
        self.assertEqual(created.status_code, 201)
        subscription_id = created.json()["id"]

        duplicate = self.client.post(
            "/subscriptions",
            json={
                "source_url": SOURCE_URL,
                "connected_account_id": self.account_id,
                "initial_sync_mode": "today",
            },
        )
        self.assertEqual(duplicate.status_code, 409)

        processed = asyncio.run(api_module._run_due_subscriptions_once())
        self.assertEqual(processed, 1)
        after_scheduled = self.client.get(f"/subscriptions/{subscription_id}")
        self.assertEqual(after_scheduled.status_code, 200)
        self.assertEqual(after_scheduled.json()["captured_item_count"], 1)
        self.assertEqual(after_scheduled.json()["items"][0]["raw_markdown"], "公开正文")

        manual = self.client.post(
            f"/subscriptions/{subscription_id}/poll",
            json={"reconciliation": False, "build_digest": True},
        )
        self.assertEqual(manual.status_code, 200)
        task_id = manual.json()["digest_task_ids"][0]
        self.assertEqual(api_module.db.get_task(task_id)["title"], "枪大侠｜2026-08-14")
        self.notify.assert_awaited_once_with(task_id)

        runs = self.client.get(f"/subscriptions/{subscription_id}/runs")
        self.assertEqual(runs.status_code, 200)
        self.assertEqual([run["trigger"] for run in runs.json()], ["manual", "scheduled"])

        denied = self.client.get(
            f"/subscriptions/{subscription_id}",
            headers={"X-XianWen-User-Id": "another-user"},
        )
        self.assertEqual(denied.status_code, 404)

        paused = self.client.patch(
            f"/subscriptions/{subscription_id}",
            json={"status": "PAUSED"},
        )
        self.assertEqual(paused.status_code, 200)
        self.assertEqual(paused.json()["status"], "PAUSED")

        removed = self.client.delete(f"/subscriptions/{subscription_id}")
        self.assertEqual(removed.status_code, 204)
        self.assertEqual(self.client.get("/subscriptions").json(), [])
        self.assertIsNotNone(api_module.db.get_task(task_id))
        self.assertEqual(len(api_module.db.list_subscription_items(subscription_id)), 1)


if __name__ == "__main__":
    unittest.main()
