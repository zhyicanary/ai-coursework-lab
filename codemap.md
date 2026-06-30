# 仓库地图: ai-coursework-lab

## 项目职责

**智能应用系统设计课设作品集** — 基于统一技术底座（DeepSeek API + Ollama Embedding + ChromaDB + MCP 协议），实现两种不同的 Agent 范式：

| # | 项目 | 范式 | 前端（方案 A） | 前端（方案 B） | 入口 |
|---|------|------|---------------|---------------|------|
| 1 | KnowSeeker | 单 Agent 深度推理 (Agentic RAG) | Streamlit | React + shadcn/ui | `knowseeker/app.py` |
| 2 | TripMind | 多 Agent 协同编排 (Multi-Agent) | Gradio | React + shadcn/ui | `tripmind/app.py` |

> **方案 A**（旧）：Streamlit / Gradio 全栈 Python，直接调用 `common/` 层逻辑。
> **方案 B**（新）：FastAPI 后端 API + Next.js + shadcn/ui 前端，前后端分离。

## 系统入口

| 文件 | 描述 |
|------|------|
| `pyproject.toml` | 项目依赖清单和 uv 构建配置 |
| `.env.example` | 环境变量模板（LLM 后端、API key、Ollama URL） |
| `CLAUDE.md` | AI 开发助手系统指令和技术架构文档 |
| `Makefile` | 快捷命令（运行、初始化等） |

## 目录聚合

| 目录 | 职责摘要 | 详细地图 |
|------|----------|----------|
| `common/` | **共享基础设施层**：LLM 客户端（DeepSeek/Ollama 热切换，含 `list_models()`）、Ollama Embedding 客户端、ChromaDB 向量存储操作、MCP 协议层（FastMCP 服务端 + Streamable HTTP 客户端 + 5 个旅行工具 + 6 城市模拟数据） | [查看地图](common/codemap.md) |
| `common/mcp_server/` | **MCP 工具层**：FastMCP 服务器注册 5 个 async 工具（航班/火车/酒店/天气/景点搜索），Streamable HTTP 传输（端口 8765），MCP 客户端包装器（透明降级到 tools.py 直接调用），6 城市模拟 JSON 数据 | [查看地图](common/mcp_server/codemap.md) |
| `backend/` | **FastAPI 统一后端**（方案 B）：12 个 REST API 端点封装 KnowSeeker + TripMind + LLM 设置，SSE 流式规划，CORS 全开，内置 MCP Server 生命周期管理 | — |
| `frontend/` | **React + shadcn/ui 前端**（方案 B）：Next.js 14 App Router，4 个页面（首页 / KnowSeeker 问答 / TripMind 规划 / 设置），12 个 shadcn/ui 组件，Tailwind CSS 双主题 | — |
| `tripmind/` | **多 Agent 旅游规划系统**：含 Gradio 前端（方案 A）和 LangGraph 状态机编排器、6 个 Agent 系统提示词、并行→顺序执行流程、追问调整（UC-05） | [查看地图](tripmind/codemap.md) |
| `tripmind/agents/` | **Agent 层**：6 个领域专用 Agent（天气/交通/住宿/行程/预算/汇总）+ 1 个抽象基类 `BaseAgent`，所有 Agent 遵循 MCP 优先、双路径执行、SafeExecute 错误隔离模式 | [查看地图](tripmind/agents/codemap.md) |
| `knowseeker/` | **单 Agent RAG 问答系统**：含 Streamlit 前端（方案 A）和 LangGraph Agentic RAG 循环（分析→检索→评估→重检索→生成）、链式思考可视化 | [查看地图](knowseeker/codemap.md) |

## 架构对比

### 方案 A — 全栈 Python（原有，可用）

```
Gradio / Streamlit 前端
    │
    ├── tripmind/ ─── orchestrator.py
    │     └── agents/ ──→ common/mcp_server/client.py
    │                           ├── Streamable HTTP (8765) → server.py → tools.py
    │                           └── 直接调用 → tools.py → mock_data/
    │
    └── knowseeker/ ─── agent.py
          └── vector_store.search_documents()
```

### 方案 B — 前后端分离（新增）

```
React + shadcn/ui (前端, 端口 3000)
    ↕ REST / SSE
FastAPI (后端, 端口 8000)
    │
    ├── knowseeker/agent.py        # RAG 问答
    ├── knowseeker/rag_chain.py    # 文档管理
    ├── tripmind/orchestrator.py   # 旅游规划 + SSE 流式
    └── common/llm_client.py       # LLM 设置
                                   
MCP Server (端口 8765, FastAPI 生命周期自动管理)
```

### 启动方式

```bash
# 方案 A（旧）
uv run streamlit run knowseeker/app.py          # KnowSeeker
uv run python tripmind/app.py                   # TripMind

# 方案 B（新）
uv run uvicorn backend.server:app --port 8000   # 后端 API
cd frontend && npm run dev                      # 前端界面
```

## 设计模式（全项目级）

| 模式 | 使用位置 |
|------|----------|
| **MCP 协议抽象** | 所有工具调用走 `client.call_tool()` → MCP Streamable HTTP 优先，失败自动降级到 `tools.py` 直接调用 |
| **Singleton / 模块级单例** | `llm`、`embedding`、ChromaDB `client`、`_mcp_available` — 均以模块级全局变量存在，无依赖注入 |
| **LLM 热切换** | `LLMClient.update()` 在 DeepSeek 和 Ollama 之间运行时切换，切换持久化到 `.env` |
| **Safe Execution** | 每个 Agent 的 `execute()` 被 `safe_execute()` 包裹，单个 Agent 失败不阻塞整体流程 |
| **并行 + 顺序混合** | 独立 Agent 用 `asyncio.gather` 并行，依赖链上的 Agent 顺序执行 |
| **Agentic 决策循环** | KnowSeeker 的 LangGraph 状态机自主判断是否需要多轮检索 |
| **前端分离** | 方案 B 用 REST/SSE 解耦前后端，React 组件化，shadcn/ui 可复用 UI 组件 |
