"""Application configuration loaded from environment / .env file."""

import os
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed settings with mandatory API credential validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./coco.db"
    # CloudBase 数据库切换（T-mobile 部署）：USE_CLOUD_DB=true 时优先用云端连接串
    # CloudBase 云数据库 URL 格式示例：
    #   mysql+aiomysql://user:pass@host:port/dbname?charset=utf8mb4
    use_cloud_db: bool = False
    cloudbase_database_url: str | None = None

    # ── JWT ─────────────────────────────────────────────────
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # ── API Keys (required) ─────────────────────────────────
    dashscope_api_key: str = ""
    workspace_id: str = ""

    # ── Retrieval ───────────────────────────────────────────
    top_k: int = 5
    score_threshold: float = 0.3

    # ── FAISS / chunks file paths ───────────────────────────
    # 默认写当前目录（本地 SQLite 场景）。CloudBase 容器 /var/user 只读，
    # 生产部署应设 FAISS_INDEX_PATH=/tmp/coco_faiss.index、CHUNKS_META_PATH=/tmp/coco_chunks.json
    # （lifespan 会自动检测并写 /tmp）。
    faiss_index_path: str = "./coco_faiss.index"
    chunks_meta_path: str = "./coco_chunks.json"

    # ── Runtime detection ────────────────────────────────────
    @property
    def is_serverless(self) -> bool:
        """检测是否运行在 CloudBase/SCF 容器（/var/user 存在即视为 serverless）。"""
        return Path("/var/user").exists() or Path("/tmp").exists() and os.environ.get("SCF_NAMESPACE") is not None

    @property
    def effective_faiss_index_path(self) -> str:
        """serverless 环境强制用 /tmp（可写），本地用配置值。"""
        if self.is_serverless and not self.faiss_index_path.startswith("/tmp"):
            return "/tmp/coco_faiss.index"
        return self.faiss_index_path

    @property
    def effective_chunks_meta_path(self) -> str:
        if self.is_serverless and not self.chunks_meta_path.startswith("/tmp"):
            return "/tmp/coco_chunks.json"
        return self.chunks_meta_path

    # ── Model identifiers ───────────────────────────────────
    deepseek_model: str = "deepseek-v3"
    embedding_model: str = "text-embedding-v3"
    rerank_model: str = "qwen3-rerank"

    # ── Validators ──────────────────────────────────────────
    @model_validator(mode="after")
    def _check_required_keys(self) -> "Settings":
        missing: list[str] = []
        if not self.dashscope_api_key:
            missing.append("DASHSCOPE_API_KEY")
        if not self.workspace_id:
            missing.append("WORKSPACE_ID")
        if missing:
            raise ValueError(
                "Missing required environment variable(s): "
                + ", ".join(missing)
            )
        return self

    # ── Dynamic URL properties ──────────────────────────────
    @property
    def effective_database_url(self) -> str:
        """生产部署时切到 CloudBase；本地默认 SQLite。"""
        if self.use_cloud_db and self.cloudbase_database_url:
            return self.cloudbase_database_url
        return self.database_url

    @property
    def deepseek_base_url(self) -> str:
        return (
            f"https://{self.workspace_id}.cn-beijing.maas.aliyuncs.com"
            "/compatible-mode/v1"
        )

    @property
    def embedding_base_url(self) -> str:
        return (
            f"https://{self.workspace_id}.cn-beijing.maas.aliyuncs.com"
            "/compatible-mode/v1"
        )

    @property
    def rerank_base_url(self) -> str:
        return (
            f"https://{self.workspace_id}.cn-beijing.maas.aliyuncs.com"
            "/compatible-api/v1"
        )


# Defer instantiation so that test fixtures can monkey-patch env vars
# before import.  A factory is provided instead of a module-level singleton.
def get_settings() -> Settings:
    """Return a fresh Settings instance (re-reads .env each call)."""
    return Settings()


# Module-level singleton for normal application use.
settings = get_settings()
