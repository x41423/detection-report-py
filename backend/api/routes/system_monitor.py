"""系统状态监控 API。

返回服务器实时指标：CPU / 内存 / 磁盘 / 进程 / 服务状态 / 内存趋势 / 告警。
权限：system:view
"""

from __future__ import annotations

import concurrent.futures
import os
import socket
import threading
import time
from collections import deque
from pathlib import Path

import psutil
from fastapi import APIRouter, Depends

from backend.auth.dependencies import require_permission
from backend.middleware.request_log_middleware import perf_stats as _perf_stats

router = APIRouter()

# ---------------------------------------------------------------------------
# 配置常量
# ---------------------------------------------------------------------------

_SAMPLE_INTERVAL = 60        # 内存采样间隔（秒）
_TREND_WINDOW = 60           # 保留最近 60 个采样点（1 小时）
_MEMORY_WARN_THRESHOLD_MB = 500
_CONSECUTIVE_GROWTH_ALERT = 5
_PORT_TIMEOUT = 0.5          # 端口检测超时（秒），降低以避免状态接口阻塞
_PORT_CACHE_TTL = 10         # 端口状态缓存时间（秒），避免每次轮询都做 4 次 connect

# 项目磁盘占用缓存
_project_disk_cache: dict = {"gb": 0.0, "time": 0.0}
_PROJECT_DISK_CACHE_TTL = 300  # 5 分钟


# ---------------------------------------------------------------------------
# 内存趋势采集器（后台线程，启动后自动运行）
# ---------------------------------------------------------------------------

class _MemoryTrendCollector:
    """后台采集 Python 进程 RSS，生成趋势 + 告警。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._trend: deque[dict] = deque(maxlen=_TREND_WINDOW)
        self._alerts: list[dict] = []
        self._start_time = time.time()
        self._pid = os.getpid()
        self._running = True

    def start(self) -> None:
        t = threading.Thread(target=self._loop, daemon=True, name="mem-collector")
        t.start()

    def collect(self) -> dict:
        """采样一次，更新趋势和告警。"""
        try:
            proc = psutil.Process(self._pid)
            rss_mb = round(proc.memory_info().rss / (1024 * 1024), 1)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            rss_mb = 0.0

        now = time.strftime("%H:%M:%S")
        entry = {"time": now, "rss_mb": rss_mb}

        with self._lock:
            self._trend.append(entry)
            self._check_leak()

        return entry

    def snapshot(self) -> dict:
        """返回当前趋势和告警的快照。"""
        with self._lock:
            return {
                "memory_trend": list(self._trend),
                "alerts": list(self._alerts),
            }

    # -- internals --

    def _loop(self) -> None:
        while self._running:
            self.collect()
            time.sleep(_SAMPLE_INTERVAL)

    def _check_leak(self) -> None:
        """分析最近 N 个采样点，检测内存持续增长。"""
        if len(self._trend) < _CONSECUTIVE_GROWTH_ALERT:
            return

        recent = list(self._trend)[-_CONSECUTIVE_GROWTH_ALERT:]
        rss_values = [p["rss_mb"] for p in recent]

        # 全部严格递增？
        growing = all(
            rss_values[i] < rss_values[i + 1]
            for i in range(len(rss_values) - 1)
        )
        if not growing:
            return

        current = rss_values[-1]
        baseline = rss_values[0]
        # 超过阈值才关注
        if current < _MEMORY_WARN_THRESHOLD_MB:
            return

        growth_pct = round((current - baseline) / baseline * 100, 1) if baseline > 0 else 0
        level = "warning" if growth_pct < 50 or current < 1024 else "critical"

        self._alerts.append({
            "level": level,
            "message": (
                f"内存持续增长：RSS 从 {baseline}MB 增至 {current}MB "
                f"(+{growth_pct}%)，已连续 {_CONSECUTIVE_GROWTH_ALERT} 分钟"
            ),
            "threshold_mb": _MEMORY_WARN_THRESHOLD_MB,
            "current_mb": current,
            "consecutive_growth": _CONSECUTIVE_GROWTH_ALERT,
            "time": time.strftime("%H:%M:%S"),
        })

        # 只保留最近 10 条告警
        if len(self._alerts) > 10:
            self._alerts.pop(0)


# 全局单例
_memory_collector = _MemoryTrendCollector()
_memory_collector.start()


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

_port_cache: dict[str, dict] = {}
_port_cache_time: float = 0


def _check_services_parallel() -> dict[str, dict]:
    """并行检测所有服务端口，带缓存。"""
    global _port_cache, _port_cache_time
    now = time.monotonic()
    if _port_cache and (now - _port_cache_time) < _PORT_CACHE_TTL:
        return _port_cache

    targets = [
        ("backend", "127.0.0.1", 8000),
        ("nginx",   "127.0.0.1", 8080),
        ("mysql",   "127.0.0.1", 3306),
        ("minio",   "127.0.0.1", 9000),
    ]

    def _check_one(name: str, host: str, port: int) -> tuple[str, dict]:
        try:
            s = socket.create_connection((host, port), timeout=_PORT_TIMEOUT)
            s.close()
            return name, {"status": "up", "port": port, "host": host}
        except (socket.timeout, ConnectionRefusedError, OSError):
            return name, {"status": "down", "port": port, "host": host}

    result: dict[str, dict] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_check_one, name, host, port): name
                   for name, host, port in targets}
        for future in concurrent.futures.as_completed(futures):
            name, info = future.result()
            result[name] = info

    _port_cache = result
    _port_cache_time = now
    return result


def _project_disk_usage_gb() -> float:
    """计算项目相关文件的磁盘占用量（带缓存）。"""
    global _project_disk_cache
    now = time.monotonic()
    if _project_disk_cache["time"] and (now - _project_disk_cache["time"]) < _PROJECT_DISK_CACHE_TTL:
        return _project_disk_cache["gb"]

    total_bytes = 0
    # 项目根目录 + MinIO 数据
    project_root = Path(__file__).resolve().parent.parent.parent.parent  # backend/api/routes/ → 项目根
    dirs_to_scan = [
        project_root,
    ]
    # 如果 MinIO 数据在 G 盘，也纳入
    minio_data = Path("G:/binxian-minio-data")
    if minio_data.exists():
        dirs_to_scan.append(minio_data)

    for base in dirs_to_scan:
        if not base.exists():
            continue
        for dirpath, _dirnames, filenames in os.walk(str(base)):
            # 跳过虚拟环境和 node_modules（太大且不是业务数据）
            if ".venv" in dirpath or "node_modules" in dirpath or "__pycache__" in dirpath:
                continue
            for fn in filenames:
                try:
                    total_bytes += os.path.getsize(os.path.join(dirpath, fn))
                except OSError:
                    pass

    gb = round(total_bytes / (1024 ** 3), 2)
    _project_disk_cache = {"gb": gb, "time": now}
    return gb


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/status")
def system_status(
    _auth=Depends(require_permission("system:view")),
):
    """返回系统实时状态。"""
    # -- 服务状态 --
    services = _check_services_parallel()

    # -- CPU --
    cpu_percent = psutil.cpu_percent(interval=0.2)
    cpu_cores = psutil.cpu_count(logical=True)

    # -- 内存 --
    mem = psutil.virtual_memory()

    # -- 磁盘 --
    try:
        disk = psutil.disk_usage(str(Path.cwd()))
    except Exception:
        disk = psutil.disk_usage("/")

    # -- 本进程 --
    try:
        proc = psutil.Process(os.getpid())
        proc_rss_mb = round(proc.memory_info().rss / (1024 * 1024), 1)
        proc_vms_mb = round(proc.memory_info().vms / (1024 * 1024), 1)
        proc_threads = proc.num_threads()
        # 进程 CPU 占用（归一化到整机百分比）
        proc_cpu_raw = proc.cpu_percent(interval=0.1)
        proc_cpu_norm = round(proc_cpu_raw / (cpu_cores or 1), 1)
        # 进程内存占总内存百分比
        proc_mem_percent = round(proc_rss_mb / (mem.total / (1024 * 1024)) * 100, 1)
    except Exception:
        proc_rss_mb = proc_vms_mb = proc_threads = 0
        proc_cpu_norm = 0.0
        proc_mem_percent = 0.0

    # -- 项目磁盘占用（带缓存）--
    project_disk_gb = _project_disk_usage_gb()

    # -- 内存趋势 + 告警 --
    trend_data = _memory_collector.snapshot()

    # -- 性能统计 --
    perf = _perf_stats.stats()

    return {
        "success": True,
        "data": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "uptime_seconds": round(time.time() - _memory_collector._start_time),
            "services": services,
            "cpu": {
                "percent": round(cpu_percent, 1),
                "cores": cpu_cores or 0,
                "process_percent": proc_cpu_norm,
            },
            "memory": {
                "total_gb": round(mem.total / (1024 ** 3), 1),
                "used_gb": round(mem.used / (1024 ** 3), 1),
                "available_gb": round(mem.available / (1024 ** 3), 1),
                "percent": mem.percent,
                "process_percent": proc_mem_percent,
            },
            "process": {
                "pid": os.getpid(),
                "rss_mb": proc_rss_mb,
                "vms_mb": proc_vms_mb,
                "threads": proc_threads,
            },
            "disk": {
                "total_gb": round(disk.total / (1024 ** 3), 1),
                "used_gb": round(disk.used / (1024 ** 3), 1),
                "percent": disk.percent,
                "project_gb": project_disk_gb,
            },
            "memory_trend": trend_data["memory_trend"],
            "alerts": trend_data["alerts"],
            "perf_stats": perf,
        },
    }
