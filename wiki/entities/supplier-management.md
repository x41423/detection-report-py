---
title: 商户管理模块（原"供应商管理"）
created: 2026-06-07
updated: 2026-06-08
type: entity
tags: [merchant, backend, frontend, vue3, fastapi]
sources: [raw/docs/code-review-report.md]
---

# 商户管理（MerchantManagement）

## ⚠️ 2026-06-08 重大重构

原 `Supplier` 模块实际管理的是**商户**（下游客户），现已重命名为 `Merchant`。

- **旧表**: `Supplier` → **新表**: `Merchant`
- **旧路由**: `/api/supplier/` → **新路由**: `/api/merchant/`
- **旧页面**: `/suppliers` → **新页面**: `/merchants`
- **列名**: `supplier_id` 保留不变（避免全库迁移风险）

真正的供应商管理见 [[entities/supplier-management-new]]。

## 后端架构

| 层 | 文件 |
|----|------|
| Route | `backend/api/routes/merchant.py` |
| Service | `backend/services/merchant_service.py` |
| Repository | `app/db/merchant_repository.py` |
| Schema | `backend/models/merchant_schemas.py` |

## 前端组件

`MerchantManagement.vue` + `MerchantDetail.vue`：
- 商户列表（编码/名称/联系人/结算方式/状态）
- 详情页（基本信息 / 结算配置 / 交易概况）

## 数据库

`Merchant` 表（原 `Supplier` 表，27 列），延迟迁移至 MySQL。

## 相关页面

- [[entities/order-management]] — 订单关联商户
- [[concepts/settlement-flow]] — 结算配置
- [[entities/supplier-management-new]] — 真正的供应商模块
