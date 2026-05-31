import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, path)

from src.main.python.sheng_wen import api as api_module
from src.main.python.sheng_wen.db import TaskDB


class TestConnectedAccountsApi(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.original_db = api_module.db
        api_module.db = TaskDB(
            file_path=os.path.join(self.temp_dir.name, "tasks.json"),
            sqlite_path=os.path.join(self.temp_dir.name, "test.db"),
        )
        self.addCleanup(lambda: setattr(api_module, "db", self.original_db))
        self.client = TestClient(api_module.app)

    def test_lists_supported_capture_providers(self):
        response = self.client.get("/providers")

        self.assertEqual(response.status_code, 200)
        providers = {item["id"]: item for item in response.json()}
        self.assertIn("bilibili", providers)
        self.assertEqual(providers["bilibili"]["credential_types"], ["sessdata_bundle"])
        self.assertIn("xiaoetong", providers)
        self.assertIn("homeway", providers)

    def test_connected_account_crud_is_user_scoped_and_redacted(self):
        create_response = self.client.put(
            "/connected-accounts/bilibili",
            headers={"X-ShengWen-User-Id": "user-a"},
            json={
                "credential_type": "sessdata_bundle",
                "payload": {"SESSDATA": "user-a-secret-value"},
                "display_name": "我的 B 站",
                "domain_scope": ".bilibili.com",
            },
        )

        self.assertEqual(create_response.status_code, 200)
        account = create_response.json()
        self.assertEqual(account["provider"], "bilibili")
        self.assertEqual(account["display_name"], "我的 B 站")
        self.assertIn("****", account["secret_masked"])
        self.assertNotIn("user-a-secret-value", create_response.text)

        user_a_list = self.client.get(
            "/connected-accounts",
            headers={"X-ShengWen-User-Id": "user-a"},
        )
        user_b_list = self.client.get(
            "/connected-accounts",
            headers={"X-ShengWen-User-Id": "user-b"},
        )

        self.assertEqual(user_a_list.status_code, 200)
        self.assertEqual([item["id"] for item in user_a_list.json()], [account["id"]])
        self.assertEqual(user_b_list.status_code, 200)
        self.assertEqual(user_b_list.json(), [])

        forbidden_delete = self.client.delete(
            f"/connected-accounts/{account['id']}",
            headers={"X-ShengWen-User-Id": "user-b"},
        )
        self.assertEqual(forbidden_delete.status_code, 404)

        delete_response = self.client.delete(
            f"/connected-accounts/{account['id']}",
            headers={"X-ShengWen-User-Id": "user-a"},
        )
        self.assertEqual(delete_response.status_code, 204)
        self.assertEqual(
            self.client.get(
                "/connected-accounts",
                headers={"X-ShengWen-User-Id": "user-a"},
            ).json(),
            [],
        )

    def test_connected_account_update_by_id_can_change_domain_scope(self):
        create_response = self.client.put(
            "/connected-accounts/xiaoetong",
            headers={"X-ShengWen-User-Id": "user-a"},
            json={
                "credential_type": "cookie_header",
                "payload": {"cookie_header": "xiaoet_session=first-cookie"},
                "display_name": "小鹅通",
                "domain_scope": "first.h5.xiaoeknow.com",
            },
        )
        account = create_response.json()

        update_response = self.client.put(
            "/connected-accounts/xiaoetong",
            headers={"X-ShengWen-User-Id": "user-a"},
            json={
                "account_id": account["id"],
                "credential_type": "cookie_header",
                "payload": {"cookie_header": "xiaoet_session=second-cookie"},
                "display_name": "小鹅通新店铺",
                "domain_scope": "second.h5.xiaoeknow.com",
            },
        )

        self.assertEqual(update_response.status_code, 200)
        updated = update_response.json()
        self.assertEqual(updated["id"], account["id"])
        self.assertEqual(updated["domain_scope"], "second.h5.xiaoeknow.com")
        self.assertEqual(updated["display_name"], "小鹅通新店铺")
        account_list = self.client.get(
            "/connected-accounts",
            headers={"X-ShengWen-User-Id": "user-a"},
        ).json()
        self.assertEqual(len(account_list), 1)
        self.assertEqual(account_list[0]["domain_scope"], "second.h5.xiaoeknow.com")

    def test_bilibili_task_uses_current_users_connected_account_secret(self):
        captured_payloads = []

        class FakeDownloaderWorker:
            async def add_task(self, payload):
                captured_payloads.append(payload)

        async def fake_resolve_worker_or_raise(worker_factory, task_id=None):
            return FakeDownloaderWorker()

        async def fake_notify_task_update(task_id):
            return None

        self.client.put(
            "/connected-accounts/bilibili",
            headers={"X-ShengWen-User-Id": "user-a"},
            json={
                "credential_type": "sessdata_bundle",
                "payload": {"SESSDATA": "stored-user-a-secret"},
                "display_name": "我的 B 站",
            },
        )

        with patch.object(api_module, "_resolve_worker_or_raise", side_effect=fake_resolve_worker_or_raise), patch.object(
            api_module, "notify_task_update", side_effect=fake_notify_task_update
        ):
            response = self.client.post(
                "/tasks/",
                headers={"X-ShengWen-User-Id": "user-a"},
                json={
                    "video_url": "https://www.bilibili.com/video/BV1234567890",
                    "quality": "best",
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(captured_payloads[0]["bilibili_sessdata"], "stored-user-a-secret")
        self.assertNotIn("stored-user-a-secret", response.text)

    def test_task_level_bilibili_sessdata_overrides_connected_account_secret(self):
        captured_payloads = []

        class FakeDownloaderWorker:
            async def add_task(self, payload):
                captured_payloads.append(payload)

        async def fake_resolve_worker_or_raise(worker_factory, task_id=None):
            return FakeDownloaderWorker()

        async def fake_notify_task_update(task_id):
            return None

        self.client.put(
            "/connected-accounts/bilibili",
            headers={"X-ShengWen-User-Id": "user-a"},
            json={
                "credential_type": "sessdata_bundle",
                "payload": {"SESSDATA": "stored-user-a-secret"},
            },
        )

        with patch.object(api_module, "_resolve_worker_or_raise", side_effect=fake_resolve_worker_or_raise), patch.object(
            api_module, "notify_task_update", side_effect=fake_notify_task_update
        ):
            response = self.client.post(
                "/tasks/",
                headers={"X-ShengWen-User-Id": "user-a"},
                json={
                    "video_url": "https://www.bilibili.com/video/BV1234567890",
                    "quality": "best",
                    "bilibili_sessdata": "task-level-secret",
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(captured_payloads[0]["bilibili_sessdata"], "task-level-secret")

    def test_xiaoetong_task_uses_current_users_connected_account_cookie(self):
        captured_payloads = []

        class FakeDownloaderWorker:
            async def add_task(self, payload):
                captured_payloads.append(payload)

        async def fake_resolve_worker_or_raise(worker_factory, task_id=None):
            return FakeDownloaderWorker()

        async def fake_notify_task_update(task_id):
            return None

        self.client.put(
            "/connected-accounts/xiaoetong",
            headers={"X-ShengWen-User-Id": "user-a"},
            json={
                "credential_type": "cookie_header",
                "payload": {"cookie_header": "xiaoet_session=user-a-cookie"},
                "display_name": "小鹅通",
                "domain_scope": "appexpqpqic7617.h5.xiaoeknow.com",
            },
        )

        with patch.object(api_module, "_resolve_worker_or_raise", side_effect=fake_resolve_worker_or_raise), patch.object(
            api_module, "notify_task_update", side_effect=fake_notify_task_update
        ):
            response = self.client.post(
                "/tasks/",
                headers={"X-ShengWen-User-Id": "user-a"},
                json={
                    "video_url": (
                        "https://appexpqpqic7617.h5.xiaoeknow.com/p/course/video/v_abc"
                        "?product_id=course_1"
                    ),
                    "quality": "best",
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(captured_payloads[0]["xiaoet_cookie_header"], "xiaoet_session=user-a-cookie")

    def test_homeway_task_uses_current_users_connected_account_token(self):
        captured_payloads = []

        class FakeDownloaderWorker:
            async def add_task(self, payload):
                captured_payloads.append(payload)

        async def fake_resolve_worker_or_raise(worker_factory, task_id=None):
            return FakeDownloaderWorker()

        async def fake_notify_task_update(task_id):
            return None

        self.client.put(
            "/connected-accounts/homeway",
            headers={"X-ShengWen-User-Id": "user-a"},
            json={
                "credential_type": "web_qtstr",
                "payload": {"web_qtstr": "homeway-user-a-token"},
                "display_name": "投研大师",
            },
        )

        with patch.object(api_module, "_resolve_worker_or_raise", side_effect=fake_resolve_worker_or_raise), patch.object(
            api_module, "notify_task_update", side_effect=fake_notify_task_update
        ):
            response = self.client.post(
                "/tasks/",
                headers={"X-ShengWen-User-Id": "user-a"},
                json={
                    "video_url": "https://tyds.homeway.com.cn/#/GraphicVideo?key=5269",
                    "quality": "best",
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(captured_payloads[0]["homeway_web_qtstr"], "homeway-user-a-token")


if __name__ == "__main__":
    unittest.main()
