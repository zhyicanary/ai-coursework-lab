# 技术栈选型决策文档

> 多个项目共用同一技术底座，降低学习成本，提高代码复用率。

---

## 一、选型总览

```
┌─────────────────────────────────────────────────────────┐
│                      前端展示层                           │
│          Streamlit（项目一）+ Gradio（项目二）               │
├─────────────────────────────────────────────────────────┤
│                      编排框架层                           │
│              LangChain + LangGraph（共用）                │
├─────────────────────────────────────────────────────────┤
│                     MCP 工具协议层                        │
│              Python MCP SDK（共用）                       │
├─────────────────────────────────────────────────────────┤
│                      AI 模型层                           │
│         DeepSeek API + 本地 Embedding 模型（共用）         │
├─────────────────────────────────────────────────────────┤
│                     数据存储层                            │
│           ChromaDB（向量）+ SQLite（元数据）（共用）        │
└─────────────────────────────────────────────────────────┘
```

---

## 二、逐层选型理由

### 2.1 大模型 API：DeepSeek

| 对比维度 | DeepSeek | 阿里千问 | OpenAI | 本地 Ollama |
| --- | --- | --- | --- | --- |
| 中文能力 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 价格 | 极低 | 低 | 高 | 免费 |
| API 兼容 | OpenAI 兼容 | OpenAI 兼容 | 原生 | 原生 |
| 调用延迟 | 快 | 快 | 中 | 取决于硬件 |
| 注册门槛 | 低 | 低 | 需翻墙 | 无 |

**结论**：DeepSeek，性价比最高，中文好，API 与 OpenAI 完全兼容，代码迁移零成本。ollama方便本地调试。项目选择 ollama。

### 2.2 编排框架：LangChain + LangGraph

| 组件 | 用途 |
| --- | --- |
| **LangChain** | RAG 基础链路：文档加载 → 分割 → Embedding → 检索 → 生成 |
| **LangGraph** | Agent 状态机编排：多步检索决策、多 Agent 协作流程 |

### 2.3 向量数据库：ChromaDB

| 对比 | ChromaDB | Milvus Lite | FAISS |
| --- | --- | --- | --- |
| 安装复杂度 | `pip install` | `pip install` | `pip install` |
| 持久化 | ✅ 内置 | ✅ | ❌ 需手动 |
| API 风格 | Pythonic | 复杂 | C++ 风格 |
| 项目适用性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |

**结论**：ChromaDB，零配置，Python 原生体验，持久化开箱即用。

### 2.4 MCP 协议：Python MCP SDK

```bash
pip install mcp
```

- Anthropic 官方 Python SDK
- 用 Python 装饰器即可将任意函数暴露为 MCP Tool
- 生态最成熟，文档最全

### 2.5 前端框架

| 项目 | 框架 | 理由 |
| --- | --- | --- |
| **项目一：知识助手** | **Streamlit** | 聊天界面天然适配，st.chat_message 开箱即用 |
| **项目二：旅游助手** | **Gradio** | 支持复杂布局，Gr.Blocks 灵活排列 Agent 状态卡片 |

> 选两个不同前端也体现了"根据场景选工具"的工程判断力，答辩时是加分项。

### 2.6 Embedding 模型

| 方案 | 模型 | 维度 | 优点 |
| --- | --- | --- | --- |
| 本地（推荐） | BAAI/bge-small-zh-v1.5 | 512 | 免费、离线、中文专用 |
| API | DeepSeek Embedding | 1024 | 效果更好、但花钱 |

**结论**：本地 bge-small-zh，免费够用。后续可无缝切到 API。

### 2.7 文档解析

```bash
pip install pypdf2 python-docx unstructured markdown
```

| 库 | 支持格式 |
| --- | --- |
| PyPDF2 | PDF |
| python-docx | .docx |
| unstructured | PDF/DOCX/PPTX/HTML/Markdown 通用 |
| markdown | .md |

---

## 三、Python 环境一键安装

```bash
# 核心框架
pip install langchain langgraph langchain-community

# LLM
pip install openai  # DeepSeek 用 OpenAI 兼容接口

# 向量数据库
pip install chromadb

# Embedding
pip install sentence-transformers

# MCP
pip install mcp

# 文档解析
pip install pypdf2 python-docx unstructured markdown

# 前端（两个项目分别用）
pip install streamlit gradio

# 工具
pip install python-dotenv tiktoken
```

> 本项目使用 **uv** 管理，实际安装命令为 `uv add <package>`，详见 `pyproject.toml`。如果你没有安装 uv，请先参看 [uv 官方文档](https://uv.doczh.com/)。

---

## 四、项目目录结构

```
agent-forge/
├── design/                      # 设计文档
│   ├── 01-tech-stack.md         # 本文件
│   ├── 02-project1-rag.md       # 项目一 设计（KnowSeeker）
│   └── 03-project2-travel.md    # 项目二 & 竞赛 设计（TripMind）
│
├── common/                      # 公共模块（两项目共享）
│   ├── __init__.py
│   ├── llm_client.py            # DeepSeek API 封装
│   ├── embedding.py             # Embedding 模型
│   ├── vector_store.py          # ChromaDB 操作
│   ├── document_loader.py       # 文档解析
│   └── mcp_server/              # 共享 MCP Server
│       ├── __init__.py
│       ├── server.py            # MCP Server 主入口
│       └── tools.py             # MCP 工具定义
│
├── project1_rag/                # 项目一：智能知识助手（KnowSeeker）
│   ├── app.py                   # Streamlit 入口
│   ├── agent.py                 # LangGraph Agent
│   └── rag_chain.py             # RAG 链路
│
├── project2_travel/             # 项目二 & 竞赛：智能旅游助手（TripMind）
│   ├── app.py                   # Gradio 入口
│   ├── orchestrator.py          # LangGraph 编排器
│   └── agents/                  # 6 个子 Agent
│       ├── __init__.py
│       ├── transport.py         # 交通 Agent
│       ├── hotel.py             # 住宿 Agent
│       ├── weather.py           # 天气 Agent
│       ├── itinerary.py         # 行程 Agent
│       ├── budget.py            # 预算 Agent
│       └── summarizer.py        # 汇总 Agent
│
├── .env.example                 # 环境变量模板
├── pyproject.toml               # uv 项目配置
├── CLAUDE.md                    # 开发说明
└── README.md                    # GitHub 首页
```
