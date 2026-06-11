"""Integration tests for Purchase In / Return API."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.db import store
from backend.main import app
from tests.auth_api_utils import auth_headers_for_permissions

PERMS = ("supplier:view", "supplier:create", "inventory:view", "inventory:create", "inventory:update")


def _client() -> TestClient:
    return TestClient(app)


_headers_cache: dict[int, dict[str, str]] = {}


def _headers(client: TestClient) -> dict[str, str]:
    cid = id(client)
    if cid not in _headers_cache:
        _headers_cache[cid] = auth_headers_for_permissions(client, PERMS)
    return _headers_cache[cid]


def _create_supplier(client: TestClient) -> int:
    resp = client.post(
        "/api/merchant/",
        json={"name": "采购测试供应商"},
        headers=_headers(client),
    )
    assert resp.status_code == 200
    return resp.json()["id"]


# ==================================================================
# Purchase In
# ==================================================================

def test_create_purchase_in():
    store.init_database()
    client = _client()
    sid = _create_supplier(client)

    resp = client.post(
        "/api/purchase/in",
        json={
            "supplier_id": sid,
            "inbound_date": "2026-05-25",
            "items": [
                {"veg_name": "大白菜", "quantity": 100, "unit_price": 2.5},
                {"veg_name": "土豆", "quantity": 50, "unit_price": 3.0},
            ],
        },
        headers=_headers(client),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["order_no"].startswith("PIN-")
    assert data["status"] == "pending"
    assert len(data["items"]) == 2


def test_list_purchase_in():
    store.init_database()
    client = _client()
    sid = _create_supplier(client)
    client.post("/api/purchase/in", json={
        "supplier_id": sid, "inbound_date": "2026-05-25",
        "items": [{"veg_name": "测试菜", "quantity": 10, "unit_price": 5}],
    }, headers=_headers(client))

    resp = client.get("/api/purchase/in", headers=_headers(client))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


def test_list_purchase_in_by_supplier():
    store.init_database()
    client = _client()
    sid = _create_supplier(client)
    client.post("/api/purchase/in", json={
        "supplier_id": sid, "inbound_date": "2026-05-25",
        "items": [{"veg_name": "过滤测试", "quantity": 5, "unit_price": 1}],
    }, headers=_headers(client))

    resp = client.get(f"/api/purchase/in?supplier_id={sid}", headers=_headers(client))
    data = resp.json()
    assert data["total"] >= 1


def test_confirm_purchase_in_creates_inventory():
    store.init_database()
    client = _client()
    sid = _create_supplier(client)

    # Create
    resp = client.post("/api/purchase/in", json={
        "supplier_id": sid, "inbound_date": "2026-05-25",
        "items": [{"veg_name": "入库联动测试菜", "quantity": 30, "unit_price": 4}],
    }, headers=_headers(client))
    rid = resp.json()["id"]

    # Confirm
    resp2 = client.post(f"/api/purchase/in/{rid}/confirm", headers=_headers(client))
    assert resp2.status_code == 200

    # Check inventory
    inv = client.get("/api/inventory/balances?search=入库联动测试菜", headers=_headers(client))
    assert inv.status_code == 200
    balances = inv.json()["items"]
    assert any(b["available_quantity"] >= 30 for b in balances), f"Inventory not updated: {balances}"


def test_confirm_already_confirmed_rejected():
    store.init_database()
    client = _client()
    sid = _create_supplier(client)
    resp = client.post("/api/purchase/in", json={
        "supplier_id": sid, "inbound_date": "2026-05-25",
        "items": [{"veg_name": "重复确认测试", "quantity": 1, "unit_price": 1}],
    }, headers=_headers(client))
    rid = resp.json()["id"]
    client.post(f"/api/purchase/in/{rid}/confirm", headers=_headers(client))
    resp2 = client.post(f"/api/purchase/in/{rid}/confirm", headers=_headers(client))
    assert resp2.status_code == 400


def test_get_purchase_in_not_found():
    store.init_database()
    client = _client()
    resp = client.get("/api/purchase/in/99999", headers=_headers(client))
    assert resp.status_code == 404


# ==================================================================
# Purchase Return
# ==================================================================

def test_create_purchase_return():
    store.init_database()
    client = _client()
    sid = _create_supplier(client)

    resp = client.post("/api/purchase/return", json={
        "supplier_id": sid, "return_date": "2026-05-25",
        "items": [{"veg_name": "退货测试菜", "quantity": 20, "unit_price": 3}],
    }, headers=_headers(client))
    assert resp.status_code == 200
    data = resp.json()
    assert data["order_no"].startswith("PRT-")
    assert data["status"] == "pending"


def test_confirm_purchase_return_creates_inventory_out():
    store.init_database()
    client = _client()
    sid = _create_supplier(client)

    # First create IN to have some stock
    in_resp = client.post("/api/purchase/in", json={
        "supplier_id": sid, "inbound_date": "2026-05-25",
        "items": [{"veg_name": "退货联动库存测试", "quantity": 100, "unit_price": 2}],
    }, headers=_headers(client))
    client.post(f"/api/purchase/in/{in_resp.json()['id']}/confirm", headers=_headers(client))

    # Create and confirm return
    ret_resp = client.post("/api/purchase/return", json={
        "supplier_id": sid, "return_date": "2026-05-25",
        "items": [{"veg_name": "退货联动库存测试", "quantity": 40, "unit_price": 2}],
    }, headers=_headers(client))
    rid = ret_resp.json()["id"]
    client.post(f"/api/purchase/return/{rid}/confirm", headers=_headers(client))

    # Check inventory decreased via balances
    inv = client.get("/api/inventory/balances?search=退货联动库存测试",
                     headers=_headers(client))
    assert inv.status_code == 200
    balances = inv.json()["items"]
    assert len(balances) >= 1, f"No balance found after return: {balances}"
    # Verify the return transaction exists (OUT direction)
    txns = client.get("/api/inventory/transactions?limit=200",
                      headers=_headers(client))
    assert txns.status_code == 200
    out_txns = [t for t in txns.json()["items"] if t["direction"] == "OUT" and t["source_type"] == "purchase_return"]
    assert len(out_txns) >= 1, f"No OUT return transaction found: {txns.json()['items'][:5]}"
