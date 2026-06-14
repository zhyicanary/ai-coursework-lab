# KnowSeeker — 基于 MCP 的 Agentic RAG 知识助手

> 范式一：单 Agent 深度推理 | [返回合集首页](../README.md)

---

## 项目简介

用户上传文档后，Agent 自主理解问题、制定检索策略、多步检索、综合回答。所有推理过程可视化展示。

**与传统 RAG 的区别：** 传统 RAG "搜一次就回答"，本系统 Agent 自主判断"搜一次够不够？要不要换个角度搜？"——体现了 Agentic 决策能力。

---

## 核心特性

- 支持 PDF / DOCX / TXT / Markdown 文档上传
- Agent 自主多步检索决策（analyze → retrieve → evaluate → reformulate → generate）
- 思考链可视化（展示 Agent 推理过程）
- 回答附带原文引用来源
- MCP 协议标准化工具调用

---

## 快速开始

```bash
# 在项目根目录
uv sync
cp .env.example .env  # 编辑填入 DeepSeek API Key
uv run streamlit run knowseeker/app.py
```

---

## 技术栈

| 层次 | 选型 | 说明 |
| --- | --- | --- |
| 大模型 | DeepSeek API | 高性价比，中文优秀 |
| 编排框架 | LangChain + LangGraph | 状态机编排 |
| 协议 | MCP (Python SDK) | 工具调用标准化 |
| 向量数据库 | ChromaDB | 零配置 |
| Embedding | BAAI/bge-small-zh-v1.5 | 本地免费 |
| 前端 | Streamlit | 聊天界面 |

---

## 设计文档

- [需求分析与软件设计](../design/02-knowseeker.md)
- [技术栈选型](../design/01-tech-stack.md)
