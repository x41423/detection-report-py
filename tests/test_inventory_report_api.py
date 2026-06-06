"""Integration tests for inventory extension endpoints (alerts, summary)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.db import store
from backend.main import app
from tests.auth_api_utils import auth_headers_for_permissions

PERMS = (
    "supplier:view", "supplier:create",
    "inventory:view", "inventory:create", "inventory:update",
)

_headers_cache: dict[int, dict[str, str]] = {}


def _client() -> TestClient:
    return TestClient(app)


def _headers(client: TestClient) -> dict[str, str]:
    cid = id(client)
    if cid not in _headers_cache:
        _headers_cache[cid] = auth_headers_for_permissions(client, PERMS)
    return _headers_cache[cid]


def _create_supplier(client: TestClient) -> int:
    resp = client.post(
        "/api/supplier/",
        json={"name": "库存扩展测试供应商"},
        headers=_headers(client),
    )
    assert resp.status_code == 200
    return resp.json()["id"]


# ==================================================================
# Alerts
# ==================================================================

def test_stock_alerts_empty():
    store.init_database()
    client = _client()
    resp = client.get("/api/inventory/alerts?threshold=10", headers=_headers(client))
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "items" in data


def test_stock_alerts_after_purchase():
    """Low-stock items appear after only a small IN (may accumulate with prior runs)."""
    store.init_database()
    client = _client()
    sid = _create_supplier(client)
    import uuid as _uuid
    suffix = _uuid.uuid4().hex[:6]

    # Create 5-unit IN
    resp = client.post("/api/purchase/in", json={
        "supplier_id": sid, "inbound_date": "2026-05-25",
        "items": [{"veg_name": f"预警菜{suffix}", "quantity": 5, "unit_price": 2}],
    }, headers=_headers(client))
    client.post(f"/api/purchase/in/{resp.json()['id']}/confirm", headers=_headers(client))

    # Threshold = 10, should find the item (5 <= 10)
    alerts = client.get("/api/inventory/alerts?threshold=10", headers=_headers(client))
    assert alerts.status_code == 200
    items = alerts.json()["items"]
    assert any(it["display_name"] == f"预警菜{suffix}" for it in items), f"Alert not found: {items}"


def test_stock_alerts_not_triggered_above_threshold():
    store.init_database()
    client = _client()
    sid = _create_supplier(client)

    resp = client.post("/api/purchase/in", json={
        "supplier_id": sid, "inbound_date": "2026-05-25",
        "items": [{"veg_name": "富裕菜", "quantity": 100, "unit_price": 2}],
    }, headers=_headers(client))
    client.post(f"/api/purchase/in/{resp.json()['id']}/confirm", headers=_headers(client))

    alerts = client.get("/api/inventory/alerts?threshold=10", headers=_headers(client))
    items = alerts.json()["items"]
    assert not any(it["display_name"] == "富裕菜" for it in items), f"Should not alert: {items}"


# ==================================================================
# Summary
# ==================================================================

def test_transaction_summary_includes_supplier():
    store.init_database()
    client = _client()
    sid = _create_supplier(client)

    resp = client.post("/api/purchase/in", json={
        "supplier_id": sid, "inbound_date": "2026-05-25",
        "items": [{"veg_name": "汇总测试菜", "quantity": 20, "unit_price": 3}],
    }, headers=_headers(client))
    client.post(f"/api/purchase/in/{resp.json()['id']}/confirm", headers=_headers(client))

    summary = client.get("/api/inventory/summary", headers=_headers(client))
    assert summary.status_code == 200
    data = summary.json()
    assert data["total"] >= 1
    items = data["items"]
    txn = next((t for t in items if t["normalized_name"] == "汇总测试菜"), None)
    assert txn is not None, f"Transaction for 汇总测试菜 not found"
    assert txn["supplier_name"] == "库存扩展测试供应商", f"Bad supplier: {txn}"
    assert txn["related_order_no"].startswith("PIN-"), f"Bad order_no: {txn}"


def test_transaction_summary_date_filter():
    store.init_database()
    client = _client()
    sid = _create_supplier(client)

    resp = client.post("/api/purchase/in", json={
        "supplier_id": sid, "inbound_date": "2026-05-20",
        "items": [{"veg_name": "日期过滤菜", "quantity": 10, "unit_price": 1}],
    }, headers=_headers(client))
    client.post(f"/api/purchase/in/{resp.json()['id']}/confirm", headers=_headers(client))

    # Filter to range that includes it
    incl = client.get("/api/inventory/summary?start_date=2026-05-15&end_date=2026-05-25", headers=_headers(client))
    assert incl.status_code == 200
    incl_items = [t for t in incl.json()["items"] if t["normalized_name"] == "日期过滤菜"]
    assert len(incl_items) >= 1

    # Filter to range that excludes it
    excl = client.get("/api/inventory/summary?start_date=2026-05-25&end_date=2026-05-30", headers=_headers(client))
    excl_items = [t for t in excl.json()["items"] if t["normalized_name"] == "日期过滤菜"]
    assert len(excl_items) == 0


def test_transaction_summary_requires_auth():
    store.init_database()
    client = _client()
    resp = client.get("/api/inventory/summary")
    assert resp.status_code == 401
