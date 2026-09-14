# CLAUDE.md

本文档为 Claude Code (claude.ai/code) 在此仓库中工作时提供指引。

## 项目概述

智数归因平台 (Starry Aurora) — 企业级 NL2SQL 自然语言查数与电商全链路归因一体化系统。四层架构：

```
用户交互层 (User Interaction)   →  Frontend React + Backend API
业务编排层 (Orchestration)      →  Insight Agent (大脑/总指挥)
能力支撑层 (Capability)         →  NL2SQL DataAgent + Attribution Models
数据与基础设施层                →  MySQL/Redis/Qdrant/Elasticsearch
```

## 常用命令

```bash
# 启动基础设施 (Docker)
make docker-up                  # docker-compose -f docker-compose.dev.yml up -d

# 启动后端
cd backend && pip install -r requirements.txt && uvicorn app.asgi:app --reload --host 0.0.0.0 --port 8000

# 启动前端
cd frontend && npm install && npm run dev

# 数据库迁移
cd backend && alembic upgrade head
make migrate-new msg="migration_description"  # 自动生成新迁移文件

# 代码格式化 + 检查
cd backend && black . && isort . && flake8 .
cd frontend && npm run lint

# 测试
cd backend && pytest -v
```

### Windows 注意事项

- **进程管理**：Git Bash `nohup` 不能可靠管理 Python 子进程（产生僵尸进程）。强制终止用 PowerShell: `Get-NetTCPConnection -LocalPort 8000 | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force }`
- **环境变量**：通过 PowerShell 设置 `$env:VAR=val; python ...` 而非 `VAR=val python ...`
- **路径格式**：在 Git Bash 中用 `/d/...` 而非 `D:\...`，或用 `cd /d/Vibe_Coding/...`

## 后端架构

### 核心目录 (`backend/app/`)

| 目录 | 职责 |
|---|---|
| `core/` | 配置(pydantic-settings)、异步DB引擎、Redis/Qdrant/ES客户端、JWT、Celery、异常处理 |
| `agents/` | **Agent 核心** — 智能体体系 |
| `api/v1/` | FastAPI 路由处理器 — queries, attribution, conversations, auth, datasources, schemas |
| `services/` | 业务逻辑层 |
| `repositories/` | 数据访问层 (SQLAlchemy 异步 CRUD) |
| `models/` | ORM 模型 — User, DataSource, SchemaMeta, Conversation, ConversationMessage |
| `schemas/` | Pydantic 请求/响应模型 |
| `search/` | 向量检索(Qdrant)、关键词检索(ES BM25)、混合检索(RRF融合)、索引同步 |
| `nlp/` | 中文 NLP — Jieba分词、实体抽取、HyDE语义对齐、因子剪枝 |
| `middleware/` | CORS、结构化日志、限流、SSE (EventSourceResponse) |
| `tasks/` | Celery 异步任务 |
| `utils/` | SQL工具、日期工具、缓存、结构化日志 |

### Agent 体系 — 三层架构

```
Insight Agent (insight_agent/)
  ├── agent.py           — 编排入口, validate → resolve_intent → check_skill → prepare_context → delegate
  │                       _resolve_intent(): 规则匹配（ROI/归因→Attribution；
  │                       销售/金额/环比/同比等业务关键词→NL2SQL；兜底UNKNOWN也走NL2SQL）
  ├── skill_manager.py   — Skill 约束方法论校验 (YAML rules)
  ├── workspace_manager.py — 工作区 CRUD + ORM 模型
  ├── attachment_manager.py — 附件管理 (ORM 模型 + 存储存根)
  └── message_bus.py     — 消息持久化 (Redis list) + 事件发布 (Redis Pub/Sub) + Celery 分发

NL2SQL Agent (nl2sql_agent/)
  ├── agent.py           — DataAgent 入口 run() / stream_run()
  ├── graph.py           — LangGraph StateGraph (6 节点 + 修复循环)
  ├── state.py           — AgentState TypedDict
  ├── parser.py          — 独立的 NL2SQL 意图解析（时间表达式、指标/维度提取）
  ├── nodes/             — intent_parser → schema_retriever → sql_generator → sql_validator → sql_executor → result_formatter
  ├── tools/             — schema_search, sql_tool, data_profile (LangChain 工具)
  └── prompts/           — YAML 提示模板 (intent, sql_generation, sql_fix, explanation)

归因模型 (attribution_models/)
  ├── base.py            — BaseAttributionModel 抽象基类 (async calculate(), validate_params())
  ├── registry.py        — @registry.register("name") 装饰器注册表
  ├── first_touch.py, last_touch.py, linear.py, time_decay.py, position_decay.py, data_driven.py, custom.py
  └── __init__.py        — 桶导入 (import 触发所有 @register 装饰器)

共享模块 (shared/)
  ├── llm_factory.py     — LiteLLM 统一封装 (generate/stream)
  ├── embedding.py       — 嵌入服务 (文本 → 向量)
  ├── retriever.py       — 三路召回: Qdrant 向量 + ES BM25 + HyDE → RRF 融合
  ├── reranker.py        — 基于 LLM 的候选重排序
  └── memory.py          — 对话记忆 (消息列表)
```

### 核心流程: NL2SQL 查询

```
用户输入 → Insight Agent (意图解析 + Skill 校验)
  → DataAgent.run()
    → LangGraph StateGraph:
      intent_parser → schema_retriever (混合检索 + 重排序 + 剪枝)
        → sql_generator (CoT 提示) → sql_validator (语法 + 权限 + EXPLAIN)
          → [失败则修复循环，最多 3 次 → sql_generator]
          → sql_executor (只读、超时、行数限制) → result_formatter (解释 + 图表类型)
```

### 核心流程: 归因分析

```
用户配置 → Insight Agent
  → 从 MySQL 数据源加载触点数据 + 转化数据
  → registry.get("模型名").calculate(touchpoints_df, conversions_df)
  → 返回: 各渠道贡献度、洞察分析
```

### 数据模型 (`models/`)

- **User**: username, email, hashed_password, role (admin/analyst/viewer), is_active
- **DataSource**: name, type (mysql/postgresql/clickhouse), host/port/db/user/password, user_id 外键
- **SchemaMeta**: datasource_id 外键, table_name, column_name, data_type, description, embedding
- **Conversation**: user_id 外键, title, workspace_type (query/attribution), status
- **ConversationMessage**: conversation_id 外键, role (user/assistant/system), content (LONGTEXT), message_type

### 混合检索架构

- **Qdrant**: `asyncio.to_thread()` 包裹同步客户端，集合 `schema_fields`，向量维度 1536
- **Elasticsearch**: 异步客户端，索引 `schema_fields`，IK 中文分词器
- **混合策略**: RRF (Reciprocal Rank Fusion, k=60)，三路召回 (向量 + BM25 + HyDE)

### 关键设计决策

- **SSE 而非 WebSocket**: NL2SQL 是单向流，更轻量、CDN 友好
- **`@registry.register()` 装饰器**: 归因模型的零侵入插件式扩展
- **RRF 融合而非加权**: Qdrant(余弦)和 ES(BM25)分数分布不可比
- **LangGraph StateGraph**: SQL 修复循环的条件分支
- **`asyncio.to_thread()`**: Qdrant 同步客户端不阻塞事件循环

## 前端架构

### 目录结构 (`frontend/src/`)

| 目录 | 职责 |
|---|---|
| `pages/Query/` | NL2SQL 聊天界面 — ChatPanel(SSE流式)、SqlPreview、ResultTable、ResultChart、SchemaExplorer、QueryHistory |
| `pages/Attribution/` | 归因分析 — ModelSelector、ParamConfig、AttributionResult、TouchpointFlow(桑基图)、ModelComparison |
| `pages/DataSource/` | 数据源连接管理 |
| `pages/SchemaManager/` | 表/字段元数据浏览器 |
| `components/charts/` | ECharts 封装 — BarChart、LineChart、PieChart、SankeyChart |
| `components/common/` | 通用组件 — Loading、EmptyState、ErrorBoundary、DataTable |
| `stores/` | Zustand — authStore、queryStore、conversationStore、attributionStore |
| `hooks/` | useSSE(fetch 流式 SSE 解析)、useQuery、useAttribution、useConversation |
| `api/` | Axios 客户端 (自动 JWT、401 刷新) + 类型化 API 函数 |

### 路由 (`router/index.tsx`)

- `/login` — 公开路由
- `/dashboard`, `/query`, `/attribution`, `/datasources`, `/schemas`, `/settings` — AuthGuard + AppLayout
- 所有页面懒加载 (Suspense)

### 关键集成点

- **SSE 流式**: `useSSE` hook 使用原生 `fetch` + `ReadableStream`，解析 `event:`/`data:` 行
- **认证**: Axios 拦截器自动附加 JWT，401 时自动刷新
- **会话管理**: Zustand conversationStore 通过 API 实现异步 CRUD

## 基础设施 (Docker)

- `docker-compose.dev.yml`: MySQL 8.0 + Redis 7 + Qdrant + Elasticsearch 8.15
- 服务暴露标准端口 (3306, 6379, 6333/6334, 9200)
- 开发环境服务无认证 (ES 安全已禁用)

## .env 配置

复制 `.env.example` → `.env`。关键配置项：
- `DATABASE_URL`: `mysql+aiomysql://user:pass@host:3306/db`
- `LLM_*`: 供应商 (openai/dashscope)、模型密钥、API 地址
- `EMBEDDING_MODEL`: 如 `text-embedding-3-small`，默认维度 1536