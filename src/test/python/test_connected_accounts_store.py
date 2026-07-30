import os
import sys
import tempfile
import unittest


path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, path)

from src.main.python.xianwen.db import CredentialSecretModel, TaskDB


class TestConnectedAccountsStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = os.path.join(self.temp_dir.name, "test.db")
        self.file_path = os.path.join(self.temp_dir.name, "tasks.json")
        self.store = TaskDB(file_path=self.file_path, sqlite_path=self.db_path)

    def test_database_url_overrides_sqlite_path(self):
        database_url = f"sqlite:///{os.path.join(self.temp_dir.name, 'custom.db')}"

        store = TaskDB(
            file_path=self.file_path,
            sqlite_path=os.path.join(self.temp_dir.name, "ignored.db"),
            database_url=database_url,
        )

        self.assertEqual(str(store.engine.url), database_url)

    def test_connected_account_secret_is_encrypted_and_user_scoped(self):
        account = self.store.upsert_connected_account(
            user_id="user-a",
            provider="bilibili",
            credential_type="sessdata_bundle",
            secret_payload={"SESSDATA": "secret-value-123456"},
            display_name="我的 B 站",
            domain_scope=".bilibili.com",
        )

        self.assertEqual(account["user_id"], "user-a")
        self.assertEqual(account["provider"], "bilibili")
        self.assertEqual(account["status"], "connected")
        self.assertIn("****", account["secret_masked"])
        self.assertNotIn("secret-value-123456", str(account))

        session = self.store.SessionLocal()
        try:
            raw_secret = session.query(CredentialSecretModel).first()
            self.assertIsNotNone(raw_secret)
            self.assertNotIn("secret-value-123456", raw_secret.encrypted_payload)
        finally:
            session.close()

        self.assertEqual(
            self.store.get_connected_account_secret("user-a", account["id"]),
            {"SESSDATA": "secret-value-123456"},
        )
        self.assertIsNone(self.store.get_connected_account_secret("user-b", account["id"]))

    def test_connected_accounts_are_isolated_by_user(self):
        account_a = self.store.upsert_connected_account(
            user_id="user-a",
            provider="bilibili",
            credential_type="sessdata_bundle",
            secret_payload={"SESSDATA": "user-a-secret"},
            display_name="A 的 B 站",
        )
        self.store.upsert_connected_account(
            user_id="user-b",
            provider="bilibili",
            credential_type="sessdata_bundle",
            secret_payload={"SESSDATA": "user-b-secret"},
            display_name="B 的 B 站",
        )

        accounts = self.store.list_connected_accounts("user-a")

        self.assertEqual([account["id"] for account in accounts], [account_a["id"]])
        self.assertEqual(accounts[0]["display_name"], "A 的 B 站")
        self.assertNotIn("user-a-secret", str(accounts))

    def test_delete_connected_account_removes_secret(self):
        account = self.store.upsert_connected_account(
            user_id="user-a",
            provider="homeway",
            credential_type="web_qtstr",
            secret_payload={"web_qtstr": "homeway-secret"},
        )

        self.assertTrue(self.store.delete_connected_account("user-a", account["id"]))

        self.assertEqual(self.store.list_connected_accounts("user-a"), [])
        self.assertIsNone(self.store.get_connected_account_secret("user-a", account["id"]))

        session = self.store.SessionLocal()
        try:
            self.assertEqual(session.query(CredentialSecretModel).count(), 0)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
