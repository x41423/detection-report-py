"""Integration tests for Order management API."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.db import store
from backend.main import app
from tests.auth_api_utils import auth_headers_for_permissions

PERMS = (
    "supplier:view", "supplier:create",
    "inventory:view", "inventory:create", "inventory:update",
    "order:view", "order:create", "order:update", "order:delete", "order:copy",
)

_headers_cache: dict[int, dict[str, str]] = {}


def _client() -> TestClient:
    return TestClient(app)


def _headers(client: TestClient) -> dict[str, str]:
    cid = id(client)
    if cid not in _headers_cache:
        _headers_cache[cid] = auth_headers_for_permissions(client, PERMS)
    return _headers_cache[cid]


# ==================================================================
# Orders
# ==================================================================

def test_create_order():
    store.init_database()
    client = _client()

    resp = client.post("/api/order/", json={
        "merchant_name": "测试客户",
        "order_date": "2026-05-25",
        "items": [
            {"product_name": "大白菜", "quantity": 10, "unit_price": 2.5},
            {"product_name": "土豆", "quantity": 20, "unit_price": 3.0},
        ],
    }, headers=_headers(client))
    assert resp.status_code == 200
    data = resp.json()
    assert data["record"]["order_no"].startswith("ORD-")
    assert data["record"]["order_status"] == "pending"
    assert len(data["record"]["items"]) == 2
    assert data["record"]["order_amount"] == 85.0  # 10*2.5 + 20*3


def test_list_orders():
    store.init_database()
    client = _client()
    client.post("/api/order/", json={
        "merchant_name": "列表测试客户", "order_date": "2026-05-25",
        "items": [{"product_name": "测试菜", "quantity": 1, "unit_price": 1}],
    }, headers=_headers(client))

    resp = client.get("/api/order/", headers=_headers(client))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


def test_list_orders_filter_status():
    store.init_database()
    client = _client()
    client.post("/api/order/", json={
        "merchant_name": "状态过滤测试", "order_date": "2026-05-25",
        "items": [{"product_name": "菜", "quantity": 1, "unit_price": 1}],
    }, headers=_headers(client))

    resp = client.get("/api/order/?order_status=pending", headers=_headers(client))
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


def test_confirm_outbound_creates_inventory_out():
    store.init_database()
    client = _client()
    # First create IN to have stock
    sid_resp = client.post("/api/supplier/", json={"name": "出库测试供应商"}, headers=_headers(client))
    sid = sid_resp.json()["id"]
    in_resp = client.post("/api/purchase/in", json={
        "supplier_id": sid, "inbound_date": "2026-05-25",
        "items": [{"veg_name": "出库联动测试菜", "quantity": 50, "unit_price": 2}],
    }, headers=_headers(client))
    client.post(f"/api/purchase/in/{in_resp.json()['id']}/confirm", headers=_headers(client))

    # Create order and outbound
    ord_resp = client.post("/api/order/", json={
        "merchant_name": "联动客户", "order_date": "2026-05-25",
        "items": [{"product_name": "出库联动测试菜", "quantity": 15, "unit_price": 3}],
    }, headers=_headers(client))
    oid = ord_resp.json()["record"]["id"]
    client.post(f"/api/order/{oid}/outbound", headers=_headers(client))

    # Check inventory balance decreased
    inv = client.get("/api/inventory/balances?search=出库联动测试菜", headers=_headers(client))
    assert inv.status_code == 200
    balances = inv.json()["items"]
    assert len(balances) >= 1, f"No balance found: {balances}"


def test_confirm_already_outbound_rejected():
    store.init_database()
    client = _client()
    sid_resp = client.post("/api/supplier/", json={"name": "重复出库供应商"}, headers=_headers(client))
    sid = sid_resp.json()["id"]
    in_resp = client.post("/api/purchase/in", json={
        "supplier_id": sid, "inbound_date": "2026-05-25",
        "items": [{"veg_name": "重复出库测试菜", "quantity": 100, "unit_price": 1}],
    }, headers=_headers(client))
    client.post(f"/api/purchase/in/{in_resp.json()['id']}/confirm", headers=_headers(client))

    ord_resp = client.post("/api/order/", json={
        "merchant_name": "重复客户", "order_date": "2026-05-25",
        "items": [{"product_name": "重复出库测试菜", "quantity": 10, "unit_price": 1}],
    }, headers=_headers(client))
    oid = ord_resp.json()["record"]["id"]
    client.post(f"/api/order/{oid}/outbound", headers=_headers(client))
    resp2 = client.post(f"/api/order/{oid}/outbound", headers=_headers(client))
    assert resp2.status_code == 400


def test_get_order_not_found():
    store.init_database()
    client = _client()
    resp = client.get("/api/order/99999", headers=_headers(client))
    assert resp.status_code == 404


# ==================================================================
# After-Sale
# ==================================================================

def test_create_after_sale():
    store.init_database()
    client = _client()
    ord_resp = client.post("/api/order/", json={
        "merchant_name": "售后测试客户", "order_date": "2026-05-25",
        "items": [{"product_name": "售后测试菜", "quantity": 10, "unit_price": 5}],
    }, headers=_headers(client))
    oid = ord_resp.json()["record"]["id"]

    resp = client.post(f"/api/order/{oid}/after-sale", json={
        "product_name": "售后测试菜",
        "after_sale_type": "return",
        "return_quantity": 3,
        "return_amount": 15,
    }, headers=_headers(client))
    assert resp.status_code == 200
    data = resp.json()
    assert data["after_sale_id"] is not None


def test_after_sale_list():
    store.init_database()
    client = _client()
    ord_resp = client.post("/api/order/", json={
        "merchant_name": "售后列表客户", "order_date": "2026-05-25",
        "items": [{"product_name": "售后列表菜", "quantity": 5, "unit_price": 2}],
    }, headers=_headers(client))
    oid = ord_resp.json()["record"]["id"]
    client.post(f"/api/order/{oid}/after-sale", json={
        "product_name": "售后列表菜", "after_sale_type": "damage", "return_quantity": 1,
    }, headers=_headers(client))

    resp = client.get(f"/api/order/{oid}/after-sale", headers=_headers(client))
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ==================================================================
# Delete Order
# ==================================================================

def test_delete_order():
    store.init_database()
    client = _client()
    ord_resp = client.post("/api/order/", json={
        "merchant_name": "删除测试客户", "order_date": "2026-05-25",
        "items": [{"product_name": "删除测试菜", "quantity": 5, "unit_price": 2}],
    }, headers=_headers(client))
    oid = ord_resp.json()["record"]["id"]

    resp = client.delete(f"/api/order/{oid}", headers=_headers(client))
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Verify deleted
    get_resp = client.get(f"/api/order/{oid}", headers=_headers(client))
    assert get_resp.status_code == 404


def test_delete_delivered_order():
    store.init_database()
    client = _client()
    # Create supplier and purchase to have stock
    sid_resp = client.post("/api/supplier/", json={"name": "删除出库供应商"}, headers=_headers(client))
    sid = sid_resp.json()["id"]
    in_resp = client.post("/api/purchase/in", json={
        "supplier_id": sid, "inbound_date": "2026-05-25",
        "items": [{"veg_name": "删除出库菜", "quantity": 100, "unit_price": 1}],
    }, headers=_headers(client))
    client.post(f"/api/purchase/in/{in_resp.json()['id']}/confirm", headers=_headers(client))

    # Create order and outbound
    ord_resp = client.post("/api/order/", json={
        "merchant_name": "删除出库客户", "order_date": "2026-05-25",
        "items": [{"product_name": "删除出库菜", "quantity": 10, "unit_price": 2}],
    }, headers=_headers(client))
    oid = ord_resp.json()["record"]["id"]
    client.post(f"/api/order/{oid}/outbound", headers=_headers(client))

    # Try to delete delivered order
    resp = client.delete(f"/api/order/{oid}", headers=_headers(client))
    assert resp.status_code == 400


def test_delete_nonexistent():
    store.init_database()
    client = _client()
    resp = client.delete("/api/order/99999", headers=_headers(client))
    assert resp.status_code == 404


# ==================================================================
# Copy Order
# ==================================================================

def test_copy_order_normal():
    store.init_database()
    client = _client()
    ord_resp = client.post("/api/order/", json={
        "merchant_name": "复制测试客户", "order_date": "2026-05-25",
        "items": [
            {"product_name": "复制测试菜1", "quantity": 10, "unit_price": 3},
            {"product_name": "复制测试菜2", "quantity": 5, "unit_price": 4},
        ],
    }, headers=_headers(client))
    oid = ord_resp.json()["record"]["id"]

    resp = client.post(f"/api/order/{oid}/copy", json={
        "copy_type": "normal",
        "sync_unit_price": "yes",
        "sync_price_change_rate": "yes",
        "copy_outbound_quantity": "no",
    }, headers=_headers(client))
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["new_order_no"].startswith("ORD-")
    assert data["new_order_id"] != oid


def test_copy_order_supplement():
    store.init_database()
    client = _client()
    ord_resp = client.post("/api/order/", json={
        "merchant_name": "补单客户", "order_date": "2026-05-25",
        "items": [{"product_name": "补单菜", "quantity": 10, "unit_price": 2}],
    }, headers=_headers(client))
    oid = ord_resp.json()["record"]["id"]

    resp = client.post(f"/api/order/{oid}/copy", json={
        "copy_type": "no",
        "sync_unit_price": "yes",
        "sync_price_change_rate": "yes",
        "copy_outbound_quantity": "no",
    }, headers=_headers(client))
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    # Verify the new order is a supplement
    new_order = client.get(f"/api/order/{data['new_order_id']}", headers=_headers(client))
    assert new_order.json()["order_type"] == "supplement"


def test_copy_with_outbound():
    store.init_database()
    client = _client()
    ord_resp = client.post("/api/order/", json={
        "merchant_name": "出库复制客户", "order_date": "2026-05-25",
        "items": [{"product_name": "出库复制菜", "quantity": 10, "unit_price": 2}],
    }, headers=_headers(client))
    oid = ord_resp.json()["record"]["id"]

    resp = client.post(f"/api/order/{oid}/copy", json={
        "copy_type": "normal",
        "sync_unit_price": "yes",
        "sync_price_change_rate": "yes",
        "copy_outbound_quantity": "yes",
    }, headers=_headers(client))
    assert resp.status_code == 200
    data = resp.json()

    # Verify status is sorting (分拣中)
    new_order = client.get(f"/api/order/{data['new_order_id']}", headers=_headers(client))
    assert new_order.json()["order_status"] == "sorting"


def test_copy_without_price():
    store.init_database()
    client = _client()
    ord_resp = client.post("/api/order/", json={
        "merchant_name": "无价复制客户", "order_date": "2026-05-25",
        "items": [{"product_name": "无价复制菜", "quantity": 10, "unit_price": 5}],
    }, headers=_headers(client))
    oid = ord_resp.json()["record"]["id"]

    resp = client.post(f"/api/order/{oid}/copy", json={
        "copy_type": "normal",
        "sync_unit_price": "no",
        "sync_price_change_rate": "yes",
        "copy_outbound_quantity": "no",
    }, headers=_headers(client))
    assert resp.status_code == 200
    data = resp.json()

    # Verify price is 0
    new_order = client.get(f"/api/order/{data['new_order_id']}", headers=_headers(client))
    items = new_order.json()["items"]
    assert all(item["unit_price"] == 0 for item in items)


# ==================================================================
# Column Preference
# ==================================================================

def test_column_preference():
    store.init_database()
    client = _client()

    # Save preference
    resp = client.put("/api/order/column-preference", json={
        "page_key": "order_list",
        "visible_columns": ["order_no", "merchant_tag", "order_status", "payment_status"],
    }, headers=_headers(client))
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Get preference
    resp = client.get("/api/order/column-preference?page_key=order_list", headers=_headers(client))
    assert resp.status_code == 200
    data = resp.json()
    assert data["visible_columns"] == ["order_no", "merchant_tag", "order_status", "payment_status"]
