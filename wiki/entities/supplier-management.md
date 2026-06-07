---
title: 供应商管理模块
created: 2026-06-07
updated: 2026-06-07
type: entity
tags: [supplier, backend, frontend, vue3, fastapi]
sources: [raw/docs/code-review-report.md]
---

# 供应商管理（SupplierManagement）

## 概述

管理滨鲜公司的供应商（上游供货商），支持详情页、结算配置、交易概况。2026-06-07 完成观麦模式融合升级。

## 后端架构

| 层 | 文件 | 关键方法 |
|----|------|----------|
| Route | `backend/api/routes/supplier.py` | `list_suppliers`, `create_supplier`, `update_supplier`, `delete_supplier`, `activate_supplier`, `hard_delete_supplier` |
| Service | `backend/services/supplier_service.py` | CRUD + `deactivate`, `activate`, `hard_delete`, `get_transaction_summary` |
| Repository | `app/db/supplier_repository.py` | CRUD + `has_purchase_records` 保护 |
| Schema | `backend/models/supplier_schemas.py` | `SupplierCreate`, `SupplierUpdate`, `SupplierResponse` |

## 关键功能

### 详情页（2026-06-07 新增）
三个 Tab：基本信息、结算配置、交易概况
- **基本信息**：编码/名称/联系人/银行/审核状态（15 字段）
- **结算配置**：结算人/周期/日期维度/冻结/白名单/优先级（9 字段）
- **交易概况**：销售额/毛利/折扣/售后数据

### 启用/停用/删除（2026-06-07 修复）
- 活跃→「停用」，停用→「启用」+「删除」
- 停用有采购记录保护（`has_purchase_records` 阻断）
- 硬删除检查无关联采购记录
- 按钮统一 `link` 样式，try/catch 错误提示

### Vue Router 参数响应（2026-06-07 修复）
- `supplierId` 从普通变量改为 `computed(() => Number(route.params.id))`
- 添加 `watch(supplierId, loadSupplier)` 监听参数变化
- 解决了「切换供应商详情页显示旧数据」的 bug

## 数据库

`Supplier` 表（27 列），核心字段：
- `settlement_method` — 结算方式（日结/周结/月结）
- `date_dimension` — 日期维度（order_date/receipt_date）
- `period_start_day` / `settlement_day` — 周期起始日/结算日
- `freeze_status` — 冻结状态
- `approval_status` — 审核状态
- `_UPDATE_WHITELIST` — Repository 字段白名单（2026-06-07 新增）

## 相关页面

- [[order-management]] — 订单创建时选择供应商
- [[settlement-flow]] — 结算配置影响结算周期
- [[purchase-management]] — 采购记录关联供应商
