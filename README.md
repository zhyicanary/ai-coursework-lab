# AgentForge — AI Agent 应用工坊 | [English](README_EN.md)

[![Python](https://img.shields.io/badge/Python-3.14-blue)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2-orange)](https://www.langchain.com/langgraph)
[![MCP](https://img.shields.io/badge/MCP-1.28-purple)](https://modelcontextprotocol.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.137-green)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![uv](https://img.shields.io/badge/uv-package%20manager-black)](https://docs.astral.sh/uv/)

> 同一个技术底座（大模型 + LangGraph + MCP），两种 AI Agent 应用范式。

---

## 为什么做这个合集

2026 年，AI Agent 正在从"调用 API"走向"自主决策 + 团队协作"。本合集通过两个完整项目，分别探索两条路径：

| | 范式一：深度推理 | 范式二：协同编排 |
|---|---|---|
| **项目** | [KnowSeeker](knowseeker/) | [TripMind](tripmind/) |
| **一句话** | 一个 Agent，多步思考 | 六个 Agent，分工协作 |
| **Agent 数量** | 1 | 6 |
| **核心机制** | Agentic RAG + 混合检索 + 重排序 | Multi-Agent DAG 调度 |
| **适合场景** | 知识问答、文档分析 | 复杂任务分解、多角色协作 |
| **前端（方案A）** | Streamlit | Gradio |
| **前端（方案B）** | React + shadcn/ui | React + shadcn/ui + SSE 流式 |

---

## 双架构说明

本项目支持两套前端方案，共享同一套 Python 后端逻辑：

| | 方案A（全栈 Python） | 方案B（前后端分离，当前主推） |
|---|---|---|
| **前端** | Streamlit / Gradio | Next.js 14 + React 18 + shadcn/ui + Tailwind CSS |
| **后端** | Python 直接调用 `common/` 层 | FastAPI REST API + SSE 流式推送 |
| **端口** | 8501 (Streamlit) / 7861 (Gradio) | 3000 (前端) + 8000 (后端) + 8765 (MCP) |
| **特点** | 快速原型，代码简洁 | 组件化 UI，实时 Agent 状态面板，响应式布局 |

---

## 快速开始

```bash
git clone <this-repo>
cd agent-forge

# 安装依赖
uv sync

# 配置 API Key
cp .env.example .env
# 编辑 .env 填入 DeepSeek API Key 或 Ollama 地址
```

### 方案A — 全栈 Python（快速体验）

```bash
# 启动项目一：知识助手（Streamlit）
uv run streamlit run knowseeker/app.py

# 启动项目二：旅游助手（Gradio，支持热加载）
uv run python -m gradio tripmind/app.py --watch-dirs .

# 或使用 Makefile
make knowseeker
make tripmind
```

### 方案B — 前后端分离（完整体验）

```bash
# 1. 启动后端 API（自动管理 MCP Server 生命周期）
uv run uvicorn backend.server:app --host 0.0.0.0 --port 8000

# 2. 启动前端界面
cd frontend
npm install   # 首次需要安装依赖
npm run dev   # 访问 http://localhost:3000
```

> 方案B 的后端会自动启动 MCP Server 子进程（端口 8765），无需手动管理。

---

## 项目一：KnowSeeker — 基于 MCP 的 Agentic RAG 知识助手

[![查看详情](https://img.shields.io/badge/-查看文档-blue)](knowseeker/README.md)

用户上传文档后，Agent **自主判断**"搜一次够不够？要不要换个角度搜？"——而非传统 RAG 的一次性检索。检索阶段采用 **BM25 稀疏检索 + ChromaDB 稠密向量检索**的混合策略，经 RRF 融合后再由 **Cross-Encoder 重排序**精排，显著提升召回质量。

**核心技术：** LangGraph 状态机编排 → analyze → retrieve（混合检索 + RRF + 重排序）→ evaluate → reformulate → generate

**课程关键词覆盖：** 大模型 · AI Agent · LangChain · LangGraph · MCP · RAG · 混合检索 · 重排序

```bash
# 方案A
uv run streamlit run knowseeker/app.py

# 方案B（通过 React 前端访问 /knowseeker 页面）
uv run uvicorn backend.server:app --port 8000
```

**LangGraph 状态流转：**

```
analyze_question → retrieve → evaluate_results
     ↑                          │
     └──── reformulate ←────────┘  (need_more_search=True)
                         │
                         └→ generate_answer → END
```

**混合检索 + 重排序流程：**

```
用户问题
  ├── BM25 Okapi 稀疏检索 (bm25_store.py)  → Top-K 候选
  ├── ChromaDB 稠密向量检索 (vector_store.py) → Top-K 候选
  └── RRF 融合 (rag_chain.py)  → 合并去重
         └── Cross-Encoder 重排序 (reranker.py) → 精排 Top-K
```

---

## 项目二：TripMind — 基于多智能体协同的旅游规划系统

[![查看详情](https://img.shields.io/badge/-查看文档-blue)](tripmind/README.md)

用户输入目的地和预算，6 个 AI Agent 像团队一样协同——调度者拆解任务、交通 Agent 查航班、住宿 Agent 比价格、行程 Agent 排路线、预算 Agent 控成本、汇总 Agent 出方案。

**核心技术：** LangGraph DAG 依赖调度 → 无依赖并行执行 → 有依赖顺序执行 → 汇总交付

**课程关键词覆盖：** 大模型 · AI Agent · LangChain · LangGraph · MCP · RAG · 多智能体协同

```bash
# 方案A
uv run python -m gradio tripmind/app.py --watch-dirs .

# 方案B（通过 React 前端访问 /tripmind 页面，支持 SSE 流式进度）
uv run uvicorn backend.server:app --port 8000
```

**Agent 执行流程：**

```
START → orchestrator → parallel (asyncio.gather)
                        ├── WeatherAgent    (无依赖)
                        ├── TransportAgent   (无依赖)
                        └── HotelAgent       (无依赖)
                      → planning (顺序)
                        ├── ItineraryAgent  (依赖: 天气+交通)
                        └── BudgetAgent     (依赖: 交通+住宿+行程)
                      → route_after_budget
                        ├── 超预算 → budget_adjust → summarizer → END
                        └── 预算内 → summarizer → END
```

**追问调整（UC-05）：** 用户可输入"换个便宜点的酒店"等指令，系统自动识别受影响的 Agent 并仅重算相关部分，保留未受影响的结果。

---

## 技术底座

两个项目共享 `common/` 模块，采用**三层架构**（推理层 + 向量化层 + 重排序层），每层独立配置、运行时热切换：

| 模块 | 文件 | 作用 |
| --- | --- | --- |
| App Context | `common/context.py` | 全局服务上下文，集中管理 LLM / Embedding / Reranker / BM25 / ChromaDB / MCP 实例 |
| LLM 客户端 | `common/llm_client.py` | 推理层：DeepSeek / Ollama 双后端热切换，持久化到 `.env` |
| Embedding | `common/embedding_client.py` | 向量化层：Ollama 本地嵌入模型（qwen3-embedding:8b） |
| Reranker | `common/reranker.py` | 重排序层：sentence-transformers Cross-Encoder，可开关 |
| BM25 检索 | `common/bm25_store.py` | 稀疏检索：Okapi BM25 算法，与稠密向量互补 |
| 向量存储 | `common/vector_store.py` | ChromaDB 操作（attractions + documents 双集合） |
| 文档解析 | `common/document_loader.py` | PDF/DOCX/TXT/MD 解析与分块 |
| MCP Server | `common/mcp_server/server.py` | FastMCP 服务端，注册 5 个异步工具 |
| MCP 客户端 | `common/mcp_server/client.py` | 双路径调用（优先 MCP 协议，失败熔断降级到 tools.py） |
| MCP 工具 | `common/mcp_server/tools.py` | 航班/火车/酒店/天气/景点搜索（读取模拟 JSON 数据） |

> 同样的底座，换一套 Agent 角色和编排逻辑，就能从"知识助手"变成"旅游规划师"。这就是 MCP + LangGraph 的架构威力。

**三层配置架构：**

```
┌─────────────────────────────────────────────┐
│           common/context.py (AppContext)     │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│  │  推理层    │ │ 向量化层   │ │ 重排序层   │  │
│  │ LLMClient │ │Embedding  │ │ Reranker  │  │
│  │DeepSeek/  │ │Client     │ │Cross-Enc  │  │
│  │Ollama     │ │Ollama     │ │s-tensors  │  │
│  └───────────┘ └───────────┘ └───────────┘  │
│  ┌───────────┐ ┌───────────┐                │
│  │  BM25     │ │ ChromaDB  │                │
│  │  Store    │ │VectorStore│                │
│  └───────────┘ └───────────┘                │
└─────────────────────────────────────────────┘
```

**MCP 工具一览：**

| 工具 | 参数 | 返回 | 数据源 |
| --- | --- | --- | --- |
| `search_flights` | departure, destination | `[{flight_no, price, airline, ...}]` | 11 条航线模拟数据 |
| `search_trains` | departure, destination | `[{train_no, type, price, ...}]` | 11 条线路模拟数据 |
| `search_hotels` | city, max_price | `[{name, price, rating, ...}]` | 6 城市 × 5 酒店模拟数据 |
| `get_weather` | city, days | `{daily: [...], clothing_advice}` | 6 城市配置动态生成 |
| `search_attractions` | city, preferences | `[{name, category, ticket_price, ...}]` | 6 城市 × 12 景点模拟数据 |

> `get_weather` 和 `search_attractions` 支持接入真实 API：在 `.env` 中填入 `WEATHER_API_KEY`（和风天气）和 `AMAP_API_KEY`（高德地图）即可切换到实时数据。

---

## 方案B 架构图

```
React + shadcn/ui (前端, 端口 3000)
    │  Next.js 14 App Router
    │  4 个页面: 首页 / KnowSeeker / TripMind / 设置
    ↕ REST API / SSE 流式
FastAPI (后端, 端口 8000)
    │  13 个 API 端点
    ├── knowseeker/agent.py        # RAG 问答（异步任务）
    ├── knowseeker/rag_chain.py    # 文档管理 + 混合检索
    ├── tripmind/orchestrator.py   # 旅游规划 + SSE 流式
    └── common/context.py          # 三层配置管理

MCP Server (端口 8765, FastAPI 生命周期自动管理)
    └── common/mcp_server/tools.py → mock_data/*.json
```

---

## API 接口（方案B）

| 方法 | 路径 | 功能 |
| --- | --- | --- |
| `POST` | `/api/chat` | 创建 RAG 问答异步任务，返回 `taskId` |
| `GET` | `/api/chat/{task_id}` | 轮询任务状态和结果（answer / thinking_trace / llm_thinking / citations） |
| `POST` | `/api/documents/upload` | 上传文档到知识库 |
| `GET` | `/api/documents` | 列出已索引文档 |
| `DELETE` | `/api/documents/{doc_id}` | 删除指定文档 |
| `POST` | `/api/travel/plan` | 一次性旅行规划 |
| `POST` | `/api/travel/plan/stream` | SSE 流式旅行规划 |
| `POST` | `/api/travel/adjust` | 追问调整旅行方案 |
| `GET` | `/api/models` | 获取可用模型列表 |
| `GET` | `/api/settings` | 获取三层配置（推理层 + 向量化层 + 重排序层） |
| `POST` | `/api/settings` | 更新三层配置（持久化到 .env） |
| `GET` | `/api/health` | 健康检查 |

---

## 项目结构

```
agent-forge/
├── common/                        # 公共模块（两个项目共享）
│   ├── context.py                 # App Context — 全局服务上下文
│   ├── llm_client.py              # 推理层：LLM 客户端（DeepSeek/Ollama 热切换）
│   ├── embedding_client.py        # 向量化层：Ollama 本地嵌入模型
│   ├── reranker.py                # 重排序层：Cross-Encoder 重排序
│   ├── bm25_store.py              # 稀疏检索：Okapi BM25
│   ├── vector_store.py            # ChromaDB 向量存储（双集合）
│   ├── document_loader.py         # 多格式文档解析与分块
│   └── mcp_server/                # MCP 协议层
│       ├── server.py              # FastMCP 服务端（5 个工具）
│       ├── tools.py               # 工具函数实现
│       ├── client.py              # MCP 客户端（双路径 + 熔断）
│       ├── init_attractions.py    # 景点数据 → ChromaDB 初始化
│       ├── smart_plan.py          # 第三方真实数据源（飞猪+高德）
│       └── mock_data/             # 模拟数据
│           ├── flights.json       # 11 条航线
│           ├── trains.json        # 11 条线路
│           ├── hotels.json        # 6 城市 × 5 酒店
│           ├── weather.json       # 6 城市天气配置
│           └── attractions/       # 6 城市 × 12 景点
├── knowseeker/                    # 项目一：知识助手
│   ├── app.py                     # Streamlit 入口（方案A）
│   ├── agent.py                   # LangGraph Agentic RAG 状态机
│   ├── rag_chain.py               # RAG 管道（混合检索 + RRF 融合 + 重排序）
│   └── README.md
├── tripmind/                      # 项目二：旅游助手
│   ├── app.py                     # Gradio 入口（方案A）
│   ├── orchestrator.py            # LangGraph 编排器（DAG 调度 + 流式）
│   ├── prompts.py                 # 6 个 Agent 系统提示词
│   ├── types.py                   # TravelRequest / TravelState 类型
│   ├── agents/                    # 6 个领域 Agent
│   │   ├── base.py                # BaseAgent 基类（LLM + MCP + 容错）
│   │   ├── weather.py             # 天气 Agent
│   │   ├── transport.py           # 交通 Agent
│   │   ├── hotel.py               # 住宿 Agent
│   │   ├── itinerary.py           # 行程 Agent
│   │   ├── budget.py              # 预算 Agent
│   │   └── summarizer.py          # 汇总 Agent
│   └── README.md
├── backend/                       # FastAPI 后端（方案B）
│   └── server.py                  # REST API 端点 + MCP 生命周期管理
├── frontend/                      # React 前端（方案B）
│   ├── app/                       # Next.js 14 App Router
│   │   ├── page.tsx               # 首页（项目导航）
│   │   ├── knowseeker/page.tsx    # 知识问答界面
│   │   ├── tripmind/page.tsx      # 旅游规划界面（SSE 流式）
│   │   ├── settings/page.tsx      # 三层配置界面
│   │   └── layout.tsx             # 全局布局 + 侧边栏
│   ├── components/ui/             # shadcn/ui 组件库
│   ├── lib/config.ts              # API 基础 URL 配置
│   └── package.json
├── design/                        # 设计文档
│   ├── 01-tech-stack.md           # 技术栈选型决策
│   ├── 02-knowseeker.md           # KnowSeeker 需求分析与设计
│   ├── 03-tripmind.md             # TripMind 需求分析与设计
│   ├── 04-tripmind-implementation.md  # TripMind 实现计划
│   └── 05-tripmind-progress.md    # TripMind 实现进度报告
├── data/
│   └── chromadb/                  # ChromaDB 持久化数据
├── .env.example                   # 环境变量模板
├── Makefile                       # 快捷启动命令
├── pyproject.toml                 # uv 项目配置
├── CLAUDE.md                      # AI 开发助手指令
├── codemap.md                     # 仓库代码地图
└── README.md                      # 本文件
```

---

## 核心设计模式

| 模式 | 说明 |
| --- | --- |
| **App Context** | `common/context.py` 集中管理所有服务实例（LLM / Embedding / Reranker / BM25 / ChromaDB），通过 `get_context()` 统一获取，替代模块级单例 |
| **三层配置** | 推理层（LLM）、向量化层（Embedding）、重排序层（Reranker）独立配置、独立热切换，各自持久化到 `.env` |
| **混合检索 + RRF** | BM25 稀疏检索 + ChromaDB 稠密向量检索并行执行，通过 Reciprocal Rank Fusion 融合去重，兼顾关键词匹配和语义理解 |
| **Cross-Encoder 重排序** | 融合后的候选集经 sentence-transformers Cross-Encoder 精排，显著提升 Top-K 质量 |
| **MCP 协议抽象** | 所有工具调用走 `client.call_tool()` → MCP Streamable HTTP 优先，连续 3 次失败后永久降级到 `tools.py` 直接调用 |
| **LLM 热切换** | `LLMClient.update()` 在 DeepSeek 和 Ollama 之间运行时切换，配置持久化到 `.env` |
| **Safe Execution** | 每个 Agent 的 `execute()` 被 `safe_execute()` 包裹，单个 Agent 失败不阻塞整体流程 |
| **并行 + 顺序混合** | 独立 Agent 用 `asyncio.gather` 并行，依赖链上的 Agent 顺序执行 |
| **Agentic 决策循环** | KnowSeeker 的 LangGraph 状态机自主判断是否需要多轮检索 |
| **追问调整** | TripMind 的 `adjust_plan()` 通过关键词匹配确定受影响 Agent，仅重算相关部分 |
| **SSE 流式推送** | 方案B 后端通过 `graph.astream()` 逐节点推送进度，前端实时更新 Agent 状态面板 |
| **双路径 LLM** | 每个 Agent 的 LLM 调用失败时自动回退到内置数据驱动逻辑，确保功能可用 |
| **异步 RAG 任务** | `/api/chat` 返回 `taskId`，后端异步执行 RAG 流程，前端轮询 `/api/chat/{task_id}` 获取结果 |

---

## 适合谁看

- 正在学习大模型 Agent 开发的同学
- 想了解 LangGraph + MCP 实战的开发者
- 需要 Multi-Agent 架构参考的工程师
- 想学习前后端分离 AI 应用架构的全栈开发者

---

## 设计文档

- [技术栈选型决策](design/01-tech-stack.md)
- [KnowSeeker 需求分析与软件设计](design/02-knowseeker.md)
- [TripMind 需求分析与软件设计](design/03-tripmind.md)
- [TripMind 实现计划](design/04-tripmind-implementation.md)
- [TripMind 实现进度报告](design/05-tripmind-progress.md)
