---
title: 代码审查报告（2026-06-07）
created: 2026-06-07
updated: 2026-06-07
type: comparison
tags: [code-review, refactor, pitfall]
sources: [docs/code-review-report.html]
---

# 代码审查报告（2026-06-07）

> 审查范围：142 Python + 110 Vue/TS 文件

## 问题清单

| # | 问题 | 风险 | 状态 |
|---|------|------|------|
| 1 | 数据库双写不同步 | 🔴 | ~~跳过~~（SQLite 已删除） |
| 2 | 响应格式不统一 | 🟡 | ✅ 已修复 |
| 3 | 部分模块缺失 Service 层 | 🟡 | ✅ 已评估（极简 CRUD 无需） |
| 4 | 敏感文件残留 | 🔴 | ✅ 已修复（垃圾文件删除） |
| 5 | 前端错误静默吞掉 | 🟡 | ✅ 已修复（16 页 try/catch） |
| 6 | Token 在 localStorage | 🔵 | ✅ 已验证不适用（httpOnly cookie） |
| 7 | 裸 except 子句 | 🟡 | ✅ 已修复（3 文件 4 处） |
| 8 | 超大文件需拆分 | 🔵 | ⏳ Phase 2 计划中 |
| 9 | 缺少审计追踪 | 🔵 | ⏳ Phase 2 计划中 |
| 10 | 交易概况 LIKE 匹配 | 🔴 | ✅ 已修复（merchant_name 精确） |
| 11 | UPDATE 字段名拼接 | 🟡 | ✅ 已修复（白名单） |
| 12 | 缺少 404 路由 | 🔵 | ✅ 已修复（NotFound.vue） |

## Phase 2 待执行

- [[convention-pitfalls]] 中的 `store.py` 拆分（按域 → `schema/_orders.py` 等）
- [[order-management]] 中 `OrderManagement.vue` 的搜索 composable 提取
- 审计追踪已在 Router 层就绪，需在关键端点加 `audit_log_service.record()`

## 相关

- [[convention-pitfalls]] — 修复过程中沉淀的开发约定
- [[order-management]] — 订单模块的关联修复
- [[supplier-management]] — 供应商模块的关联修复
