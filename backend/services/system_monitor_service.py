"""系统监控服务：CPU / 内存 / 磁盘 / 进程 / 服务状态 / 内存泄漏检测。

每个 ``collect()`` 采样一次，保留最近 60 个内存点用于趋势和告警。
"""

from __future__ import annotations

import os
import socket
import threading
import time
from datetime import datetime, timezone
from typing import Any

import psutil

# ---- 默认阈值 ----
DEFAULT_WARNING_THRESHOLD_MB = 500
DEFAULT_CONSECUTIVE_GROWTH_ALERT = 5
DEFAULT_TREND_WINDOW = 60

# 服务端口映射（只检测，不启动）
_SERVICE_PORTS: dict[str, int] = {
    "backend": 8000,
    "nginx": 8080,
    "mysql": 3306,
    "minio": 9000,
}


class SystemMonitorService:
    """采集系统运行指标 + 内存趋势监测。"""

    def __init__(
        self,
        *,
        warning_threshold_mb: int = DEFAULT_WARNING_THRESHOLD_MB,
        consecutive_growth_alert: int = DEFAULT_CONSECUTIVE_GROWTH_ALERT,
        trend_window: int = DEFAULT_TREND_WINDOW,
    ) -> None:
        self.warning_threshold_mb = warning_threshold_mb
        self.consecutive_growth_alert = consecutive_growth_alert
        self.trend_window = trend_window
        self._lock = threading.Lock()
        self._trend: list[dict] = []
        self._start_time = time.time()
        self._pid = os.getpid()

    # ----------------------------------------------------------------
    # 公共接口
    # ----------------------------------------------------------------

    def collect(self) -> dict:
        """采集一次完整指标，追加趋势，返回字典。"""
        now_dt = datetime.now(timezone.utc)
        cpu = self._collect_cpu()
        memory = self._collect_memory()
        process = self._collect_process()
        disk = self._collect_disk()

        # 追加内存趋势
        self._append_trend(now_dt, process["rss_mb"])

        # 判定告警
        alerts = self._check_alerts()

        return {
            "timestamp": now_dt.isoformat(),
            "uptime_seconds": round(time.time() - self._start_time, 1),
            "services": self._collect_services(),
            "cpu": cpu,
            "memory": memory,
            "process": process,
            "disk": disk,
            "memory_trend": list(self._trend),
            "alerts": alerts,
        }

    # ----------------------------------------------------------------
    # 各指标采集
    # ----------------------------------------------------------------

    @staticmethod
    def _collect_cpu() -> dict:
        return {
            "percent": psutil.cpu_percent(interval=0.1),
            "cores": psutil.cpu_count(logical=True) or 1,
        }

    @staticmethod
    def _collect_memory() -> dict:
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": round(mem.percent, 1),
        }

    def _collect_process(self) -> dict:
        try:
            proc = psutil.Process(self._pid)
            mi = proc.memory_info()
            return {
                "pid": self._pid,
                "rss_mb": round(mi.rss / (1024**2), 1),
                "vms_mb": round(mi.vms / (1024**2), 1),
                "threads": proc.num_threads() or 0,
            }
        except psutil.NoSuchProcess:
            return {
                "pid": self._pid,
                "rss_mb": 0,
                "vms_mb": 0,
                "threads": 0,
            }

    @staticmethod
    def _collect_disk() -> dict:
        """采集项目所在盘的使用情况。"""
        # 使用当前工作目录所在的盘
        cwd = os.getcwd()
        usage = psutil.disk_usage(cwd)
        return {
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "percent": round(usage.percent, 1),
            "path": cwd[:3],  # 盘符或根路径
        }

    @staticmethod
    def _collect_services() -> dict[str, dict]:
        """检查各个服务的端口是否在监听。"""
        result: dict[str, dict] = {}
        for name, port in _SERVICE_PORTS.items():
            status = _check_port(port)
            result[name] = {
                "status": "up" if status else "down",
                "port": port,
            }
        return result

    # ----------------------------------------------------------------
    # 内存趋势
    # ----------------------------------------------------------------

    def _append_trend(self, now_dt: datetime, rss_mb: float) -> None:
        with self._lock:
            self._trend.append({
                "time": now_dt.strftime("%H:%M:%S"),
                "rss_mb": rss_mb,
            })
            # 保持窗口大小
            while len(self._trend) > self.trend_window:
                self._trend.pop(0)

    # ----------------------------------------------------------------
    # 告警判定
    # ----------------------------------------------------------------

    def _check_alerts(self) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        with self._lock:
            if len(self._trend) < self.consecutive_growth_alert:
                return alerts

            recent = self._trend[-self.consecutive_growth_alert - 1:]
            rss_values = [p["rss_mb"] for p in recent]
            current_rss = rss_values[-1]

            # 连续增长？
            consecutive_growth = 0
            for i in range(1, len(rss_values)):
                if rss_values[i] > rss_values[i - 1]:
                    consecutive_growth += 1
                else:
                    consecutive_growth = 0

            if current_rss < self.warning_threshold_mb:
                return alerts

            if consecutive_growth >= self.consecutive_growth_alert:
                first_rss = rss_values[0]
                growth_pct = (
                    round((current_rss - first_rss) / first_rss * 100, 1)
                    if first_rss > 0
                    else 0
                )
                # 严重程度：连续 10+ 次 → critical
                level = "critical" if consecutive_growth >= 10 else "warning"
                alerts.append({
                    "level": level,
                    "message": (
                        f"内存持续增长：RSS 从 {first_rss:.0f}MB 增至 "
                        f"{current_rss:.0f}MB（+{growth_pct}%），"
                        f"已连续 {consecutive_growth} 分钟"
                    ),
                    "threshold_mb": self.warning_threshold_mb,
                    "current_mb": current_rss,
                    "first_mb": first_rss,
                    "consecutive_growth": consecutive_growth,
                    "growth_pct": growth_pct,
                })

        return alerts


# -----------------------------------------------------------------
# 端口检测工具
# -----------------------------------------------------------------

def _check_port(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    """检测端口是否在监听。"""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except (OSError, ConnectionRefusedError, TimeoutError):
        return False
