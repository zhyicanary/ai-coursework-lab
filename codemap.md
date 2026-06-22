# 仓库地图: ai-coursework-lab

## 项目职责

**智能应用系统设计课设作品集** — 基于统一技术底座（DeepSeek API + Ollama Embedding + ChromaDB + MCP 协议），实现两种不同的 Agent 范式：

| # | 项目 | 范式 | 前端 | 入口 |
|---|------|------|------|------|
| 1 | KnowSeeker | 单 Agent 深度推理 (Agentic RAG) | Streamlit | `knowseeker/app.py` |
| 2 | TripMind | 多 Agent 协同编排 (Multi-Agent) | Gradio | `tripmind/app.py` |

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
| `common/` | **共享基础设施层**：LLM 客户端（DeepSeek/Ollama 热切换）、Ollama Embedding 客户端、ChromaDB 向量存储操作、MCP 协议层（FastMCP 服务端 + 双路径客户端 + 5 个旅行工具 + 6 城市模拟数据） | [查看地图](common/codemap.md) |
| `common/mcp_server/` | **MCP 工具层**：FastMCP 服务器注册 5 个 async 工具（航班/火车/酒店/天气/景点搜索），MCP 客户端包装器（透明降级到 tools.py 直接调用），6 城市模拟 JSON 数据（11 航线、11 铁路、30 酒店、6 城市天气、72 景点） | [查看地图](common/mcp_server/codemap.md) |
| `tripmind/` | **多 Agent 旅游规划系统**：Gradio 前端（3 个 Tab：旅行规划/对话/设置）、LangGraph 状态机编排器、6 个 Agent 系统提示词、并行→顺序执行流程、追问调整（UC-05） | [查看地图](tripmind/codemap.md) |
| `tripmind/agents/` | **Agent 层**：6 个领域专用 Agent（天气/交通/住宿/行程/预算/汇总）+ 1 个抽象基类 `BaseAgent`，所有 Agent 遵循 MCP 优先、双路径执行、SafeExecute 错误隔离模式 | [查看地图](tripmind/agents/codemap.md) |
| `knowseeker/` | **单 Agent RAG 问答系统**：Streamlit 前端、LangGraph Agentic RAG 循环（分析→检索→评估→重检索→生成）、链式思考可视化、多轮自主检索决策（待实现，详见设计文档） | [查看地图](knowseeker/codemap.md) |

## 设计模式（全项目级）

| 模式 | 使用位置 |
|------|----------|
| **MCP 协议抽象** | 所有工具调用走 `client.call_tool()` → MCP stdio 优先，失败自动降级到 `tools.py` 直接调用 |
| **Singleton / 模块级单例** | `llm`、`embedding`、ChromaDB `client`、`_mcp_available` — 均以模块级全局变量存在，无依赖注入 |
| **LLM 热切换** | `LLMClient.update()` 在 DeepSeek 和 Ollama 之间运行时切换，切换持久化到 `.env` |
| **Safe Execution** | 每个 Agent 的 `execute()` 被 `safe_execute()` 包裹，单个 Agent 失败不阻塞整体流程 |
| **并行 + 顺序混合** | 独立 Agent 用 `asyncio.gather` 并行，依赖链上的 Agent 顺序执行 |
| **Agentic 决策循环** | KnowSeeker 的 LangGraph 状态机自主判断是否需要多轮检索 |

## 跨模块数据流

```
Gradio / Streamlit 前端
    │
    ├── tripmind/ ─── orchestrator.py (LangGraph)
    │     └── agents/ (6 个 BaseAgent 子类)
    │           ├── call_mcp() ──→ common/mcp_server/client.py
    │           │     ├── MCP stdio → server.py → tools.py → mock_data/
    │           │     └── 直接调用 → tools.py → mock_data/
    │           └── call_llm() ──→ common/llm_client.py
    │                                  └── DeepSeek / Ollama
    │
    └── knowseeker/ ─── agent.py (LangGraph Agentic RAG)
          ├── MCP 工具 → common/mcp_server/client.py
          │     └── search_knowledge_base → vector_store.search_documents()
          └── LLM → common/llm_client.py

common/embedding_client.py ← Ollama / sentence-transformers
common/vector_store.py ← ChromaDB (data/chromadb/)
```
