"""Application entry point — FastAPI app with CORS, routers, and global error handlers.

No business logic here — only registration, configuration, and startup.
"""

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import auth, chat, logs, sessions
from app.routers.admin import bad_cases as admin_bad_cases
from app.routers.admin import config as admin_config
from app.routers.admin import knowledge as admin_knowledge
from app.routers.admin import logs as admin_logs
from app.routers.admin import params as admin_params
from app.routers.admin import prompts as admin_prompts

logger = logging.getLogger(__name__)

app = FastAPI(
    title="可可语伴AI客服系统",
    description="基于RAG架构的智能客服API",
    version="1.0.0",
)

# ── CORS (restrict to known front-end origins) ─────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default
        "http://localhost:3000",  # fallback
    ],
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
