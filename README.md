# 检测报告工具

这是一个本地运行的检测报告工具，包含 FastAPI 后端、Vue 3 + Vite 前端、默认 SQLite 数据库，以及可选的本地语音识别能力。

## 环境要求

- Windows 10/11
- Python 3.11 或更新版本
- Node.js 20 或更新版本
- Git

## 首次安装

克隆仓库后，在项目根目录执行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup.ps1
```

这个脚本会创建 `.venv`、安装 Python 依赖，并在 `frontend` 目录执行 `npm install`。

如果想手动安装，也可以执行：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd frontend
npm install
cd ..
```

## 启动项目

安装完成后，在项目根目录运行：

```powershell
.\start.ps1
```

启动后访问：

- 前端：http://localhost:5173
- 后端：http://127.0.0.1:8000
- API 文档：http://127.0.0.1:8000/docs

也可以使用批处理启动：

```bat
start.bat
```

## 本地配置

默认配置可以直接运行。需要覆盖本地设置时，复制示例文件：

```powershell
Copy-Item .env.local.example .env.local
```

`.env.local` 不会提交到 Git，用来保存本机模型、数据库、认证种子密码等私有配置。

默认数据库是 SQLite，运行时会自动创建 `data/app.db`。如果要切换 MySQL，请先完成迁移并在 `.env.local` 中设置 `APP_DB_DRIVER=mysql` 及相关连接参数。

## 语音识别

依赖安装后，项目具备本地 ASR 运行条件。首次使用 Qwen3-ASR 或 faster-whisper 时，模型可能需要下载，缓存默认在 `.cache/huggingface`，这个目录不会上传到 GitHub。

如果新设备暂时不需要语音识别，只要不触发语音录入功能，Web 项目仍可正常启动。

## 可选桌面端

如果需要运行旧的 PySide6 桌面入口：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
.\.venv\Scripts\python.exe main.py
```

## 验证

安装依赖后可以运行：

```powershell
.\verify.ps1
```

验证脚本会运行后端测试、Python 编译检查、后端导入检查、前端类型检查和前端构建。
