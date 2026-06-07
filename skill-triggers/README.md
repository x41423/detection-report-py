# Skill 唤醒提示词速查表

> 放到项目根目录，随时查阅。你对我说左栏任一关键词，我会自动加载对应 Skill。
>
> **已安装**：Hermes 原生 124 个 + ECC 242 个 = 共 366 个 Skill

---

## 一、项目管理（Git & 计划）

| 说这些话 | 触发 Skill | 做什么 |
|----------|-----------|--------|
| "开个分支"、"新建分支"、"新功能"、"改个bug"、"修一下" | `git-branch-workflow` | Git 分支工作流，不再直接改 main |
| "存档"、"commit"、"推送"、"合并到main"、"切回main" | `git-branch-workflow` | 代码存档、推送、合并 |
| "出计划"、"写计划"、"先计划" | `writing-plans` | 编写详细实现计划 |
| "计划模式"、"plan mode" | `plan` | 只出计划不执行代码 |
| "审查方案"、"grill方案"、"审一下" | `grill-with-docs` | 对照项目文档审查方案 |
| "grill me"、"拷问我" | `grill-me` | 逐层追问设计决策 |
| "拆成issues"、"拆任务"、"拆分工作" | `to-issues` | 把计划拆成独立可执行的 issues |
| "生成PRD"、"需求文档"、"出需求" | `to-prd` | 从当前对话生成产品需求文档 |
| "交接"、"handoff"、"转交" | `handoff` | 压缩当前对话给另一个 Agent |
| "zoomit"、"大局观"、"全貌" | `zoom-out` | 从更高视角看代码和架构 |

---

## 二、滨鲜工作台开发

| 说这些话 | 触发 Skill | 做什么 |
|----------|-----------|--------|
| "滨鲜"、"工作台"、"检测报告"、"库存"、"周报价"、"供应商"、"采购"、"结算"、"农药残留" | `binxian-workbench` | 项目约定：表名、响应格式、权限、双写 |
| "接口"、"API"、"路由"、"端点"、"FastAPI" | `fastapi-patterns` | FastAPI 异步模式、依赖注入、Pydantic |
| "Python规范"、"Python风格"、"PEP" | `python-patterns` | Python 惯用写法、类型提示 |
| "加表"、"改表"、"数据库迁移"、"schema" | `database-migrations` | 安全变更数据库结构、零停机 |
| "API设计"、"REST"、"接口规范" | `api-design` | 资源命名、状态码、分页、版本控制 |
| "错误处理"、"异常"、"报错提示" | `error-handling` | 前后端错误处理最佳实践 |

---

## 三、调试与验证

| 说这些话 | 触发 Skill | 做什么 |
|----------|-----------|--------|
| "调试"、"debug"、"bug"、"报错"、"出问题了"、"diagnose" | `systematic-debugging`、`diagnose` | 四阶段根因调试法 / 诊断循环 |
| "验证"、"检查"、"跑一下"、"确认没问题" | `verification-loop` | 全面验证：类型检查、构建、无残留 |
| "TDD"、"测试驱动"、"先写测试"、"red-green-refactor" | `test-driven-development`、`tdd` | 红-绿-重构循环 |
| "代码审查"、"review"、"审代码"、"检查一下" | `requesting-code-review` | 提交前安全检查、质量门禁 |

---

## 四、浏览器自动化（观麦等）

| 说这些话 | 触发 Skill | 做什么 |
|----------|-----------|--------|
| "浏览器"、"打开网页"、"自动化"、"browser" | `browser-act` | 浏览器自动化 CLI |
| "DevTools"、"chrome调试"、"MCP" | `chrome-devtools-mcp` | Chrome DevTools 协议操作 |
| "分析网页"、"爬页面结构"、"SPA" | `spa-page-analysis` | SPA 路由提取、页面结构分析 |
| "爬取SPA"、"认证爬虫"、"绕过登录" | `spa-crawling` | 认证后 SPA 全站爬取 |

---

## 五、技能管理

| 说这些话 | 触发 Skill | 做什么 |
|----------|-----------|--------|
| "做成skill"、"保存为技能"、"记住这个做法"、"写个skill" | `write-a-skill` | 创建新 Skill |
| "skill格式"、"skill规范"、"skill怎么写" | `hermes-agent-skill-authoring` | Skill 编写规范 |
| "安装skill"、"安装技能包"、"装外部skill" | `external-skills-installation` | 从 GitHub 安装外部 Skill 包 |

---

## 六、效率工具

| 说这些话 | 触发 Skill | 做什么 |
|----------|-----------|--------|
| "caveman"、"压缩模式"、"省token" | `caveman` | 极简回复模式，省 75% token |
| "上下文"、"token预算"、"太长了" | `context-budget` | 审计上下文消耗、优化建议 |
| "脚手架"、"快速原型"、"prototype" | `prototype` | 抛弃式原型，验证想法 |
| "spike"、"验证可行性" | `spike` | 快速实验，确认技术路线 |
| "写文章"、"编辑文章"、"润色" | `edit-article` | 编辑和润色文章 |
| "Obsidian"、"笔记"、"知识库" | `obsidian`、`obsidian-vault` | Obsidian 知识库读写 |

---

## 七、GitHub 协作

| 说这些话 | 触发 Skill | 做什么 |
|----------|-----------|--------|
| "审查PR"、"review PR" | `github-code-review` | PR diff 查看、行内评论 |
| "开issue"、"创建issue"、"GitHub问题" | `github-issues` | 创建/管理 Issues |
| "提交PR"、"pull request"、"PR流程" | `github-pr-workflow` | 从分支到合并的完整 PR 流程 |
| "clone仓库"、"fork"、"fork项目" | `github-repo-management` | 仓库克隆/创建/Fork |
| "git安全"、"禁止push"、"防误删" | `git-guardrails-claude-code` | 拦截危险 Git 操作 |

---

## 八、Hermes 自身

| 说这些话 | 触发 Skill | 做什么 |
|----------|-----------|--------|
| "Hermes配置"、"hermes怎么设置"、"改模型" | `hermes-agent` | Hermes Agent 本身配置、扩展 |
| "关机卡住"、"gateway关不掉" | `hermes-gateway-shutdown` | 诊断并杀掉阻止关机的 Gateway 进程 |
| "WebUI"、"安装WebUI"、"hermes界面" | `hermes-webui` | Hermes WebUI 安装与配置 |

---

## 九、ECC 增强包（242 个 Skill）

ECC 是 Agent 增强操作系统，覆盖开发全流程。以下为重点类别速查，完整列表见 `hermes skills list ecc`。

### 开发流程增强

| 说这些话 | 触发 Skill | 做什么 |
|----------|-----------|--------|
| "代码审查"、"安全检查"、"review" | `security-review`、`security-scan` | 安全审查、AgentShield 扫描 |
| "代码标准"、"规范" | `coding-standards` | 跨项目编码规范 |
| "架构评审"、"架构决策" | `architecture-decision-records` | 记录架构决策为 ADR |
| "生成蓝图"、"出蓝图"、"blueprint" | `blueprint` | 把一句话目标拆成多步骤工程计划 |
| "E2E测试"、"端到端测试" | `e2e-testing` | Playwright E2E 测试 |
| "docker"、"容器化" | `docker-patterns` | Docker/Compose 模式 |
| "部署"、"CI/CD" | `deployment-patterns` | 部署流水线、健康检查、回滚 |
| "postgres"、"mysql" | `postgres-patterns`、`mysql-patterns` | 数据库查询优化、索引设计 |
| "redis"、"缓存" | `redis-patterns` | 缓存策略、分布式锁 |

### 代码生成与审查

| 说这些话 | 触发 Skill | 做什么 |
|----------|-----------|--------|
| "后端模式"、"API架构" | `backend-patterns` | Node.js/Express 后端架构 |
| "Git工作流"、"分支策略" | `git-workflow` | Git 分支策略、commit 规范 |
| "GitHub操作"、"PR管理" | `github-ops` | GitHub Issues/PRs/CI 操作 |
| "设计系统"、"UI一致性" | `design-system` | 设计系统生成与审计 |
| "React"、"Next.js优化" | `react-patterns`、`react-performance` | React 最佳实践与性能优化 |
| "Vite"、"构建优化" | `vite-patterns` | Vite 配置、插件、HMR |
| "接口体验"、"UI打磨" | `make-interfaces-feel-better` | UI 间距、排版、动效细节 |
| "Vue组件生成"、"截图转Vue" | `ui-to-vue` | 截图批量转 Vue 3 组件 |

### Agent 与自动化

| 说这些话 | 触发 Skill | 做什么 |
|----------|-----------|--------|
| "自主Agent"、"自动化循环" | `autonomous-agent-harness` | 构建自主 Agent 系统 |
| "多Agent"、"并行agent" | `team-agent-orchestration`、`dmux-workflows` | 多 Agent 编排 |
| "连续学习"、"session学习" | `continuous-learning-v2` | 从 session 中自动提取经验 |
| "eval"、"评估agent" | `eval-harness`、`agent-eval` | Agent 评估框架 |

### 产品与内容

| 说这些话 | 触发 Skill | 做什么 |
|----------|-----------|--------|
| "写文章"、"博客"、"长文" | `article-writing` | 撰写文章、指南、博客 |
| "市场研究"、"竞品分析" | `market-research` | 市场研究、竞品分析 |
| "投资者材料"、"BP"、"融资" | `investor-materials`、`investor-outreach` | 融资材料、投资人沟通 |
| "SEO"、"搜索优化" | `seo` | 技术SEO、结构化数据 |
| "内容分发"、"多平台" | `content-engine`、`crosspost` | 多平台内容适配发布 |

### 效率与安全

| 说这些话 | 触发 Skill | 做什么 |
|----------|-----------|--------|
| "成本追踪"、"用了多少token" | `cost-tracking` | Token 用量与花费追踪 |
| "prompt优化"、"改进指令" | `prompt-optimizer` | 优化 Prompt 质量 |
| "context预算"、"token太多" | `token-budget-advisor` | 控制回复深度 |
| "安全检查"、"漏洞扫描" | `safety-guard` | 防误操作保护 |
| "仓库审计"、"代码扫描" | `repo-scan` | 全仓库源码资产审计 |

> **提示**：Skill 是按关键词自动匹配的，不需要精确说出 Skill 名字。只要你的话跟某个类别沾边，我就会加载对应的 Skill。

---

## 十、Agent Reach — 全网搜索与平台访问

> 17 个平台统一入口：网页、社交、视频、招聘、开发。零配置 8 个渠道，剩余需登录 Cookie 或 API Key。

| 说这些话 | 触发 Skill | 做什么 |
|----------|-----------|--------|
| "搜一下"、"查一下"、"搜索"、"帮我搜" | `agent-reach` | 全网语义搜索（Exa）、通用网页阅读（Jina） |
| "小红书"、"xhs"、"红书" | `agent-reach` | 小红书笔记阅读、搜索、发帖（需登录） |
| "抖音"、"douyin" | `agent-reach` | 抖音视频解析、无水印下载 |
| "Twitter"、"推特"、"x.com"、"推文" | `agent-reach` | Twitter/X 搜索推文、看时间线（需 Cookie） |
| "微博"、"weibo"、"热搜" | `agent-reach` | 微博热搜、搜索、用户动态（装好即用） |
| "B站"、"bilibili"、"哔哩哔哩" | `agent-reach` | B站视频、字幕、热门排行、搜索 |
| "Reddit" | `agent-reach` | Reddit 搜索帖子、读帖+评论 |
| "V2EX" | `agent-reach` | V2EX 热门主题、节点、用户信息 |
| "雪球"、"股票"、"xueqiu"、"行情" | `agent-reach` | 雪球股票行情、热门帖子（需 Cookie） |
| "LinkedIn"、"领英"、"招聘"、"找工作" | `agent-reach` | LinkedIn Profile 查看、职位搜索 |
| "公众号"、"微信文章"、"RSS"、"读一下" | `agent-reach` | 微信公众号文章搜索、RSS 订阅源 |
| "YouTube"、"视频字幕"、"小宇宙"、"播客"、"转录" | `agent-reach` | YouTube/B站字幕下载、小宇宙播客转文字（需 Groq Key） |

### 快速命令参考

```bash
# Exa 全网搜索
mcporter call 'exa.web_search_exa(query: "关键词", numResults: 5)'

# 通用网页阅读
curl -s "https://r.jina.ai/URL"

# GitHub 搜索
gh search repos "关键词" --sort stars --limit 10

# Twitter 搜索
twitter search "关键词" --limit 10

# YouTube/B站字幕
yt-dlp --write-sub --skip-download -o "/tmp/%(id)s" "URL"

# Reddit 搜索
rdt search "关键词" --limit 10

# V2EX 热门
curl -s "https://www.v2ex.com/api/topics/hot.json"

# 环境检查
agent-reach doctor
```

### 配置更多渠道

```bash
# 安装指定渠道
agent-reach install --channels=twitter,weibo,xiaohongshu

# 安装全部
agent-reach install --channels=all

# Cookie 导入（Twitter/小红书/雪球）
agent-reach configure twitter-cookies "PASTED_STRING"

# 代理配置（中国大陆环境）
agent-reach configure proxy http://user:***@ip:port
```
