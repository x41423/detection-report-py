# 滨鲜工作台 — 观麦功能集成计划（修订版）

> 创建：2026-06-04 | 修订：同日
> 原则：同种功能开发一次，需要时配置化调用，互不影响

---

## 一、滨鲜工作台 vs 观麦 — 定位差异

| 维度 | 观麦 | 滨鲜工作台 |
|------|------|-----------|
| 定位 | 通用生鲜供应链 SaaS | 食品检测 + 内部业务管理 |
| 客户 | 数百家配送商 | 杭州滨鲜食品（自用） |
| 核心功能 | 订单→采购→分拣→配送→结算 全链路 | **农残检测报告生成** + 报价 + 点货 |

**滨鲜独有优势（观麦没有的）：**
- 🔥 农残检测报告生成（大表+小表→DOCX）
- 🔥 智能检测工作台（自动推荐检测清单）
- 🔥 每周报价 + 报价别名库
- 🔥 每日点货（语音录入）
- 🔥 数据迁移（大表定位→模板填充）

**结论：** 不是照搬观麦，而是补齐短板、强化长板。

---

## 二、已有的可复用基础

| 模式 | 样板参考 | 已复用的模块 |
|------|---------|------------|
| **单据型**（主表+明细行） | OrderManagement | 订单、采购、报价单 |
| **简单 CRUD**（单表） | SupplierManagement | 供应商、角色管理 |
| **Card 列表** | QuotationManagement | 报价单 |
| **全宽数据表** | ProductManagement | 商品库、订单 |
| **两栏工作台** | Pesticide.vue | 农残、智能、迁移、报价 |
| **el-upload** | ProductManagement | 商品图片、农残模板 |
| **响应格式** | `{success, items, total}` | 全部模块 |
| **权限控制** | `require_permission("module:action")` | 全部模块 |
| **编号生成** | `PREFIX-YYYYMMDD-NNN` | SPU/SUP/PIN/ORD/QUO... |
| **N:M 关联** | QuotationProduct | 报价单↔商品 |
| **列偏好持久化** | UserColumnPreference | 部分模块 |

---

## 三、观麦全量差距 — 按「模式家族」归类

### 模式 A：配置型管理页（单表 CRUD）

**模板：** SupplierManagement 模式。单表、少量字段、表格+弹窗表单。

| 功能 | Phase | 说明 |
|------|-------|------|
| 分类管理 | P1 | Category 表已有，只缺管理界面 |
| 商品备注 | P1 | 简单字段：product_id + content |
| 新品需求 | P2 | ProductDemand (name, desc, status) |
| 运营时间 | P3 | OperationTime (name, time_range) |
| 运费管理 | P3 | ShippingRule (name, cost, condition) |
| 自定义字段(订单) | P3 | OrderCustomField → 可配置的 key-value 扩展 |
| 未下单商户 | P2 | 只读查询页，过滤近N天无订单商户 |

### 模式 B：单据型管理页（主表+明细行）

**模板：** OrderManagement 模式。主表+子表行项目、编号生成、状态流转。

| 功能 | Phase | 说明 |
|------|-------|------|
| 检测报告归档 | P1 | 主表 InsepctionReport + 关联商品行 |
| 报损报溢表 | P2 | LossReport + LossReportItem |
| 损耗报表 | P3 | 加工分割产生的损耗记录 |
| 分割单据 | P3 | SplitOrder + SplitOrderItem |
| 改单审核 | P3 | 订单修改→审核→通过/驳回 |

### 模式 C：分析报表页（筛选+图表+排行）

**模板：** Dashboard.vue 增强。时间维度筛选、KPI 卡片、Canvas 图表、排名列表。

| 功能 | Phase | 说明 |
|------|-------|------|
| 库存流水明细 | P1 | InventoryTransaction 已有，加筛选+下钻 |
| 商品销售分析 | P2 | 按商品维度的销售/毛利趋势 |
| 销售总表 | P2 | 可导出的销售明细汇总 |
| 客户购买分析 | P2 | 客户复购率、客单价趋势 |
| 应付总账/明细账 | P2 | 按供应商维度的应付汇总 |
| 商品台账 | P3 | 商品维度的进出流水 |
| 货值成本表 | P3 | 库存货值+成本分析 |
| 报价记录 | P2 | 只读：报价单修改历史日志 |
| 出入库汇总/明细 | P2 | 时间段汇总+明细下钻 |

### 模式 D：定价规则引擎

**模板：** PriceLockManagement。基础价格 + 规则计算 = 最终价格。

| 功能 | Phase | 说明 |
|------|-------|------|
| 上浮定价 | P2 | base_price × (1 + rate) |
| 协议价管理 | P2 | SupplierProductPrice 供应商协议价 |
| 整单折扣 | P3 | total × (1 - discount_rate) |

### 模式 E：直接字段增强（不改页面结构）

**模板：** 在现有表/表单上加字段，不新建模块。

| 功能 | Phase | 说明 |
|------|-------|------|
| 报价单标签 | P1 | Quotation 表加 `tags` 字段，表单加 tag 输入 |
| 商品备注 | P1 | Product 表单加 `notes` 字段（与 P1-A 的商品备注不同：这是商品主数据上的备注，P1-A 是独立的备注管理页） |

### 模式 F：观麦专属 — 不需要做

| 模块 | 原因 |
|------|------|
| 供应链全套（拣货/分拣/配送/周转物/装箱） | 滨鲜不做物流配送 |
| 营销全套（秒杀/买赠/充值/积分/菜谱/优惠券/营销活动） | 滨鲜不做 C 端零售 |
| 短信管理/汇率/地磅/溯源设置/店铺运营/系统模板 | 不适用 |
| 分佣规则 | 滨鲜无分佣模式 |
| 商品组合 | 业务不需要套餐/捆绑销售 |
| 供应商列表（观麦版） | 滨鲜已有 SupplierManagement |
| 系统设置/操作日志/回收站 | 滨鲜已有 AuditLogs 覆盖 |

---

## 四、执行路线图

### Phase 1 — 补核心短板（2-3天）

```
聚焦：检测报告闭环 + 检测追溯基础 + 数据整理
```

| # | 功能 | 模式 | 关键点 |
|---|------|------|--------|
| P1.1 | **检测报告归档** | B 单据型 | 已出详细计划，直接执行 |
| P1.2 | **分类管理 UI** | A 配置型 | Category 表已有，只缺增删改界面 |
| P1.3 | **库存流水明细** | C 报表型 | InventoryTransaction 已有，加筛选下钻 |
| P1.4 | **报价单标签** | E 字段增强 | Quotation 表+表单加 `tags` |

### Phase 2 — 扩展业务能力（3-5天）

```
聚焦：报表分析 + 供应商财务 + 基础定价
```

| # | 功能 | 模式 |
|---|------|------|
| P2.1 | 商品备注（独立管理） | A 配置型 |
| P2.2 | 商品销售分析 | C 报表型 |
| P2.3 | 销售总表 | C 报表型 |
| P2.4 | 客户购买分析 | C 报表型 |
| P2.5 | 出入库汇总/明细 | C 报表型 |
| P2.6 | 应付总账/明细账 | C 报表型 |
| P2.7 | 报价记录 | C 报表型（只读日志） |
| P2.8 | 上浮定价 | D 规则引擎 |
| P2.9 | 协议价管理 | D 规则引擎 |
| P2.10 | 新品需求 | A 配置型 |
| P2.11 | 未下单商户 | A 配置型（只读） |
| P2.12 | 报损报溢表 | B 单据型 |

### Phase 3 — 锦上添花（以后评估）

| # | 功能 | 模式 |
|---|------|------|
| P3.1 | 改单审核 | B 单据型 |
| P3.2 | 分割单据 | B 单据型 |
| P3.3 | 损耗报表 | B 单据型 |
| P3.4 | 商品台账 | C 报表型 |
| P3.5 | 货值成本表 | C 报表型 |
| P3.6 | 商户货值查询 | C 报表型 |
| P3.7 | 整单折扣 | D 规则引擎 |
| P3.8 | 运营时间 | A 配置型 |
| P3.9 | 运费管理 | A 配置型 |
| P3.10 | 自定义字段(订单) | A 配置型 |

---

## 五、DRY 策略：Composable 而非 Monolithic 组件

### 5.1 后端：轻量辅助函数而非基类继承

放弃 `BaseCRUD` 的 `@classmethod` 继承方案（与项目 `@staticmethod` 惯例冲突），改用**一组标准辅助函数**：

```python
# app/db/crud_helpers.py

def simple_create(conn, table: str, columns: tuple[str, ...], data: dict) -> int:
    """单表 INSERT，返回 lastrowid。符合现有 @staticmethod 风格。"""
    cols = ", ".join(columns)
    ph = ", ".join(["?"] * len(columns))
    values = [data.get(c, _default_for(c)) for c in columns]
    cursor = conn.cursor()
    try:
        cursor.execute(f"INSERT INTO {table} ({cols}) VALUES ({ph})", values)
        conn.commit()
        return cursor.lastrowid
    finally:
        cursor.close()

def simple_list(table: str, limit=50, offset=0, where="", params=None) -> list[dict]:
    """单表 SELECT。直接调用 store.query()。"""
    sql = f"SELECT * FROM {table}"
    if where:
        sql += f" WHERE {where}"
    sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
    return query(sql, (*(params or ()), limit, offset))

def simple_update(conn, table: str, pk: int, columns: tuple[str, ...], data: dict) -> bool:
    """单表 UPDATE by id。"""
    sets = [f"{c} = ?" for c in columns]
    values = [data.get(c, _default_for(c)) for c in columns] + [pk]
    cursor = conn.cursor()
    try:
        cursor.execute(f"UPDATE {table} SET {', '.join(sets)} WHERE id = ?", values)
        conn.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()

def simple_delete(conn, table: str, pk: int) -> bool:
    """单表 DELETE by id。"""
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM {table} WHERE id = ?", (pk,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()
```

**每个 Repository 依然保持 `@staticmethod`：**

```python
# app/db/category_repository.py
from app.db.store import get_connection, query
from app.db.crud_helpers import simple_create, simple_list, simple_update, simple_delete

class CategoryRepository:
    @staticmethod
    def create_category(data: dict) -> int:
        conn = get_connection()
        return simple_create(conn, "Category",
            ("name", "parent_id", "sort_order"), data)

    @staticmethod
    def list_categories(limit=50, offset=0) -> list[dict]:
        return simple_list("Category", limit, offset)

    # 树形查询是特有的，单独实现
    @staticmethod
    def get_tree() -> list[dict]:
        rows = query("SELECT * FROM Category ORDER BY parent_id, sort_order")
        return CategoryRepository._build_tree(rows)
```

### 5.2 前端：Composable 而非巨无霸组件

放弃一个 `GenericTablePage` 处理所有场景，改用**一组 composable**，各页面按需组合：

```
useCrudTable(apiPrefix, columns)    → 表格数据加载 + 分页 + 排序
useCrudForm(formFields)             → 表单状态 + 验证 + 提交
useFileUpload(uploadUrl)            → el-upload 状态管理（已有模式）
useTableFilter(filters)             → 筛选栏状态 + URL 参数同步
```

**每个页面 = composable 组合 + 模板，而非配置对象：**

```vue
<!-- CategoryManagement.vue -->
<script setup lang="ts">
const { items, total, loading, load, page, pageSize } = useCrudTable('/api/category')
const { form, dialogVisible, openCreate, openEdit, submit } = useCrudForm(categoryFields)

onMounted(() => load())
</script>
```

比写配置对象更灵活——遇到树形选择器、批量操作等特殊情况不会被"通用组件"卡住。

### 5.3 交付物

| 交付物 | 类型 | 说明 |
|--------|------|------|
| `app/db/crud_helpers.py` | 后端 | 单表 CRUD 辅助函数（4 函数） |
| `frontend/src/composables/useCrudTable.ts` | 前端 | 通用表格加载 composable |
| `frontend/src/composables/useCrudForm.ts` | 前端 | 通用表单提交 composable |

---

## 六、执行顺序

```
第一步：建 composable + 辅助函数（半天）
第二步：Phase 1（2-3 天，4 功能）
第三步：Phase 2（按需渐进，每个功能独立）
第四步：Phase 3（远期评估后决定）
```

---

## 七、文件变更预估

| Phase | 通用基础 | 业务模块 | 总文件 |
|-------|---------|---------|--------|
| 基础 | 3（crud_helpers + 2 composable） | 0 | 3 |
| Phase 1 | 0 | ~12 | ~12 |
| Phase 2 | 0 | ~36 | ~36 |
| Phase 3 | 0 | ~30 | ~30 |

---

## 八、修订记录

| 版本 | 改动 |
|------|------|
| v1 | 初始版 |
| v2 | ① 补齐遗漏：报价记录、损耗报表、新品需求<br>② BaseCRUD `@classmethod`→辅助函数 `@staticmethod` 风格<br>③ GenericTablePage→composable 组合<br>④ 统一库存流水明细为 P1（检测追溯需要）<br>⑤ 商品销售分析移至 P2（非检测核心）<br>⑥ 报价单标签改为字段增强（E 模式），非独立模块<br>⑦ 新增「滨鲜独有优势」对比 |
