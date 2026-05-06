# 变更日志

所有重要变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

### 新增
- 数据库存储架构（SQLite）
- 变更日志文件
- 数据库初始化脚本
- 数据访问层（DAO）
- 数据迁移框架
- 共享农残数据核心模块 `shared/pesticide_data.py`
- `tests/` 回归测试目录，覆盖抑制率生成与每周报价核心辅助逻辑
- 根目录 `.gitignore`，统一忽略缓存、日志、前端构建产物与运行态文件
- 前端统一 API 错误消息提取 helper `frontend/src/api/errors.ts`
- `tests/test_pesticide_service.py`，覆盖农残服务的配置刷新、文档处理调用和目标文件定位
- 周报价特性目录 `frontend/src/features/weekly-price/`，收纳工作流 composable 与类型定义
- 数据转移与农残检测特性 composable：
  `frontend/src/features/data-transfer/composables/useDataTransferWorkflow.ts`
  `frontend/src/features/pesticide/composables/usePesticideWorkflow.ts`
- 前端共享工作流辅助层 `frontend/src/features/shared/workflow.ts`
- 后端 smoke 测试 `tests/test_backend_smoke.py`
- 前端 `npm run typecheck` 脚本，便于快速回归多端适配改动

### 变更
- 收敛桌面端与后端重复的抑制率生成实现，保留原入口兼容
- 前端 `src/api/index.ts` 按领域拆分为 `config`、`transfer`、`pesticide`、`weekly-price`
- 前端 README 改为项目说明，移除 `HelloWorld.vue` 模板残留引用
- 前端多个页面与工作流组件改为复用统一的 API 异常信息提取逻辑
- `WeeklyPriceUpdateWorkflow.vue` 与 `WeeklyQuoteSummaryWorkflow.vue` 的脚本逻辑迁入 composable，组件收敛为模板装配层
- 周报价路由页改为直接从 `features/weekly-price/components/` 引入工作流组件，特性目录边界闭合
- `DataTransfer.vue` 与 `Pesticide.vue` 的脚本逻辑迁入 feature composable，页面层收敛为模板装配与组件引用
- 四个前端 workflow composable 统一复用共享的日志写入、路径选择与配置 patch 辅助函数
- 删除不再需要的 `frontend/src/features/weekly-price/types.ts` 中转层，周报价组件直接复用共享 workflow 类型
- 前端全局布局、头部导航、PageHero、首页和每周报价主界面增加手机/平板断点与受控横向滚动策略
- 每周新报价总结的供应商切换区改为按桌面/平板/手机三层断点自适应列数

### 修复
- 补足整项目结构优化前的可执行回归验证，避免清理时行为漂移
- 修正农残服务目标文件定位测试中的月份格式期望，锁定 `MM.D` 命名规则
- 修正后端一周报价汇总预览 smoke 测试的输入，改为最小有效 payload

### 移除
- 未使用的 `frontend/src/components/HelloWorld.vue`

### 修复
- 对齐 `daily-intake` 后端与前端的响应 contract，补回 `success/message/sheet/merged` 包装结构，避免页面运行时拿不到 `sheet` 与 `merged` 字段。
- 修复 `daily-intake` 语音解析接口缺少 `intake_date` 与 `merge_preview` 的问题，使重复条目在保存前就能预览累计结果。
- 补齐 `daily-intake` 条目与历史序列化字段，新增 `sheet_id`、`unit_id`、`unit_name`、`total_quantity` 等前端实际使用的数据。

### 修复
- 调整移动端 `daily-intake` 语音会话管理：改为短生命周期识别实例、启用 interim transcript、对 `aborted` 增加一次自动重试，并把开始录入提示延后到真正进入 listening 状态后再显示，降低手机和平板上的误中断概率。
- 对 Via 浏览器与 Android WebView 壳层环境的 `daily-intake` 语音输入改为明确降级提示，不再在这类环境里继续尝试浏览器语音识别，避免反复出现“语音被浏览器中断”误报。
- 将 `daily-intake` 语音输入进一步调整为按环境切换兼容策略：Android Chromium、Android WebView、Via 浏览器都会继续尝试识别，并在 `aborted`/`no-speech` 时切换备用策略和重试；若最终失败，再显示定向兼容性提示。

### 变更
- 收紧 `DailyIntake.vue` 的当前单据条目展示：将数量前置、默认折叠语音转写，并在桌面端为条目列表启用局部滚动，减少查看整张单据时的滚动成本
- `daily-intake` 本地 STT 改为 GPU 优先策略，新增 `auto/cuda/cpu` 与 `auto` compute type 解析、GPU 初始化失败时的 CPU 回退、能力接口运行态字段，以及预热脚本的设备诊断输出
- 新增 `scripts/benchmark_local_stt.py`，可用同一段录音对比 `cpu/int8`、`cuda/float16`、`cuda/int8_float16` 的本地 STT 预热耗时、转写耗时与转写文本

## [1.0.0] - 2026-04-06

### 新增
- 农残检测报告生成功能
- 大表数据写入小表功能
- 卡片式主页布局
- 左右两栏布局（子功能页面）
- 浮动操作按钮
- 抑制率生成逻辑（基于历史记录波动±5%）
- 多表支持和路径记忆功能

### 变更
- UI界面配色优化（浅青蓝色主题）
- 重构为MVC架构
- 抑制率生成逻辑优化

### 修复
- 日期选择框显示不全
- 大表数据匹配bug
- 浮动按钮事件连接问题
