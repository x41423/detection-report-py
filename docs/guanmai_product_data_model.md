# 观麦商品库 — 数据模型文档

> **抓取时间**: 2026-05-27  
> **抓取方法**: Chrome DevTools MCP (evaluate_script + snapshot + click)  
> **数据来源**: `https://station.guanmai.cn/station/new#/merchandise/manage/list`

---

## 一、商品库列表页

### 1.1 表格列（9列，已确认）

| 列 | 数据格式 | 示例 |
|----|---------|------|
| 商品图片 | 缩略图 URL | `image.document.guanmai.cn/product_img/xxx.jpeg` |
| 商品 | 名称 + SPU ID（两行） | 开背草鱼 / C16687400 |
| 分类 | `一级/二级/品类` | 水产/其它/其它 |
| 销售规格数 (上架/全部) | `N/N` | 1/1 |
| 所在报价单数 | 数字 | 1 |
| 基本单位 | 文字 | 斤/件/卷/个/瓶/把 |
| 销售价 | `最低~最高元` | 1.00~1.00元 |
| 投框方式 | 文字 | 按司机投框 |
| 操作 | 图标按钮（编辑/下架） | — |

### 1.2 筛选条件

| 组件 | 类型 | 说明 |
|------|------|------|
| 一级分类 | 下拉选择（11个选项） | 通用、蔬菜（通用）、肉（通用）、水产（通用）、冻品（通用）、干货&调味品（通用）、厨房用品（通用）、粮油（通用）、其它（通用）、测试分类（通用）、动物制品（通用） |
| 二级分类 | 下拉选择 | 依赖一级分类联动 |
| 品类 | 下拉选择 | 依赖二级分类联动 |
| 搜索框 | 文本输入 | placeholder: "输入商品名称或ID" |

### 1.3 操作按钮

| 按钮 | 说明 |
|------|------|
| 搜索 | 执行筛选 |
| 导出 | 导出 Excel |
| 高级筛选 ▾ | 折叠面板（更多筛选条件） |
| 新建销售商品 | 跳转新建页面 |
| 更多功能 ▾ | 下拉菜单（见 1.4） |

### 1.4 「更多功能」下拉菜单（8项）

1. 智能菜单
2. 分类管理
3. 周期定价
4. 云商品导入
5. 批量新建商品(导入)
6. 批量修改销售商品(导入)
7. 参考成本来源
8. 快速匹配商品图片

### 1.5 分页

共 3188 条记录，每页 10 条，1-319 页。

---

## 二、新建商品表单（`#/merchandise/manage/list/sku_detail`）

### 2.1 页面结构

- **面包屑**: 商品 > 商品管理 > 商品库 > 新建商品
- **Tab 页**: 基础信息 | 规格信息
- **说明文案**: SPU（基础信息）是标准特征描述；SKU（规格信息）是销售/采购规格
- **按钮**: 取消 | 保存 | 保存并新建

### 2.2 基础信息 Tab — 18 个字段

| # | 字段名 | 类型 | 必填 | 说明 |
|---|--------|------|------|------|
| 1 | 所属分类 | 下拉（分类树） | ✓ | 支持三级选择；附带"新建分类"链接 |
| 2 | 商品名称 | 文本输入 | ✓ | 主名称 |
| 3 | 商品别名 | 文本输入 | | 选填，可多别名，空格分隔 |
| 4 | 商品类型 | 下拉 | ✓ | 默认"通用" |
| 5 | 自定义编码 | 文本输入 | | 占位"请填写自定义编码" |
| 6 | 投框方式 | 下拉 | ✓ | 默认"按订单投框"（列表显示"按司机投框"说明有两种） |
| 7 | 采购类型 | 下拉 | | 默认"临采" |
| 8 | 基本单位 | 下拉 | ✓ | — |
| 9 | 商品图片 | 图片上传 | | "+ 加图"；建议 1MB/720px/jpg/png |
| 10 | 保质期 | 数字输入 + "天" | | 占位"请填写保质期" |
| 11 | 采购模式 | 单选（radio） | | 订单采购 / 库存采购（默认"订单采购"）|
| 12 | 默认供应商 | 搜索下拉 | | 占位"搜索" |
| 13 | 描述 | 多行文本 | | "长度小于等于100个字" |
| 14 | 商品标签 | 下拉 + "管理标签" | | — |
| 15 | 税收分类编码 | 文本输入 | | "填写19位税收分类编码用于开票" |
| 16 | 税收税率 | 数字输入 | | "可填数0-100，填写0表示免税" |
| 17 | 商品自定义字段1/2/3 | 文本输入 | | 三个独立的文本字段 |
| 18 | 检测报告 | 复选框 | | — |

### 2.3 规格信息 Tab

- 初始状态: 空状态 "您好，暂未建立销售规格" + "新建销售规格" 按钮
- 规格类型: 销售规格 / 采购规格 两种
- 规格字段: 待深爬（需先保存 SPU 后才能看到完整 SKU 表单）

---

## 三、商品详情页（`#/merchandise/manage/list/detail`）

### 3.1 页面结构

- **参数**: `?id=C16687400`（但实际 API 使用 `spu_id` 参数，SPU ID 和展示的 Code 不同）
- **Tab**: 基础信息 | 规格信息
- **按钮**: 取消 | 保存（初始 disabled，修改后启用）

### 3.2 基础信息 Tab — 编辑模式字段

| 字段 | 与新建的差异 |
|------|------------|
| 商品名称 | 同新建 |
| 自定义编码 | 同新建 |
| 商品别名 | 同新建 |
| 所属分类 | 拆为三个独立下拉：选择一级分类 / 选择二级分类 / 选择品类 |
| 商品类型 | 显示为"本站"（vs 新建的"通用"） |
| 基本单位 | 下拉 |
| 投框方式 | 下拉，默认"请选择..." |
| 商品图片 | "+" 加图 + "商品主图" + "点击同步" 灰色提示 |
| 描述 | 多行文本 |
| 商品详情 | "+" 加图 + "图片大小请不要超过1Mb，推荐尺寸宽度为720，支持jpg/png格式" |
| 固定URL | 显示 "-" |
| 是否显示检测报告 | 复选框 |

### 3.3 规格信息 Tab

- 下拉切换销售规格（选择不同 SKU）
- "新建销售规格" 按钮
- 空状态提示: "您好，暂未建立销售规格"

---

## 四、分类数据结构（从一级分类下拉抓取）

### 4.1 一级分类（11 个）

| # | 名称 |
|---|------|
| 1 | 通用 |
| 2 | 蔬菜（通用） |
| 3 | 肉（通用） |
| 4 | 水产（通用） |
| 5 | 冻品（通用） |
| 6 | 干货&调味品（通用） |
| 7 | 厨房用品（通用） |
| 8 | 粮油（通用） |
| 9 | 其它（通用） |
| 10 | 测试分类（通用） |
| 11 | 动物制品（通用） |

### 4.2 分类层级关系

- 一级 → 二级 → 品类（三级联动下拉）
- 二级和品类数据依赖一级选择后异步加载
- 支持"无合适分类，去新建分类"快捷入口

---

## 五、滨鲜工作台数据模型设计（建议）

### 5.1 Category 表

```sql
CREATE TABLE IF NOT EXISTS Category (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER REFERENCES Category(id),
    level INTEGER NOT NULL DEFAULT 1,   -- 1=一级 2=二级 3=品类
    sort_order INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1
);
```

### 5.2 Product 表

```sql
CREATE TABLE IF NOT EXISTS Product (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,           -- SPU ID, e.g. C16687400
    name TEXT NOT NULL,                  -- 商品名称
    alias TEXT DEFAULT '',               -- 别名，空格分隔
    category_id INTEGER REFERENCES Category(id),
    product_type TEXT DEFAULT '通用',    -- 商品类型
    custom_code TEXT DEFAULT '',         -- 自定义编码
    delivery_method TEXT DEFAULT '按订单投框',
    purchase_type TEXT DEFAULT '临采',
    base_unit TEXT NOT NULL DEFAULT '斤',
    image_url TEXT DEFAULT '',
    shelf_life_days INTEGER DEFAULT 0,   -- 保质期(天)
    purchase_mode TEXT DEFAULT '订单采购', -- 订单采购/库存采购
    default_supplier_id INTEGER DEFAULT NULL,
    description TEXT DEFAULT '',
    tax_category_code TEXT DEFAULT '',    -- 19位税收分类编码
    tax_rate REAL DEFAULT 0,             -- 税率 0-100
    custom_field_1 TEXT DEFAULT '',
    custom_field_2 TEXT DEFAULT '',
    custom_field_3 TEXT DEFAULT '',
    has_inspection_report INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### 5.3 ProductSku 表

```sql
CREATE TABLE IF NOT EXISTS ProductSku (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES Product(id),
    sku_code TEXT DEFAULT '',
    spec_name TEXT DEFAULT '',           -- 规格名称
    sku_type TEXT DEFAULT '销售规格',   -- 销售规格/采购规格
    is_listed INTEGER DEFAULT 1,         -- 上架状态
    price REAL DEFAULT 0,
    stock REAL DEFAULT 0
);
```

### 5.4 滨鲜工作台简化点

相比观麦，以下字段可暂时省略或简化：

| 观麦字段 | 滨鲜处理 |
|----------|---------|
| 税收分类编码/税率 | 保留但置为"高级字段"（默认隐藏） |
| 商品自定义字段1/2/3 | 合并为"备注"字段 |
| 商品详情图（720px） | 与商品图片合并 |
| 固定URL | 暂不实现 |
| 检测报告 | 保留 checkbox，后续对接 |
| 供应商搜索 | 关联现有 Supplier 表 |
| 商品标签 | 暂不实现 |
| 「更多功能」8项 | 优先实现：分类管理、批量导入；其余后续迭代 |

---

## 六、API 端点规划

```
GET    /api/product/                列表（search, category_id, limit, offset）
GET    /api/product/categories      分类树（递归返回 JSON 树）
GET    /api/product/{id}            详情（含 SKU 列表）
POST   /api/product/                新建（body 含 SKU 可选数组）
PUT    /api/product/{id}            编辑
DELETE /api/product/{id}            下架
GET    /api/product/{id}/skus       该商品的所有规格
POST   /api/product/{id}/skus       新增规格
PUT    /api/product/skus/{sku_id}   编辑规格
```

---

## 七、未完成项（Phase B 前补充）

- [ ] 规格信息 Tab 的完整 SKU 表单字段（需先保存 SPU）
- [ ] 「高级筛选」面板完整字段
- [ ] 操作列的下拉菜单项（编辑/下架/删除等）
- [ ] 投框方式的枚举值（按订单投框 vs 按司机投框 vs 其他？）
- [ ] 商品类型的枚举值（通用 vs 本站 vs 其他？）
- [ ] 采购类型的枚举值（临采 vs 其他？）
