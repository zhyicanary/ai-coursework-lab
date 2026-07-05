# KnowSeeker — 基于 MCP 的 Agentic RAG 知识助手

> 范式一：单 Agent 深度推理 | [返回合集首页](../README.md)

---

## 项目简介

用户上传文档后，Agent 自主理解问题、制定检索策略、多步检索、综合回答。所有推理过程可视化展示。

与传统 RAG "搜一次就回答"不同，本系统 Agent 自主判断"搜一次够不够？要不要换个角度搜？"——体现了 Agentic 决策能力。检索阶段采用 **BM25 稀疏检索 + ChromaDB 稠密向量检索**的混合策略，经 RRF 融合后再由 **Cross-Encoder 重排序**精排，显著提升召回质量。

---

## 核心特性

- 支持 PDF / DOCX / TXT / Markdown 文档上传
- Agent 自主多步检索决策（analyze → retrieve → evaluate → reformulate → generate）
- **混合检索**：BM25 稀疏检索 + ChromaDB 稠密向量检索，RRF 融合去重
- **Cross-Encoder 重排序**：sentence-transformers 逐对打分精排，可开关
- 思考链可视化（展示 Agent 推理过程 + LLM 思考内容）
- 回答附带原文引用来源
- MCP 协议标准化工具调用

---

## 快速开始

```bash
# 在项目根目录
uv sync
cp .env.example .env  # 编辑填入 DeepSeek API Key 或 Ollama 地址

# 方案A — Streamlit
uv run streamlit run knowseeker/app.py

# 方案B — FastAPI + React 前端
uv run uvicorn backend.server:app --port 8000
cd frontend && npm run dev  # 访问 /knowseeker 页面
```

---

## 技术栈

| 层次 | 选型 | 说明 |
| --- | --- | --- |
| 大模型 | DeepSeek API / Ollama | 运行时热切换，OpenAI 兼容接口 |
| 编排框架 | LangChain + LangGraph | 状态机编排 |
| 协议 | MCP (Python SDK) | 工具调用标准化 |
| 向量数据库 | ChromaDB | 稠密向量检索，零配置 |
| 稀疏检索 | rank-bm25 (Okapi) | 关键词匹配，与向量检索互补 |
| Embedding | Ollama (qwen3-embedding:8b) | 本地免费 |
| 重排序 | sentence-transformers Cross-Encoder | 二阶段精排，可开关 |
| 前端 | Streamlit / React + shadcn/ui | 双方案 |

---

## 混合检索 + 重排序流程

```
用户问题
  ├── BM25 Okapi 稀疏检索          → Top-K 候选（擅长精确术语匹配）
  ├── ChromaDB 稠密向量检索         → Top-K 候选（擅长语义理解）
  └── RRF 融合 (Reciprocal Rank Fusion)
        → 合并去重候选集
           └── Cross-Encoder 重排序  → 精排 Top-K（逐对打分）
```

BM25 擅长精确术语和专有名词匹配，稠密向量擅长理解意图和近义表达。两者通过 RRF 公式 `score = Σ 1/(k + rank_i)` 融合后，再由 Cross-Encoder 对 query-document 逐对计算相关性分数，精排出最终 Top-K 结果。

---

## LangGraph 状态流转

```
analyze_question → retrieve → evaluate_results
     ↑                          │
     └──── reformulate ←────────┘  (need_more_search=True)
                         │
                         └→ generate_answer → END
```

| 节点 | 作用 |
| --- | --- |
| `analyze_question` | LLM 分析问题复杂度，生成检索计划（关键词、策略、最大轮次 1-3） |
| `retrieve` | 混合检索：BM25 + ChromaDB → RRF 融合 → Cross-Encoder 重排序 |
| `evaluate_results` | LLM 判断检索结果是否足够回答；不够则触发下一轮 |
| `reformulate` | LLM 从不同角度生成新关键词，回到 `retrieve` 重搜 |
| `generate_answer` | 综合多轮检索结果生成回答，附带引用来源 |

---

## 设计文档

- [需求分析与软件设计](../design/02-knowseeker.md)
- [技术栈选型](../design/01-tech-stack.md)
