import os
import sys
import unittest
import uuid


path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, path)

from src.main.python.sheng_wen.db import TaskDB


@unittest.skipUnless(
    os.getenv("SHENGWEN_TEST_DATABASE_URL"),
    "Set SHENGWEN_TEST_DATABASE_URL to run PostgreSQL integration tests",
)
class TestPostgresConnectedAccounts(unittest.TestCase):
    def test_connected_accounts_persist_to_postgres(self):
        store = TaskDB(
            file_path=os.path.join(path, "temp", "postgres-test-tasks.json"),
            database_url=os.environ["SHENGWEN_TEST_DATABASE_URL"],
        )
        user_id = f"user-{uuid.uuid4().hex}"

        account = store.upsert_connected_account(
            user_id=user_id,
            provider="bilibili",
            credential_type="sessdata_bundle",
            secret_payload={"SESSDATA": "postgres-secret"},
            display_name="Postgres Bilibili",
        )

        try:
            accounts = store.list_connected_accounts(user_id)
            self.assertEqual([item["id"] for item in accounts], [account["id"]])
            self.assertEqual(
                store.get_connected_account_secret(user_id, account["id"]),
                {"SESSDATA": "postgres-secret"},
            )
            self.assertTrue(str(store.engine.url).startswith("postgresql+psycopg://"))
        finally:
            store.delete_connected_account(user_id, account["id"])


if __name__ == "__main__":
    unittest.main()
