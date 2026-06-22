# knowseeker/

## 职责

KnowSeeker 是一个单智能体的 **Agentic RAG**（检索增强生成）知识助手。用户上传文档（PDF/DOCX/TXT/MD），然后提出自然语言问题。与传统的一次性检索不同，LangGraph 状态机自主判断一次检索是否足够，还是需要重新构造查询并再次搜索——以此展示智能体的决策能力。所有推理步骤、检索日志和来源引用均在 Streamlit 前端中可视化展示。

## 文件

- `__init__.py` — 空包标记文件。KnowSeeker 是单仓库（monorepo）中的顶层包。

- `README.md` — 中文项目自述文件。记录项目概览、核心功能（多步检索、思维链可视化、MCP 协议）、快速启动命令以及技术栈（DeepSeek API、LangChain + LangGraph、ChromaDB、BAAI/bge-small-zh-v1.5、Streamlit）。

- `README_EN.md` — `README.md` 的英文翻译。结构与内容相同。

- `codemap.md` — 本文档。面向开发者的架构图。

### 待实现文件（根据设计文档）

以下文件在 `design/02-knowseeker.md` 中有说明，但尚未存在于本目录中。这里列出作为路线图：

- `app.py` — **Streamlit 前端入口点**。三个 UI 区域：侧边栏用于文档上传（文件上传组件），主聊天面板（使用 `st.chat_message` 展示用户/助手对话轮次），以及一个可展开的思维链区域展示每个推理步骤。通过 `streamlit run knowseeker/app.py` 运行。

- `agent.py` — **LangGraph 状态机**，实现 Agentic RAG 循环。定义了一个 `AgentState` TypedDict，包含以下字段：`question`、`search_plan`、`search_history`、`need_more_search`、`final_context`、`answer`、`citations`、`thinking_trace`。包含五个图节点：
  - `analyze_question(state)` — LLM 分析问题并生成搜索计划（关键词、策略、轮次数）。
  - `retrieve(state)` — 调用 MCP 工具 `search_knowledge_base` 执行向量搜索，返回 Top-K 文本块。
  - `evaluate_results(state)` — LLM 判断检索到的文本块是否足以回答问题；设置 `need_more_search`。
  - `reformulate(state)` — LLM 使用不同关键词重写搜索查询，进行第二次尝试。
  - `generate_answer(state)` — LLM 根据 `final_context` 综合生成最终答案并附带内联引用。

  边：`analyze → retrieve → evaluate → (sufficient ? generate : reformulate → retrieve)`。

- `rag_chain.py` — **基础 RAG 管道**工具。封装 LangChain 的文档加载（`PyPDF2`、`python-docx`、`unstructured`、`markdown`）、文本分块（`chunk_size=500`、`overlap=50`）、使用 `BAAI/bge-small-zh-v1.5` 进行嵌入、ChromaDB 导入以及相似度搜索。将纯检索管道与智能体决策层分离。

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
用户在 Streamlit 侧边栏上传文件
    │
    ▼
common/document_loader.py.load(file)
    ├── 检测格式 (PDF → PyPDF2, DOCX → python-docx, TXT/MD → 纯文本读取)
    ├── 提取原始文本
    └── 分块为文本片段 (500 字符, 50 字符重叠)
    │
    ▼
common/embedding_client.py  (BAAI/bge-small-zh-v1.5 → 512 维向量)
    │
    ▼
common/vector_store.py.add_to_chromadb(chunks, embeddings, metadata)
    │
    ▼
Streamlit 显示: "已入库 N 个文档片段"
```

### 问答流程 (Agentic RAG)

```
用户在 Streamlit 聊天输入框中输入问题
    │
    ▼
[analyze_question]  LLM 分析问题复杂度
    ├── 输出: {keywords: [...], strategy: "single"|"multi", num_rounds: int}
    └── 记录到 thinking_trace
    │
    ▼
[retrieve]  调用 MCP 工具: search_knowledge_base(query=keywords, top_k=5)
    ├── MCP 服务器 → vector_store.similarity_search() → ChromaDB
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
Streamlit 渲染:
    ├── 💬 助手回答（附可展开的引用）
    └── 🧠 思维链面板（分析 → 每轮检索 → 评估 → 最终结果）
```

## 集成点

| 集成模块 | 方向 | 详情 |
|------------|-----------|-------|
| **common/llm_client.py** | 依赖 | DeepSeek API（兼容 OpenAI 接口）。每个智能体节点在分析、评估、重新构造和生成时都会使用。默认 5 秒超时并带降级回退。 |
| **common/embedding_client.py** | 依赖 | 通过 sentence-transformers 使用 `BAAI/bge-small-zh-v1.5`。在文档摄入期间使用。512 维向量。 |
| **common/vector_store.py** | 依赖 | ChromaDB 封装。提供 `add_to_chromadb()`、`similarity_search()`、`list_documents()`、`delete_document()`。通过 MCP 工具间接调用。 |
| **common/document_loader.py** | 依赖（预期） | 解析 PDF/DOCX/TXT/MD 文件。以 500 字符粒度、50 字符重叠生成文本块。 |
| **common/mcp_server/server.py** | 依赖 | FastMCP 服务器，注册三个工具：`search_knowledge_base(query, top_k, filter_doc)`、`list_documents()`、`delete_document(doc_name)`。作为子进程或边车（sidecar）启动。 |
| **common/mcp_server/client.py** | 依赖 | MCP 客户端封装。智能体调用 `call_tool("search_knowledge_base", args)`，该调用通过 MCP 协议路由，在服务器不可用时降级为直接调用 `tools.py`。 |
| **Streamlit (前端)** | 面向用户 | `streamlit run knowseeker/app.py`。单页应用，包含侧边栏（文档上传 + 文档列表）和主区域（聊天面板 + 思维链跟踪 + 带引用的答案）。 |
| **design/02-knowseeker.md** | 被文档说明 | 完整的需求、架构图、LangGraph 状态图、数据结构（`AgentState` TypedDict）以及 UI 线框图。 |
