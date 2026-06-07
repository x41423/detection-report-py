---
title: 报损报溢管理
created: 2026-06-07
updated: 2026-06-07
type: entity
tags: [loss, backend, frontend, fastapi, vue3]
---

# 报损报溢（LossReport）

## 概述

记录商品损耗（报损）和溢余（报溢），支持主子表明细。

## 后端架构

| 层 | 文件 |
|----|------|
| Route | `backend/api/routes/loss_report.py` |
| API | `frontend/src/api/loss-report.ts` |

## 前端组件

`LossReportManagement.vue`：
- 列表（单号、日期、类型、金额、状态）
- 新增（主子表：品名、数量、单位、单价、原因）
- 明细查看
- 删除

## 相关页面

- [[entities/inventory-management]] — 报损报溢影响库存
