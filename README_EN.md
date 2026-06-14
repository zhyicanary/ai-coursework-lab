# Intelligent Application System Design — Coursework Portfolio | [中文](README.md)

[![Python](https://img.shields.io/badge/Python-3.14-blue)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2-orange)](https://www.langchain.com/langgraph)
[![MCP](https://img.shields.io/badge/MCP-1.28-purple)](https://modelcontextprotocol.io/)
[![uv](https://img.shields.io/badge/uv-package%20manager-black)](https://docs.astral.sh/uv/)

> One technical foundation (LLM + LangGraph + MCP), two AI Agent application paradigms.

---

## Overview

Two complete projects exploring distinct AI Agent paradigms:

| | Paradigm 1: Deep Reasoning | Paradigm 2: Collaborative Orchestration |
|---|---|---|
| **Project** | [KnowSeeker](knowseeker/) | [TripMind](tripmind/) |
| **In one sentence** | Single Agent, multi-step reasoning | Seven Agents, collaborative teamwork |
| **Agent count** | 1 | 7 |
| **Core mechanism** | Agentic RAG | Multi-Agent DAG scheduling |
| **Use case** | Knowledge Q&A, document analysis | Complex task decomposition, multi-role collaboration |
| **Frontend** | Streamlit | Gradio |

---

## Quick Start

```bash
git clone https://github.com/zhyicanary/ai-coursework-lab.git
cd ai-coursework-lab

# Install dependencies
uv sync

# Configure API Key
cp .env.example .env
# Edit .env and enter your DeepSeek API Key

# Launch Project 1: Knowledge Assistant
uv run streamlit run knowseeker/app.py

# Launch Project 2: Travel Planner
uv run python tripmind/app.py
```

---

## Project 1: KnowSeeker — MCP-based Agentic RAG Knowledge Assistant

[![View Details](https://img.shields.io/badge/-Documentation-blue)](knowseeker/README_EN.md)

After a user uploads documents, the Agent autonomously decides whether one retrieval is sufficient or if it should try a different search strategy — unlike traditional RAG's one-shot retrieval.

**Core Technology:** LangGraph state machine orchestration → analyze → retrieve → evaluate → reformulate → generate

```bash
uv run streamlit run knowseeker/app.py
```

---

## Project 2: TripMind — Multi-Agent Collaborative Travel Planning System

[![View Details](https://img.shields.io/badge/-Documentation-blue)](tripmind/README_EN.md)

Users input a destination and budget, and 7 AI Agents collaborate like a team — the dispatcher decomposes tasks, the transportation Agent searches flights, the accommodation Agent compares prices, the itinerary Agent plans routes, the budget Agent controls costs, and the summary Agent produces the final plan.

**Core Technology:** LangGraph DAG dependency scheduling → independent parallel execution → dependent sequential execution → summary delivery

```bash
uv run python tripmind/app.py
```

---

## Shared Foundation

Both projects share the `common/` module:

| Module | File | Purpose |
| --- | --- | --- |
| LLM Client | `common/llm_client.py` | DeepSeek API wrapper |
| Embedding | `common/embedding.py` | BGE Chinese vector model |
| Vector Store | `common/vector_store.py` | ChromaDB operations |
| Document Loader | `common/document_loader.py` | PDF/DOCX/MD parsing |
| MCP Server | `common/mcp_server/` | Tool protocol standardization |

> Same foundation, different Agent roles and orchestration logic — transforming from a "knowledge assistant" into a "travel planner." This is the power of MCP + LangGraph architecture.

---

## Project Structure

```
ai-coursework-lab/
├── common/                    # Shared modules
│   ├── llm_client.py
│   ├── embedding.py
│   ├── vector_store.py
│   ├── document_loader.py
│   └── mcp_server/
├── knowseeker/                # Project 1: Knowledge Assistant
│   ├── app.py                 # Streamlit entry point
│   ├── agent.py               # LangGraph Agent state machine
│   ├── rag_chain.py           # RAG pipeline
│   └── README.md
├── tripmind/                  # Project 2: Travel Planner
│   ├── app.py                 # Gradio entry point
│   ├── orchestrator.py        # LangGraph orchestrator
│   ├── agents/                # 7 sub-Agents
│   └── README.md
├── design/                    # Design documents
│   ├── 01-tech-stack.md
│   ├── 02-knowseeker.md
│   └── 03-tripmind.md
├── .env.example
├── pyproject.toml
└── README.md
```

---

## Design Documents

- [Tech Stack Selection](design/01-tech-stack.md)
- [KnowSeeker: Requirements & Design](design/02-knowseeker.md)
- [TripMind: Requirements & Design](design/03-tripmind.md)
