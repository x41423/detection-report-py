---
title: 检测报告归档
created: 2026-06-07
updated: 2026-06-08
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
- **文件预览**：详情弹窗内嵌预览 PDF/DOCX/JPG/PNG/CSV/TXT，基于 [[concepts/file-preview]] 统一组件

## 文件上传与预览

| 功能 | 详情 |
|------|------|
| 上传格式 | PDF、DOCX/DOC、JPG/JPEG/PNG、ZIP |
| 大小限制 | 5MB |
| 存储路径 | `data/uploads/reports/` |
| 预览方式 | 详情弹窗内嵌 `FilePreviewDialog`，支持预览 PDF/Word/Excel/图片/CSV/文本；表格行点击 👁 图标直接预览；保留"新窗口打开"作为备选 |

## 数据库

`InspectionReport` + `InspectionReportProduct`（主子表）

## 相关页面

- [[entities/pesticide-detection]] — 检测生成报告 → 归档
- [[entities/product-management]] — 报告关联商品
- [[concepts/file-preview]] — 文件预览统一组件
