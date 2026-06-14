# 课设1：基于 MCP 的 Agentic RAG 智能知识助手

## 需求分析与软件设计文档

---

## 一、项目概述

### 1.1 项目名称
**KnowSeeker** — 基于 MCP 协议的 Agentic RAG 智能知识助手

### 1.2 一句话描述
用户上传文档后，Agent 自主理解问题、制定检索策略、多步检索、综合回答，所有推理过程可视化。

### 1.3 核心价值
传统 RAG 是"一次性检索"（搜一次就直接回答），本系统是 **Agentic RAG**（Agent 自主决定搜几次、怎么搜），配合 MCP 协议标准化工具调用，体现 2026 年最热门的技术方向。

---

## 二、需求分析

### 2.1 用户角色

| 角色 | 描述 |
|------|------|
| **知识消费者** | 上传文档，提问，获取精准回答 |

（课设规模，单角色足够）

### 2.2 功能需求（用例）

```
┌──────────────────────────────────────────────────┐
│                   KnowSeeker                      │
├──────────────────────────────────────────────────┤
│  UC-01  上传文档                                   │
│         └─ 支持 PDF / DOCX / TXT / MD             │
│         └─ 文档自动分段、向量化、入库               │
│                                                   │
│  UC-02  智能问答                                   │
│         └─ 用户自然语言提问                         │
│         └─ Agent 自主制定检索计划                   │
│         └─ 多步检索 + 重排序                        │
│         └─ 生成带来源引用的回答                     │
│                                                   │
│  UC-03  推理过程可视化                              │
│         └─ 展示 Agent 的思考链（Thought Process）   │
│         └─ 展示每轮检索的关键词和召回结果数          │
│         └─ 展示最终回答引用的具体文档片段            │
│                                                   │
│  UC-04  知识库管理                                  │
│         └─ 查看已上传文档列表                       │
│         └─ 删除指定文档                             │
└──────────────────────────────────────────────────┘
```

### 2.3 非功能需求

| 需求 | 指标 |
| --- | --- |
| 性能 | 单次问答 < 15 秒 |
| 可用性 | Streamlit 单页 Web 应用 |
| 准确性 | 回答需附带原文引用 |
| 可扩展 | MCP 协议标准化，工具可插拔 |

### 2.4 Agentic 决策规则设计

Agent 在以下情况需要**自主决策**：

```
用户提问 → Agent 分析
              │
              ├── 简单事实问题？
              │     └── 单轮检索 → 直接回答
              │
              ├── 需要对比/多角度？
              │     └── 拆成多个子问题 → 多轮检索 → 综合
              │
              ├── 第一轮检索结果不够？
              │     └── 自动换关键词重搜 → 合并结果
              │
              └── 文档中没有相关信息？
                    └── 诚实回答"未找到" + 建议
```

---

## 三、技术架构

### 3.1 系统架构图

```
┌────────────────────────────────────────────────────────┐
│                    Streamlit 前端                        │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │ 文档上传  │  │  对话面板     │  │  思考链可视化    │   │
│  └──────────┘  └──────────────┘  └─────────────────┘   │
├────────────────────────────────────────────────────────┤
│                 LangGraph Agent 编排层                   │
│  ┌───────────────────────────────────────────────────┐ │
│  │              Agentic RAG 状态机                     │ │
│  │                                                    │ │
│  │  analyze ──→ retrieve ──→ evaluate ──→ generate    │ │
│  │     ↑                        │          │          │ │
│  │     └────── reformulate ←────┘          │          │ │
│  │                                         ↓          │ │
│  │                                      answer        │ │
│  └───────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────┤
│                   MCP 协议工具层                         │
│  ┌──────────┐  ┌───────────┐  ┌──────────────────┐    │
│  │ 向量检索  │  │ 文档列表   │  │  关键词检索(备)   │    │
│  └──────────┘  └───────────┘  └──────────────────┘    │
├────────────────────────────────────────────────────────┤
│                     数据层                              │
│  ┌──────────┐  ┌───────────┐  ┌──────────────────┐    │
│  │ ChromaDB │  │ 文档元数据 │  │  本地 Embedding   │    │
│  └──────────┘  └───────────┘  └──────────────────┘    │
└────────────────────────────────────────────────────────┘
```

### 3.2 LangGraph 状态图设计

```
                    ┌──────────┐
                    │  START   │
                    └────┬─────┘
                         ↓
                   ┌───────────┐
                   │  analyze  │  分析问题，生成检索计划
                   │  _question│  → 提取关键词、判断复杂度
                   └─────┬─────┘
                         ↓
                   ┌───────────┐
              ┌──→│ retrieve  │  调用 MCP 工具执行检索
              │   │ _search   │  → 返回 top-K 文档片段
              │   └─────┬─────┘
              │         ↓
              │   ┌───────────┐
              │   │ evaluate  │  评估检索结果质量
              │   │ _results  │  → 是否足够回答？
              │   └─────┬─────┘
              │         │
              │    ┌────┴─────┐
              │    │ 够？      │
              │    └──────────┘
              │    │ yes      │ no
              │    ↓          ↓
              │  ┌──────┐  ┌─────────────┐
              │  │generate│  │ reformulate │ 重新组织查询
              │  └──┬───┘  └──────┬──────┘
              │     │             │
              │     │             └──→ 回到 retrieve
              │     ↓
              │  ┌───────────┐
              │  │  answer   │  生成最终回答 + 引用
              │  └─────┬─────┘
              │        ↓
              │   ┌──────────┐
              └───│   END    │
                  └──────────┘
```

### 3.3 核心数据结构

```python
# Agent 状态（在 LangGraph 节点间流转）
class AgentState(TypedDict):
    question: str              # 用户问题
    search_plan: dict          # 检索计划 {keywords, strategy, num_rounds}
    search_history: list       # 每轮检索记录 [{round, query, results_count, top_chunks}]
    need_more_search: bool     # 是否需要继续检索
    final_context: str         # 最终用于生成的上下文（多轮结果合并后）
    answer: str                # 最终回答
    citations: list            # 引用来源 [{chunk_text, doc_name, page}]
    thinking_trace: list       # 推理过程（供前端可视化）
```

---

## 四、模块设计

### 4.1 模块清单

| 模块 | 文件 | 职责 |
|------|------|------|
| 文档加载器 | `common/document_loader.py` | 多格式文档解析、分段 |
| 向量存储 | `common/vector_store.py` | ChromaDB CRUD、相似检索 |
| MCP Server | `common/mcp_server/server.py` | 暴露向量检索为 MCP Tool |
| LLM 客户端 | `common/llm_client.py` | DeepSeek API 封装 |
| RAG 链 | `project1_rag/rag_chain.py` | 基础 RAG 链路 |
| Agent 编排 | `project1_rag/agent.py` | LangGraph 状态机 |
| 前端 | `project1_rag/app.py` | Streamlit 界面 |

### 4.2 关键接口

#### MCP Server 暴露的工具

```python
@server.tool()
async def search_knowledge_base(
    query: str,
    top_k: int = 5,
    filter_doc: str | None = None
) -> list[dict]:
    """在知识库中搜索相关文档片段。

    Args:
        query: 搜索查询
        top_k: 返回结果数
        filter_doc: 可选，限定搜索特定文档

    Returns:
        [{text, source, page, score}, ...]
    """

@server.tool()
async def list_documents() -> list[dict]:
    """列出知识库中所有文档。"""

@server.tool()
async def delete_document(doc_name: str) -> bool:
    """从知识库中删除指定文档。"""
```

#### LangGraph Agent 核心节点

```python
def analyze_question(state: AgentState) -> AgentState:
    """分析问题，生成检索计划"""

def retrieve(state: AgentState) -> AgentState:
    """执行检索（通过 MCP Client 调用 MCP Tool）"""

def evaluate_results(state: AgentState) -> AgentState:
    """评估结果质量，决定是否继续"""

def reformulate(state: AgentState) -> AgentState:
    """重新组织查询关键词"""

def generate_answer(state: AgentState) -> AgentState:
    """综合上下文生成最终回答 + 引用"""
```

---

## 五、数据流

### 5.1 文档入库流程

```
用户上传文件
    │
    ▼
document_loader.load(file)
    ├── 识别格式 (PDF/DOCX/TXT/MD)
    ├── 提取文本
    └── 分段 (chunk_size=500, overlap=50)
    │
    ▼
embedding_model.encode(chunks)
    │
    ▼
chromadb.add(chunks, embeddings, metadata)
    │
    ▼
返回: "已入库 N 个文档片段"
```

### 5.2 问答流程（Agentic）

```
用户: "这份合同里的违约责任条款和行业标准相比有什么不足？"
    │
    ▼
[analyze] LLM 分析问题
    └→ 计划:
       Round 1: 搜索"违约责任条款"
       Round 2: 搜索"行业标准 违约责任"
       Round 3: 对比两个结果
    │
    ▼
[retrieve] Round 1 → MCP Tool: search("违约责任条款", top_k=5)
    └→ 找回 5 个片段
    │
    ▼
[evaluate] LLM 评估: "找到了合同相关内容，但缺少行业标准参考"
    └→ need_more_search = True
    │
    ▼
[reformulate] LLM 重构: "违约责任 行业标准 法律规定"
    │
    ▼
[retrieve] Round 2 → MCP Tool: search("违约责任 行业标准 法律规定", top_k=5)
    └→ 找回 5 个片段（含行业通用标准）
    │
    ▼
[evaluate] LLM 评估: "现在可以对比分析了"
    └→ need_more_search = False
    │
    ▼
[generate] LLM 综合两轮结果
    └→ 生成对比分析 + 改进建议
    │
    ▼
[answer] 展示: 回答 + 引用来源 + 思考链
```

---

## 六、前端界面设计

### 6.1 Streamlit 布局

```
┌─────────────────────────────────────────────────┐
│  🤖 KnowSeeker — Agentic RAG 知识助手            │
├──────────────┬──────────────────────────────────┤
│              │                                  │
│  📁 文档管理  │  💬 对话区                        │
│              │                                  │
│  [上传文件]   │  用户: 这份合同有问题吗？          │
│              │                                  │
│  📄 合同.pdf  │  🧠 思考过程:                     │
│  📄 标准.docx │  ├ 分析: 需要从2个角度检索         │
│              │  ├ 检索1: "违约责任条款"(5条)      │
│              │  ├ 评估: 需补充行业标准             │
│              │  ├ 检索2: "行业标准"(3条)          │
│              │  └ 综合生成回答                    │
│              │                                  │
│              │  🤖 回答:                         │
│              │  对比发现以下不足...               │
│              │  📎 来源: 合同.pdf 第3段,          │
│              │     标准.docx 第7段               │
│              │                                  │
│              │  [输入框]              [发送]     │
└──────────────┴──────────────────────────────────┘
```

### 6.2 关键交互

- **文档上传**：侧边栏，上传后自动入库，显示进度条
- **思考链折叠**：每次问答自动展开 Agent 的推理步骤，可折叠
- **引用高亮**：回答中的引用可点击，弹出原文片段

---

## 七、课程要求覆盖检查

| 课程关键词 | 覆盖位置 |
|-----------|---------|
| ✅ 大模型 | DeepSeek API 调用 |
| ✅ AI Agent | LangGraph 自主检索决策 Agent |
| ✅ LangChain | RAG 基础链路（加载-分割-检索-生成）|
| ✅ LangGraph | Agent 状态机编排（analyze-retrieve-evaluate-reformulate-generate）|
| ✅ MCP | 自建 MCP Server，暴露向量检索工具 |
| ✅ RAG | 文档向量化 + 检索增强生成 |
| ✅ Skills | MCP Server 作为可复用的 Skill 工具集 |
