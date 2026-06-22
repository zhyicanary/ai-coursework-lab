# common/mcp_server/

## 职责

本目录为 TripMind 多智能体旅游规划系统实现了 **MCP（模型上下文协议）工具层**。它提供了五个领域专用工具（航班/火车搜索、酒店搜索、天气预报、景点搜索），这些工具既作为 **FastMCP 注册的服务端端点**，也作为 **独立的异步函数** 使用。此外，它还提供了一个智能 MCP 客户端包装器，能从 MCP 子进程协议透明地回退到直接 Python 函数调用，确保 Agent 层无论 MCP 服务器是否可用都能访问工具。

## 文件

### 核心源文件

- **`__init__.py`** — 空包标记文件；支持 `from common.mcp_server import ...` 语法。

- **`server.py`** — FastMCP 服务端入口。创建一个名为 `"TripMind Tools"` 的 `FastMCP` 实例（`mcp_server`），并通过 `register_tools()` 函数使用 `@mcp_server.tool()` 装饰器注册 5 个工具。每个注册的工具都是一个轻量 `async` 包装器，将实际工作委托给 `tools.py` 中的对应函数。暴露 `run_server()`（调用 `mcp_server.run_stdio_async()`）和 `main()` CLI 入口点。关键函数：
  - `register_tools()` — 装饰 5 个工具函数：`_search_flights`、`_search_trains`、`_search_hotels`、`_get_weather`、`_search_attractions`
  - `run_server()` — 启动 MCP 协议所需的 stdio 传输
  - `main()` — CLI 入口（`asyncio.run(run_server())`）

- **`tools.py`** — 读取模拟 JSON 数据的纯异步工具函数实现。每个工具：
  - `search_flights(departure, destination, date=None)` → `list[dict]` — 在 `flights.json` 中查找 `"{departure}-{destination}"` 键；同时检查反向键；若找不到路线则返回默认的备用航班。
  - `search_trains(departure, destination, date=None)` → `list[dict]` — 对 `trains.json` 使用相同的键逻辑；未知路线返回默认的备用火车数据。
  - `search_hotels(city, check_in=None, check_out=None, max_price=None, preferences=None)` → `list[dict]` — 按城市名称读取 `hotels.json`；按 `max_price` 过滤；按 `rating` 降序排序。
  - `get_weather(city, days=3)` → `dict` — 读取 `weather.json` 中各城市的配置；使用该配置的温度范围和天气状况生成 `days`（1-7 天，有上限）天的随机逐日预报；附加穿衣建议（`clothing_advice_base` 加上可选的雨天/高温修饰词）和 `impact_on_travel` 评估。
  - `search_attractions(city, preferences=None, top_k=10)` → `list[dict]` — 使用 `CITY_NAME_MAP` 将中文城市名转换为拼音后，读取 `mock_data/attractions/{city_pinyin}.json`。支持偏好评分：将 `preferences` 与每个景点的 `preferences` 标签（×2）、`description`（×1）和 `name`（×1）进行匹配，然后按评分降序排序。对于未知城市，回退到通用默认景点。
  - 辅助函数：`_load_json(filename)` — 从 `MOCK_DATA_DIR` 读取 JSON；`_city_to_filename(city)` — 通过 `CITY_NAME_MAP` 进行映射。常量 `CITY_NAME_MAP` 将 6 个中文城市名映射到拼音文件名。

- **`client.py`** — 智能 MCP 客户端包装器，提供三种调用路径并支持自动回退：
  - **全局模块级状态**：`_mcp_available: bool | None` — 三态缓存（`None` = 未尝试，`True` = MCP 工作正常，`False` = MCP 不可用，永久回退）。
  - `call_tool(name, arguments=None)` → 推荐的入口点。首次调用时尝试 MCP；若成功则缓存为 `True`，若失败则缓存为 `False` 并回退。后续调用：若 `False` → 直接调用；若 `True` → 使用 MCP，并在连接丢失时回退到直接调用。
  - `call_tool_via_mcp(name, arguments=None)` — 通过 `mcp.client.stdio.stdio_client` 使用 `uv run python -m common.mcp_server.server` 以子进程方式启动 `common.mcp_server.server`，打开一个 `ClientSession`，调用 `session.call_tool()`，并从响应中解析 JSON 文本结果。
  - `call_tool_direct(name, arguments=None)` — 在 `tool_map` 字典中动态导入 `tools.py` 的函数，并直接调用匹配的异步函数。

- **`init_attractions.py`** — 用于向 ChromaDB 填充景点向量嵌入的独立脚本。读取 `mock_data/attractions/*.json`，为每个景点构建由 `name + category + description + preferences` 组成的组合文本，然后调用 `common.vector_store.add_attractions(city_name, attractions, texts)`。在处理前，通过 `common.embedding_client.embedding.embed_texts()` 检查 Embedding 服务的可用性。如果 Ollama/Embedding 未运行则完全跳过，并输出清晰的信息提示。用法：`uv run python -m common.mcp_server.init_attractions`。

### 模拟数据文件

- **`mock_data/flights.json`** — 11 条路线键（`"北京-成都"`、`"北京-上海"` 等），每个键对应 2–3 条航班记录。字段：`flight_no`、`departure`（机场）、`arrival`（机场）、`departure_time`、`arrival_time`、`price`、`airline`。

- **`mock_data/trains.json`** — 11 条路线键，每个键对应 2–4 条火车记录。字段：`train_no`、`departure_station`、`arrival_station`、`departure_time`、`arrival_time`、`duration`、`price`、`type`（高铁/动车/直达/特快/快速）。

- **`mock_data/hotels.json`** — 6 个城市键，每个键对应 5 条酒店记录。字段：`name`、`price`、`location`、`rating`（4.1–4.7）、`distance_to_center`（公里）。包含连锁酒店（如家/汉庭/全季/亚朵）和每个城市的当地民宿。

- **`mock_data/weather.json`** — 6 个城市键，包含天气配置：`conditions`（天气字符串列表）、`temp_range` [最小值, 最大值]、`humid`、`clothing_advice_base`（包含城市特定建议的字符串）。

- **`mock_data/attractions/`** — 6 个 JSON 文件（每城市一个），每个约 12 个景点。字段：`name`、`category`、`ticket_price`、`duration`、`description`、`preferences`（如 "历史文化"、"美食"、"自然风光"、"购物"、"博物馆" 等标签）。
  - `beijing.json` — 12 个景点（故宫、长城、颐和园 等）
  - `chengdu.json` — 12 个景点（宽窄巷子、大熊猫基地 等）
  - `shanghai.json`、`guangzhou.json`、`hangzhou.json`、`xian.json` — 格式类似

## 设计模式

1. **通过装饰器注册 FastMCP 工具** — `register_tools()` 使用 `@mcp_server.tool(name=, description=)` 装饰器和异步内部函数。每个内部函数是一个轻量代理，将工作委托给 `tools.py`。这种分离使服务器传输层（MCP）与业务逻辑保持独立。

2. **城市名称映射** — `tools.py` 中的 `CITY_NAME_MAP` 字典将中文城市名转换为拼音文件名，使 `search_attractions` 能定位每个城市的 JSON 文件。此映射专供 `_city_to_filename()` 使用。

3. **带备用默认值的 JSON 模拟数据** — 每个 `tools.py` 函数都从结构化的 JSON 文件中读取数据，但在数据缺失（未知城市、未知路线）时提供硬编码的默认结果。航班/火车的备用数据返回 2 条通用记录；景点返回 2 条通用记录；天气返回通用配置。

4. **动态天气生成** — `get_weather()` 不存储预计算的预报数据。而是存储每个城市的**配置**（温度范围、天气状况列表、建议基础文本），并动态生成随机的逐日预报，预报值受配置中 `temp_range` 的限制。这使得数据保持简单，同时产生合理的多样性。

5. **景点偏好评分** — `search_attractions()` 实现了一个简单的基于标签的排序：`preferences` 字段中匹配的偏好词得 2 分；`description` 或 `name` 中匹配得 1 分。结果按评分降序排列。这模拟了向量相似度搜索的效果，且不需要 ChromaDB 连接。

6. **带透明回退的 MCP 客户端** — `client.py` 实现了级联重试模式：MCP 子进程 → 直接函数调用。`_mcp_available` 三态全局变量避免了重复启动失败的子进程。直接路径完全绕过了 MCP 协议，以 `tools.py` 作为规范的实现来源。

7. **双基础路径设置** — `server.py` 和 `client.py` 在导入时将项目根目录（`common/mcp_server/../../`）添加到 `sys.path`，允许它们从任何工作目录以 `python -m` 模块方式运行。

8. **可选的 ChromaDB 集成** — 景点搜索可以选择使用 ChromaDB（由 `init_attractions.py` 填充）进行向量相似度搜索，但默认仍使用 JSON 文件读取。ChromaDB 路径不会从 `tools.py` 直接调用——它是一个独立管理的数据基础设施层。

## 数据与控制流

### 工具调用（两条路径）

**MCP 协议路径**（主要路径，用于生产环境）：
```
Agent 代码（例如 TransportAgent）
  → client.call_tool("search_flights", {...})
    →（首次）client.call_tool_via_mcp()
      → 启动子进程：`uv run python -m common.mcp_server.server`
        → server.py：FastMCP 接收 stdio 传输
          → 分发给已注册的工具（例如 _search_flights）
            → tools.py：search_flights() 读取 mock_data/flights.json
              → 返回 list[dict]
        → MCP session.call_tool() 返回结果
      → 子进程关闭
    → 返回解析后的数据
  → Agent 接收结构化数据
```

**直接回退路径**（当 MCP 不可用时）：
```
Agent 代码
  → client.call_tool("search_flights", {...})
    → _mcp_available 为 False → client.call_tool_direct()
      → 导入 tools.py 的函数
      → 直接调用 search_flights()
        → 读取 mock_data/flights.json
        → 返回 list[dict]
    → 返回解析后的数据
```

ChromaDB 初始化流程：
```
init_attractions.py（独立脚本）
  → 读取 mock_data/attractions/{city}.json
  → 构建用于向量化的组合文本
  → 调用 common.vector_store.add_attractions()
    → ChromaDB 集合 "attractions"
  （tools.search_attractions 不查询 ChromaDB——它始终读取 JSON）
```

## 集成点

### 依赖项（本模块依赖的项目）

| 依赖项 | 使用文件 | 原因 |
|---|---|---|
| `mcp`（PyPI：`mcp[cli]`） | `server.py`、`client.py` | FastMCP 服务端框架；用于子进程通信的 stdio 客户端/会话 |
| `common/vector_store` | `init_attractions.py` | `add_attractions()` 用于 ChromaDB 数据导入 |
| `common/embedding_client` | `init_attractions.py` | 在 ChromaDB 导入前检查 Embedding 可用性 |
| `mock_data/*.json` | `tools.py` | 全部五个工具都从此目录读取各自的 JSON 文件 |

### 被依赖方（使用本模块的组件）

| 组件 | 使用方式 |
|---|---|
| **`tripmind/agents/base.py`**（BaseAgent） | 所有 6 个 agent 调用 `self.call_mcp(tool_name, args)`，内部调用 `client.call_tool()`。这是本模块的主要消费者。 |
| **`tripmind/app.py`**（Gradio 前端） | 通过 agent 编排管道间接使用。不直接导入本模块。 |
| **`knowseeker/`** | 当前不是消费者，但设计为两个项目均可访问的共享公共层。 |
| **CLI / `uv run`** | `server.py` 可通过 `uv run python -m common.mcp_server.server` 独立运行；`init_attractions.py` 可通过 `uv run python -m common.mcp_server.init_attractions` 运行。 |

### 边界

- 本目录是一个**只读数据源**——所有工具均不写入模拟数据文件或修改服务器状态。
- ChromaDB 数据导入（`init_attractions.py`）是一次性批量操作，不属于运行时请求流程的一部分。
- `client.py` 的子进程启动会为每次工具调用创建一个临时的 MCP 服务器进程；服务器状态不会在调用之间共享。
