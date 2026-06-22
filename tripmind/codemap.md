# tripmind/

## 职责

TripMind 是一个基于 **LangGraph** 状态机编排和 **Gradio** 前端构建的**多智能体旅行规划系统**。它是 `ai-coursework-lab` 系列中的第二个课程项目，展示了**多智能体编排范式**：用户的旅行请求被分解为并行的和顺序的子任务，每个子任务由专门的智能体（天气、交通、酒店、行程、预算、汇总器）处理。该系统与同一技术基础下的兄弟项目 `knowseeker/`（单智能体 RAG）共享 `common/` 模块（LLM 客户端、MCP 服务器、向量存储）。

## 文件

- **`app.py`** — Gradio 前端入口点（420 行）。定义了一个包含 3 个标签页的 `gr.Blocks` UI：
  - **旅行规划 (Travel Planning)**：输入表单（目的地、天数、预算、出发地、偏好），`plan_btn` 触发 `plan_travel()`，后者通过 `run_travel_planner_stream()` 流式传输结果。展示智能体执行状态（`_format_agent_status()`）、通信日志、最终 Markdown 方案以及下载按钮。包含用于 UC-05 追问调整的**调整手风琴**（`handle_adjustment()`）。
  - **对话 (Chat)**：通过 `chat()` 使用 `llm.chat_completion()` 实现的简易聊天机器人，以 `list[dict]` 形式维护消息历史。
  - **设置 (Settings)**：LLM 后端配置（`deepseek`/`ollama`），包含 `update_settings()`、用于即时下拉切换的 `on_backend_change()`、用于异步获取模型列表的 `refresh_model_list()`，以及用于页面加载回显的 `get_config()`。
  - **MCP 生命周期**：`start_mcp_server()` 将 `common.mcp_server.server` 作为子进程启动；`stop_mcp_server()` 在关闭时终止该进程。在 Gradio 重载线程期间跳过 MCP。

- **`orchestrator.py`** — LangGraph 状态机编排器（454 行）。通过 `build_travel_graph()` 构建包含 5 个节点的 `StateGraph(TravelState)`：
  - `orchestrator_node` — 初始化，记录调度开始日志。
  - `parallel_agents` — 通过 `asyncio.gather` 并发执行 3 个独立智能体（天气、交通、酒店），每个智能体通过 `_copy_state()` 避免日志污染。
  - `planning_agents` — 顺序执行：`itinerary` → `budget`（行程依赖天气和交通；预算依赖交通、酒店和行程）。
  - `budget_adjust_node` — 当超出预算时标记 `budget_adjusted=True`。
  - `summarizer_node` — 运行汇总器智能体生成最终 Markdown。
  - **路由**：`dispatch_to_agents()`（来自编排器的条件边），`route_after_budget()`（超预算 → 调整，否则 → 汇总器）。
  - **入口点**：`run_travel_planner(request)` 使用 `graph.ainvoke()` 进行单次执行；`run_travel_planner_stream(request, progress)` 使用 `graph.astream()` 进行逐节点流式传输，配合 `_NODE_PROGRESS` 映射（0.05→0.95）更新 `gr.Progress`。
  - **追问调整 (UC-05)**：`adjust_plan(previous_state, instruction)` 通过 `_parse_adjustment()`（关键词→智能体映射）和 `_apply_adjustment()`（基于正则表达式的请求字段更新）仅重新执行受影响的智能体。`_AGENT_DEPENDENCIES` 字典中的依赖图决定了传递性的重新执行范围。

- **`prompts.py`** — 所有 6 个智能体及编排器的系统提示词（235 行）。常量包括：`ORCHESTRATOR_SYSTEM_PROMPT`、`TRANSPORT_SYSTEM_PROMPT`、`HOTEL_SYSTEM_PROMPT`、`WEATHER_SYSTEM_PROMPT`、`ITINERARY_SYSTEM_PROMPT`、`BUDGET_SYSTEM_PROMPT`、`SUMMARIZER_SYSTEM_PROMPT`。每个提示词定义了智能体的角色、任务描述、输入字段、工作流程、结构化输出格式（数据类智能体使用带模式的 JSON，汇总器使用 Markdown 模板）以及行为约束（例如酒店不超过预算的 40%，餐费 120 元/天）。

- **`types.py`** — 核心 `TypedDict` 定义（33 行）。所有智能体和编排器共享两种类型：
  - `TravelRequest`：`destination`、`days`、`budget`、`preferences`、`departure_city`。
  - `TravelState`：完整的 LangGraph 状态 — `weather_result`、`transport_result`、`hotel_result`、`itinerary_result`、`budget_result`、`final_plan`、`agent_logs`、`current_step`、`budget_adjusted`、`adjustment_history`。

- **`__init__.py`** — 空包标记文件。

- **`README.md` / `README_EN.md`** — 项目级别的中英文文档。涵盖架构、设置和使用说明。

## 设计模式

- **LangGraph StateGraph 状态机**：智能体是有向图中的节点；状态（`TravelState` TypedDict）通过带有条件路由的边流动。每次请求通过 `build_travel_graph()` → `.compile()` 重新构建图。
- **并行→顺序拆分**：独立智能体（天气、交通、酒店）通过 `asyncio.gather()` 运行；依赖型智能体（行程 → 预算 → 汇总器）顺序执行，中间状态逐步累积。
- **双路径智能体执行**：每个智能体继承 `BaseAgent`（位于 `agents/base.py`），通过 `call_mcp()`（优先使用 MCP 协议，回退到直接调用 `tools.py`）和 `call_llm()`（5 秒超时，回退到内置逻辑）执行。`safe_execute()` 包装 `execute()` 以隔离故障。
- **分派时复制**：每个子智能体接收 `_copy_state(state)`，该函数将 `agent_logs` 重置为 `[]`，防止合并结果时日志重复。
- **定向重新执行 (UC-05)**：`adjust_plan()` 使用 `_parse_adjustment()` 的关键词匹配和 `_AGENT_DEPENDENCIES` 计算最小重新执行集合，保留 `previous_state` 中未受影响的结果。
- **流式进度**：`run_travel_planner_stream()` 通过 `graph.astream()` 逐节点产出 `TravelState` 快照；`_NODE_PROGRESS` 将节点名称映射为 `(百分比, 标签)` 元组，用于 Gradio 进度条。

## 数据流与控制流

```
User form input (destination, days, budget, departure, preferences)
    │
    ▼
plan_travel() → TravelRequest TypedDict
    │
    ▼
run_travel_planner_stream(request, progress)
    │
    ▼  graph.astream(initial_state)
    │
    ├── [node: orchestrator]  →  orchestrator_node()
    │     records dispatch start log
    │
    ├── [node: parallel]      →  parallel_agents()
    │     asyncio.gather(
    │       WeatherAgent.safe_execute()    →  state["weather_result"]
    │       TransportAgent.safe_execute()  →  state["transport_result"]
    │       HotelAgent.safe_execute()      →  state["hotel_result"]
    │     )
    │
    ├── [node: planning]      →  planning_agents()
    │     sequentially:
    │       1. ItineraryAgent.safe_execute()  →  state["itinerary_result"]
    │       2. BudgetAgent.safe_execute()     →  state["budget_result"]
    │
    ├── [conditional: route_after_budget]
    │     ├── over budget  →  budget_adjust_node()  →  sets budget_adjusted=True
    │     └── within budget →  skip
    │
    ├── [node: summarizer]    →  summarizer_node()
    │     SummarizerAgent.safe_execute()  →  state["final_plan"] (Markdown)
    │
    ▼
Gradio UI: final_plan (rendered Markdown) + agent_status + agent_logs + download button
```

流中的每次 `yield` 都会实时更新 Gradio UI（Markdown 方案、智能体状态面板、通信日志、进度条）。

## 集成点

- **依赖 (`common/` 模块)**：
  - `common.llm_client.llm` — LLM 客户端单例，所有智能体通过 `BaseAgent.call_llm()` 使用，`app.py` 也用于对话和设置管理。
  - `common.mcp_server.server` — FastMCP 服务器，由 `start_mcp_server()` 作为子进程启动。提供 5 个工具（get_weather、search_flights、search_trains、search_hotels、search_attractions）供智能体使用。
  - `common.mcp_server.client` 和 `common.mcp_server.tools` — MCP 客户端包装器和直接工具函数实现；当 MCP 服务器不可用时，智能体回退使用 `tools.py`。
  - `common.mcp_server.mock_data/` — MCP 工具使用的 JSON 数据文件（flights.json、trains.json、hotels.json、weather.json、attractions/*.json）。

- **依赖 (`tripmind/agents/`)**：
  - `agents/base.py` — `BaseAgent` 类，包含 `call_mcp()`、`call_llm()`、`safe_execute()`、`add_log()`。
  - `agents/weather.py`、`agents/transport.py`、`agents/hotel.py`、`agents/itinerary.py`、`agents/budget.py`、`agents/summarizer.py` — 具体的智能体实例，以单例形式（`weather_agent`、`transport_agent` 等）在 `orchestrator.py` 中导入。

- **被消费方**：Gradio 前端（`app.launch()` 监听 `0.0.0.0:7861`）。最终的 `final_plan`（Markdown）直接渲染在 UI 中，并可作为 `.md` 文件下载。
