"""应用日志配置：分级轮转文件 + JSON 结构化 + 控制台纯文本。

配置后生效：
  logs/app.log    — INFO+（10MB × 5 备份）
  logs/error.log  — WARNING+（5MB × 3 备份）
  logs/access.log — 请求日志专用（需额外调用 configure_access_logger）
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from shared.log_formatter import JsonLineFormatter

# ---- 轮转参数 ----
_MB = 1024 * 1024
_APP_MAX = 10 * _MB
_APP_BACKUPS = 5
_ERROR_MAX = 5 * _MB
_ERROR_BACKUPS = 3
_ACCESS_MAX = 10 * _MB
_ACCESS_BACKUPS = 5


def configure_application_logging(
    log_dir: Path,
    *,
    include_stream: bool = False,
    level: int = logging.INFO,
) -> None:
    """配置 root logger。

    - log_dir: 日志目录（如 ROOT_DIR / "logs"），自动创建
    - include_stream: 是否输出控制台（开发模式，纯文本格式）
    - level: root logger 最低级别
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    json_fmt = JsonLineFormatter()

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    # 控制台（开发用，纯文本）
    if include_stream:
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
            datefmt="%H:%M:%S",
        ))
        sh.setLevel(logging.DEBUG)
        root.addHandler(sh)

    # app.log —— INFO+
    _add_rotating(root, log_dir / "app.log", json_fmt, logging.INFO,
                  _APP_MAX, _APP_BACKUPS)

    # error.log —— WARNING+
    _add_rotating(root, log_dir / "error.log", json_fmt, logging.WARNING,
                  _ERROR_MAX, _ERROR_BACKUPS)


def configure_access_logger(log_dir: Path) -> logging.Logger:
    """返回专用的 access logger，输出 JSON 到 access.log。"""
    access = logging.getLogger("access")
    access.setLevel(logging.INFO)
    access.propagate = False
    access.handlers.clear()
    _add_rotating(access, log_dir / "access.log", JsonLineFormatter(),
                  logging.INFO, _ACCESS_MAX, _ACCESS_BACKUPS)
    return access


# ---- internal ----

def _add_rotating(
    logger: logging.Logger,
    path: Path,
    fmt: logging.Formatter,
    level: int,
    max_bytes: int,
    backup_count: int,
) -> None:
    """添加一个 RotatingFileHandler。"""
    h = RotatingFileHandler(
        str(path),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    h.setFormatter(fmt)
    h.setLevel(level)
    logger.addHandler(h)
