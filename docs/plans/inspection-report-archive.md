# 检测报告归档管理 — 执行计划

> 创建：2026-06-04
> 参考：观麦检测报告模块（`supply_chain/food_security/supplier_report`）
> 目标：为滨鲜工作台补齐检测报告归档管理，形成"生成→归档→查询"闭环

---

## 一、需求对标

| 观麦字段 | 滨鲜工作台 | 说明 |
|---------|-----------|------|
| 报告编号 | `report_no` (IRT-YYYYMMDD-NNN) | 自动生成，前缀 IRT = Inspection Report |
| 报告名称 | `name` | 输入框，max 50 |
| 检测报告(文件) | `file_url` | PDF/DOCX/图片，MinIO 存储 |
| 检测日期 | `test_date` | 日期选择器 |
| 有效期 | `valid_from` ~ `valid_until` | 日期范围 |
| 供应商 | `supplier_id` | 关联供应商表 |
| 送检机构 | `submit_org` | 输入框 |
| 检测机构 | `test_org` | 输入框 |
| 状态（审核状态） | `status` | draft/approved/rejected |
| 上传人 | `uploaded_by` | 自动取当前用户 |
| 上传时间 | `created_at` / `updated_at` | 自动 |
| 检测商品 | 关联表 `InspectionReportProduct` | N:M 关联 ProductSku |

**滨鲜工作台增强**（观麦没有的）：
- `source` 字段：`manual`（手动上传）| `generated`（系统生成）— 标记报告来源
- `pesticide_task_id`：当 source=generated 时关联农残检测任务

---

## 二、数据库设计

### 2.1 InspectionReport 表

```sql
CREATE TABLE IF NOT EXISTS InspectionReport (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_no TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL DEFAULT '',
    file_url TEXT NOT NULL DEFAULT '',
    test_date TEXT NOT NULL DEFAULT '',
    valid_from TEXT NOT NULL DEFAULT '',
    valid_until TEXT NOT NULL DEFAULT '',
    supplier_id INTEGER DEFAULT 0,
    submit_org TEXT NOT NULL DEFAULT '',
    test_org TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft',
    source TEXT NOT NULL DEFAULT 'manual',
    pesticide_task_id INTEGER DEFAULT 0,
    uploaded_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ir_report_no ON InspectionReport(report_no);
CREATE INDEX IF NOT EXISTS idx_ir_supplier ON InspectionReport(supplier_id);
CREATE INDEX IF NOT EXISTS idx_ir_status ON InspectionReport(status);
CREATE INDEX IF NOT EXISTS idx_ir_test_date ON InspectionReport(test_date);
```

### 2.2 InspectionReportProduct 关联表

```sql
CREATE TABLE IF NOT EXISTS InspectionReportProduct (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    sku_id INTEGER NOT NULL DEFAULT 0,
    product_id INTEGER NOT NULL DEFAULT 0,
    batch TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (report_id) REFERENCES InspectionReport(id),
    FOREIGN KEY (sku_id) REFERENCES ProductSku(id),
    FOREIGN KEY (product_id) REFERENCES Product(id)
);
CREATE INDEX IF NOT EXISTS idx_irp_report ON InspectionReportProduct(report_id);
CREATE INDEX IF NOT EXISTS idx_irp_sku ON InspectionReportProduct(sku_id);
```

---

## 三、后端实现（5 Steps）

### Step 1: Pydantic Schemas

**文件：** `backend/models/inspection_report_schemas.py`

```python
from pydantic import BaseModel, Field
from datetime import date

class InspectionReportProductCreate(BaseModel):
    sku_id: int = 0
    product_id: int = 0
    batch: str = ''

class InspectionReportProductResponse(BaseModel):
    id: int
    report_id: int
    sku_id: int
    product_id: int
    batch: str
    product_name: str = ''    # JOIN from Product
    product_code: str = ''    # JOIN from Product
    sku_name: str = ''        # JOIN from ProductSku

class InspectionReportCreate(BaseModel):
    name: str = ''
    test_date: str = ''
    valid_from: str = ''
    valid_until: str = ''
    supplier_id: int = 0
    submit_org: str = ''
    test_org: str = ''
    file_url: str = ''
    status: str = 'draft'
    source: str = 'manual'
    pesticide_task_id: int = 0
    products: list[InspectionReportProductCreate] = []

class InspectionReportUpdate(BaseModel):
    name: str | None = None
    test_date: str | None = None
    valid_from: str | None = None
    valid_until: str | None = None
    supplier_id: int | None = None
    submit_org: str | None = None
    test_org: str | None = None
    file_url: str | None = None
    status: str | None = None
    products: list[InspectionReportProductCreate] | None = None

class InspectionReportResponse(BaseModel):
    id: int
    report_no: str
    name: str
    file_url: str
    test_date: str
    valid_from: str
    valid_until: str
    supplier_id: int
    supplier_name: str = ''
    submit_org: str
    test_org: str
    status: str
    source: str
    pesticide_task_id: int
    uploaded_by: int
    uploader_name: str = ''
    product_count: int = 0
    products: list[InspectionReportProductResponse] = []
    created_at: str
    updated_at: str
```

### Step 2: Repository

**文件：** `app/db/inspection_report_repository.py`

方法清单：
- `create_report(data) → int` — 插入主表 + products，事务
- `update_report(report_id, data) → bool` — 更新字段 + 重建 products
- `list_reports(filters) → list[dict]` — 分页 + JOIN supplier/user
- `get_report(report_id) → dict | None` — 详情含 products JOIN
- `delete_report(report_id) → bool`
- `_generate_report_no(cursor) → str` — IRT-YYYYMMDD-NNN

关键 SQL 模式：
```python
# 列表 LEFT JOIN
SELECT ir.*, s.name AS supplier_name, u.display_name AS uploader_name,
       (SELECT COUNT(*) FROM InspectionReportProduct WHERE report_id = ir.id) AS product_count
FROM InspectionReport ir
LEFT JOIN Supplier s ON ir.supplier_id = s.id
LEFT JOIN User u ON ir.uploaded_by = u.id
WHERE ... ORDER BY ir.created_at DESC LIMIT ? OFFSET ?
```

### Step 3: Service

**文件：** `backend/services/inspection_report_service.py`

```python
class InspectionReportService:
    def __init__(self):
        pass  # 无参构造

    def create(self, data: dict, user_id: int) -> dict:
        # → repository.create_report()
        # → mutation_response()

    def update(self, report_id: int, data: dict) -> dict:
        # → mutation_response()

    def list_reports(self, ...) -> dict:
        # → list_response()

    def get_report(self, report_id: int) -> dict:
        # → {"success": True, "item": {...}}
```

### Step 4: Routes

**文件：** `backend/api/routes/inspection_report.py`

```python
router = APIRouter()
service = InspectionReportService()

GET    /api/inspection-report/       — 列表（search, status, supplier_id, test_date_from/to, limit/offset）
GET    /api/inspection-report/{id}   — 详情（含 products）
POST   /api/inspection-report/       — 创建
PUT    /api/inspection-report/{id}   — 更新
DELETE /api/inspection-report/{id}   — 删除

POST   /api/inspection-report/upload — 文件上传（MinIO）
```

**权限：**
- `inspection_report:view` — 列表、详情、下载
- `inspection_report:create` — 创建、上传
- `inspection_report:update` — 更新
- `inspection_report:delete` — 删除

**⚠️ Pitfall #4：** mutation 端点不加 `response_model`。

### Step 5: main.py 注册

```python
("backend.api.routes.inspection_report", "/api/inspection-report", ["检测报告"]),
```

### Step 6: 权限种子

**文件：** `app/db/auth_seed.py`

在 `DEFAULT_PERMISSIONS` 中新增：
```python
("inspection_report:view", "查看检测报告", "inspection_report", "查看检测报告归档"),
("inspection_report:create", "新增检测报告", "inspection_report", "上传检测报告文件"),
("inspection_report:update", "修改检测报告", "inspection_report", "修改检测报告信息"),
("inspection_report:delete", "删除检测报告", "inspection_report", "删除检测报告"),
```

在 `ROLE_PERMISSION_CODES` 中为 `inspector` 角色添加：
```python
"inspection_report:view", "inspection_report:create", "inspection_report:update",
```

---

## 四、前端实现（4 Steps）

### Step F.1: API 层

**文件：** `frontend/src/api/inspection-report.ts`

```typescript
export interface InspectionReportProduct {
  id: number; report_id: number; sku_id: number; product_id: number;
  batch: string; product_name: string; product_code: string; sku_name: string;
}

export interface InspectionReport {
  id: number; report_no: string; name: string; file_url: string;
  test_date: string; valid_from: string; valid_until: string;
  supplier_id: number; supplier_name: string;
  submit_org: string; test_org: string;
  status: string; source: string; pesticide_task_id: number;
  uploaded_by: number; uploader_name: string;
  product_count: number; products: InspectionReportProduct[];
  created_at: string; updated_at: string;
}

// 函数：getReports, getReport, createReport, updateReport, deleteReport, uploadReportFile
```

### Step F.2: View 组件

**文件：** `frontend/src/views/InspectionReportManagement.vue`

布局：标准 CRUD 页面
- PageHero + 筛选区（搜索框、状态下拉、供应商下拉、日期范围）
- 表格列：报告编号 | 报告名称 | 检测日期 | 有效期 | 供应商 | 状态 | 上传人 | 上传时间 | 操作
- 弹窗表单：新增/编辑
- 详情弹窗：含关联商品列表 + 文件预览/下载

**⚠️ 文件上传：**
- 复用 `el-upload` 模式（Pitfall #9, #15）
- `uploadHeaders` 用 `useAuth().accessToken`（Pitfall #15）
- `name="file"` 与后端 `File(...)` 参数名一致
- `accept=".pdf,.docx,.jpg,.png,.zip"`

**⚠️ Pitfall #30：** 创建/删除后直接更新本地数组，不要立即 `load()`。

### Step F.3: 导航注册

**文件：** `frontend/src/navigation/appNavigation.ts`

在 `AppNavigationGroupId` 中新增 `'quality'`，
插入 group：
```typescript
{
  id: 'quality',
  title: '质量管理',
  kicker: 'QUALITY',
  description: '检测报告归档与追溯',
  spotlight: '管理农残检测报告，实现生成→归档→查询闭环',
  icon: DocumentChecked,
  order: 6,  // 在 processing(5) 之后，pricing(6) 调整为 7
}
```

**⚠️ Pitfall（导航）：** 插入 group 后，所有后续 order 必须 +1。

导航项：
```typescript
{
  name: 'inspection-reports',
  path: '/inspection-reports',
  title: '检测报告',
  shortTitle: '检测报告',
  description: '管理检测报告归档，支持上传、查询、关联商品。',
  accent: 'teal',
  group: 'quality',
  order: 1,
  icon: DocumentChecked,
  component: () => import('../views/InspectionReportManagement.vue'),
  requiredPermission: 'inspection_report:view',
}
```

### Step F.4: 数据库迁移

**文件：** `scripts/migrate_inspection_report.py`

按项目模式（Pitfall #28, migration template），idempotent `ALTER TABLE ADD COLUMN`。

---

## 五、验证步骤

1. `python -c "import backend.main"` — 后端导入不报错
2. `APP_DB_DRIVER=sqlite python scripts/migrate_inspection_report.py` — 迁移执行成功
3. `APP_DB_DRIVER=sqlite python -m pytest tests/test_inspection_report_api.py -v` — 测试通过
4. `cd frontend && npx vue-tsc --noEmit && npx vite build` — 前端编译通过
5. 手动测试：创建报告 → 上传PDF → 关联商品 → 搜索/筛选

---

## 六、文件清单

| 文件 | 操作 |
|------|------|
| `app/db/store.py` | 修改（双 CREATE TABLE） |
| `app/db/auth_seed.py` | 修改（权限 + 角色权限） |
| `app/db/inspection_report_repository.py` | 新建 |
| `backend/models/inspection_report_schemas.py` | 新建 |
| `backend/services/inspection_report_service.py` | 新建 |
| `backend/api/routes/inspection_report.py` | 新建 |
| `backend/main.py` | 修改（注册路由） |
| `scripts/migrate_inspection_report.py` | 新建 |
| `tests/test_inspection_report_api.py` | 新建 |
| `frontend/src/api/inspection-report.ts` | 新建 |
| `frontend/src/views/InspectionReportManagement.vue` | 新建 |
| `frontend/src/navigation/appNavigation.ts` | 修改（group + item） |

共：6 新建 + 3 修改

---

## 七、自审查

### 7.1 疏漏检查

- [x] InspectionReportProduct 关联表包含 product_id（商品级）和 sku_id（规格级），因为农药残留检测可能针对 SPU 或 SKU
- [x] `file_url` 支持 MinIO 存储，上传端点复用 StorageService
- [x] 来源字段 `source` 区分手动上传和系统生成，为未来农药残留任务完成后自动归档留接口
- [x] 状态字段 `status` 支持 draft/approved/rejected 三种状态
- [x] 列表查询支持按供应商、状态、日期范围筛选
- [x] 文件上传 support 多种格式（PDF/DOCX/JPG/PNG/ZIP），与观麦一致
- [x] 详情接口返回关联商品完整信息（product_name, product_code, sku_name）

### 7.2 潜在 Bug 预防

- [x] **Pitfall #8**：路由中 `/upload` 静态路径必须在 `/{id}` 之前定义
- [x] **Pitfall #4**：POST/PUT 端点不加 `response_model`
- [x] **Pitfall #15**：前端 el-upload 的 Authorization header 从 `useAuth().accessToken` 获取，不是 localStorage
- [x] **Pitfall #30**：创建/删除后本地更新数组，不调用 `load()` 重刷
- [x] **Pitfall #9**：el-upload 加 `on-error` handler，调试上传失败
- [x] **Pitfall #27**：INSERT 语句的 `?` 数量与列数一致（InspectionReport 20 列）
- [x] **Pitfall #6**：Vue SFC 顺序 template → script → style
- [x] `store.py` 双建表（SQLite + MySQL），用 `replace_all=true` 同步更新
- [x] `mutation_response` 包裹：测试中访问 `data["record"]["id"]` 不是 `data["id"]`
- [x] 导航 group order：插入 `quality` 后 pricing(6→7)、account(7→8)

### 7.3 与现有系统的集成点

- [x] 复用 StorageService（MinIO）做文件存储
- [x] 复用 save_upload() 做文件接收
- [x] 复用 Supplier 表做供应商关联
- [x] 复用 Product/ProductSku 表做商品关联
- [x] 复用 get_current_auth_context 做用户身份
- [x] 复用 list_response() / mutation_response() 做响应格式
- [x] 复用 require_permission() 做权限控制
