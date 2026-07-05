# knowseeker/

## 职责

KnowSeeker 是一个单智能体的 **Agentic RAG**（检索增强生成）知识助手。用户上传文档（PDF/DOCX/TXT/MD），然后提出自然语言问题。与传统的一次性检索不同，LangGraph 状态机自主判断一次检索是否足够，还是需要重新构造查询并再次搜索——以此展示智能体的决策能力。所有推理步骤、检索日志和来源引用均通过 FastAPI + React 前端可视化展示。

> ⚠️ 本文件部分内容描述的是旧方案 A（Streamlit 前端），该方案已移除。KnowSeeker 当前通过 FastAPI（`backend/server.py`）提供 API、React（`frontend/app/knowseeker/`）作为前端。核心模块（`agent.py`、`rag_chain.py`）已实现且完整可用。

## 文件

- `__init__.py` — 空包标记文件。KnowSeeker 是单仓库（monorepo）中的顶层包。

- `README.md` — 中文项目自述文件。记录项目概览、核心功能（多步检索、思维链可视化、MCP 协议）、快速启动命令以及技术栈（DeepSeek API、LangChain + LangGraph、ChromaDB、BAAI/bge-small-zh-v1.5、Streamlit）。

- `README_EN.md` — `README.md` 的英文翻译。结构与内容相同。

- `codemap.md` — 本文档。面向开发者的架构图。

## 设计模式

| 模式 | 用途 |
|---------|-------|
| **State Machine (LangGraph)** | 智能体决策循环以有向图的形式表达，带有类型化的状态传递。`AgentState` 字典流经 `analyze → retrieve → evaluate → (reformulate loop) → generate → answer`。 |
| **Agentic RAG** | 传统 RAG 仅做一次检索 → 生成。这里的智能体根据结果质量评估自主决定是否使用新关键词重新搜索。三个决策分支：简单事实（单次检索）、对比（多轮）、结果不足（重新构造）。 |
| **MCP Tool Abstraction** | 所有知识库操作（搜索、列出文档、删除）均通过 `common/mcp_server/server.py` 中的 FastMCP 装饰器暴露为 MCP 工具。智能体通过 `common/mcp_server/client.py` 中的 MCP 客户端调用这些工具，从而屏蔽底层 ChromaDB 和嵌入逻辑。 |
| **Plugin Architecture** | 公共模块（`common/llm_client.py`、`common/vector_store.py`、`common/embedding_client.py`、`common/document_loader.py`）提供所有基础设施。KnowSeeker 仅添加智能体编排和 Streamlit UI——不直接调用 ChromaDB 或 LLM API。 |
| **Chain-of-Thought Logging** | 每个智能体决策步骤（分析、检索结果、评估判断、最终生成）都会追加到状态中的 `thinking_trace`，然后在 Streamlit UI 中以可展开区域的方式逐步渲染展示。 |

## 数据与控制流

### 文档摄入流程

```
用户通过 React 前端上传文件
    │
    ▼
backend/server.py /api/documents/upload → knowseeker/rag_chain.py.index_document()
    │
    ▼
common/document_loader.py.load(file)
    ├── 检测格式 (PDF → PyPDF2, DOCX → python-docx, TXT/MD → 纯文本读取)
    ├── 提取原始文本
    └── 分块为文本片段 (500 字符, 50 字符重叠)
    │
    ▼
common/vector_store.py.add_documents() → ChromaDB (qwen3-embedding:8b 向量)
    │
    ▼
common/context.get_context().bm25_store.add_texts() → 同步 BM25 索引
    │
    ▼
React 显示: "已入库 N 个文档片段"
```

### 问答流程 (Agentic RAG)

```
用户在 React 前端聊天输入框中输入问题
    │
    ▼
backend/server.py → knowseeker/agent.py agentic_rag_stream()
    │
    ▼
[analyze_question]  LLM 分析问题复杂度
    ├── 输出: {keywords: [...], strategy: "single"|"multi", num_rounds: int}
    └── 记录到 thinking_trace
    │
    ▼
[retrieve]  本地调用: search_with_rerank(query, top_k=5, recall_k=20)
    ├── 稠密检索: vector_store.search_documents() → ChromaDB
    ├── 稀疏检索: bm25_store.search() → BM25 索引
    ├── RRF 融合 → Cross-Encoder 重排序
    └── 返回 Top-5 文本块 → 存入 search_history, 记录到 thinking_trace
    │
    ▼
[evaluate_results]  LLM 评估检索到的文本块
    ├── 条件: 文本块是否足以回答问题？
    ├── 是 → need_more_search=False → 跳转到 generate_answer
    └── 否 → need_more_search=True  → 跳转到 reformulate
    │
    ▼ (如果需要)
[reformulate]  LLM 生成新关键词 (例如 "违约责任 行业标准")
    └── 循环回到 retrieve (最大轮数 = search_plan.num_rounds)
    │
    ▼
[generate_answer]  LLM 根据 final_context 综合生成答案
    ├── 合并多轮检索的所有文本块
    ├── 输出: answer (str) + citations [{chunk_text, doc_name, page}]
    └── 记录到 thinking_trace
    │
    ▼
React (SSE 流式接收):
    ├── 助手回答（附可展开的引用和来源）
    └── 思维链面板（分析 → 每轮检索 → 评估 → 最终结果）
```

## 集成点

| 集成模块 | 方向 | 详情 |
|------------|-----------|-------|
| **common/llm_client.py** | 依赖 | DeepSeek API（兼容 OpenAI 接口）。每个智能体节点在分析、评估、重新构造和生成时都会使用。默认 5 秒超时并带降级回退。 |
| **common/embedding_client.py** | 依赖 | 通过 Ollama 使用 `qwen3-embedding:8b` 进行文本向量化。 |
| **common/vector_store.py** | 依赖 | ChromaDB 封装。提供 `add_documents()`、`search_documents()`、`list_documents()`、`delete_document()`。直接调用（非 MCP）。 |
| **common/bm25_store.py** | 依赖 | BM25 稀疏检索，与稠密检索互补（RRF 融合）。通过 `context.get_context().bm25_store` 获取。 |
| **common/reranker.py** | 依赖 | Cross-Encoder 重排序器，对 RRF 融合结果二次排序。通过 `context.get_context().reranker` 获取。 |
| **common/document_loader.py** | 依赖 | 解析 PDF/DOCX/TXT/MD 文件。以 500 字符粒度、50 字符重叠生成文本块。 |
| **React (前端)** | 面向用户 | `frontend/app/knowseeker/page.tsx`。基于 Next.js 14 + shadcn/ui 的聊天界面，包含文档上传、思维链追踪、引用展示。通过 `backend/server.py` 的 FastAPI 接口与后端通信。 |
| **design/02-knowseeker.md** | 被文档说明 | 完整的需求、架构图、LangGraph 状态图、数据结构（`AgentState` TypedDict）以及 UI 线框图。 |
