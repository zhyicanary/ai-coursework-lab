# KCSJ Collection — 智能应用系统设计 课设作品集

## 项目概述

同一技术底座，两种 Agent 范式：

| # | 项目 | 范式 | 前端 | 入口 |
|---|------|------|------|------|
| 1 | KnowSeeker | 单 Agent 深度推理 (Agentic RAG) | Streamlit | `knowseeker/app.py` |
| 2 | TripMind | 多 Agent 协同编排 (Multi-Agent) | Gradio | `tripmind/app.py` |

两个项目共享 `common/` 模块（LLM API、向量库、MCP Server）。

## 技术栈

- **Python 3.14** + **uv** 包管理
- **LLM**: DeepSeek API（OpenAI 兼容接口）
- **Embedding**: BAAI/bge-small-zh-v1.5（本地）
- **向量库**: ChromaDB
- **编排**: LangChain + LangGraph
- **协议**: MCP (Python MCP SDK)
- **前端**: Streamlit + Gradio

## 运行

```bash
# 项目一
uv run streamlit run knowseeker/app.py

# 项目二
uv run python tripmind/app.py
```

## 开发约定

- 中文注释，Python typing 类型标注
- 配置通过 `.env` + `python-dotenv` 管理
- 每个子项目有独立的 README.md
