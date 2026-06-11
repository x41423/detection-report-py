---
title: 项目开发约定与已知坑
created: 2026-06-07
updated: 2026-06-07
type: concept
tags: [convention, pitfall, backend, frontend, testing]
---

# 开发约定与已知坑

## Pydantic Literal 双写（Pitfall #9）

`InventorySourceType` 新增值（如 `purchase_outbound_undo`）必须同步改两处：
1. `schemas.py` 顶部 `Literal` 别名
2. 行内 `source_type: Literal[...]` 字段

漏一处 → 400 错误。

## Vue Router 参数响应（Pitfall #10）

详情页路由参数（如 `suppliers/:id`）用 `computed + watch`：
```typescript
const id = computed(() => Number(route.params.id))
watch(id, () => load())
```
不要只 `const id = Number(route.params.id)` → 切换不刷新。

## 前端操作按钮规范（Pitfall #11）

统一风格：`size="small"` + `link` + 状态驱动 `v-if`：
```
活跃状态 → 显示「停用」
停用状态 → 显示「启用」+「删除」
```

## Dashboard 测试日期（Pitfall #12）

Dashboard 用 `date.today()` 过滤当月数据，测试数据必须用当前日期。不能用硬编码日期如 `2026-05-15`。

## 错误处理规范（2026-06-07 统一）

所有 API 调用必须有 try/catch：
```typescript
try {
  await api.xxx()
  ElMessage.success('成功')
} catch (e: any) {
  if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || '操作失败')
}
```

## 响应格式约定

项目约定 `{success, message, items, total}`。新建端点应遵守。

## 数据库双写（已废弃）

2026-06-07 起项目已切换到纯 MySQL。SQLite 文件已删除。`mysql_schema.py` 与 `store.py` 需保持一致（59 张表）。

## Supplier 字段白名单

`supplier_repository.py` 新增 `_UPDATE_WHITELIST`。新增 Supplier 表字段时需同步更新。

## 测试数据清理

供应商测试可能创建采购记录 → 阻断停用。测试前需调用 `_cleanup_tables()` 清理。

**完整清理工具**：`python scripts/cleanup_test_data.py --dry-run`（预览）→ `python scripts/cleanup_test_data.py`（执行）。
清理范围：所有 `test.*` 用户 + `display_name='API Test User'` + 全部业务表数据。
详见 `test-data-cleanup` skill。

## 相关页面

- [[comparisons/code-review-2026-06-07]] — 原始代码审查报告
- [[comparisons/skill-ecosystem]] — 开发中常用的 Skill 清单
