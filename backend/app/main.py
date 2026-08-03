"""Application entry point — FastAPI app with CORS, routers, and global error handlers.

No business logic here — only registration, configuration, and startup.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import auth, chat, logs, sessions
from app.routers.admin import bad_cases as admin_bad_cases
from app.routers.admin import config as admin_config
from app.routers.admin import knowledge as admin_knowledge
from app.routers.admin import logs as admin_logs
from app.routers.admin import params as admin_params
from app.routers.admin import prompts as admin_prompts
from app.routers.admin import agent_traces as admin_agent_traces
from app.routers.practice import assessment as practice_assessment
from app.routers.practice import plan as practice_plan
from app.routers.practice import progress as practice_progress
from app.routers.practice import session as practice_session

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动钩子：立即 yield（让 uvicorn 立刻可接收请求），重操作后台异步执行。

    为什么这样设计：
    - CloudBase Custom Runtime 网关只检测 9000 端口能否响应；
      若 lifespan 卡 60s 才 yield，网关超时返回 446
    - 之前 init_db 连 MySQL 阻塞（VPC/网络/连接串），卡 60s+，导致 446
    - 现在：lifespan 立即 yield，DB/索引后台异步；
      首请求若未就绪返回 503 + 自动重试，10s 后可用

    - init_db：建表 + 默认 admin（SQLite 下含 FTS5，MySQL 自动跳过）
    - FAISS 索引缺失时自动重建
    """
    s = get_settings()
    app.state.ready = False
    app.state.init_error: str | None = None

    async def _bg_init() -> None:
        try:
            from app.database import init_db
            await init_db()
            logger.info("[bg] init_db OK")
        except Exception as exc:  # noqa: BLE001
            logger.warning("[bg] init_db failed: %s", exc)
            app.state.init_error = f"db: {exc}"

        try:
            # 题库种子（assessment_questions 表）：跨方言，幂等
            from app.services.assessment_seed import seed_assessment_data
            n = await seed_assessment_data()
            logger.info("[bg] assessment seed OK (%d inserted)", n)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[bg] assessment seed failed: %s", exc)
            app.state.init_error = (app.state.init_error or "") + f" seed: {exc}"

        try:
            # 用 effective 路径（serverless 下自动 /tmp，可写）
            faiss_path = Path(s.effective_faiss_index_path)
            chunks_path = Path(s.effective_chunks_meta_path)
            # 确保父目录存在（/tmp 可写）
            for p in (faiss_path, chunks_path):
                p.parent.mkdir(parents=True, exist_ok=True)
            if not faiss_path.exists() or not chunks_path.exists():
                logger.info("[bg] Knowledge index missing → rebuilding to %s ...",
                            faiss_path.parent)
                from scripts.build_index import main as build_main
                await build_main()
            logger.info("[bg] Index OK (%s, %s)", faiss_path, chunks_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[bg] Index build failed: %s", exc)
            app.state.init_error = (app.state.init_error or "") + f" idx: {exc}"

        app.state.ready = True
        logger.info("[bg] Initialization complete ✅")

    # 后台异步执行，立即返回（不阻塞 uvicorn 启动）
    asyncio.create_task(_bg_init())

    yield


app = FastAPI(
    title="可可语伴AI客服系统",
    description="基于RAG架构的智能客服API",
    version="1.0.0",
    lifespan=lifespan,
)


# ── 健康检查 + 启动状态端点 ─────────────────────────────
@app.get("/")
async def root():
    """CloudBase 网关探活用（必须 200，避免 67s 超时 → 446）。"""
    if not getattr(app.state, "ready", False):
        return JSONResponse(
            status_code=503,
            content={
                "code": 503,
                "msg": "Initializing, please retry in 5-10s",
                "ready": False,
                "error": getattr(app.state, "init_error", None),
            },
        )
    return {"code": 0, "msg": "coco-api ready ✅", "ready": True}


@app.get("/_health")
async def health():
    """轻量健康检查（不依赖 DB/索引）。"""
    return {"status": "ok"}

# ── CORS (restrict to known front-end origins) ─────────────
# 注意：allow_origins 只支持精确匹配或 "*"，不支持 "*.domain" 子域通配符！
# EdgeOne Pages 域名通过 allow_origin_regex 匹配（含 .app / .cool 等后缀）。
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default
        "http://localhost:5174",  # dev worktree
        "http://localhost:5175",  # mobile-pwa dev
        "http://localhost:3000",  # fallback
    ],
    allow_origin_regex=(
        r"^https://.*\.edgeone\.(app|cool)$"   # EdgeOne Pages 公网（任意子域）
        r"|^https://.*\.tcloudbase\.com$"      # CloudBase 网关
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Router registration ───────────────────────────────────
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(logs.router)
app.include_router(sessions.router)
app.include_router(admin_knowledge.router)
app.include_router(admin_prompts.router)
app.include_router(admin_params.router)
app.include_router(admin_logs.router)
app.include_router(admin_bad_cases.router)
app.include_router(admin_config.router)
app.include_router(admin_agent_traces.router)
app.include_router(practice_assessment.router)
app.include_router(practice_plan.router)
app.include_router(practice_session.router)
app.include_router(practice_progress.router)


# ── Global exception handlers ─────────────────────────────
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Return HTTP exceptions in a unified format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "data": None,
            "msg": exc.detail,
            "detail": exc.detail,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Catch-all: log the error, return a sanitised 500 response."""
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "data": None,
            "msg": "Internal Server Error",
            "detail": "Internal Server Error",
        },
    )


# ── Public endpoints ─────────────────────────────────────
@app.get("/")
async def root():
    return {"message": "可可语伴AI客服系统已启动", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
