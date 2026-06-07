---
title: 数据迁移模块
created: 2026-06-07
updated: 2026-06-07
type: entity
tags: [transfer, backend, frontend, fastapi, vue3]
---

# 数据迁移（DataTransfer）

## 概述

月度数据迁移和批量文件处理。支持文件选择、路径锁定、单次/月度处理。

## 后端架构

| 层 | 文件 |
|----|------|
| Route | `backend/api/routes/transfer.py` |

## 前端组件

`DataTransfer.vue`：
- 文件来源面板（FileSourcePanel）
- 单次处理 / 月度处理
- 路径锁定切换

## 文件选择器

统一的 `FileSourcePanel` 组件，被多个模块复用：
- 路径锁定模式（记住上次路径）
- 临时模式（单次使用不记忆）
- 2026-06 改造为统一文件选择器

## 相关页面

- [[entities/pesticide-detection]] — 复用 FileSourcePanel
