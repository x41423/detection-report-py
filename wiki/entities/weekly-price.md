---
title: 每周报价模块
created: 2026-06-07
updated: 2026-06-07
type: entity
tags: [quotation, backend, frontend, fastapi, vue3]
---

# 每周报价（WeeklyPrice）

## 概述

滨鲜工作台最核心的功能之一。管理每周执行价更新，支持粘贴菜名+价格双模式、Excel 导入、别名匹配、候选确认。

## 后端架构

| 层 | 文件 |
|----|------|
| Route | `backend/api/routes/weekly_price.py` |
| Service | `backend/services/weekly_price_service.py` |

## 关键端点

| 端点 | 功能 |
|------|------|
| `/preview/paste` | 粘贴模式预检匹配 |
| `/execute/paste` | 粘贴模式执行更新 |
| `/preview/upload` | Excel 上传预检 |
| `/import-reference` | Excel 导入参考 |
| `/summary/measure-units` | 计量单位管理 |
| `/summary/aliases` | 别名库管理 |

## 前端组件

- `WeeklyPrice.vue` — 主流程页
- `WeeklyPriceAliases.vue` — 别名库管理
- `WeeklyPriceUpdateWorkflow.vue` — 粘贴/导入工作流

## 业务流程

1. 粘贴菜名（或导入 Excel）
2. 粘贴价格
3. 运行预检 → 匹配模板中的菜名
4. 处理未匹配项（手动映射/创建别名）
5. 执行更新 → 写入执行价

## 模板

- 待更新报价表 + 参考报价表
- 模板存储在 MinIO（优先本地）
- 编辑模板网格（excel-grid 组件）

## 相关页面

- [[entities/product-management]] — 报价引用商品价格
- [[concepts/convention-pitfalls]] — 价格格式校验规范
