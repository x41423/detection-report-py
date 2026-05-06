import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.db import store
from backend.main import app


class BackendSmokeTests(unittest.TestCase):
    """End-to-end smoke checks.

    Each test gets a fresh temporary auth DB seeded with a super admin so
    permission-protected endpoints (e.g. ``/api/weekly-price/*``) can be
    exercised by an authenticated request without leaking state across
    tests.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self._original_db_dir = store.DB_DIR
        self._original_db_path = store.DB_PATH
        store.close_connection()
        store.DB_DIR = self.temp_dir.name
        store.DB_PATH = os.path.join(self.temp_dir.name, "backend-smoke.db")
        store._connection = None

        self.env_patch = patch.dict(
            os.environ,
            {
                "SEED_SUPER_ADMIN_USERNAME": "smoke.admin",
                "SEED_SUPER_ADMIN_PASSWORD": "smoke-password",
                "SEED_SUPER_ADMIN_FORCE_CHANGE_PASSWORD": "false",
            },
            clear=False,
        )
        self.env_patch.start()

        self.client_ctx = TestClient(app)
        self.client = self.client_ctx.__enter__()

    def tearDown(self):
        self.client_ctx.__exit__(None, None, None)
        self.env_patch.stop()
        store.close_connection()
        store.DB_DIR = self._original_db_dir
        store.DB_PATH = self._original_db_path
        store._connection = None
        self.temp_dir.cleanup()

    def _admin_token(self) -> str:
        response = self.client.post(
            "/api/auth/login",
            json={"username": "smoke.admin", "password": "smoke-password"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["access_token"]

    def _admin_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._admin_token()}"}

    def test_root_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json())

    def test_config_endpoint(self):
        response = self.client.get("/api/config/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("config", body)
        self.assertIsInstance(body["config"], dict)

    def test_transfer_browse_endpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            response = self.client.post("/api/transfer/browse", json={"path": tmpdir})
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body["path"], tmpdir)
            self.assertIn("subdirs", body)
            self.assertIn("files", body)

    def test_transfer_varieties_upload_endpoint(self):
        with patch(
            "backend.api.routes.transfer.doc_service.extract_all_varieties",
            return_value=["白菜", "萝卜"],
        ):
            response = self.client.post(
                "/api/transfer/varieties/upload",
                files=[
                    ("table_files", ("table-1.docx", b"doc-a", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
                    ("table_files", ("table-2.docx", b"doc-b", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
                ],
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 2)
        self.assertEqual(body["varieties"], ["白菜", "萝卜"])

    def test_transfer_find_files_endpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "a.docx").write_bytes(b"a")
            (root / "b.DOCX").write_bytes(b"b")
            (root / "c.txt").write_bytes(b"c")

            response = self.client.post("/api/transfer/find-files", json={"path": str(root)})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(sorted(body["files"]), ["a.docx", "b.DOCX"])
        self.assertEqual(body["path"], str(root))

    def test_transfer_find_files_rejects_invalid_path(self):
        response = self.client.post("/api/transfer/find-files", json={"path": "/nope/not/here"})
        self.assertEqual(response.status_code, 400)

    def test_transfer_log_restore_endpoint(self):
        response = self.client.post("/api/transfer/log-restore", json={"path": "D:\\test"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_transfer_execute_from_paths_requires_files(self):
        response = self.client.post("/api/transfer/execute-from-paths", data={
            "table_paths_json": "[]",
            "small_template_path": "/nope.docx",
            "veg_names_json": '["白菜"]',
        })
        self.assertNotEqual(response.status_code, 200)

    def test_transfer_execute_from_paths_with_missing_template(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            table = root / "table.docx"
            table.write_bytes(b"big")
            response = self.client.post("/api/transfer/execute-from-paths", data={
                "table_paths_json": json.dumps([str(table)]),
                "small_template_path": str(root / "missing.docx"),
                "veg_names_json": '["白菜"]',
            })
        self.assertEqual(response.status_code, 400)
        self.assertIn("小表模板路径", response.json()["detail"])

    def test_pesticide_dedup_json_endpoint(self):
        payload = {
            "json_text": json.dumps(
                [
                    {"variety": "鐧借彍", "rate": "1.000%"},
                    {"variety": "鐧借彍", "rate": "2.000%"},
                ],
                ensure_ascii=False,
            )
        }
        response = self.client.post("/api/pesticide/dedup-json", json=payload)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["removed_count"], 1)
        self.assertEqual(len(body["data"]), 1)

    def test_pesticide_execute_upload_endpoint(self):
        def fake_execute(big_path: str, small_path: str, json_text: str, date_label: str, output_dir: str, inspector_name: str):
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            (Path(output_dir) / "big.docx").write_bytes(b"big")
            (Path(output_dir) / "small.docx").write_bytes(b"small")
            return {
                "success": True,
                "message": "zip-ok",
                "data_count": 1,
                "output_dir": output_dir,
            }

        with patch("backend.api.routes.pesticide.service.execute_task", side_effect=fake_execute):
            response = self.client.post(
                "/api/pesticide/execute/upload",
                data={
                    "json_text": '[{"variety":"白菜","rate":"1.000%"}]',
                    "date_label": "2026年4月24日",
                    "inspector_name": "tester",
                },
                files=[
                    ("big_file", ("big.docx", b"big", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
                    ("small_file", ("small.docx", b"small", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
                ],
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-operation-message"], "zip-ok")
        self.assertIn("attachment;", response.headers["content-disposition"])
        self.assertTrue(response.content.startswith(b"PK"))

    def test_weekly_price_aliases_endpoint(self):
        response = self.client.get(
            "/api/weekly-price/aliases", headers=self._admin_headers()
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("aliases", body)
        self.assertIn("total", body)

    def test_weekly_quote_summary_preview_endpoint(self):
        response = self.client.post(
            "/api/weekly-price/summary/preview",
            headers=self._admin_headers(),
            json={
                "batches": [
                    {
                        "supplier": "\u52fe\u5e84",
                        "quote_date": "2026-04-14",
                        "entries": [
                            {
                                "name": "\u767d\u83dc",
                                "unit": "\u65a4",
                                "price": 2.5,
                            }
                        ],
                    }
                ]
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["total_batches"], 1)
        self.assertEqual(len(body["unit_summaries"]), 5)


if __name__ == "__main__":
    unittest.main()
