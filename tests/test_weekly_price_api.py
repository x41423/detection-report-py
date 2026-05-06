import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import app.db.store as store
from backend.main import app
from tests.auth_api_utils import auth_headers_for_permissions


WEEKLY_PRICE_TEST_PERMISSIONS = [
    "weekly_quote:view",
    "weekly_quote:create",
    "weekly_quote:update",
    "weekly_quote:export",
    "weekly_quote:aliases",
]


class WeeklyPriceApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.original_db_dir = store.DB_DIR
        cls.original_db_path = store.DB_PATH
        store.close_connection()
        store.DB_DIR = cls.temp_dir.name
        store.DB_PATH = os.path.join(cls.temp_dir.name, "weekly-price-api-test.db")
        store._connection = None
        cls.client_ctx = TestClient(app)
        cls.client = cls.client_ctx.__enter__()
        cls.client.headers.update(auth_headers_for_permissions(cls.client, WEEKLY_PRICE_TEST_PERMISSIONS))

    @classmethod
    def tearDownClass(cls):
        cls.client_ctx.__exit__(None, None, None)
        store.close_connection()
        store.DB_DIR = cls.original_db_dir
        store.DB_PATH = cls.original_db_path
        store._connection = None
        cls.temp_dir.cleanup()

    def test_execute_returns_400_when_output_parent_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            update_path = root / "update.xlsx"
            reference_path = root / "reference.xlsx"
            update_path.write_text("update", encoding="utf-8")
            reference_path.write_text("reference", encoding="utf-8")

            response = self.client.post(
                "/api/weekly-price/execute",
                json={
                    "update_path": str(update_path),
                    "reference_path": str(reference_path),
                    "output_path": str(root / "missing" / "custom-output.xlsx"),
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("\u8f93\u51fa\u8def\u5f84", response.json()["detail"])

    def test_preview_upload_returns_preview_payload(self):
        with patch(
            "backend.api.routes.weekly_price.service.preview",
            return_value={
                "success": True,
                "message": "preview-ok",
                "matched_count": 3,
                "updated_count": 3,
                "matched_items": [],
                "not_matched": [],
                "not_matched_count": 0,
                "not_matched_unique_count": 0,
                "suggested_matches": [],
                "alias_hit_count": 0,
                "warnings": [],
                "update_start_row": 1,
                "reference_start_row": 1,
            },
        ):
            response = self.client.post(
                "/api/weekly-price/preview/upload",
                files=[
                    (
                        "update_file",
                        (
                            "update.xlsx",
                            b"update",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        ),
                    ),
                    (
                        "reference_file",
                        (
                            "reference.xlsx",
                            b"reference",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        ),
                    ),
                ],
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["matched_count"], 3)

    def test_execute_upload_returns_downloadable_file(self):
        def fake_execute(update_path: str, reference_path: str, output_path: str):
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(b"fake-xlsx")
            return {
                "success": True,
                "message": "execute-ok",
                "matched_count": 4,
                "updated_count": 4,
                "matched_items": [],
                "not_matched": [],
                "not_matched_count": 0,
                "not_matched_unique_count": 0,
                "alias_hit_count": 0,
                "warnings": [],
                "output_path": output_path,
                "backup_path": None,
            }

        with patch("backend.api.routes.weekly_price.service.execute", side_effect=fake_execute):
            response = self.client.post(
                "/api/weekly-price/execute/upload",
                files=[
                    (
                        "update_file",
                        (
                            "update.xlsx",
                            b"update",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        ),
                    ),
                    (
                        "reference_file",
                        (
                            "reference.xlsx",
                            b"reference",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        ),
                    ),
                ],
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"fake-xlsx")
        self.assertIn("attachment;", response.headers["content-disposition"])
        self.assertEqual(response.headers["x-operation-message"], "execute-ok")
        self.assertEqual(response.headers["x-matched-count"], "4")
        self.assertEqual(response.headers["x-updated-count"], "4")

    def test_preview_endpoint_requires_authentication(self):
        self.client.headers.clear()

        response = self.client.post("/api/weekly-price/preview", json={"update_path": "a", "reference_path": "b"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "AUTH_REQUIRED")
        self.client.headers.update(auth_headers_for_permissions(self.client, WEEKLY_PRICE_TEST_PERMISSIONS))

    def test_execute_endpoint_requires_update_permission(self):
        self.client.headers.clear()
        self.client.headers.update(auth_headers_for_permissions(self.client, ["weekly_quote:view"]))

        response = self.client.post(
            "/api/weekly-price/execute",
            json={"update_path": "a", "reference_path": "b", "output_path": "c"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"]["code"], "PERMISSION_DENIED")
        self.client.headers.clear()
        self.client.headers.update(auth_headers_for_permissions(self.client, WEEKLY_PRICE_TEST_PERMISSIONS))


if __name__ == "__main__":
    unittest.main()
