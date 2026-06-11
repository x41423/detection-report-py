---
title: 供应商管理模块（真实上游供货商）
created: 2026-06-08
updated: 2026-06-08
type: entity
tags: [supplier, backend, frontend, vue3, fastapi, guanmai]
sources: [docs/plans/2026-06-08-supplier-module.md]
---

# 供应商管理（SupplierManagement）

## 概述

真正的**上游供货商**模块。与旧 `Supplier`（实为商户，现已重命名为 [[entities/supplier-management|Merchant]]）彻底分离。

参考观麦供应商管理页面结构设计。

## 数据模型

### 主表 `Supplier`

| 字段 | 类型 | 说明 |
|------|------|------|
| supplier_code | VARCHAR(50) | 供应商编号（手动输入，唯一） |
| name | VARCHAR(100) | 供应商名称 |
| settlement_cycle | VARCHAR(20) | 结款周期：日结/周结/半月结/月结 |
| invoice_type | VARCHAR(30) | 开票类型 |
| supplier_nature | VARCHAR(20) | 供应商性质：普通/基地/批发商/厂家 |

### 关联表

- `SupplierCategory` — 可供分类
- `SupplierProduct` — 可供商品
- `SupplierContact` — 联系人
- `SupplierContract` — 合同管理

## 后端架构

| 层 | 文件 |
|----|------|
| Route | `backend/api/routes/supplier.py` |
| Service | `backend/services/supplier_service.py` |
| Repository | `app/db/supplier_repository.py` |
| Schema | `backend/models/supplier_schemas.py` |

## 前端组件

`SupplierManagement.vue` + `SupplierDetail.vue`：
- 供应商列表（编号/名称/结款周期/开票类型/性质/状态）
- 详情页 5 Tab：基本信息 / 可供分类 / 可供商品 / 联系人 / 合同管理

## 路由

- 列表: `/suppliers`
- 详情: `/suppliers/:id`
- API: `/api/supplier/`（权限码 `supplier:*`）

## 相关页面

- [[entities/supplier-management]] — 商户管理（已重命名）
- [[concepts/pricing-center]] — 报价中心关联供应商
