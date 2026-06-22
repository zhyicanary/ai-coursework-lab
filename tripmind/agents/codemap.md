# tripmind/agents/

## 职责

Agent 层实现了 6 个专业旅行规划 Agent 加一个抽象基类。每个 Agent 封装一个领域（天气、交通、住宿、行程、预算、汇总），并遵循一致的双路径执行模式：通过 MCP 工具调用收集数据，然后通过 LLM 增强/分析，且任意路径失败时均有内置的回退逻辑。编排器（`tripmind/orchestrator.py`）通过 `asyncio.gather`（并行）或顺序调用来分发这些 Agent，`BaseAgent.safe_execute()` 确保单个 Agent 的失败不会阻塞整个流水线。

## 文件

- **`__init__.py`** — 模块导出。导入并重新导出所有 6 个单例 Agent 实例：`transport_agent`、`hotel_agent`、`weather_agent`、`itinerary_agent`、`budget_agent`、`summarizer_agent`。

- **`base.py`** — `BaseAgent`（抽象类，`ABC`）。类级别字段：`name: str`、`emoji: str`、`system_prompt: str`（由子类设置）。关键方法：
  - `async execute(self, state: dict) -> dict` — 抽象方法；子类在此实现领域逻辑。
  - `async call_llm(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 2000, timeout: float = 5.0) -> str` — 封装 `common.llm_client.llm.chat_completion()` 并配合 `asyncio.wait_for(timeout)`；超时时抛出 `asyncio.TimeoutError`。
  - `async call_mcp(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any` — 封装 `common.mcp_server.client.call_tool()`。客户端本身实现了 MCP 优先并带有回退机制；此方法只是一个轻量透传。
  - `add_log(self, state: dict, message: str, status: str = "done")` — 将 `{"step": f"{emoji}{name}"`, `"message": ...`, `"status": ...}` 追加到 `state["agent_logs"]`。
  - `build_llm_messages(self, user_content: str) -> list[dict]` — 构造 `[{"role": "system", "content": self.system_prompt}, {"role": "user", "content": user_content}]`。
  - `async safe_execute(self, state: dict) -> dict` — 将 `self.execute()` 包裹在 try/except 中；失败时通过 `add_log(state, ..., "error")` 记录错误，并写入 `state[f"{result_key}_result"] = {"error": ..., "source": ...}` 以防止下游键错误。
  - `_result_key(self) -> str` — 将中文 `self.name` 映射为英文状态键前缀（例如 `"天气"` → `"weather"`）。

- **`weather.py`** — `WeatherAgent(BaseAgent)`。`name = "天气"`，`emoji = "🌤️"`，`system_prompt = WEATHER_SYSTEM_PROMPT`。调用 MCP `get_weather(city, days)`。LLM 路径：发送城市、天数及原始每日数据，要求进行分析；结果存储 `{**weather_data, "city": ..., "llm_analysis": ...}`。LLM 失败时，展开 `weather_data` 但不包含 `llm_analysis`。设置 `state["weather_result"]`。从每日天气状况构建精简的日志摘要。

- **`transport.py`** — `TransportAgent(BaseAgent)`。`name = "交通"`，`emoji = "✈️"`，`system_prompt = TRANSPORT_SYSTEM_PROMPT`。调用 MCP `search_flights(departure, destination)` 和 `search_trains(departure, destination)`。使用 `"type"` 区分器（`"航班"` / 来自火车的 `"type"` 字段）合并所有选项。按 `price` 升序排序；选取最便宜的作为 `recommended`；`total_cost_round = price * 2`。LLM 路径：发送出发地/目的地/天数/预算及原始航班/火车数据；失败时回退到内置建议字符串。设置 `state["transport_result"]`。

- **`hotel.py`** — `HotelAgent(BaseAgent)`。`name = "住宿"`，`emoji = "🏨"`，`system_prompt = HOTEL_SYSTEM_PROMPT`。调用 MCP `search_hotels(city, max_price)`，其中 `max_price = (budget * 0.4) / days`（预算的 40% 上限）。按 `max_price` 筛选，选取评分最高的作为 `recommended`；`total_cost = price * days`。LLM 路径：发送目的地/天数/预算/偏好及酒店列表；失败时回退到内置建议。设置 `state["hotel_result"]`。

- **`itinerary.py`** — `ItineraryAgent(BaseAgent)`。`name = "行程"`，`emoji = "🗺️"`，`system_prompt = ITINERARY_SYSTEM_PROMPT`。依赖于 `state["weather_result"]` 和 `state["transport_result"]`（读取它们作为上下文，但不强制要求）。调用 MCP `search_attractions(city, preferences, top_k=12)`。LLM 路径：发送目的地/天数/偏好 + 天气/交通上下文 + 景点列表；期望返回包含 `daily_plans` 数组的 JSON 输出。辅助方法：
  - `_extract_daily_plans(llm_text: str) -> list` — 优先尝试正则 `\`\`\`(?:json)?\s*(\{.*?\})\s*\`\`\``，然后直接使用 `json.loads`；返回 `data["daily_plans"]` 或 `[]`。
  - `_calc_ticket_cost(llm_text, attractions) -> float` — 从提取的计划中累加 `ticket_cost`；回退：`sum(a["ticket_price"] for a in attractions[:2]) * 3`。
  - `_build_fallback_plan(request, weather, attractions) -> dict` — LLM 不可用时的路径：遍历天数，根据天气选择景点（雨天选择室内/博物馆类别，否则每日取两个切片），构建包含上午/下午/晚上时段的 `daily_plans`。
  - 设置 `state["itinerary_result"]`。

- **`budget.py`** — `BudgetAgent(BaseAgent)`。`name = "预算"`，`emoji = "💰"`，`system_prompt = BUDGET_SYSTEM_PROMPT`。从 state 中读取 `transport_result`、`hotel_result`、`itinerary_result`。计算：`transport_cost = total_cost_round`、`hotel_cost = total_cost`、`ticket_cost = total_ticket_cost`、`meal_cost = days * 120`、`other_cost = days * 50`。判断 `is_over_budget` 并生成内联 `suggestions`（例如若酒店费用超过预算 30%，则提示"可选择价格更低的酒店"）。LLM 路径：发送明细 + 总计 + 建议以进行更丰富的分析；失败时保留内置建议逻辑。设置 `state["budget_result"]`。

- **`summarizer.py`** — `SummarizerAgent(BaseAgent)`。`name = "汇总"`，`emoji = "📝"`，`system_prompt = SUMMARIZER_SYSTEM_PROMPT`。从 state 中读取所有 5 个结果键。LLM 路径：调用 `_build_user_message(...)` 构建包含所有 Agent 数据及 Markdown 模板的详细提示；LLM 返回完整 Markdown → 存入 `state["final_plan"]`。回退路径：`_build_fallback_plan(...)` — 组装包含 6 个部分的 Markdown（预算概览 / 行程总览 table / 交通安排 / 住宿推荐 / 每日详细行程 / 费用明细 + 调整建议 / 天气提醒），以 `*方案由 TripMind 多 Agent 协同生成*` 结尾。

## 设计模式

- **模板方法 / 继承**：所有 6 个 Agent 均继承 `BaseAgent`，仅需实现 `async execute(self, state: dict) -> dict`。基类提供共享基础设施（`call_llm`、`call_mcp`、`add_log`、`safe_execute`），子类可自由调用。在模块级别创建单例实例，供编排器直接导入。

- **双路径执行（MCP 优先，回退到 tools.py）**：`call_mcp()` 委托给 `common.mcp_server.client.call_tool()`，后者首先尝试 MCP 协议（基于子进程 stdio）；首次失败后将该工具永久标记为不可用，并回退到直接调用 `tools.py` 中的函数。这对 Agent 是透明的——它们只看到 `await self.call_mcp(...)`。

- **双路径 LLM（每个 Agent 的 try/except）**：每个 Agent 将其 LLM 分析调用包裹在 `try/except Exception` 中。成功时，结果包含 `"llm_analysis"` 键。失败时（超时、网络错误、解析错误），Agent 使用内置逻辑返回纯数据驱动的结果（最便宜的交通、评分最高的酒店、感知天气的行程、预算建议、模板 Markdown）。没有任何 Agent 会因 LLM 失败而崩溃。

- **安全执行与错误隔离**：`safe_execute(state)` 将 `execute()` 包裹在 try/except 中。如果任何 Agent 抛出意外异常，它会向 `agent_logs` 记录 `"error"`，并写入 `state[result_key] = {"error": str(e), "source": self.name}`。这保证了下游 Agent 读取该结果键时能获得一个字典（而非崩溃），并可检查 `"error"` 键。

- **并行 + 顺序执行**：编排器通过 `asyncio.gather` 并行运行 WeatherAgent、TransportAgent 和 HotelAgent（无相互依赖）。ItineraryAgent、BudgetAgent 和 SummarizerAgent 随后顺序执行，因为它们依赖于前面的结果。

## 数据与控制流

```
User request (TravelRequest)
       │
       ▼
BaseAgent.safe_execute(state)              ← orchestrator calls this for each agent
       │
       ├─ add_log(state, "...启动", "start")
       │
       ├─ execute(state)                    ← subclass implements
       │     │
       │     ├── call_mcp(tool, args)       ← MCP → tools.py (transparent fallback)
       │     │
       │     ├── try: call_llm(messages)    ← LLM analysis (5s timeout)
       │     │     └─ on success: result["llm_analysis"] = ...
       │     │
       │     └── except Exception:          ← LLM failed, use built-in logic
       │           result = {data-driven fields, no llm_analysis}
       │
       ├─ state["{domain}_result"] = result  ← store result for downstream agents
       │
       └─ add_log(state, "...完成", "done")
             │
             ▼
       if Exception in execute():
         add_log(state, f"执行失败：{e}", "error")
         state["{domain}_result"] = {"error": ..., "source": ...}
```

**状态字典**（`state`）在流水线中流转，键值逐步累积：
- `state["request"]` — 用户的 `TravelRequest`（出发城市、目的地、天数、预算、偏好）
- `state["weather_result"]` — 由 WeatherAgent 设置
- `state["transport_result"]` — 由 TransportAgent 设置
- `state["hotel_result"]` — 由 HotelAgent 设置
- `state["itinerary_result"]` — 由 ItineraryAgent 设置
- `state["budget_result"]` — 由 BudgetAgent 设置
- `state["final_plan"]` — 由 SummarizerAgent 设置（Markdown 字符串）
- `state["agent_logs"]` — 所有 Agent 累积的日志条目

## 集成点

- **`common.llm_client.llm`**（`common/llm_client.py`）— `BaseAgent.call_llm()` 调用 `llm.chat_completion(messages, temperature, max_tokens)`。LLM 客户端支持通过环境配置在 DeepSeek/Ollama 之间热切换。每次调用默认超时：5 秒。

- **`common.mcp_server.client.call_tool`** — `BaseAgent.call_mcp()` 委托至此。该客户端实现两阶段策略：（1）通过 `stdio` 尝试 MCP 子进程协议；（2）对于某个工具首次失败后，永久回退到 `common/mcp_server/tools.py` 中对应的函数。返回格式始终是 Python 列表或字典（已解析的 JSON）。

- **`tripmind/prompts.py`** — 每个 Agent 从此模块读取其 `system_prompt`。包含 6 个提示词（`TRANSPORT_SYSTEM_PROMPT`、`HOTEL_SYSTEM_PROMPT`、`WEATHER_SYSTEM_PROMPT`、`ITINERARY_SYSTEM_PROMPT`、`BUDGET_SYSTEM_PROMPT`、`SUMMARIZER_SYSTEM_PROMPT`）以及 `ORCHESTRATOR_SYSTEM_PROMPT`。每个提示词定义了角色、任务、输入字段、输出 JSON 模式及约束。

- **`tripmind/orchestrator.py`** — LangGraph 状态机构建 `TravelState`，按正确顺序（并行后串行）为每个 Agent 调用 `safe_execute`，并返回最终方案。Agent 不了解编排逻辑——它们仅操作接收到的状态字典。
