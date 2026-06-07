---
title: 商品管理模块
created: 2026-06-07
updated: 2026-06-07
type: entity
tags: [product, backend, frontend, fastapi, vue3]
---

# 商品管理（ProductManagement）

## 概述

管理商品主数据、分类、SKU，支持查询、筛选、上下架。商品被订单、采购、库存模块引用。

## 后端架构

| 层 | 文件 |
|----|------|
| Route | `backend/api/routes/product.py` |
| Repository | `app/db/product_repository.py` |

## 关键功能

### 商品 CRUD
- 列表：search、category_id 筛选、分页
- 新增/编辑：名称、分类、单位、内部备注
- 下架（is_active=0）/ 上架

### 分类管理（CategoryManagement.vue）
- 树形无限层级分类
- 自动计算 level、新增/编辑/删除

### 商品台账（ProductLedger.vue）
- 按商品查询库存流水

## 数据库

`Product` 表核心字段：name、category_id、base_unit、is_active、notes

## 相关页面

- [[entities/order-management]] — 订单引用商品
- [[entities/inventory-management]] — 库存关联商品
- [[concepts/convention-pitfalls]] — 商品操作错误处理规范
