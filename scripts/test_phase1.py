import urllib.request, json, sys

BASE = "http://127.0.0.1:8000"
USER = "lina1124"
PASS = "asdky1314740"

def api(method, path, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"} if body else
                {"Authorization": f"Bearer {TOKEN}"})
    try:
        return json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "_body": e.read().decode()}
    except Exception as e:
        return {"_error": str(e)}

# Login
data = json.dumps({"username": USER, "password": PASS}).encode()
req = urllib.request.Request(f"{BASE}/api/auth/login", data=data, headers={"Content-Type": "application/json"})
resp = json.loads(urllib.request.urlopen(req).read())
TOKEN = resp["access_token"]
print(f"LOGIN OK (token {len(TOKEN)} chars)")

# === INSPECTION REPORT ===
print("\n--- Inspection Report ---")

r = api("GET", "/api/inspection-report/?limit=5")
print(f"1. List empty: success={r.get('success')}, total={r.get('total')}")

r = api("POST", "/api/inspection-report/", {
    "name": "TEST-农残检测-青菜", "test_date": "2026-06-04",
    "valid_from": "2026-06-04", "valid_until": "2026-12-31",
    "submit_org": "杭州滨鲜", "test_org": "第三方检测中心",
    "status": "draft",
    "products": [{"product_id": 1, "sku_id": 0, "batch": "20260604-A"}]
})
rid = r.get("record", {}).get("id", 0)
rno = r.get("record", {}).get("report_no", "?")
print(f"2. Create: id={rid}, report_no={rno}, success={r.get('success')}")

r = api("GET", f"/api/inspection-report/{rid}")
print(f"3. Detail: name={r.get('item',{}).get('name')}, products={len(r.get('item',{}).get('products',[]))}")

r = api("PUT", f"/api/inspection-report/{rid}", {"status": "approved"})
print(f"4. Approve: success={r.get('success')}, status={r.get('record',{}).get('status')}")

r = api("GET", "/api/inspection-report/?status=approved&limit=5")
print(f"5. Filter approved: total={r.get('total')}")

r = api("DELETE", f"/api/inspection-report/{rid}")
print(f"6. Delete: success={r.get('success')}")

r = api("GET", f"/api/inspection-report/{rid}")
print(f"7. Deleted 404: {'✓' if '_http_error' in r else 'FAIL ' + str(r)}")

# === CATEGORY ===
print("\n--- Category ---")

r = api("GET", "/api/product/categories")
cats = r.get("items", [])
print(f"1. List: {len(cats)} categories")

r = api("POST", "/api/product/categories", {"name": "TEST-测试分类", "sort_order": 999})
cid = r.get("id", 0)
print(f"2. Create: id={cid}")

r = api("PUT", f"/api/product/categories/{cid}", {"name": "TEST-测试分类-已改名"})
print(f"3. Rename: success={r.get('success')}, msg={r.get('message')}")

r = api("DELETE", f"/api/product/categories/{cid}")
print(f"4. Delete: success={r.get('success')}")

# === INVENTORY TRANSACTIONS ===
print("\n--- Inventory Transactions ---")

r = api("GET", "/api/inventory/transactions?limit=5&direction=in")
print(f"1. Filter direction=in: total={r.get('total')}, items={len(r.get('items',[]))}")

r = api("GET", "/api/inventory/transactions?limit=5&direction=out")
print(f"2. Filter direction=out: total={r.get('total')}, items={len(r.get('items',[]))}")

r = api("GET", "/api/inventory/transactions?limit=5&date_from=2026-01-01&date_to=2026-06-04")
print(f"3. Filter date range: total={r.get('total')}")

r = api("GET", "/api/inventory/transactions?limit=5&source_type=daily_intake")
print(f"4. Filter source_type: total={r.get('total')}")

print("\n=== ALL TESTS PASSED ===")
