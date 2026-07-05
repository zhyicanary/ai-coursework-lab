# common/

## 职责

`common/` 是 KnowSeeker（单智能体 RAG 问答）和 TripMind（多智能体旅行规划器）的共享基础设施层。它通过 `AppContext` 容器（`context.py`）统一管理所有客户端生命周期，提供 LLM 客户端（`LLMClient`，可在 DeepSeek API 和本地 Ollama 之间热切换）、Embedding 客户端（`EmbeddingClient`，Ollama qwen3-embedding:8b）、Cross-Encoder 重排序器（`RerankerClient`）、BM25 稀疏检索（`BM25Store`）、以及 ChromaDB 向量存储（两个命名空间：`"attractions"` 和 `"documents"`）。此外还包含完整的 **MCP 协议层**——注册了 5 个旅行工具的 FastMCP 服务器、双路径客户端（Streamable HTTP → 直接函数调用，含熔断机制），以及涵盖 6 个中国城市的模拟 JSON 数据。

## 文件说明

- `__init__.py` — 空初始化文件；将 `common` 标记为包。
- `context.py` — **`AppContext`** 容器类，通过懒加载 property 统一管理 `LLMClient`、`EmbeddingClient`、`RerankerClient`、`BM25Store` 等生命周期。使用 `get_context()` 获取全局实例。替代了原来的模块级全局单例模式，支持依赖注入和测试替身。
- `llm_client.py` — **`LLMClient`** 类，包含 `chat_completion(messages, ...)` 方法。从 `.env` 读取 `LLM_BACKEND` 以选择 DeepSeek 或 Ollama。`update(backend, model, api_key, base_url)` 通过 `dotenv.set_key()` 将更改持久化回 `.env`。通过 `context.get_context().llm` 获取实例。
- `embedding_client.py` — **`EmbeddingClient`** 类，包含 `embed_texts(texts)` 和 `embed_query(text)` 方法，用于文本到向量的转换。始终连接到 Ollama（通过 `.env` 中的 `EMBEDDING_MODEL` 和 `OLLAMA_BASE_URL` 配置）。通过 `context.get_context().embedding` 获取实例。
- `vector_store.py` — ChromaDB 持久化层。模块级函数（非类）：
  - `init_collection(collection_name)` → 使用余弦距离的 `get_or_create_collection()`。
  - `add_attractions(city, attractions, texts)` — 批量写入 `"attractions"` 集合。
  - `search_attractions(city, query, top_k, preferences)` — 余弦相似度搜索，可选基于偏好的重排序。
  - `add_documents(doc_id, documents, texts)` — 批量写入 `"documents"` 集合（KnowSeeker）。
  - `search_documents(query, top_k)` — 对 `"documents"` 集合进行相似度搜索。
  ChromaDB 持久化目录：`data/chromadb/`。
- `document_loader.py` — 文档解析层，支持 `load(file, filename)` 自动检测 PDF/DOCX/TXT/MD 格式并提取文本；`chunk_documents(docs, chunk_size, chunk_overlap)` 按指定粒度分块。
- `reranker.py` — **`RerankerClient`** 类，通过 Cross-Encoder（`BAAI/bge-reranker-v2-m3`）对检索结果重排序。通过 `context.get_context().reranker` 获取实例。`enabled` 标志可动态开启/关闭重排序。
- `bm25_store.py` — **`BM25Store`** 类，提供基于 BM25 算法的稀疏检索，与稠密向量检索互补。通过 `context.get_context().bm25_store` 获取实例。`rebuild()` 同步 ChromaDB 的全量文档。
- `mcp_server/__init__.py` — 空初始化文件。
- `mcp_server/server.py` — 名为 `"TripMind Tools"` 的 **FastMCP** 服务器，通过 `register_tools()` 注册了 5 个异步工具：`search_flights`, `search_trains`, `search_hotels`, `get_weather`, `search_attractions`。入口点：`uv run python -m common.mcp_server.server`。
- `mcp_server/tools.py` — 5 个工具的纯异步实现。从 `mock_data/` 读取模拟 JSON 数据。`CITY_NAME_MAP` 将中文城市名称映射为拼音文件名。`_load_json(filename)` 和 `_city_to_filename(city)` 是内部辅助函数。每个工具在没有匹配的模拟数据时都有回退默认值。
- `mcp_server/client.py` — **`call_tool(name, arguments)`** — 带熔断缓存的统一 MCP 入口点。优先通过 Streamable HTTP 连接常驻 MCP Server（`call_tool_via_http`，连接 `http://127.0.0.1:8765/mcp`）；成功时缓存 `_mcp_available = True`；`_MAX_HTTP_FAILS = 3` 次连续失败后将 `_mcp_available` 设为 `False` 并永久回退到 `call_tool_direct`（直接调用 `tools.py` 函数）。使用 `mcp.client.streamable_http` 和 `ClientSession`。
- `mcp_server/init_attractions.py` — 一次性脚本（`uv run python -m common.mcp_server.init_attractions`），读取所有 `mock_data/attractions/*.json`，构建组合文本以供向量化，并通过 `vector_store.add_attractions()` 持久化嵌入向量。当 Ollama 离线时具有优雅降级——仅跳过 ChromaDB 导入。

## 设计模式

- **容器模式**：`AppContext`（`context.py`）作为统一容器，通过懒加载 property 管理所有子组件生命周期。组件通过 `get_context().llm` / `.embedding` 等访问，不再直接导入模块级单例。支持测试替身注入。MCP 熔断状态（`_mcp_available`）也由 AppContext 管理。
- **策略/热切换模式**：`LLMClient` 通过 `update()` 在运行时在 `"deepseek"` 和 `"ollama"` 后端之间切换，同时将选择持久化到 `.env`，使切换在重启后仍然生效。
- **熔断/故障转移模式**：`mcp_server/client.py:call_tool()` 将 MCP 可用性分为三态（`None` → 未尝试，`True` → HTTP 可用，`False` → 不可用）。连续 `_MAX_HTTP_FAILS = 3` 次 HTTP 调用失败后通过 `context.get_context().mark_mcp_failure()` 标记为不可用，切换到直接调用 `tools.py`。熔断状态由 `AppContext` 统一管理。
- **模块级函数式 API**：`vector_store.py` 暴露裸函数而非类——使 KnowSeeker（文档搜索）和 TripMind（景点搜索）都能更简单地按需导入。

## 数据与控制流

```
                      ┌──────────────────────────────────┐
                      │         knowseeker/ 应用          │
                      │  (Streamlit RAG QA)               │
                      │  导入: llm, vector_store           │
                      │  使用: chat_completion,            │
                      │        add/search_documents        │
                      └──────────┬───────────────────────┘
                                 │
    ┌────────────────────────────┼────────────────────────────┐
    │                            │                            │
    ▼                            ▼                            ▼
┌─────────────┐       ┌──────────────────┐       ┌──────────────────────┐
│ llm_client   │       │ vector_store      │       │ embedding_client     │
│ LLMClient    │       │ ChromaDB          │       │ EmbeddingClient      │
│ ┌─────────┐ │       │ ┌──────────────┐  │       │ ┌──────────────────┐│
│ │DeepSeek │ │       │ │"attractions" │  │       │ │Ollama            ││
│ │ 或      │─┼──▶    │ │ collection   │  │       │ │qwen3-embedding   ││
│ │Ollama   │ │       │ │"documents"   │  │       │ │:4b               ││
│ └─────────┘ │       │ └──────────────┘  │       │ └──────────────────┘│
└─────────────┘       └──────────────────┘       └──────────────────────┘
                                 ▲
                                 │
    ┌────────────────────────────┼────────────────────────────┐
    │                            │                            │
    │                    tripmind/ 应用                        │
     │              (TripMind 多智能体)                         │
    │              智能体通过以下方式调用：                     │
    │              BaseAgent.call_mcp() → client.call_tool()  │
    │              BaseAgent.call_llm() → llm.chat_completion │
    └────────────────────────────┼────────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  mcp_server/client.py    │
                    │  call_tool()             │
                    │  ┌───────────────────┐   │
                    │  │ _mcp_available?   │   │
                     │  │  True  → HTTP     │   │
                     │  │  False → 直接调用   │   │
                    │  └───────────────────┘   │
                    └────────┬────────────────┘
                             │
                  ┌──────────┴──────────┐
                  ▼                     ▼
     ┌─────────────────────┐  ┌───────────────────────┐
     │ MCP HTTP Server      │  │ 直接函数调用            │
     │ (常驻进程, 端口8765)  │  │ tools.py               │
    │ server.py            │  │ search_flights/        │
    │ 工具分发器            │  │ search_trains/         │
    └──────────┬──────────┘  │ search_hotels/          │
               │             │ get_weather/            │
               ▼             │ search_attractions     │
    ┌──────────────────┐     └───────────┬───────────┘
    │  mock_data/       │                │
    │  flights.json     │◄───────────────┘
    │  trains.json      │
    │  hotels.json      │
    │  weather.json     │
    │  attractions/*    │
    └──────────────────┘
```

**关键流程**：TripMind 智能体从不直接调用 `tools.py`。它们通过 `BaseAgent.call_mcp(tool_name, args)` → `client.call_tool()` → 要么 MCP Streamable HTTP，要么直接 `tools.py` 回退。KnowSeeker 直接使用 `llm.chat_completion()` 进行答案生成，使用 `search_with_rerank()`（稠密 + BM25 混合检索 + 重排序）进行检索。

## 集成点

| 集成点 | 依赖什么 | 被什么依赖 |
|-------|---------|----------|
| `llm_client.py` | `openai.AsyncOpenAI`, `python-dotenv`, `.env` 文件 | `knowseeker/` 的答案生成，`tripmind/agents/base.py` 的 `call_llm()` |
| `embedding_client.py` | `openai.OpenAI`（同步）, `OLLAMA_BASE_URL`, Ollama 服务 | `vector_store.py`（所有 add/search 函数） |
| `vector_store.py` | `chromadb.PersistentClient`, `embedding_client` | `knowseeker/` 的文档 RAG，`mcp_server/init_attractions.py` |
| `mcp_server/server.py` | `mcp.server.fastmcp.FastMCP`, `tools.py` 的 5 个函数 | `mcp_server/client.py`（通过 Streamable HTTP） |
| `mcp_server/tools.py` | `mock_data/*.json`（6 城市 × 12 景点，11 条航班线路，11 条火车线路，6 城市 × 5 酒店，6 个城市天气配置） | `server.py` 的注册，`client.py` 的直接回退 |
| `mcp_server/client.py` | `common.context`（熔断状态），`mcp.client.streamable_http`, `tools.py` | `tripmind/agents/base.py` 的 `call_mcp()`——所有 5 个 TripMind 智能体 |
| `mcp_server/init_attractions.py` | `vector_store.add_attractions()`, `embedding_client` | 一次性 CLI 脚本；无运行时依赖 |
