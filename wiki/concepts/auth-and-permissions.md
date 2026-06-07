---
title: 认证与权限系统
created: 2026-06-07
updated: 2026-06-07
type: concept
tags: [auth, security, backend, frontend]
---

# 认证与权限

## 概述

滨鲜工作台的用户认证、权限控制、设备管理、审计日志系统。

## 架构

- **认证**：JWT + httpOnly cookie 会话恢复
- **权限**：`require_permission("order:view")` 依赖注入
- **审计**：AuditMiddleware 自动记录所有 POST/PUT/PATCH/DELETE

## 前端组件

| 页面 | 功能 |
|------|------|
| `AuthAccess.vue` | 登录/注册 |
| `UserManagement.vue` | 用户管理 |
| `RoleManagement.vue` | 角色权限配置 |
| `PermissionRequests.vue` | 权限申请审批 |
| `AuditLogs.vue` | 审计日志查看 |

## 安全特性

- 密码使用 salt + hash（bcrypt）
- Token 不在 localStorage（已确认）
- 设备管理 + 登录追踪
- 审计日志记录所有变更操作

## 超级管理员

账号：lina1124，用于初始化权限和用户管理。

## 相关页面

- [[comparisons/code-review-2026-06-07]] — 审计追踪增强（Phase 2 计划）
- [[concepts/convention-pitfalls]] — 权限测试规范
