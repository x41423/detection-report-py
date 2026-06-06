"""Integration tests for Price Lock API."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.db import store
from backend.main import app
from tests.auth_api_utils import auth_headers_for_permissions

PERMS = ("supplier:view", "supplier:create", "supplier:edit")

_headers_cache: dict[int, dict[str, str]] = {}


def _client() -> TestClient:
    return TestClient(app)


def _headers(client: TestClient) -> dict[str, str]:
    cid = id(client)
    if cid not in _headers_cache:
        _headers_cache[cid] = auth_headers_for_permissions(client, PERMS)
    return _headers_cache[cid]


def test_create_price_lock():
    store.init_database()
    client = _client()
    resp = client.post("/api/price-lock/", json={
        "rule_name": "元旦锁价活动",
        "salemenu_name": "元旦菜单",
        "start_time": "2026-01-01",
        "end_time": "2026-01-07",
        "items": [
            {"veg_name": "大白菜", "locked_price": 1.5},
            {"veg_name": "土豆", "locked_price": 2.0},
        ],
    }, headers=_headers(client))
    assert resp.status_code == 200
    data = resp.json()
    assert data["rule_code"].startswith("PLCK-")
    assert data["category_count"] == 2
    assert len(data["items"]) == 2


def test_list_price_locks():
    store.init_database()
    client = _client()
    client.post("/api/price-lock/", json={
        "rule_name": "列表测试", "items": [],
    }, headers=_headers(client))
    resp = client.get("/api/price-lock/", headers=_headers(client))
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


def test_deactivate_price_lock():
    store.init_database()
    client = _client()
    resp = client.post("/api/price-lock/", json={
        "rule_name": "停用测试", "items": [],
    }, headers=_headers(client))
    rid = resp.json()["id"]
    r = client.delete(f"/api/price-lock/{rid}", headers=_headers(client))
    assert r.status_code == 200
    # Verify deactivated
    detail = client.get(f"/api/price-lock/{rid}", headers=_headers(client))
    assert detail.json()["status"] == "inactive"


def test_get_not_found():
    store.init_database()
    client = _client()
    resp = client.get("/api/price-lock/99999", headers=_headers(client))
    assert resp.status_code == 404
