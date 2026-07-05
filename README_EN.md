# Intelligent Application System Design — Coursework Portfolio | [中文](README.md)

[![Python](https://img.shields.io/badge/Python-3.14-blue)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2-orange)](https://www.langchain.com/langgraph)
[![MCP](https://img.shields.io/badge/MCP-1.28-purple)](https://modelcontextprotocol.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.137-green)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![uv](https://img.shields.io/badge/uv-package%20manager-black)](https://docs.astral.sh/uv/)

> One technical foundation (LLM + LangGraph + MCP), two AI Agent application paradigms.

---

## Why This Portfolio

In 2026, AI Agents are evolving from "calling APIs" to "autonomous decision-making + team collaboration." This portfolio explores two paths through two complete projects:

| | Paradigm 1: Deep Reasoning | Paradigm 2: Collaborative Orchestration |
|---|---|---|
| **Project** | [KnowSeeker](knowseeker/) | [TripMind](tripmind/) |
| **In one sentence** | Single Agent, multi-step reasoning | Six Agents, collaborative teamwork |
| **Agent count** | 1 | 6 |
| **Core mechanism** | Agentic RAG + Hybrid Retrieval + Reranking | Multi-Agent DAG scheduling |
| **Use case** | Knowledge Q&A, document analysis | Complex task decomposition, multi-role collaboration |
| **Frontend (Option A)** | Streamlit | Gradio |
| **Frontend (Option B)** | React + shadcn/ui | React + shadcn/ui + SSE streaming |

---

## Dual Architecture

This project supports two frontend options, sharing the same Python backend logic:

| | Option A (Full-stack Python) | Option B (Decoupled, Recommended) |
|---|---|---|
| **Frontend** | Streamlit / Gradio | Next.js 14 + React 18 + shadcn/ui + Tailwind CSS |
| **Backend** | Python directly calls `common/` layer | FastAPI REST API + SSE streaming |
| **Ports** | 8501 (Streamlit) / 7861 (Gradio) | 3000 (frontend) + 8000 (backend) + 8765 (MCP) |
| **Features** | Rapid prototyping, concise code | Component-based UI, real-time Agent status panel, responsive layout |

---

## Quick Start

```bash
git clone <this-repo>
cd ai-coursework-lab

# Install dependencies
uv sync

# Configure API Key
cp .env.example .env
# Edit .env with your DeepSeek API Key or Ollama endpoint
```

### Option A — Full-stack Python (Quick Start)

```bash
# Launch Project 1: Knowledge Assistant (Streamlit)
uv run streamlit run knowseeker/app.py

# Launch Project 2: Travel Planner (Gradio, with hot reload)
uv run python -m gradio tripmind/app.py --watch-dirs .

# Or use Makefile
make knowseeker
make tripmind
```

### Option B — Decoupled Architecture (Full Experience)

```bash
# 1. Start backend API (auto-manages MCP Server lifecycle)
uv run uvicorn backend.server:app --host 0.0.0.0 --port 8000

# 2. Start frontend
cd frontend
npm install   # Required on first run
npm run dev   # Visit http://localhost:3000
```

> Option B backend automatically starts the MCP Server subprocess (port 8765) — no manual management needed.

---

## Project 1: KnowSeeker — MCP-based Agentic RAG Knowledge Assistant

[![View Details](https://img.shields.io/badge/-Documentation-blue)](knowseeker/README.md)

After a user uploads documents, the Agent autonomously decides whether one retrieval is sufficient or if it should try a different search strategy. The retrieval stage uses a **hybrid approach**: BM25 sparse retrieval + ChromaDB dense vector retrieval, fused via RRF, then refined by **Cross-Encoder reranking**.

**Core Technology:** LangGraph state machine → analyze → retrieve (hybrid + RRF + reranking) → evaluate → reformulate → generate

**Course Keywords:** LLM · AI Agent · LangChain · LangGraph · MCP · RAG · Hybrid Retrieval · Reranking

---

## Project 2: TripMind — Multi-Agent Collaborative Travel Planning System

[![View Details](https://img.shields.io/badge/-Documentation-blue)](tripmind/README.md)

Users input a destination and budget, and 6 AI Agents collaborate like a team — the dispatcher decomposes tasks, the transport Agent searches flights, the hotel Agent compares prices, the itinerary Agent plans routes, the budget Agent controls costs, and the summarizer Agent produces the final plan.

**Core Technology:** LangGraph DAG dependency scheduling → independent parallel execution → dependent sequential execution → summary delivery

**Course Keywords:** LLM · AI Agent · LangChain · LangGraph · MCP · RAG · Multi-Agent Collaboration

---

## Shared Foundation

Both projects share the `common/` module, built on a **three-tier architecture** (inference + vectorization + reranking), each tier independently configurable and hot-swappable:

| Module | File | Purpose |
| --- | --- | --- |
| App Context | `common/context.py` | Global service context, manages LLM / Embedding / Reranker / BM25 / ChromaDB / MCP instances |
| LLM Client | `common/llm_client.py` | Inference tier: DeepSeek / Ollama dual-backend hot-switching |
| Embedding | `common/embedding_client.py` | Vectorization tier: Ollama local embedding model |
| Reranker | `common/reranker.py` | Reranking tier: sentence-transformers Cross-Encoder, toggleable |
| BM25 Store | `common/bm25_store.py` | Sparse retrieval: Okapi BM25 algorithm |
| Vector Store | `common/vector_store.py` | ChromaDB operations (attractions + documents dual collections) |
| Document Loader | `common/document_loader.py` | PDF/DOCX/TXT/MD parsing and chunking |
| MCP Server | `common/mcp_server/server.py` | FastMCP server, registers 5 async tools |
| MCP Client | `common/mcp_server/client.py` | Dual-path calls (MCP protocol first, circuit-breaker fallback) |
| MCP Tools | `common/mcp_server/tools.py` | Flight/train/hotel/weather/attraction search |

**MCP Tools Overview:**

| Tool | Parameters | Returns | Data Source |
| --- | --- | --- | --- |
| `search_flights` | departure, destination | `[{flight_no, price, airline, ...}]` | 11 route mock data |
| `search_trains` | departure, destination | `[{train_no, type, price, ...}]` | 11 route mock data |
| `search_hotels` | city, max_price | `[{name, price, rating, ...}]` | 6 cities × 5 hotels mock data |
| `get_weather` | city, days | `{daily: [...], clothing_advice}` | 6 city configs, dynamically generated |
| `search_attractions` | city, preferences | `[{name, category, ticket_price, ...}]` | 6 cities × 12 attractions mock data |

> `get_weather` and `search_attractions` support real APIs: set `WEATHER_API_KEY` (QWeather) and `AMAP_API_KEY` (Amap) in `.env`.

---

## Option B Architecture

```
React + shadcn/ui (Frontend, port 3000)
    │  Next.js 14 App Router
    │  4 pages: Home / KnowSeeker / TripMind / Settings
    ↕ REST API / SSE streaming
FastAPI (Backend, port 8000)
    │  13 API endpoints
    ├── knowseeker/agent.py        # RAG Q&A (async task)
    ├── knowseeker/rag_chain.py    # Document management + hybrid retrieval
    ├── tripmind/orchestrator.py   # Travel planning + SSE streaming
    └── common/context.py          # Three-tier config management

MCP Server (port 8765, FastAPI lifecycle auto-managed)
    └── common/mcp_server/tools.py → mock_data/*.json
```

---

## API Endpoints (Option B)

| Method | Path | Function |
| --- | --- | --- |
| `POST` | `/api/chat` | Create RAG Q&A async task, returns `taskId` |
| `GET` | `/api/chat/{task_id}` | Poll task status and results |
| `POST` | `/api/documents/upload` | Upload document to knowledge base |
| `GET` | `/api/documents` | List indexed documents |
| `DELETE` | `/api/documents/{doc_id}` | Delete a document |
| `POST` | `/api/travel/plan` | One-shot travel planning |
| `POST` | `/api/travel/plan/stream` | SSE streaming travel planning |
| `POST` | `/api/travel/adjust` | Follow-up adjustment to travel plan |
| `GET` | `/api/models` | Get available model list |
| `GET` | `/api/settings` | Get three-tier config (inference + vectorization + reranking) |
| `POST` | `/api/settings` | Update three-tier config (persisted to .env) |
| `GET` | `/api/health` | Health check |

---

## Core Design Patterns

| Pattern | Description |
| --- | --- |
| **App Context** | `common/context.py` centralizes all service instances, accessed via `get_context()` |
| **Three-tier Config** | Inference (LLM), Vectorization (Embedding), Reranking tiers independently configurable and hot-swappable |
| **Hybrid Retrieval + RRF** | BM25 sparse + ChromaDB dense retrieval in parallel, fused via Reciprocal Rank Fusion |
| **Cross-Encoder Reranking** | Fused candidates refined by sentence-transformers Cross-Encoder |
| **MCP Protocol Abstraction** | MCP Streamable HTTP first, permanent fallback to `tools.py` after 3 consecutive failures |
| **LLM Hot-switching** | Runtime switching between DeepSeek and Ollama, persisted to `.env` |
| **Safe Execution** | Each Agent's `execute()` wrapped by `safe_execute()`, single failure doesn't block pipeline |
| **Parallel + Sequential** | Independent Agents run via `asyncio.gather`, dependent Agents execute sequentially |
| **Agentic Decision Loop** | KnowSeeker's LangGraph state machine autonomously decides multi-round retrieval |
| **Follow-up Adjustment** | TripMind's `adjust_plan()` identifies affected Agents via keyword matching |
| **SSE Streaming** | Backend pushes progress per-node via `graph.astream()` |
| **Dual-path LLM** | Each Agent falls back to built-in data-driven logic when LLM calls fail |
| **Async RAG Task** | `/api/chat` returns `taskId`, frontend polls `/api/chat/{task_id}` for results |

---

## Design Documents

- [Tech Stack Selection](design/01-tech-stack.md)
- [KnowSeeker: Requirements & Design](design/02-knowseeker.md)
- [TripMind: Requirements & Design](design/03-tripmind.md)
- [TripMind Implementation Plan](design/04-tripmind-implementation.md)
- [TripMind Progress Report](design/05-tripmind-progress.md)
