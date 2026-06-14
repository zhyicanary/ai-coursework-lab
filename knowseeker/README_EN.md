# KnowSeeker — MCP-based Agentic RAG Knowledge Assistant

> Paradigm 1: Single Agent Deep Reasoning | [Back to Home](../README_EN.md)

---

## Introduction

After a user uploads documents, the Agent autonomously understands questions, formulates retrieval strategies, performs multi-step retrieval, and synthesizes answers. All reasoning processes are visualized.

**vs. Traditional RAG:** Traditional RAG "retrieves once and answers." This system's Agent autonomously decides whether one retrieval is sufficient or if it should try a different search strategy — demonstrating Agentic decision-making capability.

---

## Core Features

- Supports PDF / DOCX / TXT / Markdown document uploads
- Agent autonomous multi-step retrieval decisions (analyze → retrieve → evaluate → reformulate → generate)
- Chain-of-thought visualization (displays Agent reasoning process)
- Answers with source citations
- MCP protocol standardized tool invocation

---

## Quick Start

```bash
# From the project root
uv sync
cp .env.example .env  # Edit and enter your DeepSeek API Key
uv run streamlit run knowseeker/app.py
```

---

## Tech Stack

| Layer | Choice | Description |
| --- | --- | --- |
| LLM | DeepSeek API | Cost-effective, excellent Chinese support |
| Orchestration | LangChain + LangGraph | State machine orchestration |
| Protocol | MCP (Python SDK) | Tool invocation standardization |
| Vector DB | ChromaDB | Zero-config |
| Embedding | BAAI/bge-small-zh-v1.5 | Local, free |
| Frontend | Streamlit | Chat interface |

---

## Design Documents

- [Requirements & Design](../design/02-knowseeker.md)
- [Tech Stack Selection](../design/01-tech-stack.md)
