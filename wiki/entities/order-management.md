---
title: 订单管理模块
created: 2026-06-07
updated: 2026-06-07
type: entity
tags: [order, backend, frontend, fastapi, vue3]
sources: [raw/docs/code-review-report.md]
---

# 订单管理（OrderManagement）

## 概述

滨鲜工作台的核心业务模块，管理客户订单的全生命周期。最近一次大规模改造在 2026-06-07。

## 后端架构

| 层 | 文件 | 关键方法 |
|----|------|----------|
| Route | `backend/api/routes/order.py` | `list_orders`, `create_order`, `update_order`, `delete_order`, `confirm_outbound`, `undo_outbound` |
| Service | `backend/services/order_service.py` | `list_orders`, `create_order`, `outbound`, `undo_outbound`, `get_transaction_summary` |
| Repository | `app/db/order_repository.py` | `list_orders`, `create`, `get_order_by_id`, `delete_order` |
| Schema | `backend/models/order_schemas.py` | `OrderCreateForm`, `OrderUpdateForm`, `OrderResponse` |

## 关键功能

### 日期筛选（2026-06-07 新增）
- 两种模式：按下单日期 / 按收货日期
- FilterBar `select` 类型切换 + `date-range` 选择
- 后端 `date_mode` / `date_from` / `date_to` 参数

### 商户/商品智能搜索（2026-06-07 新增）
- `el-autocomplete` 实时搜索 Supplier/Product 表
- 选中自动填充收货人、地址、单位、价格
- 搜索无结果时显示「新建商户」入口

### 出库与撤销（2026-06-07 新增）
- `confirm_outbound` → 写入 `OUT` 库存交易
- `undo_outbound` → 写入 `IN` 交易恢复库存，回退订单状态
- 已出库订单不能直接删除

### 订单复制
- 支持正常复制 / 补单复制
- 复制时可选择是否同步单价、加价率、出库数量

## 前端组件

`frontend/src/views/OrderManagement.vue`（937 行）集成了：
- 列表展示（DataTable + 自定义列选择器）
- FilterBar 筛选（状态、支付、日期模式、日期范围）
- 新建/编辑弹窗（分步流程：先选商户→解锁其他）
- 商品搜索 Autocomplete
- 订单复制弹窗
- 删除/撤销出库操作

## 数据库

`OrderRecord` 表（50+ 列），核心字段：
- `order_no` — 订单编号
- `merchant_name` — 商户名称
- `order_date` — 下单日期
- `order_status` — 状态（pending/confirmed/delivered/cancelled）
- `order_amount` — 订单金额
- `outbound_status` — 出库状态

明细表 `OrderItem` 通过 `order_id` 关联。

## 已知问题

- 交易概况用 `merchant_name` 精确匹配（2026-06-07 从 LIKE 改为精确）
- 订单创建表单分步流程依赖 `v-if="form.merchant_name"` 控制
- 编辑模式需手动同步 `merchantQuery` 回显

## 相关页面

- [[entities/supplier-management]] — 供应商选择联动
- 出库/撤销的库存影响（OUT/IN 交易恢复）
- [[concepts/settlement-flow]] — 结算的订单数据来源
