# 智数归因平台 (Starry Aurora)

企业级自然语言查数与电商全链路归因一体化系统。基于 DataAgent、AttributionAgent 架构，实现 NL2SQL 自助取数和多模型智能归因分析。

## 技术栈

- **后端**: Python 3.12, FastAPI, AsyncIO, LangChain, LangGraph, LiteLLM
- **存储**: MySQL, Redis, Qdrant, Elasticsearch
- **前端**: React 18, TypeScript, Vite, Ant Design 5, ECharts
- **基础设施**: Docker Compose, Celery, Nginx

## 快速启动

```bash
# 1. 启动基础设施
docker-compose -f docker-compose.dev.yml up -d

# 2. 启动后端
cd backend && pip install -r requirements.txt && uvicorn app.asgi:app --reload

# 3. 启动前端
cd frontend && npm install && npm run dev
```

## 项目结构

```
starry-aurora/
├── backend/              # FastAPI 后端
├── frontend/             # React 前端
├── docker/               # Docker 容器配置
├── mcp/                  # MCP 集成
└── docs/                 # 文档
```