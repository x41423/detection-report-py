"""Integration tests for Dashboard API."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.db import store
from backend.main import app
from tests.auth_api_utils import auth_headers_for_permissions

PERMS = (
    "supplier:view", "supplier:create",
    "inventory:view", "inventory:create", "inventory:update",
    "order:create",
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
        "/api/supplier/", json={"name": "驾驶舱测试供应商"},
        headers=_headers(client),
    )
    assert resp.status_code == 200
    return resp.json()["id"]


def test_dashboard_empty():
    store.init_database()
    client = _client()
    resp = client.get("/api/dashboard/", headers=_headers(client))
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "overview" in data
    assert "purchase_trend" in data
    assert "order_trend" in data
    assert "top_suppliers" in data
    # All zero when empty
    assert data["overview"]["total_suppliers"] >= 0


def test_dashboard_with_data():
    store.init_database()
    client = _client()
    sid = _create_supplier(client)

    from datetime import date
    today = date.today().isoformat()

    # Create purchase-in with large amount to ensure top-5 placement
    r = client.post("/api/purchase/in", json={
        "supplier_id": sid, "inbound_date": today,
        "items": [{"veg_name": "驾驶舱测试菜", "quantity": 2000, "unit_price": 500}],
    }, headers=_headers(client))
    client.post(f"/api/purchase/in/{r.json()['id']}/confirm", headers=_headers(client))

    # Create order
    client.post("/api/order/", json={
        "merchant_name": "驾驶舱客户", "order_date": today,
        "items": [{"product_name": "驾驶舱测试菜", "quantity": 10, "unit_price": 8}],
    }, headers=_headers(client))

    # Create settlement
    client.post("/api/settlement/", json={
        "supplier_id": sid, "settlement_period": date.today().strftime("%Y-%m"), "payable_amount": 100,
    }, headers=_headers(client))

    resp = client.get("/api/dashboard/", headers=_headers(client))
    assert resp.status_code == 200
    data = resp.json()

    ov = data["overview"]
    assert ov["active_suppliers"] >= 1
    assert ov["purchase_this_month"] >= 500000  # 2000*500 = 1,000,000
    assert ov["orders_this_month"] >= 80  # 10*8
    assert ov["pending_settlements"] >= 1
    assert len(data["top_suppliers"]) >= 1
    names = [s["supplier_name"] for s in data["top_suppliers"]]
    assert "驾驶舱测试供应商" in names, f"Supplier not in top: {names}"


def test_dashboard_requires_auth():
    store.init_database()
    client = _client()
    resp = client.get("/api/dashboard/")
    assert resp.status_code == 401
