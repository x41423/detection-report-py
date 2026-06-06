"""Integration tests for Supplier Settlement API."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.db import store
from backend.main import app
from tests.auth_api_utils import auth_headers_for_permissions

PERMS = (
    "supplier:view", "supplier:create", "supplier:edit",
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
        json={"name": "结算测试供应商"},
        headers=_headers(client),
    )
    assert resp.status_code == 200
    return resp.json()["id"]


# ==================================================================
# CRUD
# ==================================================================

def test_create_settlement():
    store.init_database()
    client = _client()
    sid = _create_supplier(client)
    resp = client.post("/api/settlement/", json={
        "supplier_id": sid,
        "settlement_period": "2026-05",
        "payable_amount": 10000,
        "paid_amount": 3000,
        "fee_amount": 200,
        "discount_amount": 500,
    }, headers=_headers(client))
    assert resp.status_code == 200
    data = resp.json()
    assert data["supplier_id"] == sid
    assert data["balance_amount"] == 6300  # 10000 - 3000 - 200 - 500


def test_list_settlements():
    store.init_database()
    client = _client()
    sid = _create_supplier(client)
    client.post("/api/settlement/", json={
        "supplier_id": sid, "settlement_period": "2026-05", "payable_amount": 5000,
    }, headers=_headers(client))
    resp = client.get("/api/settlement/", headers=_headers(client))
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


def test_list_settlements_filter_period():
    store.init_database()
    client = _client()
    sid = _create_supplier(client)
    import uuid as _uuid
    p1 = f"2050-{_uuid.uuid4().hex[:2]}"
    p2 = f"2050-{_uuid.uuid4().hex[-2:]}"
    client.post("/api/settlement/", json={
        "supplier_id": sid, "settlement_period": p1, "payable_amount": 1000,
    }, headers=_headers(client))
    client.post("/api/settlement/", json={
        "supplier_id": sid, "settlement_period": p2, "payable_amount": 2000,
    }, headers=_headers(client))
    resp = client.get(f"/api/settlement/?period={p2}", headers=_headers(client))
    assert resp.json()["total"] == 1


def test_confirm_settlement():
    store.init_database()
    client = _client()
    sid = _create_supplier(client)
    resp = client.post("/api/settlement/", json={
        "supplier_id": sid, "settlement_period": "2026-05", "payable_amount": 5000,
    }, headers=_headers(client))
    sid = resp.json()["id"]
    c = client.post(f"/api/settlement/{sid}/confirm", headers=_headers(client))
    assert c.status_code == 200
    assert client.get(f"/api/settlement/{sid}", headers=_headers(client)).json()["status"] == "settled"


def test_confirm_already_confirmed_rejected():
    store.init_database()
    client = _client()
    sid = _create_supplier(client)
    resp = client.post("/api/settlement/", json={
        "supplier_id": sid, "settlement_period": "2026-05", "payable_amount": 1000,
    }, headers=_headers(client))
    sid = resp.json()["id"]
    client.post(f"/api/settlement/{sid}/confirm", headers=_headers(client))
    resp2 = client.post(f"/api/settlement/{sid}/confirm", headers=_headers(client))
    assert resp2.status_code == 400


# ==================================================================
# Auto-create from PurchaseInRecord
# ==================================================================

def test_auto_create_settlement():
    store.init_database()
    client = _client()
    sid = _create_supplier(client)

    # Create and confirm purchase-in records
    for qty in (30, 50):
        r = client.post("/api/purchase/in", json={
            "supplier_id": sid, "inbound_date": "2026-05-15",
            "items": [{"veg_name": "自动结算菜", "quantity": qty, "unit_price": 10}],
        }, headers=_headers(client))
        client.post(f"/api/purchase/in/{r.json()['id']}/confirm", headers=_headers(client))

    # Auto-create settlement
    resp = client.post("/api/settlement/auto?supplier_id={}&period=2026-05".format(sid),
                       headers=_headers(client))
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    record = data["record"]
    assert record["payable_amount"] == 800  # (30+50) * 10
    assert record["settlement_period"] == "2026-05"


def test_auto_create_no_purchases_rejected():
    store.init_database()
    client = _client()
    sid = _create_supplier(client)
    resp = client.post("/api/settlement/auto?supplier_id={}&period=2026-05".format(sid),
                       headers=_headers(client))
    assert resp.status_code == 400
