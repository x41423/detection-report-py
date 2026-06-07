---
title: 库存管理模块
created: 2026-06-07
updated: 2026-06-07
type: entity
tags: [inventory, backend, frontend, fastapi, vue3]
---

# 库存管理（InventoryManagement）

## 概述

管理商品库存、库存流水、出入库汇总。被订单出库、采购入库、手动调整驱动。

## 后端架构

| 层 | 文件 |
|----|------|
| Route | `backend/api/routes/inventory.py` |
| Repository | `app/db/inventory_repository.py` |

## 前端组件

- `Inventory.vue` — 库存总览
- `InventoryTransactions.vue` — 库存流水明细（方向/来源/日期筛选）
- `InventorySummary.vue` — 出入库汇总统计

## 库存数据流

```
采购入库 → IN (purchase_in)
采购退货 → OUT (purchase_return)
订单出库 → OUT (purchase_outbound)
撤销出库 → IN (purchase_outbound_undo)
每日采集 → IN (daily_intake)
手动调整 → IN/OUT (manual_adjust)
```

## 相关页面

- [[concepts/inventory-sync]] — 每种交易类型的详细同步逻辑
- [[entities/order-management]] — 出库触发库存变更
- [[entities/purchase-management]] — 入库触发库存变更
