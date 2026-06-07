---
title: 采购管理模块
created: 2026-06-07
updated: 2026-06-07
type: entity
tags: [purchase, backend, frontend, fastapi, vue3]
---

# 采购管理（PurchaseManagement）

## 概述

管理采购入库和退货流程，自动同步库存。与供应商、结算模块联动。

## 后端架构

| 层 | 文件 |
|----|------|
| Route | `backend/api/routes/purchase.py` |
| Service | `backend/services/purchase_service.py` |
| Repository | `app/db/purchase_repository.py` |

## 库存同步

确认采购入库 → `InventoryTransaction(direction=IN, source_type=purchase_in)` → 库存+
确认退货 → `InventoryTransaction(direction=OUT, source_type=purchase_return)` → 库存-

## 前端组件

`PurchaseManagement.vue`：
- Tab 切换（采购入库 / 退货）
- 主子表录入（品名、数量、单价）
- 保存/确认操作（2026-06-07 已添加 try/catch）

## 相关页面

- [[entities/supplier-management]] — 关联供应商，has_purchase_records 保护
- [[concepts/inventory-sync]] — 库存同步机制
- [[concepts/settlement-flow]] — 入库记录驱动结算
