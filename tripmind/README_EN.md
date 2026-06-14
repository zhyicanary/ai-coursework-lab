# TripMind — Multi-Agent Collaborative Travel Planning System

> Paradigm 2: Multi-Agent Collaborative Orchestration | [Back to Home](../README_EN.md)

---

## Introduction

Users input a destination, duration, and budget. 7 AI Agents automatically collaborate (searching transportation, comparing accommodations, planning itineraries, checking weather, calculating budgets). The Agent collaboration process is displayed in real-time, ultimately generating a complete travel plan.

**Core Innovation:** Rather than a single AI handling everything, multiple specialized Agents collaborate like a team — with clear responsibilities, dependencies, and communication.

---

## Agent Team

| Agent | Responsibility | Dependencies |
| --- | --- | --- |
| Dispatcher Agent | Understands requirements, decomposes tasks, schedules execution | None |
| Transportation Agent | Queries flights/high-speed rail | None |
| Accommodation Agent | Recommends hotels | None |
| Weather Agent | Queries weather forecasts | None |
| Itinerary Agent | Plans daily schedules | Weather + Transportation |
| Budget Agent | Summarizes costs, validates budget | Transportation + Accommodation + Itinerary |
| Summary Agent | Generates final plan | All |

---

## Quick Start

```bash
# From the project root
uv sync
cp .env.example .env  # Edit and enter your DeepSeek API Key
uv run python tripmind/app.py
```

---

## Tech Stack

| Layer | Choice | Description |
| --- | --- | --- |
| LLM | DeepSeek API | Powers all Agents |
| Orchestration | LangChain + LangGraph | DAG dependency scheduling |
| Protocol | MCP (Python SDK) | Tool invocation standardization |
| Vector DB | ChromaDB | Scenic spot knowledge base |
| Frontend | Gradio | Multi-component complex layout |
| Package Manager | uv | Python package management |

---

## Design Documents

- [Requirements & Design](../design/03-tripmind.md)
- [Tech Stack Selection](../design/01-tech-stack.md)
