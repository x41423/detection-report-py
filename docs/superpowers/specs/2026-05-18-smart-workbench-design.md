# 智能检测工作台 — 设计文档

> 版本: v1.0 | 日期: 2026-05-18

## 一、概述

将农残检测与数据迁移两大功能融合为"智能检测工作台"，实现从启动到生成报告的全链路自动化，同时整合 13 项优化，减少手动操作步骤。

### 目标

- 启动即迁移：系统启动时自动完成数据迁移
- 打开即推荐：进入工作台自动加载检测清单（每日点货 + 昨日库存）
- 确认即生成：确认蔬菜清单后一键完成抑制率生成 → 模板填充 → 报告输出
- 遗漏即补做：自动发现未检测日期，支持批量补做

---

## 二、整体架构

```
┌─────────────────────────────────────────────────────┐
│                    start.bat                        │
│  ① 统一迁移检查（JSON→SQLite → 周报价 → MySQL）     │
│  ② 启动 Backend (FastAPI) + Frontend (Vite)         │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                智能工作台（Web 前端）                 │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐         │
│  │ 今日进货  │  │ 昨日库存  │  │ 手动补充   │         │
│  │ 需检清单  │  │ 未检清单  │  │           │         │
│  └──────────┘  └──────────┘  └───────────┘         │
│                                                     │
│  [一键生成报告]  [补做遗漏日期]  [PDF导出]           │
│  [导入点货]                                       │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              Backend 服务层                           │
│  ・SmartDetectionService（智能检测编排）              │
│  ・GapDetectionService（遗漏检测）                   │
│  ・OutputArchiver（输出归档）                         │
│  ・ExportService（PDF 导出）                          │
│  ・LowStockNotifier（库存低量提醒）                   │
│  ・SmartTemplateMatcher（模板智能匹配）               │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                    Data Layer                        │
│  ・MySQL（生产）/ SQLite（离线）                      │
│  ・统一配置 → config/app.json                        │
│  ・输出归档 → output/{year}/{month}/{day}/           │
└─────────────────────────────────────────────────────┘
```

---

## 三、数据层

### 3.1 配置整合

| 合并前 | 合并后 |
|--------|--------|
| `config.json`（根目录，数据陈旧） | ❌ 删除 / 重命名为 .bak |
| `config/app.json`（规范位置，数据最新） | ✅ 唯一配置源 |
| `DEFAULT_CONFIG` 内嵌于 `config_model.py` | ✅ 抽出为 `config/defaults.json` |

合并逻辑：
1. 以 `config/app.json` 为基准，优先级最高
2. 将 root `config.json` 中有而 `config/app.json` 无的字段补充进去
3. 完成后将 root `config.json` 重命名为 `config.json.merged.bak`
4. 启动时若两者同时存在且存在冲突字段，输出警告日志

### 3.2 数据迁移统一

统一入口 `scripts/migrate.py`：

| 子命令 | 功能 |
|--------|------|
| `check` | 检查数据库状态，报告是否有未执行的迁移 |
| `run` | 执行所有迁移（JSON→SQLite → 周报价 → MySQL） |
| `verify` | 验证迁移完整性 |
| `status` | 显示当前版本和迁移历史 |

`start.bat` 启动流程：
1. `python scripts/migrate.py check` — 检查数据库状态
2. 若存在待执行迁移 → 自动 `python scripts/migrate.py run`
3. 若已全部完成 → 跳过
4. 启动 Backend + Frontend

迁移版本表 `MigrationVersion` 扩展为记录所有三层迁移的版本号，幂等可重入。

---

## 四、智能检测工作台 Web 前端

### 4.1 页面布局

三栏布局 + 操作区域，支持自动推荐和完全手动两种模式：

```
┌──────────────────────────────────────────────────────────────┐
│  🧪 智能检测工作台                              检查员: 朱林初 │
├──────────────────────────────────────────────────────────────┤
│  [数据源选择]  ● 自动推荐  ○ 完全手动                        │
├────────────┬────────────┬─────────────┬──────────────────────┤
│ 今日进货需检│ 昨日库存未检│  手动补充    │    操作区             │
│            │            │             │                      │
│ ☑ 大白菜   │ ☑ 菠菜     │ [添加蔬菜]   │  📅 检测日期: 05-18   │
│ ☑ 黄瓜     │ ☑ 白萝卜   │ + 输入名称   │  📋 模板: 自动匹配    │
│ ☑ 番茄     │ ☑ 小葱     │             │                      │
│ ☑ 茄子     │            │             │  [一键生成报告]        │
│ ☑ 辣椒     │            │             │  [生成并导出PDF]       │
│ ☐ 冬瓜     │            │             │                      │
│ ☐ 南瓜     │            │             │  📊 库存低量: 菠菜(2)  │
│            │            │             │                      │
│ [全选/反选]│ [全选/反选] │             │  补做遗漏:            │
│            │            │             │  发现 3 天遗漏        │
│ 共 12 种   │  已选 10 种 │             │  [批量补做]           │
└────────────┴────────────┴─────────────┴──────────────────────┘
```

### 4.2 交互流程

**模式一：自动推荐（默认）**
1. 页面加载 → 调用 `/smart-recommend`，获取今日点货蔬菜 + 昨日库存未检蔬菜
2. 三栏展示推荐清单，默认全选
3. 用户可取消勾选、手动补充
4. 点击"一键生成" → 调用 `/smart-execute` 执行完整流水线

**模式二：完全手动**
1. 切换为"完全手动"，仅保留手动补充栏
2. 退回当前手动输入流程

### 4.3 新增 Composables

| Composable | 职责 |
|------------|------|
| `useSmartDetection` | 智能推荐逻辑：获取推荐清单、管理勾选状态、一键执行 |
| `useGapDetection` | 遗漏检测逻辑：查询遗漏日期、执行批量补做 |

### 4.4 新增 API 端点

```
POST /pesticide/smart-recommend
  → 返回 { today_intake: [...], yesterday_inventory: [...], missing_dates: [...] }

POST /pesticide/smart-execute
  → 接收 { selected_varieties, date, manual_additions, output_options }
  → 返回 { success, output_paths, report_summary, low_stock_alerts }

POST /pesticide/backfill
  → 接收 { date_range: {start, end} }
  → 对缺失日期逐天执行检测流程

GET  /pesticide/gaps
  → 返回 { missing_dates: [...], last_detection_date, statistics }

POST /daily-intake/import
  → multipart/form-data: file (CSV/Excel), date
  → 批量导入点货数据
```

---

## 五、后端服务设计

### 5.1 SmartDetectionService

```python
class SmartDetectionService:
    def recommend(date: date, inspector_id: str) -> SmartRecommendation:
        """
        1. 查询 daily_intake，提取该日所有蔬菜名
        2. 查询 inventory，找出昨日库存中未在检测记录中标记的蔬菜
        3. 返回推荐清单，附来源标记（daily_intake / inventory）
        """
    
    def execute(detection_request: SmartDetectionRequest) -> DetectionResult:
        """
        1. 解析蔬菜列表（合并三栏来源）
        2. 调用 DataGeneratorService 生成抑制率
        3. 调用 SmartTemplateMatcher 匹配模板
        4. 调用 doc_handler 填充数据
        5. 调用 OutputArchiver 归档
        6. 调用 LowStockNotifier 检查库存阈值
        return { output_paths, summary, low_stock_alerts }
        """
```

### 5.2 SmartTemplateMatcher

模板匹配优先级：
1. 精确匹配 `农残检测记录表{y}.{m}.{d}.docx`
2. 模糊匹配模板目录中日期最近的文件
3. 兜底：使用模板库中保存的通用模板

### 5.3 GapDetectionService

```python
class GapDetectionService:
    def detect_gaps(from_date, to_date) -> GapReport:
        """
        遍历日期范围 → 检查输出目录是否存在对应大表/小表
        返回缺失日期列表
        """

    def backfill(date_range, templates) -> BackfillResult:
        """
        对缺失日期逐天执行检测流程
        返回成功/失败明细清单，支持断点续做
        """
```

### 5.4 OutputArchiver

```
output/
├── 2026/
│   ├── 05/
│   │   ├── 18/
│   │   │   ├── big/农残检测记录表2026.05.18.docx
│   │   │   ├── big/农残检测记录表2026.05.18-1.docx
│   │   │   └── small/单位农残记录表5.18.docx
│   │   └── ...
└── archive.json
```

### 5.5 ExportService

使用 LibreOffice headless 将 `.docx` 转换为 `.pdf`：

```python
class ExportService:
    def docx_to_pdf(docx_path: str) -> str:
        """subprocess: soffice --headless --convert-to pdf"""
    
    def export_detection_report(date, docx_paths, format='both') -> ExportResult:
        """返回 {docx_files: [...], pdf_files: [...], download_url}"""
```

### 5.6 LowStockNotifier

```python
class LowStockNotifier:
    def check() -> list[LowStockAlert]:
        """
        检测生成后自动执行:
        1. 查询所有商品库存
        2. 筛选库存 ≤ threshold（默认 3）
        3. 返回告警列表
        """
```

### 5.7 批量导入点货

```
POST /daily-intake/import
  Content-Type: multipart/form-data

CSV/Excel 格式:
  名称, 数量, 单位, 类别
  大白菜, 50, 斤, 蔬菜

支持预览确认后导入。
```

---

## 六、权限 & 检测员身份绑定

### 6.1 新增角色

| 角色 | 权限 |
|------|------|
| `inspector`（检测员） | `pesticide:view`, `pesticide:execute`, `daily_intake:view`, `inventory:view` |
| `operator`（操作员） | `daily_intake:view`, `daily_intake:create`, `daily_intake:edit`, `inventory:view` |

### 6.2 身份绑定

- `inspector_name` 不再从 config 文件读取
- 改为从当前登录用户的 `display_name` 获取
- 生成报告时在文档中签署当前用户名
- DB 层记录 `user_id`，追溯"谁生成了哪份报告"

### 6.3 权限矩阵

| 操作 | super_admin | admin | inspector | operator | member |
|------|:---:|:---:|:---:|:---:|:---:|
| 查看仪表盘 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 智能推荐检测清单 | ✓ | ✓ | ✓ | | |
| 执行检测生成 | ✓ | ✓ | ✓ | | |
| 批量补做 | ✓ | ✓ | ✓ | | |
| 录入每日点货 | ✓ | ✓ | | ✓ | |
| 批量导入点货 | ✓ | ✓ | | ✓ | |
| 浏览库存 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 管理用户/角色 | ✓ | ✓ | | | |
| 管理模板 | ✓ | ✓ | | | |

---

## 七、模板版本管理

### 7.1 存储结构

```
data/templates/
├── pesticide/
│   ├── big-template.docx              (latest)
│   ├── big-template.2026-05-18.docx   (历史版本)
│   └── versions.json                  (版本索引)
```

### 7.2 versions.json 格式

```json
{
  "pesticide_big": [
    {"version": 2, "date": "2026-05-18", "file": "big-template.2026-05-18.docx", "uploaded_by": "admin"},
    {"version": 1, "date": "2026-05-15", "file": "big-template.2026-05-15.docx", "uploaded_by": "admin"}
  ]
}
```

### 7.3 新增 API

| 端点 | 功能 |
|------|------|
| `GET /pesticide/templates/{kind}/versions` | 版本历史列表 |
| `POST /pesticide/templates/{kind}/rollback` | 回退到指定版本 |
| `DELETE /pesticide/templates/{kind}/versions/{date}` | 删除旧版本 |

---

## 八、通知提醒

### 8.1 库存低量提醒

- 检测生成后自动检查：所有商品库存 ≤ `inventory_low_stock_threshold` 的列入告警
- 前端展示：工作台页面顶部横幅 + 库存页面红色标记
- 生成报告时在结果摘要中附带低量蔬菜列表

### 8.2 检测遗漏提醒

- 进入工作台时自动检查最近 7 天内有点货但未生成报告的日期
- 横幅提示："⚠ 发现 3 天遗漏检测：[05-15, 05-16, 05-17]"
- 点击可跳转到补做功能

---

## 九、实施顺序

| 阶段 | 内容 | 依赖 |
|------|------|------|
| P1 | 数据层：配置整合 (`config.json` 合并) + 统一迁移入口 `scripts/migrate.py` | 无 |
| P2 | 后端核心：`SmartDetectionService` + `GapDetectionService` + API 路由 | P1 |
| P3 | 前端核心：智能工作台页面 `SmartDetection.vue` 及 composables | P2 |
| P4 | 权限：新增 `inspector` / `operator` 角色 + 检测员身份绑定 | P1 |
| P5 | 增强：模板版本管理 + 输出归档 + PDF 导出 + 库存低量提醒 | P2 |
| P6 | 增强：点货批量导入 CSV/Excel | P2 |

---

## 十、涉及文件变更汇总

### 新增文件

| 文件 | 用途 |
|------|------|
| `scripts/migrate.py` | 统一迁移 CLI 入口 |
| `app/db/unified_migration.py` | 统一迁移编排逻辑 |
| `backend/services/smart_detection_service.py` | 智能检测编排 |
| `backend/services/gap_detection_service.py` | 遗漏检测 & 补做 |
| `backend/services/output_archiver.py` | 输出目录归档 |
| `backend/services/export_service.py` | PDF 导出 |
| `backend/services/low_stock_notifier.py` | 库存低量提醒 |
| `backend/api/routes/smart_detection.py` | 智能检测 API 路由 |
| `frontend/src/views/SmartDetection.vue` | 智能工作台页面 |
| `frontend/src/features/smart-detection/composables/useSmartDetection.ts` | 智能检测 composable |
| `frontend/src/features/smart-detection/composables/useGapDetection.ts` | 遗漏检测 composable |
| `config/defaults.json` | 抽出 DEFAULT_CONFIG |

### 修改文件

| 文件 | 变更 |
|------|------|
| `start.bat` / `start.ps1` | 集成自动迁移 |
| `app/db/auth_seed.py` | 添加 inspector / operator 角色 |
| `backend/services/auth_service.py` | 检测员身份绑定 |
| `backend/api/routes/daily_intake.py` | 新增批量导入端点 |
| `backend/services/template_library_service.py` | 模板版本管理 |
| `app/models/config_model.py` | 整合双配置逻辑 |
| `frontend/src/router/` | 添加智能工作台路由 |

### 废弃 / 删除

| 文件 | 处理 |
|------|------|
| `config.json`（根目录） | 合并后重命名为 `config.json.merged.bak` |
| `run_migration.bat` | 被统一入口替代 |
