# Wiki Log

> Chronological record of all wiki actions. Append-only.

## [2026-06-11] update | 新报价汇总空批次 Bug 修复（三层防护）
- Root cause: 酱菜 2026-06-05 批次存在但 0 条记录，`_normalize_batches()` raise ValueError 导致整个周视图崩溃
- Fix 1 (入库拦截): `weekly_quote_repository.py:save_batch()` — entries 为空时直接删除批次，不留空壳
- Fix 2 (汇总跳过): `weekly_quote_summary.py:_normalize_batches()` — 空批次静默 continue，不抛异常
- Fix 3 (前端校验): `WeeklyQuoteSummaryWorkflow.vue:saveCurrentRecord()` — 0 行时已拦截（已有）
- 附带：全局扫描删除空批次 `id=33`（酱菜 2026-06-05）

## [2026-06-11] update | 路由 chunk 后台预下载（真正加速导航）
- Created: `composables/useChunkPreload.ts` — App.vue onMounted 后延迟 2s，遍历所有路由逐个 `import()`，间隔 150ms
- 效果：首屏加载后 4s 内所有页面 chunk 预下载完毕，之后点任何菜单秒开
- 配合：之前的全局 loading 条 + hover 预加载

## [2026-06-11] update | 订单管理默认日期 + 中控台分段条 + Supplier 修复
- 订单管理: FilterBar `date_mode` 默认 `receipt_date`，`date_range` 默认今天
- 中控台: CPU/内存/磁盘 卡片改为一条分段条（绿色=滨鲜，灰色=其他）
- Supplier: `datetime('now','localtime')` → `NOW()`（SQLite 方言）
- el-checkbox: `label` → `value`（Element Plus 弃用警告）

## [2026-06-11] update | Wiki 加载机制修复
- 发现：连续多日工作未加载 wiki（索引+实体+概念页），导致遗漏 20 页已归档知识
- 修复：binxian-workbench SKILL.md 新增 Rule #1：「每次会话必须加载 wiki/index.md + wiki/SCHEMA.md + wiki/log.md 最近 30 行」
- 约定：所有重大变更需同步更新 wiki（实体页 + log.md）

## [2026-06-10] update | 日志系统全面重构 + 中控台
- Refactored: 日志系统 — JSON 结构化（UTC+8）、3 轮转文件（app/error/access）、RequestLogMiddleware（request_id/脱敏/慢请求/PerfStats）
- Created: SystemMonitor 中控台 — 实时 CPU/内存/磁盘/进程/服务状态/内存趋势/日志流
- Frontend: `views/SystemMonitor.vue` + 后端 `api/routes/system_monitor.py`
- Pitfalls added: #17（Starlette 中间件反序）, #27（端口并行检测+缓存）

## [2026-06-10] update | 商户模块增强 + 订单批量操作
- Merchant: `created_at` 显示、同名禁止创建（排除已停用）、status 默认 active
- Order: checkbox 多选、批量操作（5 态流转）、冻结/解冻、退款、取消保护、状态驱动按钮、表格全宽
- Pitfalls added: #29（查重排除已停用）, #30（execute_code token 脱敏）, #31（订单保护状态机）, #32（订单状态机正向推进）, #33（Vue Router watch 简化）, #34（_serialize_order_summary 同步）, #35（前端正确但没效果）

## [2026-06-10] update | Cloudflare Tunnel 部署
- Deployed: Cloudflare Tunnel + 本地 Nginx(:8080) + 域名 lina1126.eu.cc
- Scripts: `start.bat`, `stop.bat`
- Pitfall added: #15（Windows port 80 SYSTEM 占用）

## [2026-06-10] update | 大规模重构 OA 评审流程确立
- Pitfall added: #16（4 阶段 OA 评审：影响面分析→逐模块方案对比→冲突检测→可行性分析→定稿）
- User requirement: 禁止拍脑袋出方案，所有大规模改动必须走 OA 流程

## [2026-06-10] update | 开发铁律确立
- Pitfalls added: #18-#28（config_model 不可删除、write_file 静默覆盖、Vue 模板双引号、.bat 文件 heredoc 写入、API 前缀 /api、前端数据守卫、ERR_BLOCKED_BY_CLIENT、patch 转义漂移、execute_code 行号污染）
- 铁律：(1)声称完成前必实测 (2)测试后清理 test.* 用户 (3).bat 用 cat heredoc+chcp65001 (4)勿用 execute_code 读写文件 (5)OA 式流程 (6)状态机严格正向流转

## [2026-06-08] update | Supplier → Merchant 迁移 + 新供应商模块
- Updated: entities/supplier-management — 重命名为商户管理（Supplier→Merchant 表/路由/前端全链路）
- Created: entities/supplier-management-new — 真正供应商模块（观麦结构，5 Tab 详情页）
- Updated: comparisons/mysql-vs-sqlite — 纯 MySQL 模式修复清单
- Migration scope: 50+ 文件，DB 表重命名（列名保留），前端 `/merchants` + `/suppliers` 双路由
- Data: SQLite→MySQL 迁入 6,500+ 行（801 用户→清理后 3 正常用户），测试用户已删除

## [2026-06-08] update | File Preview Feature
- Updated: entities/inspection-report — 新增文件上传规格 + 预览方式说明
- Created: concepts/file-preview — 文件预览统一组件文档（依赖、API、集成指南）
- Feature summary: `@vue-office/docx` + `@vue-office/excel` + `@vue-office/pdf`
  安装并接入检测报告管理，支持 PDF/Word/Excel/图片/CSV/文本内嵌预览。
  组件路径: `frontend/src/components/FilePreviewDialog.vue`
  设计原则: DRY — 一次开发全局复用，禁止各模块重复造轮子。

## [2026-06-07] create | Wiki initialized
- Domain: 滨鲜工作台（Binxian Workbench）
- Structure: SCHEMA.md, index.md, log.md
- Created entities: order-management, supplier-management
- Created concepts: convention-pitfalls
- Source: auto-generated from existing project docs and code analysis

## [2026-06-07] ingest | Code Review Report
- Source: docs/code-review-report.html (2026-06-07)
- Created: code-review-2026-06-07
- 12 issues total, 7 fixed in Phase 1, 2 remaining for Phase 2

## [2026-06-07] ingest | Skill Ecosystem
- Source: skill-triggers/README.md
- Created: skill-ecosystem
- 366 skills cataloged (Hermes 124 + ECC 242 + Superpowers 19)

## [2026-06-07] ingest | Full project upload
 Added 11 pages covering all business modules:
 - entities: product, purchase, inventory, weekly-price, pesticide-detection,
   inspection-report, loss-report, data-transfer, dashboard-analytics
 - concepts: pricing-center, auth-and-permissions
 - comparisons: mysql-vs-sqlite
 Wiki now at 20 pages, 63 wikilinks, 0 broken links
