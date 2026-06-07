---
title: MySQL vs SQLite 迁移
created: 2026-06-07
updated: 2026-06-07
type: comparison
tags: [mysql, sqlite, database, migration]
---

# MySQL vs SQLite 迁移演变

## 时间线

| 日期 | 事件 |
|------|------|
| 初期 | 项目使用 SQLite 开发 |
| 2026-05 | MySQL 双写开始（部分表） |
| 2026-06-05 | 首次迁移：20 张核心表到 MySQL |
| 2026-06-07 | **SQLite 完全删除**，项目切换纯 MySQL |
| 2026-06-07 | `mysql_schema.py` 从 34 张扩展到 59 张表 |

## 关键文件

| 文件 | 用途 |
|------|------|
| `app/db/mysql_schema.py` | 59 张表 MySQL 建表语句 |
| `app/db/store.py` | 历史 SQLite schema（保留供参考） |
| `scripts/mysql_migration.py` | 迁移脚本（需 MySQL root 密码） |
| `scripts/mysql_full_migrate.py` | 全量迁移辅助脚本 |

## 双写补齐过程

1. 原 MySQL 只有 34 张表（auth + 旧核心表）
2. SQLite 有 58 张完整业务表
3. 缺失 25 张表：OrderRecord、Product、PurchaseInRecord、Quotation 等
4. 通过 `mysql_full_migrate.py` 从 SQLite 自动生成 25 张表定义 + 数据迁移
5. 最终 MySQL 达到 59 张表 → SQLite 删除

## 测试验证

- `APP_DB_DRIVER=mysql` → pytest 305 passed
- SQLite 文件已删除（`data/app.db`）

## 剩余注意事项

- `mysql_schema.py` 需与 `store.py` 保持同步
- `_migrate_supplier_columns()` 处理 SQLite → MySQL 字段补齐
- `crud_helpers.py` 通用 CRUD 兼容两种驱动

## 相关页面

- [[comparisons/code-review-2026-06-07]] — 修复了双写问题
- [[concepts/convention-pitfalls]] — 数据库相关约定
