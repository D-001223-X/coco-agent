"""Knowledge-base admin service: list/upload/delete markdown files, rebuild index."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)

# Knowledge base directory (repo root /knowledge_base)
KB_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "knowledge_base"


class KnowledgeService:
    """Filesystem + index operations for the knowledge base."""

    # ── File listing ────────────────────────────────────────
    def list_files(self) -> list[dict]:
        files: list[dict] = []
        if not KB_DIR.exists():
            return files
        for p in sorted(KB_DIR.glob("*.md")):
            st = p.stat()
            files.append({
                "filename": p.name,
                "size": st.st_size,
                "modified_at": datetime.fromtimestamp(
                    st.st_mtime, tz=timezone.utc
                ).isoformat(),
            })
        return files

    # ── Upload ──────────────────────────────────────────────
    async def upload_file(self, filename: str, content: bytes) -> dict:
        KB_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = Path(filename).name  # strip any path traversal
        if not safe_name.endswith(".md"):
            raise ValueError("只支持 .md 文件")
        target = KB_DIR / safe_name
        target.write_bytes(content)
        logger.info("Knowledge file uploaded: %s", safe_name)
        return {"filename": safe_name, "size": len(content)}

    # ── Delete ──────────────────────────────────────────────
    async def delete_file(self, filename: str) -> dict:
        safe_name = Path(filename).name
        target = KB_DIR / safe_name
        if not target.exists():
            raise FileNotFoundError(f"文件不存在: {safe_name}")
        target.unlink()
        logger.info("Knowledge file deleted: %s", safe_name)
        return {"deleted": safe_name}

    # ── Index status ────────────────────────────────────────
    def get_status(self) -> dict:
        s = get_settings()
        faiss_path = Path(s.faiss_index_path).resolve()
        chunks_path = Path(s.chunks_meta_path).resolve()

        chunk_count = 0
        if chunks_path.exists():
            try:
                data = json.loads(chunks_path.read_text(encoding="utf-8"))
                chunk_count = len(data)
            except Exception:
                chunk_count = 0

        mtime = None
        if faiss_path.exists():
            mtime = datetime.fromtimestamp(
                faiss_path.stat().st_mtime, tz=timezone.utc
            ).isoformat()

        return {
            "chunk_count": chunk_count,
            "last_build_at": mtime,
            "index_path": str(faiss_path),
        }

    # ── Chunk details (from coco_chunks.json) ─────────────
    def get_chunks(self) -> list[dict]:
        """Return all chunks with previews (source: coco_chunks.json)."""
        s = get_settings()
        chunks_path = Path(s.chunks_meta_path).resolve()
        if not chunks_path.exists():
            return []
        try:
            data = json.loads(chunks_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        return [
            {
                "chunk_id": c.get("chunk_id", ""),
                "section": c.get("section", ""),
                "content_preview": c.get("content", "")[:100],
                "content_full": c.get("content", ""),
            }
            for c in data
        ]

    # ── Rebuild index ───────────────────────────────────────
    async def rebuild_index(self) -> dict:
        """Run build_index.main() in-process (async), returns summary."""
        try:
            from scripts.build_index import main as build_main

            await build_main()
            status = self.get_status()
            return {"ok": True, "message": "索引重建完成", **status}
        except Exception as exc:
            logger.error("Rebuild index failed: %s", exc, exc_info=True)
            return {"ok": False, "message": f"索引重建失败: {exc}"}
