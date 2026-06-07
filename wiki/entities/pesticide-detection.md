---
title: 农残检测模块
created: 2026-06-07
updated: 2026-06-07
type: entity
tags: [pesticide, backend, frontend, fastapi, vue3]
---

# 农残检测（PesticideDetection）

## 概述

农产品农药残留检测核心功能。支持单次检测、月度批量处理、模板管理、报告生成。

## 后端架构

| 层 | 文件 |
|----|------|
| Route | `backend/api/routes/pesticide.py`、`smart_detection.py` |
| Service | 相关检测逻辑 |

## 前端组件

- `Pesticide.vue` — 农残检测主页面
- `SmartDetection.vue` — 智能检测（单次/批量/补做）
- `FileSourcePanel` — 文件来源统一面板

## 关键功能

### SmartDetection
- 单次检测：选择模板 → 编辑模板 → 执行 → 生成报告
- 批量检测：批量文件处理
- 补做功能：按日期范围批量补做缺失报告

### 模板管理
- Big template（大模板）+ Small template（小模板）
- 上传/编辑/保存到 MinIO

### 报告生成
- 导出格式：DOCX / PDF + DOCX（both）
- 自动填充检测员信息

## 检测流程

```
选择模板 → 编辑网格 → 选择日期 → 执行检测 → 下载报告
```

## 相关页面

- [[entities/inspection-report]] — 检测报告归档
- [[entities/data-transfer]] — 数据迁移模块（文件选择复用）
