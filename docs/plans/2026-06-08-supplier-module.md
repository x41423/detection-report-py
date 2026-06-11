# 真正的供应商管理 — 实现计划

> **For Hermes:** 按 Task 顺序逐步实现。先做后端数据模型和 API，再做前端页面。

**Goal:** 新建"供应商管理"模块（上游供货商），与现有"商户管理"（下游客户）彻底分离。

**现状问题:** 当前系统中的 `Supplier` 表、API、前端页面名为"供应商管理"，但实际存的是商户/客户数据（结算周期、交易概况、销售额等）。真正的供应商功能（供货关系、采购同步、资质管理）完全缺失。

**来源:** 观麦供应商管理页面结构分析（2026-06-08）

---

## 差异分析：商户 vs 供应商

| 维度 | 商户（现有 `supplier`） | 供应商（观麦参考） |
|------|----------------------|-------------------|
| 业务方向 | 下游：滨鲜卖给谁 | 上游：谁卖给滨鲜 |
| 核心字段 | 结算周期、日期维度、冻结/审核状态 | 供应商编号/名称、默认采购员、结款周期、开票类型 |
| 关联 | 订单（售出） | 采购单（进货） |
| 特有功能 | 销售额统计、毛利、未下单提醒 | 可供商品/分类分配、合同管理、采购单据同步 |
| 资质管理 | 无 | 公司名、营业执照号、开户行/账号、资质图片 |
| 工商信息 | 无 | 供应商性质（普通/基地/批发商）、地理位置 |

---

## 数据库设计

### 新建表：`Supplier`（替换现有 `Supplier` 表）

> **重要**: 先重命名现有 `Supplier` 表为 `Merchant`，避免数据丢失。

```sql
-- Step 0: 重命名现有表
ALTER TABLE Supplier RENAME TO Merchant;

-- 更新关联表外键
-- PurchaseRecord.supplier_id → merchant_id
-- Settlement.supplier_id → merchant_id
-- 等所有引用 Supplier 的表

-- Step 1: 新建真正的供应商表
CREATE TABLE Supplier (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_code   TEXT NOT NULL UNIQUE,    -- 供应商编号（手动输入，非自增）
    name            TEXT NOT NULL,           -- 供应商名称（必填）
    company_name    TEXT DEFAULT '',         -- 公司名称（工商）
    contact_address TEXT DEFAULT '',         -- 公司地址
    remark          TEXT DEFAULT '',         -- 备注

    -- 业务信息
    default_purchaser TEXT DEFAULT '',       -- 默认采购员
    linked_station    TEXT DEFAULT '',       -- 关联站点

    -- 结算信息
    settlement_cycle     TEXT DEFAULT '日结',   -- 结款周期: 日结/周结/半月结/月结
    invoice_type         TEXT DEFAULT '普票或无票', -- 开票类型: 一般纳税人/小规模纳税人/普票或无票
    sales_purchase_settlement INTEGER DEFAULT 0, -- 以销定采入库结算

    -- 工商信息
    business_license   TEXT DEFAULT '',      -- 营业执照号
    bank_account_name  TEXT DEFAULT '',      -- 开户名
    bank_name          TEXT DEFAULT '',      -- 开户银行
    bank_account       TEXT DEFAULT '',      -- 银行账号
    supplier_nature    TEXT DEFAULT '普通',   -- 供应商性质: 普通/基地/批发商/厂家

    -- 其他
    purchase_auto_sync   INTEGER DEFAULT 0,  -- 采购单据自动同步
    geo_location         TEXT DEFAULT '',    -- 地理位置（坐标JSON）
    qualification_images TEXT DEFAULT '[]',  -- 资质图片URL列表（JSON数组，最多10张）
    payment_qr           TEXT DEFAULT '',    -- 付款码图片URL（最多1张）

    -- 状态
    status TEXT DEFAULT 'active',            -- active/inactive
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 新建关联表：供应商可供分类
CREATE TABLE SupplierCategory (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL REFERENCES Supplier(id),
    category_id INTEGER NOT NULL REFERENCES Category(id),
    UNIQUE(supplier_id, category_id)
);

-- 新建关联表：供应商可供商品
CREATE TABLE SupplierProduct (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL REFERENCES Supplier(id),
    product_id  INTEGER NOT NULL REFERENCES Product(id),
    UNIQUE(supplier_id, product_id)
);

-- 新建关联表：供应商联系人
CREATE TABLE SupplierContact (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL REFERENCES Supplier(id),
    name        TEXT NOT NULL DEFAULT '',
    phone       TEXT NOT NULL DEFAULT '',
    role        TEXT NOT NULL DEFAULT '',    -- 职务
    is_default  INTEGER DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 新建关联表：供应商合同
CREATE TABLE SupplierContract (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL REFERENCES Supplier(id),
    contract_no TEXT NOT NULL DEFAULT '',
    start_date  TEXT NOT NULL DEFAULT '',
    end_date    TEXT NOT NULL DEFAULT '',
    file_url    TEXT DEFAULT '',            -- 合同文件
    status      TEXT DEFAULT 'active',      -- active/expired/terminated
    created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
```

### 字段 vs 观麦字段对照

| 观麦字段 | 滨鲜字段 | 说明 |
|---------|---------|------|
| 供应商编号* | supplier_code | TXT |
| 供应商名称* | name | TXT |
| 公司地址 | contact_address | TXT |
| 备注 | remark | TXT |
| 登录账户 | — | 滨鲜不设供应商登录 |
| 默认采购员 | default_purchaser | TXT |
| 关联站点 | linked_station | 滨鲜单站点，可省略 |
| 结款周期 | settlement_cycle | 日结/周结/半月结/月结 |
| 开票类型 | invoice_type | 一般纳税人/小规模纳税人/普票或无票 |
| 以销定采结算 | sales_purchase_settlement | BOOL |
| 公司名称 | company_name | TXT |
| 营业执照号 | business_license | TXT |
| 开户名 | bank_account_name | TXT |
| 开户银行 | bank_name | TXT |
| 银行账号 | bank_account | TXT |
| 供应商性质 | supplier_nature | 普通/基地/批发商/厂家 |
| 采购单据同步 | purchase_auto_sync | BOOL |
| 地理位置 | geo_location | JSON coordinate |
| 资质图片 | qualification_images | JSON URL array |
| 付款码 | payment_qr | image URL |
| 可供分类 | → SupplierCategory | 关联表 |
| 可供商品 | → SupplierProduct | 关联表 |
| 联系人 | → SupplierContact | 关联表 |
| 合同管理 | → SupplierContract | 关联表 |

---

## 后端实现

### Task 1：创建 schemas

**File:** `backend/models/supplier_schemas.py`（重写）

```python
from pydantic import BaseModel, Field

class SupplierCreate(BaseModel):
    supplier_code: str             # 必填
    name: str                      # 必填
    company_name: str = ""
    contact_address: str = ""
    remark: str = ""
    default_purchaser: str = ""
    linked_station: str = ""
    settlement_cycle: str = "日结"
    invoice_type: str = "普票或无票"
    sales_purchase_settlement: int = 0
    business_license: str = ""
    bank_account_name: str = ""
    bank_name: str = ""
    bank_account: str = ""
    supplier_nature: str = "普通"
    purchase_auto_sync: int = 0
    geo_location: str = ""
    qualification_images: str = "[]"
    payment_qr: str = ""

class SupplierUpdate(BaseModel):
    # All fields optional for PATCH
    supplier_code: str | None = None
    name: str | None = None
    company_name: str | None = None
    # ... (all fields optional)

class SupplierResponse(BaseModel):
    # All fields returned
    id: int
    supplier_code: str
    name: str
    # ... (all fields)
    created_at: str
    updated_at: str
```

### Task 2：创建 Repository

**File:** `app/db/supplier_repository.py`（重写）

参照 `app/db/product_repository.py` 的 `@staticmethod` 模式：

```python
class SupplierRepository:
    @staticmethod
    def list(*, search, limit, offset) -> dict
    @staticmethod
    def get_by_id(sid) -> dict | None
    @staticmethod
    def create(data) -> int
    @staticmethod
    def update(sid, data) -> bool
    @staticmethod
    def delete(sid) -> bool
    @staticmethod
    def has_purchase_records(sid) -> bool  # 保护：有采购记录不能删
```

### Task 3：创建 Service

**File:** `backend/services/supplier_service.py`（重写）

### Task 4：创建 Route

**File:** `backend/api/routes/supplier.py`（重写）

路由:
```
GET    /api/supplier/                  → list (search, status, limit, offset)
GET    /api/supplier/{id}              → detail (含可供商品/分类/联系人/合同)
POST   /api/supplier/                  → create
PUT    /api/supplier/{id}              → update
DELETE /api/supplier/{id}              → soft delete (status=inactive)
POST   /api/supplier/{id}/activate     → activate
POST   /api/supplier/{id}/deactivate   → deactivate
POST   /api/supplier/{id}/hard-delete  → hard delete (check no purchases)

# 子资源
GET    /api/supplier/{id}/categories   → 可供分类列表
PUT    /api/supplier/{id}/categories   → 更新可供分类
GET    /api/supplier/{id}/products     → 可供商品列表
PUT    /api/supplier/{id}/products     → 更新可供商品
GET    /api/supplier/{id}/contacts     → 联系人列表
POST   /api/supplier/{id}/contacts     → 新增联系人
PUT    /api/supplier/{id}/contacts/{cid}  → 编辑联系人
DELETE /api/supplier/{id}/contacts/{cid}  → 删除联系人
GET    /api/supplier/{id}/contracts    → 合同列表
POST   /api/supplier/{id}/contracts    → 新增合同
PUT    /api/supplier/{id}/contracts/{cid}  → 编辑合同
DELETE /api/supplier/{id}/contracts/{cid}  → 删除合同
```

权限码：`supplier:view/create/update/delete`（已存在 ✅）

---

## 前端实现

### Task 5：供应商列表页

**File:** `frontend/src/views/SupplierManagement.vue`（重写）

参照观麦列表页：
- 搜索栏：供应商编号/名称输入框、状态下拉
- 操作栏：新建供应商、批量导入（暂不做）
- 表格列：供应商编号、名称、结款周期、开票类型、默认采购员、状态、创建时间、操作
- 操作：点击行进详情、编辑/停用/启用按钮

### Task 6：供应商详情页

**File:** `frontend/src/views/SupplierDetail.vue`（重写）

5 个 Tab：
1. **基本信息** — 表单编辑模式（字段按 5 个区块分组：基本资料/业务信息/结算信息/工商信息/其他信息）
2. **可供分类** — 多选分类树，保存到 SupplierCategory
3. **可供商品** — 搜索+多选商品列表，保存到 SupplierProduct
4. **联系人** — 列表 + 新增/编辑/删除弹窗
5. **合同管理** — 列表 + 新增/编辑/删除弹窗（含合同文件）

### Task 7：API 层

**File:** `frontend/src/api/supplier.ts`（重写）

---

## 商户重命名（不丢失数据）

### Task 8：重命名现有 `Supplier` → `Merchant`

- 现有 `Supplier` 表 → 重命名为 `Merchant`
- `supplier/` 路由 → 拆分为 `merchant/` + 新 `supplier/`
- 前端 `SupplierManagement.vue` → 重命名为 `MerchantManagement.vue`
- 前端 `SupplierDetail.vue` → 重命名为 `MerchantDetail.vue`
- 导航菜单中 `supplier:view` 权限页面拆分
- 相关的结算、采购引用改为新的 merchant_id

> ⚠️ 这是破坏性变更，需要数据库迁移脚本 + 前后端同步上线。

---

## 优先级

| 优先级 | 内容 | 理由 |
|--------|------|------|
| P0 | Task 1-4（后端 CRUD） | 先有数据才能看 |
| P1 | Task 5-7（前端列表+详情） | 基础增删改查 |
| P2 | 可供商品/分类（Tab 2-3） | 核心差异功能 |
| P3 | 联系人+合同（Tab 4-5） | 锦上添花 |
| P4 | Task 8（商户重命名） | 破坏性变更，需谨慎 |

---

## 自检：潜在问题

| 问题 | 风险 | 缓解 |
|------|------|------|
| 大量模块引用 `supplier_id`（采购/商品/结算/库存/检测报告/仪表盘等 6+ 模块） | 🔴 极高 | Task 8 必须作为独立迁移项目，不能混在新增功能中 |
| 现有Supplier表已有商户数据 | 高 | 先迁移/重命名表，不要直接DROP |

| 可供商品数量大（滨鲜有200+商品） | 中 | 搜索+分页多选，不一次性加载全部 |
| 图片上传（资质图片/付款码） | 中 | 复用检测报告的 FilePreviewDialog |
| 供应商编号手动输入 | 低 | 后端校验唯一性，前端提示重复 |
