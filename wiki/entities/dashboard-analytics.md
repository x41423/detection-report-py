---
title: 仪表盘与分析
created: 2026-06-07
updated: 2026-06-07
type: entity
tags: [dashboard, analytics, frontend, vue3]
---

# 仪表盘与分析（Dashboard & Analytics）

## 概述

数据可视化与分析模块。6 个子页面提供销售、客户、库存、应付、未下单商户视角。

## 前端组件

| 页面 | 功能 |
|------|------|
| `Dashboard.vue` | 首页仪表盘（本月订单/采购/库存 KPI） |
| `ProductSalesAnalysis.vue` | 商品销售排行（日期筛选、CSS 柱状图） |
| `SalesReport.vue` | 销售总表（按日期汇总、CSV 导出） |
| `CustomerAnalysis.vue` | 客户购买分析（排名、汇总） |
| `PayablesReport.vue` | 应付总账（按供应商汇总） |
| `InactiveMerchants.vue` | 未下单商户（N 天无订单客户） |

## 后端

- `backend/api/routes/dashboard.py` + `product_analysis.py`
- `dashboard_repository.py` — 当月聚合查询
- `product_analysis_repository.py` — 销售/客户/库存/应付查询

## Dashboard 日期注意事项（Pitfall #12）

Dashboard 使用 `date.today()` 过滤当月数据。测试数据必须用当前日期创建，不能用硬编码日期。

## 相关页面

- [[entities/order-management]] — 销售数据来源
- [[entities/purchase-management]] — 采购数据来源
- [[concepts/convention-pitfalls]] — Dashboard 测试日期规范
