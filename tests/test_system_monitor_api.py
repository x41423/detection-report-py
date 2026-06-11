"""Integration tests for System Monitor & Log Viewer API.

TDD: RED phase — tests should fail until routes are implemented.
"""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from tests.auth_api_utils import auth_headers_for_permissions

PERMS = ("system:view",)


def _client() -> TestClient:
    return TestClient(app)


def _super_admin_headers(client: TestClient) -> dict[str, str]:
    """超管拥有所有权限，无需指定 PERMS。"""
    return auth_headers_for_permissions(client, PERMS)


# ---------------------------------------------------------------------------
# Log viewer tests
# ---------------------------------------------------------------------------

class TestLogViewerAPI:
    """RED phase: 这些测试当前应全部失败（路由未注册）。"""

    def test_logs_endpoint_requires_auth(self):
        """未认证请求应返回 401。"""
        client = _client()
        resp = client.get("/api/system/logs")
        assert resp.status_code == 401, f"expected 401, got {resp.status_code}"

    def test_logs_tail_returns_recent_lines(self):
        """/api/system/logs/tail 返回最近 N 行。"""
        client = _client()
        resp = client.get(
            "/api/system/logs/tail?lines=5&file=app",
            headers=_super_admin_headers(client),
        )
        assert resp.status_code == 200, f"expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["success"] is True
        assert "lines" in data
        assert isinstance(data["lines"], list)
        assert len(data["lines"]) <= 5

    def test_logs_filter_by_level(self):
        """按级别过滤 ERROR 日志。"""
        client = _client()
        resp = client.get(
            "/api/system/logs?level=ERROR&limit=10",
            headers=_super_admin_headers(client),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        for line in data.get("lines", []):
            # 每条 JSON 行应包含 "level": "ERROR"
            assert '"level": "ERROR"' in line

    def test_logs_filter_by_search(self):
        """按关键词搜索日志。"""
        client = _client()
        resp = client.get(
            "/api/system/logs?search=ASR&limit=5&file=app",
            headers=_super_admin_headers(client),
        )
        assert resp.status_code == 200
        data = resp.json()
        for line in data.get("lines", []):
            assert "ASR" in line


# ---------------------------------------------------------------------------
# System monitor tests
# ---------------------------------------------------------------------------

class TestSystemMonitorAPI:
    """RED phase: 系统状态端点测试。"""

    def test_status_requires_auth(self):
        client = _client()
        resp = client.get("/api/system/status")
        assert resp.status_code == 401

    def test_status_returns_structure(self):
        """/api/system/status 返回正确的数据结构。"""
        client = _client()
        resp = client.get(
            "/api/system/status",
            headers=_super_admin_headers(client),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

        sys_data = data["data"]
        # 必需字段
        assert "timestamp" in sys_data
        assert "uptime_seconds" in sys_data
        assert "services" in sys_data
        assert "cpu" in sys_data
        assert "memory" in sys_data
        assert "process" in sys_data
        assert "disk" in sys_data

        # 服务状态子字段
        services = sys_data["services"]
        assert "backend" in services
        assert "nginx" in services
        assert "mysql" in services
        assert isinstance(services["backend"]["status"], str)

        # CPU 子字段
        assert "percent" in sys_data["cpu"]
        assert "cores" in sys_data["cpu"]

        # 内存子字段
        assert "total_gb" in sys_data["memory"]
        assert "used_gb" in sys_data["memory"]
        assert "percent" in sys_data["memory"]

        # 进程子字段
        assert "pid" in sys_data["process"]
        assert "rss_mb" in sys_data["process"]

    def test_status_includes_memory_trend(self):
        """状态应包含内存趋势数据。"""
        client = _client()
        resp = client.get(
            "/api/system/status",
            headers=_super_admin_headers(client),
        )
        data = resp.json()["data"]
        assert "memory_trend" in data
        assert isinstance(data["memory_trend"], list)

    def test_status_includes_alerts(self):
        """状态应包含告警列表。"""
        client = _client()
        resp = client.get(
            "/api/system/status",
            headers=_super_admin_headers(client),
        )
        data = resp.json()["data"]
        assert "alerts" in data
        assert isinstance(data["alerts"], list)
