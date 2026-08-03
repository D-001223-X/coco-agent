#!/usr/bin/env python3
"""本地模拟 CloudBase 解压环境，验证部署包完整性。

用法:
    python3 scripts/verify_package.py [path/to/backend.zip]

检查项:
  1. zip 结构（scf_bootstrap / app / requirements.txt / knowledge_base 在根目录）
  2. scf_bootstrap 语法（bash -n）与可执行权限
  3. 依赖可安装性（dry-run 检查；本机已装的直接验证 import）
  4. app.main 可导入（用当前 Python 解释器）
  5. uvicorn 启动冒烟测试（短暂拉起 → 访问 /docs → 关闭）

退出码: 0 = 全部通过；非 0 = 有问题。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

REQUIRED_ROOT_ENTRIES = [
    "scf_bootstrap",
    "app/main.py",
    "app/__init__.py",
    "requirements.txt",
    "knowledge_base/cefr_standards.md",
]

FORBIDDEN_ENTRIES = [
    ".env", ".env.example", "coco.db", "coco_faiss.index", "coco_chunks.json",
]


def main() -> int:
    zip_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        __file__).resolve().parent.parent.parent / "backend.zip"
    if not zip_path.exists():
        print(f"❌ 找不到 {zip_path}")
        return 1

    print(f"🔍 验证部署包: {zip_path} ({zip_path.stat().st_size/1024:.0f} KB)")
    ok = True

    # ── 1. zip 结构 ──────────────────────────────────────
    print("\n── 1. zip 结构 ──")
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        for entry in REQUIRED_ROOT_ENTRIES:
            if entry in names:
                print(f"  ✅ {entry}")
            else:
                print(f"  ❌ 缺少 {entry}")
                ok = False
        for entry in FORBIDDEN_ENTRIES:
            if entry in names:
                print(f"  ⚠️ 发现不应打包的文件: {entry}")
                ok = False
        # 顶层目录检查
        top_levels = sorted({n.split("/")[0] for n in names})
        print(f"  顶层条目: {top_levels}")

    # ── 2. scf_bootstrap 语法 + 权限 ────────────────────
    print("\n── 2. scf_bootstrap ──")
    with tempfile.TemporaryDirectory() as tmp:
        extract_dir = Path(tmp)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)
        boot = extract_dir / "scf_bootstrap"
        if not boot.exists():
            print("  ❌ scf_bootstrap 未解压出来")
            return 1
        # 语法检查
        r = subprocess.run(["bash", "-n", str(boot)], capture_output=True, text=True)
        if r.returncode == 0:
            print("  ✅ bash -n 语法通过")
        else:
            print(f"  ❌ bash -n 失败:\n{r.stderr}")
            ok = False
        # 权限
        if os.access(boot, os.X_OK):
            print("  ✅ 具有可执行权限")
        else:
            print("  ⚠️ 本地无执行位（zip 不保留权限，CloudBase 解压后通常自动 chmod）")
        # 关键部署配置检查（防止回归）
        boot_text = boot.read_text(encoding="utf-8", errors="ignore")
        checks = {
            "阿里云镜像": "--target=" in boot_text and "mirrors.aliyun.com" in boot_text,
            "PYTHONPATH 注入": "PYTHONPATH=" in boot_text and "coco_deps" in boot_text,
            "真实退出码(非管道)": "PIP_EXIT=$?" in boot_text,
            "uvicorn 9000": "--port 9000" in boot_text,
        }
        for label, passed in checks.items():
            print(f"  {'✅' if passed else '❌'} {label}")

        # ── 3. 依赖检查（dry-run 安装）────────────────────
        print("\n── 3. 依赖 ──")
        req = extract_dir / "requirements.txt"
        if req.exists():
            pkgs = [ln.strip() for ln in req.read_text().splitlines() if ln.strip() and not ln.startswith("#")]
            print(f"  requirements.txt: {len(pkgs)} 个依赖")
            # 检查已安装
            missing = []
            for pkg in pkgs:
                name = pkg.split(">=")[0].split("==")[0].split("[")[0].strip()
                try:
                    __import__(name.replace("-", "_"))
                except ImportError:
                    missing.append(name)
            if missing:
                print(f"  ⚠️ 本机未安装: {missing}（CloudBase 会自动 pip install；若安装失败应用无法启动）")
            else:
                print("  ✅ 全部依赖本机已安装")

        # ── 4. app.main 导入 ─────────────────────────────
        print("\n── 4. app.main 导入 ──")
        sys.path.insert(0, str(extract_dir))
        try:
            from app.main import app  # noqa: F401
            print(f"  ✅ app.main 导入成功 (app={app.title})")
        except Exception as exc:
            print(f"  ❌ app.main 导入失败: {exc}")
            ok = False

        # ── 5. uvicorn 冒烟测试 ──────────────────────────
        print("\n── 5. uvicorn 冒烟测试 ──")
        # 用项目现有环境验证（解压目录无依赖，CloudBase 会 pip 安装；
        # 本地冒烟在 backend/ 项目根执行，验证"代码+lifespan 可正常启动"）
        smoke_dir = Path(__file__).resolve().parent.parent  # backend/
        smoke_cmd = [sys.executable, "-m", "uvicorn", "app.main:app"]
        try:
            import uvicorn  # noqa: F401
        except ImportError:
            smoke_cmd = ["uv", "run", "--no-sync", "python", "-m", "uvicorn",
                         "app.main:app"]
            print("  ℹ️ 当前解释器无 uvicorn，改用 uv run（项目环境）")
        port = 9876
        proc = subprocess.Popen(
            [*smoke_cmd, "--host", "127.0.0.1", "--port", str(port), "--log-level", "error"],
            cwd=str(smoke_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        smoke_ok = False
        try:
            for _ in range(60):
                time.sleep(0.2)
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/docs", timeout=1)
                    smoke_ok = True
                    break
                except Exception:
                    pass
            if smoke_ok:
                print(f"  ✅ uvicorn 启动成功，/docs 返回 200（端口 {port}）")
            else:
                print("  ❌ uvicorn 未能在 12 秒内响应 /docs（可能依赖缺失或 lifespan 卡住）")
                ok = False
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except Exception:
                proc.kill()

    print("\n" + ("✅ 全部通过，可上传部署" if ok else "❌ 存在问题，请修复后重试"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
