---
title: 测试数据清理
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [backend, database, testing, convention]
sources: []
---

# 功能试用数据清理

## 概述

一键清空试用期间录入的业务数据（商户、订单、报价、检测报告等），恢复数据库到干净状态。

脚本：`scripts/cleanup_test_data.py`

## 三种模式

| 模式 | 参数 | 业务表 | 用户 | 场景 |
|------|------|--------|------|------|
| 大清理 | 默认 | 全清空 | 删所有非保护用户 | 正式上线前 |
| 只清业务 | `--business-only` | 全清空 | 不动 | 保留员工，只清数据 |
| 仅测用户 | `--user-mode test-only` | 全清空 | 仅删 `test.*` | pytest 跑完 |

## 保护机制

- 超级管理员（`is_super_admin=1`）永久保护
- `lina1124` 永远不删
- `--keep-user` 可保护任意用户
- `--keep-table` 可保护任意业务表
- 系统配置表（Category, Config, Unit, Veg, permissions, roles）不碰
- 需输入 `YES` 确认，支持 `--dry-run` 预览、`--backup` 备份

## 级联删除顺序

FK 从子到父：
```
auth: sessions → refresh_token_grace → pending_logins → devices
    → permission_overrides → permission_requests → audit_logs
    → user_roles → users

biz: OrderAfterSale → OrderItem → OrderModification → DeliveryTask → OrderRecord
     PurchaseInItem → PurchaseInRecord
     ... (共 65 张业务表)
```

## 相关

- [[concepts/convention-pitfalls]] — 原 pitfall #11 测试数据清理
- [[comparisons/skill-ecosystem]] — 相关 skill: `test-data-cleanup`
- `scripts/cleanup_test_data.py` — 清理脚本
