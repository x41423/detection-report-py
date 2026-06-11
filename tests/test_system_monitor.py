"""系统中控台 — 单元测试 + API 集成测试。

TDD Step 1：先写测试，预期全部 FAIL。
"""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.db import store
from backend.main import app


class SystemMonitorServiceTests(unittest.TestCase):
    """Service 层单元测试（mock psutil）。"""

    def setUp(self):
        """Mock psutil 环境。Service 层不依赖数据库。"""

    def tearDown(self):
        pass

    @patch("backend.services.system_monitor_service.psutil.cpu_percent", return_value=42.5)
    @patch("backend.services.system_monitor_service.psutil.cpu_count", return_value=8)
    @patch("backend.services.system_monitor_service.psutil.virtual_memory")
    @patch("backend.services.system_monitor_service.psutil.disk_usage")
    @patch("backend.services.system_monitor_service.psutil.Process")
    def test_collect_returns_all_expected_keys(
        self,
        mock_process: MagicMock,
        mock_disk: MagicMock,
        mock_memory: MagicMock,
        mock_cpu_count: MagicMock,
        mock_cpu_pct: MagicMock,
    ):
        mock_memory.return_value = MagicMock(
            total=16 * 1024**3,
            used=4 * 1024**3,
            percent=25.0,
        )
        mock_disk.return_value = MagicMock(
            total=500 * 1024**3,
            used=100 * 1024**3,
            percent=20.0,
        )
        mock_proc = MagicMock()
        mock_proc.memory_info.return_value = MagicMock(rss=300 * 1024**2, vms=600 * 1024**2)
        mock_proc.num_threads.return_value = 4
        mock_process.return_value = mock_proc

        from backend.services.system_monitor_service import SystemMonitorService
        svc = SystemMonitorService()
        result = svc.collect()

        # 顶层字段
        self.assertIn("timestamp", result)
        self.assertIn("uptime_seconds", result)
        self.assertIn("services", result)
        self.assertIn("cpu", result)
        self.assertIn("memory", result)
        self.assertIn("process", result)
        self.assertIn("disk", result)
        self.assertIn("memory_trend", result)
        self.assertIn("alerts", result)

        # 类型检查
        self.assertIsInstance(result["uptime_seconds"], (int, float))
        self.assertIsInstance(result["services"], dict)
        self.assertIsInstance(result["memory_trend"], list)
        self.assertIsInstance(result["alerts"], list)

    @patch("backend.services.system_monitor_service.psutil.cpu_percent", return_value=10.0)
    @patch("backend.services.system_monitor_service.psutil.cpu_count", return_value=4)
    @patch("backend.services.system_monitor_service.psutil.virtual_memory")
    @patch("backend.services.system_monitor_service.psutil.disk_usage")
    @patch("backend.services.system_monitor_service.psutil.Process")
    def test_collect_with_memory_trend(
        self,
        mock_process: MagicMock,
        mock_disk: MagicMock,
        mock_memory: MagicMock,
        mock_cpu_count: MagicMock,
        mock_cpu_pct: MagicMock,
    ):
        mock_memory.return_value = MagicMock(
            total=8 * 1024**3, used=3 * 1024**3, percent=37.5,
        )
        mock_disk.return_value = MagicMock(
            total=256 * 1024**3, used=50 * 1024**3, percent=19.5,
        )
        mock_proc = MagicMock()
        mock_proc.memory_info.return_value = MagicMock(rss=150 * 1024**2, vms=400 * 1024**2)
        mock_proc.num_threads.return_value = 3
        mock_process.return_value = mock_proc

        from backend.services.system_monitor_service import SystemMonitorService
        svc = SystemMonitorService()

        # 多次采样，趋势记录
        for _ in range(3):
            svc.collect()

        result = svc.collect()
        # 趋势应该有 4 个点（3+1）
        self.assertGreaterEqual(len(result["memory_trend"]), 3)

        # 每个趋势点有 time 和 rss_mb
        for point in result["memory_trend"]:
            self.assertIn("time", point)
            self.assertIn("rss_mb", point)
            self.assertIsInstance(point["rss_mb"], float)

    @patch("backend.services.system_monitor_service.psutil.cpu_percent", return_value=5.0)
    @patch("backend.services.system_monitor_service.psutil.cpu_count", return_value=2)
    @patch("backend.services.system_monitor_service.psutil.virtual_memory")
    @patch("backend.services.system_monitor_service.psutil.disk_usage")
    @patch("backend.services.system_monitor_service.psutil.Process")
    def test_alerts_generated_when_memory_grows(
        self,
        mock_process: MagicMock,
        mock_disk: MagicMock,
        mock_memory: MagicMock,
        mock_cpu_count: MagicMock,
        mock_cpu_pct: MagicMock,
    ):
        mock_memory.return_value = MagicMock(
            total=4 * 1024**3, used=2 * 1024**3, percent=50.0,
        )
        mock_disk.return_value = MagicMock(
            total=100 * 1024**3, used=30 * 1024**3, percent=30.0,
        )
        mock_proc = MagicMock()
        # 模拟增长：500→520→540→560→580→600→620（每次+20MB，连续7次=6次循环+1次result）
        rss_values = [500, 520, 540, 560, 580, 600, 620]
        rss_iter = iter(rss_values)

        def rss_side_effect():
            return MagicMock(rss=next(rss_iter) * 1024**2, vms=800 * 1024**2)

        mock_proc.memory_info.side_effect = rss_side_effect
        mock_proc.num_threads.return_value = 4
        mock_process.return_value = mock_proc

        from backend.services.system_monitor_service import SystemMonitorService
        svc = SystemMonitorService(
            warning_threshold_mb=500,
            consecutive_growth_alert=5,
        )

        for _ in range(6):
            svc.collect()

        result = svc.collect()
        # 连续增长 ≥5 次 + RSS ≥ 500MB → 应有告警
        self.assertGreater(len(result["alerts"]), 0)
        alert = result["alerts"][0]
        self.assertIn("message", alert)
        self.assertIn("current_mb", alert)


class SystemMonitorAPITests(unittest.TestCase):
    """API 层集成测试（需要认证）。"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self._original_db_dir = store.DB_DIR
        self._original_db_path = store.DB_PATH
        store.close_connection()
        store.DB_DIR = self.temp_dir.name
        store.DB_PATH = os.path.join(self.temp_dir.name, "smoke.db")
        store._connection = None
        # 使用上下文管理器触发 lifespan → init_database()
        self.client_ctx = TestClient(app)
        self.client = self.client_ctx.__enter__()

    def tearDown(self):
        self.client_ctx.__exit__(None, None, None)
        store.close_connection()
        store.DB_DIR = self._original_db_dir
        store.DB_PATH = self._original_db_path
        store._connection = None
        self.temp_dir.cleanup()

    def _login_as_super_admin(self) -> str:
        resp = self.client.post("/api/auth/login", json={
            "username": "lina1124",
            "password": "asdky1314740",
        })
        return resp.json()["access_token"]

    def test_status_endpoint_requires_auth(self):
        """未登录 → 401。"""
        resp = self.client.get("/api/system/status")
        self.assertEqual(resp.status_code, 401)

    def test_status_endpoint_with_auth_returns_200(self):
        """超管登录 → 200 + 完整字段。"""
        token = self._login_as_super_admin()
        resp = self.client.get(
            "/api/system/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIn("services", data["data"])
        self.assertIn("cpu", data["data"])
        self.assertIn("memory", data["data"])
        self.assertIn("alerts", data["data"])
