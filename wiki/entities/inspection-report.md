---
title: 检测报告归档
created: 2026-06-07
updated: 2026-06-07
type: entity
tags: [inspection, backend, frontend, fastapi, vue3]
---

# 检测报告归档（InspectionReport）

## 概述

检测报告的归档管理系统。支持上传文件、关联商品、生成编号。

## 后端架构

| 层 | 文件 |
|----|------|
| Route | `backend/api/routes/inspection_report.py` |
| Repository | `app/db/inspection_report_repository.py` |

## 前端组件

`InspectionReportManagement.vue`：
- 报告列表（编号、日期、关联商品、文件上传）
- 新增/编辑/删除

## 数据库

`InspectionReport` + `InspectionReportProduct`（主子表）

## 相关页面

- [[entities/pesticide-detection]] — 检测生成报告 → 归档
- [[entities/product-management]] — 报告关联商品
