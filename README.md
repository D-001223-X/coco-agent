# 可可语伴 AI 智能客服系统

> 一个基于 RAG（检索增强生成）架构的 AI 智能客服助手，为 AI 外语学习产品「可可语伴（CocoMate）」提供智能问答服务。

![screenshots/screenshot-login.png](screenshots/screenshot-login.png)
![screenshots/screenshot-chat.png](screenshots/screenshot-chat.png)
![screenshots/screenshot-sessions.png](screenshots/screenshot-sessions.png)
![screenshots/screenshot-logs.png](screenshots/screenshot-logs.png)
![screenshots/screenshot-trace.png](screenshots/screenshot-trace.png)
![screenshots/screenshot-new-session.png](screenshots/screenshot-new-session.png)

## 技术栈

- **后端**: Python 3.13 + FastAPI + SQLAlchemy (async) + aiosqlite
- **前端**: React 18 + TypeScript + Vite + TailwindCSS + Zustand + Axios
- **AI**: DeepSeek-V3 + FAISS + FTS5 + RRF + qwen3-rerank
- **部署**: Railway (后端) + Vercel (前端)

## 功能特性

- 智能意图识别（SUPPORT / FEEDBACK / CHAT）
- RAG 混合检索（FAISS 语义检索 + FTS5 BM25 + RRF 融合 + qwen3-rerank 重排）
- JWT 鉴权与会话管理
- 多轮对话与指代消解
- 全链路日志追踪
