# Wiki Schema

## Domain
滨鲜工作台（Binxian Workbench）——农产品食品安全检测系统。FastAPI + Vue 3 + MySQL，为杭州滨鲜食品有限公司开发。

## Conventions
- File names: lowercase, hyphens, no spaces (e.g., `order-management.md`)
- Every wiki page starts with YAML frontmatter
- Use wikilinks to link between pages (minimum 2 outbound links per page)
- When updating a page, always bump the `updated` date
- Every new page must be added to `index.md` under the correct section
- Every action must be appended to `log.md`

## Frontmatter
```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query
tags: [from taxonomy below]
sources: [raw/source-file.md]
---
```

## Tag Taxonomy
- 业务域: order, supplier, product, inventory, purchase, quotation, settlement
- 模块: backend, frontend, database, api
- 技术: fastapi, vue3, mysql, minio, pytest
- 方法论: architecture, debug, testing, refactor
- 外部: guanmai, opensource
- Meta: decision, pitfall, convention

## Page Thresholds
- **Create a page** when a module/feature has its own set of routes, services, and views
- **Add to existing page** when refining an existing module
- **DON'T create a page** for minor utilities or helper functions
- **Split a page** when it exceeds ~200 lines
