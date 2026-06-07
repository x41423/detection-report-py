---
title: 报价/锁价/改单/协议价
created: 2026-06-07
updated: 2026-06-07
type: concept
tags: [quotation, pricing, backend, frontend]
---

# 报价中心（报价/锁价/改单/协议价）

## 概述

滨鲜工作台的营销工具模块，管理限时锁价、协议价、报价单、订单改单。

## 子模块

### 限时锁价（PriceLockManagement）
- 规则：rule_code、rule_name、品类数、有效期
- 锁定价覆盖指定菜单的商品价格
- 停用/启用操作

### 协议价管理（AgreementPriceManagement）
- 供应商 × 商品 × 协议单价
- 有效期范围
- 入库时按协议价自动填入

### 上浮定价（PriceMarkupManagement）
- 按分类/商品/全局设置上浮比例（%）
- 影响报价计算

### 报价单管理（QuotationManagement）
- 报价单 CRUD
- 关联标签（tags）
- 报价商品明细

### 改单审核（OrderModificationManagement）
- 订单修改提交审核
- 待审核/已通过/已驳回状态流转
- 审核意见填写

## 相关页面

- [[entities/weekly-price]] — 每周报价主流程
- [[entities/supplier-management]] — 协议价关联供应商
- [[entities/order-management]] — 改单审核关联订单
