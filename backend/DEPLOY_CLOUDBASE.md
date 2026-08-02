# 可可语伴 · CloudBase 云数据库部署指南

> 适用：腾讯云开发 CloudBase（免费体验版 3000 资源点/月）
> 数据库选择：**云数据库（MySQL）** ✅（已选择）

## 一、后端云函数部署（backend/）

### 1. 环境变量（云函数控制台配置）

| 变量 | 值 | 说明 |
| :--- | :--- | :--- |
| `DASHSCOPE_API_KEY` | `sk-xxx` | DashScope API Key（必填）|
| `WORKSPACE_ID` | `xxx` | 阿里云百炼工作空间 ID（必填）|
| `USE_CLOUD_DB` | `true` | 启用云数据库 |
| `CLOUDBASE_DATABASE_URL` | `mysql+aiomysql://user:pass@host:port/db?charset=utf8mb4` | CloudBase 云数据库连接串（控制台可查）|
| `FAISS_INDEX_PATH` | `/tmp/coco_faiss.index` | FAISS 索引路径（云函数临时目录）|
| `CHUNKS_META_PATH` | `/tmp/coco_chunks.json` | 分块元数据路径 |

> ⚠️ **FAISS 索引路径**：云函数文件系统只读（除 /tmp），建议：
> 1. 首次部署把 `coco_faiss.index` + `coco_chunks.json` 上传到 **云存储**
> 2. 云函数启动时（lifespan）自动从云存储下载到 `/tmp` 再加载
> 3. 或让启动钩子在 `/tmp` 自动重建（`FAISS_INDEX_PATH=/tmp/...` 时触发 rebuild）

### 2. 入口函数

CloudBase 云函数配置：
- **入口**：`app.main:app`（FastAPI ASGI 应用，含 lifespan 启动钩子）
- **运行环境**：Python 3.11+（本项目要求 >=3.13，若 CloudBase 仅支持 3.11 需降级配置或改用 Docker 云托管）
- **依赖安装**：`uv sync` 或 `pip install -r requirements.txt`（pyproject.toml 已含 `aiomysql`）

### 3. 启动时自动初始化（已内置）

`app/main.py` 的 `lifespan` 钩子会在云函数冷启动时自动：

1. `init_db()`：建表 + 默认 admin（`admin@app.com` / `123456`）
   - SQLite → 建 FTS5 虚拟表
   - MySQL → **跳过 FTS5**（检索走 FAISS 向量 + Python 关键词）
2. 检查 FAISS 索引文件，缺失则自动重建

## 二、数据库兼容性说明（已改造）

| 项 | SQLite（本地）| MySQL（CloudBase）|
| :--- | :--- | :--- |
| ORM 建表 | ✅ create_all | ✅ create_all |
| FTS5 全文检索 | ✅ 原生 | ❌ 跳过 → FAISS 向量 + 关键词 fallback |
| 连接池 | 无 | ✅ pool_size=5 + pool_pre_ping |
| utf8mb4 | 天然 | ✅ charset=utf8mb4（URL 参数）|

**代码改动清单**：
- `app/database.py`：`is_sqlite_url()` 判定 + MySQL 连接池参数 + init_db 按 dialect 建 FTS5
- `scripts/build_index.py`：`populate_fts5` 非 SQLite 直接跳过
- `app/config.py`：`use_cloud_db` / `cloudbase_database_url` + `effective_database_url` property
- `app/main.py`：lifespan 启动钩子（init_db + 索引兜底重建）
- `pyproject.toml`：+`aiomysql>=0.2.0`

## 三、前端 EdgeOne Pages 部署

1. 推送到 GitHub（feature/mobile-pwa 分支）
2. EdgeOne Pages 导入仓库，构建：`npm run build`，输出 `dist/`
3. 环境变量：`VITE_API_BASE_URL` = CloudBase 云函数网关地址（如 `https://xxx.service.tcloudbase.com`）
4. 加速区域：**全球可用区（含中国大陆）**

## 四、验证清单

- [ ] 云函数部署后访问 `/api/auth/login` 返回 token
- [ ] 知识库问答正常（FAISS 检索生效）
- [ ] 口语陪练对话正常（DeepSeek API）
- [ ] 管理后台登录 + 知识库/Prompt/Agent 追踪可用
