"""Integration tests for the Supplier management API."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.db import store
from backend.main import app
from tests.auth_api_utils import auth_headers_for_permissions

SUPPLIER_PERMISSIONS = (
    "supplier:view",
    "supplier:create",
    "supplier:edit",
    "supplier:delete",
)


def _client() -> TestClient:
    return TestClient(app)


def _headers(client: TestClient) -> dict[str, str]:
    return auth_headers_for_permissions(client, SUPPLIER_PERMISSIONS)


def _create(client: TestClient, name: str = "测试供应商") -> dict:
    resp = client.post(
        "/api/supplier/",
        json={"name": name, "contact_person": "张三", "contact_phone": "13800000000"},
        headers=_headers(client),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def test_create_supplier():
    store.init_database()
    client = _client()
    supplier = _create(client, "杭州绿源农副产品有限公司")
    assert supplier["name"] == "杭州绿源农副产品有限公司"
    assert supplier["code"].startswith("SUP-")
    assert supplier["status"] == "active"


def test_create_supplier_minimal_fields():
    store.init_database()
    client = _client()
    resp = client.post(
        "/api/supplier/",
        json={"name": "最小字段供应商"},
        headers=_headers(client),
    )
    assert resp.status_code == 200
    supplier = resp.json()
    assert supplier["contact_person"] is None
    assert supplier["contact_phone"] is None


def test_create_supplier_empty_name_rejected():
    store.init_database()
    client = _client()
    resp = client.post("/api/supplier/", json={"name": ""}, headers=_headers(client))
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

def test_list_suppliers():
    store.init_database()
    client = _client()
    _create(client, "A供应商")
    _create(client, "B供应商")
    resp = client.get("/api/supplier/", headers=_headers(client))
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["total"] >= 2


def test_list_suppliers_search():
    store.init_database()
    client = _client()
    _create(client, "杭州绿源")
    _create(client, "上海鲜美")
    resp = client.get("/api/supplier/?search=杭州", headers=_headers(client))
    data = resp.json()
    assert data["total"] >= 1
    assert all("杭州" in item["name"] for item in data["items"])


def test_list_suppliers_status_filter():
    store.init_database()
    client = _client()
    supplier = _create(client, "待停用供应商")
    client.delete(f"/api/supplier/{supplier['id']}", headers=_headers(client))
    resp = client.get("/api/supplier/?status=inactive", headers=_headers(client))
    data = resp.json()
    assert data["total"] >= 1
    assert all(item["status"] == "inactive" for item in data["items"])


def test_list_suppliers_pagination():
    store.init_database()
    client = _client()
    for i in range(5):
        _create(client, f"分页测试{i}")
    resp = client.get("/api/supplier/?limit=2&offset=0", headers=_headers(client))
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] >= 5


# ---------------------------------------------------------------------------
# Get by ID
# ---------------------------------------------------------------------------

def test_get_supplier():
    store.init_database()
    client = _client()
    supplier = _create(client, "查询测试")
    resp = client.get(f"/api/supplier/{supplier['id']}", headers=_headers(client))
    assert resp.status_code == 200
    assert resp.json()["name"] == "查询测试"


def test_get_supplier_not_found():
    store.init_database()
    client = _client()
    resp = client.get("/api/supplier/99999", headers=_headers(client))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

def test_update_supplier():
    store.init_database()
    client = _client()
    supplier = _create(client, "更新前")
    resp = client.put(
        f"/api/supplier/{supplier['id']}",
        json={"name": "更新后", "contact_phone": "13900000000"},
        headers=_headers(client),
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["name"] == "更新后"
    assert updated["contact_phone"] == "13900000000"
    assert updated["contact_person"] == "张三"


def test_update_supplier_not_found():
    store.init_database()
    client = _client()
    resp = client.put("/api/supplier/99999", json={"name": "不存在"}, headers=_headers(client))
    assert resp.status_code == 404


def test_update_supplier_empty_payload():
    store.init_database()
    client = _client()
    supplier = _create(client, "空更新测试")
    resp = client.put(f"/api/supplier/{supplier['id']}", json={}, headers=_headers(client))
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Delete (soft)
# ---------------------------------------------------------------------------

def test_delete_supplier_soft():
    store.init_database()
    client = _client()
    supplier = _create(client, "软删除测试")
    resp = client.delete(f"/api/supplier/{supplier['id']}", headers=_headers(client))
    assert resp.status_code == 200
    detail = client.get(f"/api/supplier/{supplier['id']}", headers=_headers(client))
    assert detail.json()["status"] == "inactive"


def test_delete_supplier_not_found():
    store.init_database()
    client = _client()
    resp = client.delete("/api/supplier/99999", headers=_headers(client))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# FUTURE endpoints
# ---------------------------------------------------------------------------

def test_future_purchase_history_returns_501():
    store.init_database()
    client = _client()
    resp = client.get("/api/supplier/1/purchase-history", headers=_headers(client))
    assert resp.status_code == 501
    assert resp.json()["detail"]["future"] is True


def test_future_settlement_returns_501():
    store.init_database()
    client = _client()
    resp = client.get("/api/supplier/1/settlement", headers=_headers(client))
    assert resp.status_code == 501


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def test_unauthenticated_rejected():
    store.init_database()
    client = _client()
    resp = client.get("/api/supplier/")
    assert resp.status_code == 401
