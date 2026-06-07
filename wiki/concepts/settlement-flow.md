---
title: 结算业务流程
created: 2026-06-07
updated: 2026-06-07
type: concept
tags: [settlement, supplier, order]
---

# 结算业务流程

## 观麦模式参考

观麦的商户结算配置包含：
- **结算方式**：先货后款 / 现款现货
- **账期方式**：按周期（固定周期结算）
- **日期维度**：按下单日期 / 按收货日期
- **结款周期**：日结 / 周结 / 月结
- **起始日**：每月 N 日
- **结算日**：每月 N 日

## 滨鲜实现

`Supplier` 表中的结算配置字段：
- `settlement_method` — 结算方式
- `date_dimension` — 日期维度（`order_date` / `receipt_date`）
- `period_start_day` — 周期起始日
- `settlement_day` — 结算日
- `freeze_status` — 冻结状态（禁止下新单）

## 结算单管理

`SettlementManagement.vue` 提供：
- 手动创建结算单（指定供应商 + 周期）
- 自动生成结算单（根据已确认入库记录）
- 结算单确认（2026-06-07 已添加 try/catch）

## 相关页面

- [[supplier-management]] — 结算配置的来源
- [[order-management]] — 订单的结算周期计算
- [[purchase-management]] — 入库记录驱动结算
