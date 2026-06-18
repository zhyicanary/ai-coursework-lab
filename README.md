# 智能应用系统设计 — 课程设计作品集 | [English](README_EN.md)

[![Python](https://img.shields.io/badge/Python-3.14-blue)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2-orange)](https://www.langchain.com/langgraph)
[![MCP](https://img.shields.io/badge/MCP-1.28-purple)](https://modelcontextprotocol.io/)
[![uv](https://img.shields.io/badge/uv-package%20manager-black)](https://docs.astral.sh/uv/)

> 同一个技术底座（大模型 + LangGraph + MCP），两种 AI Agent 应用范式。

---

## 为什么做这个合集

2026 年，AI Agent 正在从"调用 API"走向"自主决策 + 团队协作"。本合集通过两个完整项目，分别探索两条路径：

| | 范式一：深度推理 | 范式二：协同编排 |
|---|---|---|
| **项目** | [KnowSeeker](knowseeker/) | [TripMind](tripmind/) |
| **一句话** | 一个 Agent，多步思考 | 七个 Agent，分工协作 |
| **Agent 数量** | 1 | 7 |
| **核心机制** | Agentic RAG | Multi-Agent DAG 调度 |
| **适合场景** | 知识问答、文档分析 | 复杂任务分解、多角色协作 |
| **前端** | Streamlit | Gradio |

---

## 快速开始

```bash
git clone <this-repo>
cd ai-coursework-lab

# 安装依赖
uv sync

# 配置 API Key
cp .env.example .env
# 编辑 .env 填入 DeepSeek API Key

# 启动项目一：知识助手
uv run streamlit run knowseeker/app.py

# 启动项目二：旅游助手（支持热加载）
uv run python -m gradio tripmind/app.py --watch-dirs .

# 或使用 Makefile（更简洁）
make knowseeker
make tripmind
```

---

## 项目一：KnowSeeker — 基于 MCP 的 Agentic RAG 知识助手

[![查看详情](https://img.shields.io/badge/-查看文档-blue)](knowseeker/README.md)

用户上传文档后，Agent **自主判断**"搜一次够不够？要不要换个角度搜？"——而非传统 RAG 的一次性检索。

**核心技术：** LangGraph 状态机编排 → analyze → retrieve → evaluate → reformulate → generate

**课程关键词覆盖：** 大模型 · AI Agent · LangChain · LangGraph · MCP · RAG

```bash
uv run streamlit run knowseeker/app.py
```

---

## 项目二：TripMind — 基于多智能体协同的旅游规划系统

[![查看详情](https://img.shields.io/badge/-查看文档-blue)](tripmind/README.md)

用户输入目的地和预算，7 个 AI Agent 像团队一样协同——调度者拆解任务、交通 Agent 查航班、住宿 Agent 比价格、行程 Agent 排路线、预算 Agent 控成本、汇总 Agent 出方案。

**核心技术：** LangGraph DAG 依赖调度 → 无依赖并行执行 → 有依赖顺序执行 → 汇总交付

**课程关键词覆盖：** 大模型 · AI Agent · LangChain · LangGraph · MCP · RAG · 多智能体协同

```bash
uv run python -m gradio tripmind/app.py --watch-dirs .
```

---

## 技术底座

两个项目共享 `common/` 模块：

| 模块 | 文件 | 作用 |
| --- | --- | --- |
| LLM 客户端 | `common/llm_client.py` | DeepSeek API 封装 |
| Embedding | `common/embedding.py` | BGE 中文向量模型 |
| 向量存储 | `common/vector_store.py` | ChromaDB 操作 |
| 文档解析 | `common/document_loader.py` | PDF/DOCX/MD 解析 |
| MCP Server | `common/mcp_server/` | 工具协议标准化 |

> 同样的底座，换一套 Agent 角色和编排逻辑，就能从"知识助手"变成"旅游规划师"。这就是 MCP + LangGraph 的架构威力。

---

## 项目结构

```
ai-coursework-lab/
├── common/                    # 公共模块（两个项目共享）
│   ├── llm_client.py
│   ├── embedding.py
│   ├── vector_store.py
│   ├── document_loader.py
│   └── mcp_server/
├── knowseeker/                # 项目一：知识助手
│   ├── app.py                 # Streamlit 入口
│   ├── agent.py               # LangGraph Agent 状态机
│   ├── rag_chain.py           # RAG 链路
│   └── README.md
├── tripmind/                  # 项目二：旅游助手
│   ├── app.py                 # Gradio 入口
│   ├── orchestrator.py        # LangGraph 编排器
│   ├── agents/                # 7 个子 Agent
│   └── README.md
├── design/                    # 设计文档
│   ├── 01-tech-stack.md
│   ├── 02-knowseeker.md
│   └── 03-tripmind.md
├── .env.example
├── Makefile                   # 快捷启动命令
├── pyproject.toml
└── README.md                  # 本文件
```

---

## 适合谁看

- 正在做大模型/Agent 课设的同学
- 想了解 LangGraph + MCP 实战的开发者
- 需要 Multi-Agent 架构参考的工程师

---

## 设计文档

- [技术栈选型决策](design/01-tech-stack.md)
- [KnowSeeker 需求分析与软件设计](design/02-knowseeker.md)
- [TripMind 需求分析与软件设计](design/03-tripmind.md)
