---
title: 库存同步机制
created: 2026-06-07
updated: 2026-06-07
type: concept
tags: [inventory, backend, fastapi]
---

# 库存同步机制

## 出库（OUT）

`OrderService.outbound()` 对每个订单商品写入 InventoryTransaction：
- `direction=OUT`, `source_type=purchase_outbound`
- 扣减对应的 ProductSku 库存

## 撤销出库（UNDO）

`OrderService.undo_outbound()` 写入反向交易：
- `direction=IN`, `source_type=purchase_outbound_undo`
- 恢复 ProductSku 库存
- 回退 OrderRecord.order_status → pending

## 采购入库（IN）

`PurchaseService.confirm_purchase_in()` 写入：
- `direction=IN`, `source_type=purchase_in`
- 增加库存

## 采购退货（OUT）

`PurchaseService.confirm_purchase_return()` 写入：
- `direction=OUT`, `source_type=purchase_return`
- 减少库存

## Pydantic Literal 同步（⚠️ Pitfall #9）

`InventorySourceType` Literal 新增值必须同时改两处：
1. `schemas.py` 顶部别名
2. 行内 `source_type: Literal[...]`

漏一处 → 400 错误。

## 相关页面

- [[entities/order-management]] — 出库/撤销操作
- [[concepts/convention-pitfalls]] — 同步规范
