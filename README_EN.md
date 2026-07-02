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
| **Core mechanism** | Agentic RAG | Multi-Agent DAG scheduling |
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

[![View Details](https://img.shields.io/badge/-Documentation-blue)](knowseeker/README_EN.md)

After a user uploads documents, the Agent autonomously decides whether one retrieval is sufficient or if it should try a different search strategy — unlike traditional RAG's one-shot retrieval.

**Core Technology:** LangGraph state machine → analyze → retrieve → evaluate → reformulate → generate

**Course Keywords:** LLM · AI Agent · LangChain · LangGraph · MCP · RAG

```bash
# Option A
uv run streamlit run knowseeker/app.py

# Option B (access /knowseeker page via React frontend)
uv run uvicorn backend.server:app --port 8000
```

**LangGraph State Flow:**

```
analyze_question → retrieve → evaluate_results
     ↑                          │
     └──── reformulate ←────────┘  (need_more_search=True)
                         │
                         └→ generate_answer → END
```

---

## Project 2: TripMind — Multi-Agent Collaborative Travel Planning System

[![View Details](https://img.shields.io/badge/-Documentation-blue)](tripmind/README_EN.md)

Users input a destination and budget, and 6 AI Agents collaborate like a team — the dispatcher decomposes tasks, the transport Agent searches flights, the hotel Agent compares prices, the itinerary Agent plans routes, the budget Agent controls costs, and the summarizer Agent produces the final plan.

**Core Technology:** LangGraph DAG dependency scheduling → independent parallel execution → dependent sequential execution → summary delivery

**Course Keywords:** LLM · AI Agent · LangChain · LangGraph · MCP · RAG · Multi-Agent Collaboration

```bash
# Option A
uv run python -m gradio tripmind/app.py --watch-dirs .

# Option B (access /tripmind page via React frontend, with SSE streaming)
uv run uvicorn backend.server:app --port 8000
```

**Agent Execution Flow:**

```
START → orchestrator → parallel (asyncio.gather)
                        ├── 🌤️ WeatherAgent    (no dependencies)
                        ├── ✈️ TransportAgent   (no dependencies)
                        └── 🏨 HotelAgent       (no dependencies)
                      → planning (sequential)
                        ├── 🗺️ ItineraryAgent  (depends: weather+transport)
                        └── 💰 BudgetAgent     (depends: transport+hotel+itinerary)
                      → route_after_budget
                        ├── over budget → budget_adjust → summarizer → END
                        └── within budget → summarizer → END
```

**Follow-up Adjustment (UC-05):** Users can input instructions like "find a cheaper hotel" — the system automatically identifies affected Agents and only re-runs the relevant parts, preserving unaffected results.

---

## Shared Foundation

Both projects share the `common/` module:

| Module | File | Purpose |
| --- | --- | --- |
| LLM Client | `common/llm_client.py` | DeepSeek / Ollama dual-backend hot-switching, persists to `.env` |
| Embedding | `common/embedding_client.py` | Ollama local embedding model (qwen3-embedding:8b) |
| Vector Store | `common/vector_store.py` | ChromaDB operations (attractions + documents dual collections) |
| Document Loader | `common/document_loader.py` | PDF/DOCX/TXT/MD parsing and chunking |
| MCP Server | `common/mcp_server/server.py` | FastMCP server, registers 5 async tools |
| MCP Client | `common/mcp_server/client.py` | Dual-path calls (MCP protocol first, circuit-breaker fallback to tools.py) |
| MCP Tools | `common/mcp_server/tools.py` | Flight/train/hotel/weather/attraction search (reads mock JSON data) |

> Same foundation, different Agent roles and orchestration logic — transforming from a "knowledge assistant" into a "travel planner." This is the power of MCP + LangGraph architecture.

**MCP Tools Overview:**

| Tool | Parameters | Returns | Data Source |
| --- | --- | --- | --- |
| `search_flights` | departure, destination | `[{flight_no, price, airline, ...}]` | 11 route mock data |
| `search_trains` | departure, destination | `[{train_no, type, price, ...}]` | 11 route mock data |
| `search_hotels` | city, max_price | `[{name, price, rating, ...}]` | 6 cities × 5 hotels mock data |
| `get_weather` | city, days | `{daily: [...], clothing_advice}` | 6 city configs, dynamically generated |
| `search_attractions` | city, preferences | `[{name, category, ticket_price, ...}]` | 6 cities × 12 attractions mock data |

---

## Option B Architecture

```
React + shadcn/ui (Frontend, port 3000)
    │  Next.js 14 App Router
    │  4 pages: Home / KnowSeeker / TripMind / Settings
    ↕ REST API / SSE streaming
FastAPI (Backend, port 8000)
    │  12 API endpoints
    ├── knowseeker/agent.py        # RAG Q&A
    ├── knowseeker/rag_chain.py    # Document management
    ├── tripmind/orchestrator.py   # Travel planning + SSE streaming
    └── common/llm_client.py       # LLM settings management
                                   
MCP Server (port 8765, FastAPI lifecycle auto-managed)
    └── common/mcp_server/tools.py → mock_data/*.json
```

---

## API Endpoints (Option B)

| Method | Path | Function |
| --- | --- | --- |
| `POST` | `/api/chat` | KnowSeeker RAG Q&A |
| `POST` | `/api/documents/upload` | Upload document to knowledge base |
| `GET` | `/api/documents` | List indexed documents |
| `DELETE` | `/api/documents/{doc_id}` | Delete a document |
| `POST` | `/api/travel/plan` | One-shot travel planning |
| `POST` | `/api/travel/plan/stream` | SSE streaming travel planning |
| `POST` | `/api/travel/adjust` | Follow-up adjustment to travel plan |
| `GET` | `/api/models` | Get available model list |
| `GET` | `/api/settings` | Get current LLM configuration |
| `POST` | `/api/settings` | Update LLM configuration (persisted to .env) |
| `GET` | `/api/health` | Health check |

---

## Project Structure

```
ai-coursework-lab/
├── common/                        # Shared modules
│   ├── llm_client.py              # LLM client (DeepSeek/Ollama hot-switch)
│   ├── embedding_client.py        # Ollama local embedding model
│   ├── vector_store.py            # ChromaDB vector store (dual collections)
│   ├── document_loader.py         # Multi-format document parsing & chunking
│   └── mcp_server/                # MCP protocol layer
│       ├── server.py              # FastMCP server (5 tools)
│       ├── tools.py               # Tool function implementations
│       ├── client.py              # MCP client (dual-path + circuit breaker)
│       ├── init_attractions.py    # Attractions data → ChromaDB initialization
│       ├── smart_plan.py          # Third-party real data (Fliggy+Amap)
│       └── mock_data/             # Mock data
│           ├── flights.json       # 11 routes
│           ├── trains.json        # 11 routes
│           ├── hotels.json        # 6 cities × 5 hotels
│           ├── weather.json       # 6 city weather configs
│           └── attractions/       # 6 cities × 12 attractions
├── knowseeker/                    # Project 1: Knowledge Assistant
│   ├── app.py                     # Streamlit entry (Option A)
│   ├── agent.py                   # LangGraph Agentic RAG state machine
│   ├── rag_chain.py               # RAG pipeline (load→chunk→vectorize→retrieve)
│   └── README.md
├── tripmind/                      # Project 2: Travel Planner
│   ├── app.py                     # Gradio entry (Option A)
│   ├── orchestrator.py            # LangGraph orchestrator (DAG + streaming)
│   ├── prompts.py                 # 6 Agent system prompts
│   ├── types.py                   # TravelRequest / TravelState types
│   ├── agents/                    # 6 domain Agents
│   │   ├── base.py                # BaseAgent (LLM + MCP + fault tolerance)
│   │   ├── weather.py             # 🌤️ Weather Agent
│   │   ├── transport.py           # ✈️ Transport Agent
│   │   ├── hotel.py               # 🏨 Hotel Agent
│   │   ├── itinerary.py           # 🗺️ Itinerary Agent
│   │   ├── budget.py              # 💰 Budget Agent
│   │   └── summarizer.py          # 📝 Summarizer Agent
│   └── README.md
├── backend/                       # FastAPI backend (Option B)
│   └── server.py                  # 12 REST API endpoints + MCP lifecycle management
├── frontend/                      # React frontend (Option B)
│   ├── app/                       # Next.js 14 App Router
│   │   ├── page.tsx               # Home (project navigation)
│   │   ├── knowseeker/page.tsx    # Knowledge Q&A interface
│   │   ├── tripmind/page.tsx      # Travel planning interface (SSE streaming)
│   │   ├── settings/page.tsx      # LLM configuration interface
│   │   └── layout.tsx             # Global layout + sidebar
│   ├── components/ui/             # shadcn/ui component library
│   └── package.json
├── design/                        # Design documents
│   ├── 01-tech-stack.md           # Tech stack selection
│   ├── 02-knowseeker.md           # KnowSeeker requirements & design
│   ├── 03-tripmind.md             # TripMind requirements & design
│   ├── 04-tripmind-implementation.md  # TripMind implementation plan
│   └── 05-tripmind-progress.md    # TripMind progress report
├── data/
│   └── chromadb/                  # ChromaDB persistent data
├── .env.example                   # Environment variable template
├── Makefile                       # Quick launch commands
├── pyproject.toml                 # uv project config
├── CLAUDE.md                      # AI development assistant instructions
├── codemap.md                     # Repository code map
└── README.md                      # This file
```

---

## Core Design Patterns

| Pattern | Description |
| --- | --- |
| **MCP Protocol Abstraction** | All tool calls go through `client.call_tool()` → MCP Streamable HTTP first, permanent fallback to `tools.py` after 3 consecutive failures |
| **LLM Hot-switching** | `LLMClient.update()` switches between DeepSeek and Ollama at runtime, persists to `.env` |
| **Safe Execution** | Each Agent's `execute()` is wrapped by `safe_execute()`, single Agent failure doesn't block the pipeline |
| **Parallel + Sequential** | Independent Agents run via `asyncio.gather`, dependent Agents execute sequentially |
| **Agentic Decision Loop** | KnowSeeker's LangGraph state machine autonomously decides multi-round retrieval |
| **Follow-up Adjustment** | TripMind's `adjust_plan()` identifies affected Agents via keyword matching, only re-runs relevant parts |
| **SSE Streaming** | Option B backend pushes progress per-node via `graph.astream()`, frontend updates Agent status panel in real-time |
| **Dual-path LLM** | Each Agent falls back to built-in data-driven logic when LLM calls fail, ensuring availability |

---

## Who Is This For

- Students working on LLM/Agent course projects
- Developers wanting LangGraph + MCP hands-on experience
- Engineers needing Multi-Agent architecture reference
- Full-stack developers learning decoupled AI application architecture

---

## Design Documents

- [Tech Stack Selection](design/01-tech-stack.md)
- [KnowSeeker: Requirements & Design](design/02-knowseeker.md)
- [TripMind: Requirements & Design](design/03-tripmind.md)
- [TripMind Implementation Plan](design/04-tripmind-implementation.md)
- [TripMind Progress Report](design/05-tripmind-progress.md)
