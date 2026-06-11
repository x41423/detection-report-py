from __future__ import annotations

from contextlib import asynccontextmanager
from importlib import import_module
import ipaddress
import logging
import os
import socket
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from backend.env import load_project_env  # noqa: E402
from shared.logging_utils import configure_application_logging, configure_access_logger  # noqa: E402

load_project_env()

qwen_hf_home = ROOT_DIR / ".cache" / "huggingface"
os.environ.setdefault("HF_HOME", str(qwen_hf_home))
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(qwen_hf_home / "hub"))
os.environ.setdefault("HF_HUB_CACHE", str(qwen_hf_home / "hub"))
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

configure_application_logging(ROOT_DIR / "logs", include_stream=True)
configure_access_logger(ROOT_DIR / "logs")

from app.db import init_database  # noqa: E402

logger = logging.getLogger(__name__)


def _load_router(module_name: str, router_name: str = "router"):
    try:
        module = import_module(module_name)
        return getattr(module, router_name)
    except Exception:
        logger.exception("Skipping router import for %s", module_name)
        return None


def _local_private_ipv4_addresses() -> list[str]:
    addresses: list[str] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            addr = info[4][0]
            try:
                if ipaddress.ip_address(addr).is_private:
                    addresses.append(addr)
            except ValueError:
                pass
    except OSError:
        pass
    return addresses


def _resolve_cors_origins() -> list[str]:
    origins = ["http://localhost:5173", "https://localhost:5173"]
    for addr in _local_private_ipv4_addresses():
        origins.append(f"http://{addr}:5173")
        origins.append(f"https://{addr}:5173")
    return list(set(origins))


_cors_origins = _resolve_cors_origins()
_allow_credentials = True


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    try:
        from backend.diagnostics.asr_self_check import run_asr_self_check

        report = run_asr_self_check(strict=False)
        if not report["ok"]:
            logger.warning("ASR self-check reported issues: %s", report["warnings"])
        else:
            logger.info("ASR self-check passed")
    except Exception:
        logger.exception("ASR self-check raised unexpectedly")
    yield


app = FastAPI(title="检测工具 API", version="1.0.0", lifespan=lifespan)

from backend.middleware import AuditMiddleware, RequestLogMiddleware  # noqa: E402 - after app init

app.add_middleware(AuditMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=(
        "Content-Disposition",
        "X-Operation-Message",
        "X-Processed-Files",
        "X-Matched-Count",
        "X-Written-Count",
        "X-Updated-Count",
        "X-Generated-Count",
        "X-Skipped-Count",
        "X-Request-ID",
    ),
)

app.add_middleware(RequestLogMiddleware)

for module_name, prefix, tags in [
    ("backend.api.routes.auth", "/api/auth", ["Auth"]),
    ("backend.api.routes.audit", "/api/audit", ["审计"]),
    ("backend.api.routes.config", "/api/config", ["配置"]),
    ("backend.api.routes.daily_intake", "/api/daily-intake", ["每日点货"]),
    ("backend.api.routes.inventory", "/api/inventory", ["库存管理"]),
    ("backend.api.routes.inventory_report", "/api/inventory", ["库存管理"]),
    ("backend.api.routes.inspection_report", "/api/inspection-report", ["检测报告"]),
    ("backend.api.routes.transfer", "/api/transfer", ["数据迁移"]),
    ("backend.api.routes.pesticide", "/api/pesticide", ["农残检测"]),
    ("backend.api.routes.smart_detection", "/api/pesticide", ["农残检测-智能"]),
    ("backend.api.routes.merchant", "/api/merchant", ["商户管理"]),
    ("backend.api.routes.supplier", "/api/supplier", ["供应商管理"]),
    ("backend.api.routes.purchase", "/api/purchase", ["采购管理"]),
    ("backend.api.routes.order", "/api/order", ["订单管理"]),
    ("backend.api.routes.product", "/api/product", ["商品库"]),
    ("backend.api.routes.quotation", "/api/quotation", ["报价单管理"]),
    ("backend.api.routes.settlement", "/api/settlement", ["供应商结算"]),
    ("backend.api.routes.dashboard", "/api/dashboard", ["数据驾驶舱"]),
    ("backend.api.routes.product_analysis", "/api/dashboard", ["数据驾驶舱"]),
    ("backend.api.routes.price_lock", "/api/price-lock", ["营销工具"]),
    ("backend.api.routes.price_markup", "/api/price-markup", ["营销工具"]),
    ("backend.api.routes.agreement_price", "/api/agreement-price", ["营销工具"]),
    ("backend.api.routes.loss_report", "/api/loss-report", ["质量报告"]),
    ("backend.api.routes.order_modification", "/api/order-modification", ["订单"]),
    ("backend.api.routes.future_reserved", "/api/coupon", ["优惠券"]),
    ("backend.api.routes.future_reserved", "/api/delivery", ["配送管理"]),
    ("backend.api.routes.future_reserved", "/api/sorting", ["分拣管理"]),
    ("backend.api.routes.weekly_price", "/api/weekly-price", ["每周报价"]),
    ("backend.funasr_lab.router", "", ["FunASR 实验"]),
    ("backend.api.routes.mimo", "/api", ["MiMo"]),
    ("backend.api.routes.storage", "", ["文件存储"]),
    ("backend.api.routes.system_monitor", "/api/system", ["中控台"]),
    ("backend.api.routes.log_viewer", "/api/system", ["中控台"]),
]:
    router = _load_router(module_name)
    if router is None:
        continue
    if prefix:
        app.include_router(router, prefix=prefix, tags=tags)
    else:
        app.include_router(router, tags=tags)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


UPLOADS_DIR = ROOT_DIR / "data" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


@app.get("/")
async def root():
    return {"message": "检测工具 API", "version": "1.0.0"}
