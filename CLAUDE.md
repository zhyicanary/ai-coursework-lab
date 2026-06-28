# KCSJ Collection — 智能应用系统设计 课设作品集

同一技术底座，两种 Agent 范式：

| # | 项目 | 范式 | 前端 | 入口 |
|---|------|------|------|------|
| 1 | KnowSeeker | 单 Agent 深度推理 (Agentic RAG) | Streamlit | `knowseeker/app.py` |
| 2 | TripMind | 多 Agent 协同编排 (Multi-Agent) | Gradio | `tripmind/app.py` |

两个项目共享 `common/` 模块（LLM API、向量库、MCP Server）。

---

## 技术栈

- **Python 3.14** + **uv** 包管理
- **LLM**: DeepSeek API（OpenAI 兼容接口）
- **Embedding**: Ollama 本地模型（qwen3-embedding:8b）
- **向量库**: ChromaDB
- **编排**: LangChain + LangGraph
- **协议**: MCP (Python MCP SDK, FastMCP)
- **前端**: Streamlit + Gradio

---

## 项目结构

```
ai-coursework-lab/
├── common/                          # 公共模块
│   ├── llm_client.py                # LLM 客户端（DeepSeek/Ollama 热切换）
│   ├── embedding_client.py          # Embedding 客户端（Ollama 本地）
│   ├── vector_store.py              # ChromaDB 向量存储操作
│   └── mcp_server/
│       ├── server.py                # FastMCP 主入口，注册 5 个工具
│       ├── tools.py                 # 工具函数实现（异步、读 JSON、偏好匹配）
│       ├── client.py                # MCP 客户端封装（优先MCP协议，失败回退到 tools.py）
│       ├── init_attractions.py      # 景点数据→ChromaDB 初始化脚本
│       └── mock_data/
│           ├── flights.json         # 11 条航线 × 2-3 班次
│           ├── trains.json          # 11 条线路 × 2-4 车次
│           ├── hotels.json          # 6 城市 × 5 酒店
│           ├── weather.json         # 6 城市天气配置
│           └── attractions/         # 6 城市 × 12 景点（含偏好标签）
│               ├── chengdu.json
│               ├── beijing.json
│               ├── shanghai.json
│               ├── xian.json
│               ├── guangzhou.json
│               └── hangzhou.json
├── tripmind/                        # 课设二：多 Agent 旅游规划
│   ├── app.py                       # Gradio 前端（旅行规划/对话/设置 Tab）
│   ├── orchestrator.py              # LangGraph 状态机编排器
│   ├── prompts.py                   # 6 个 Agent 系统提示词（含 JSON 输出格式）
│   └── agents/
│       ├── base.py                  # BaseAgent 基类（LLM + MCP + 日志 + 容错）
│       ├── transport.py             # TransportAgent：航班/高铁查询推荐
│       ├── hotel.py                 # HotelAgent：酒店搜索推荐
│       ├── weather.py               # WeatherAgent：天气预报分析
│       ├── itinerary.py             # ItineraryAgent：每日行程规划
│       ├── budget.py                # BudgetAgent：费用汇总预算检查
│       └── summarizer.py            # SummarizerAgent：Markdown 方案生成
├── knowseeker/                      # 课设一：单 Agent RAG 问答
│   ├── app.py
│   └── ...
├── design/                          # 设计文档
│   ├── 01-tech-stack.md
│   ├── 02-knowseeker.md
│   ├── 03-tripmind.md
│   ├── 04-tripmind-implementation.md
│   └── 05-tripmind-progress.md
├── .env.example
├── pyproject.toml
└── README.md
```

---

## TripMind 架构详解

### 执行流程

```
用户表单输入
    ↓
plan_travel() → TravelRequest
    ↓
run_travel_planner() → LangGraph 状态机
    │
    ├── orchestrator_node     调度决策
    │       ↓
    ├── parallel_agents       asyncio.gather 并行执行
    │   ├── WeatherAgent      get_weather
    │   ├── TransportAgent    search_flights + search_trains
    │   └── HotelAgent        search_hotels
    │       ↓
    └── sequential_agents     顺序执行（依赖前序结果）
        ├── ItineraryAgent    search_attractions + 天气+交通
        ├── BudgetAgent       汇总交通+住宿+行程费用
        └── SummarizerAgent   整合所有结果为 Markdown
            ↓
    返回完整 TravelState（含结果 + 日志 + 最终方案）
```

### Agent 双路径调用机制

所有 Agent 继承 `BaseAgent`（`tripmind/agents/base.py`），执行时走双路径：

```
Agent.execute(state)
  │
  ├─ 1. call_mcp(tool, args) ──→ 优先 MCP 协议 (client.py)
  │                                  │
  │                          首次成功 → 缓存可用，后续走 MCP
  │                          首次失败 → 标记不可用，永久回退到 tools.py
  │
  ├─ 2. call_llm(messages) ──→ LLM 分析/格式化结果
  │                               │
  │                         5 秒超时 → 捕获异常，回退到内置逻辑
  │
  └─ 3. 返回结构化结果 → 存入 state
```

关键设计：
- `call_llm` 默认 5 秒超时（`asyncio.wait_for`），LLM 不可用时快速回退
- `safe_execute` 包裹 `execute`，单 Agent 失败不阻塞整体流程
- `_copy_state` 为每个子 Agent 清空 `agent_logs`，避免日志重复累加

### 6 个 Agent

| Agent | 文件 | MCP 工具 | LLM 角色 | 依赖 |
|-------|------|----------|----------|------|
| 🌤️ 天气 | `weather.py` | `get_weather` | 穿衣+出行建议 | 无 |
| ✈️ 交通 | `transport.py` | `search_flights` + `search_trains` | 推荐最优方案 | 无 |
| 🏨 住宿 | `hotel.py` | `search_hotels` | 按预算筛选推荐 | 无 |
| 🗺️ 行程 | `itinerary.py` | `search_attractions` | 规划每日行程 | 天气 + 交通 |
| 💰 预算 | `budget.py` | 无（聚合结果） | 超支分析建议 | 交通 + 住宿 + 行程 |
| 📝 汇总 | `summarizer.py` | 无（聚合全部结果） | 生成 Markdown 方案 | 全部 |

---

## 运行

```bash
# 课设二 - TripMind（Gradio）
uv run python tripmind/app.py
# 启动后自动访问 http://localhost:7861
# 三个 Tab：旅行规划 / 对话 / 设置

# 单独启动 MCP Server
uv run python -m common.mcp_server.server

# 初始化景点数据到 ChromaDB（可选，需要 Ollama 运行中）
# 即使不跑，search_attractions 也会从 JSON 文件直接读取
ollama serve
uv run python -m common.mcp_server.init_attractions

# 课设一 - KnowSeeker（Streamlit）
uv run streamlit run knowseeker/app.py
```

---

## MCP 模拟数据

| 文件 | 内容 | 格式 |
|------|------|------|
| `flights.json` | 航线 → 航班列表 | 含 flight_no, departure_time, price, airline |
| `trains.json` | 线路 → 列车列表 | 含 train_no, type(高铁/动车/直达/快速), price |
| `hotels.json` | 城市 → 酒店列表 | 含 name, price, rating, distance_to_center |
| `weather.json` | 城市 → 天气配置 | 含 conditions, temp_range, clothing_advice_base |
| `attractions/*.json` | 城市 → 景点列表 | 含 name, category, ticket_price, preferences 标签 |

中文城市名 ↔ 拼音文件名映射（`tools.py` 中 `CITY_NAME_MAP`）：
北京→beijing, 上海→shanghai, 成都→chengdu, 西安→xian, 广州→guangzhou, 杭州→hangzhou

---

## 开发约定

- **Python 3.14** + **uv** 包管理（不用 pip）
- 类型标注 + 中文注释
- 配置通过 `.env` + `python-dotenv` 管理
- **Agent 开发**：继承 `BaseAgent`，重写 `execute(state)` 方法
  - 数据获取走 `self.call_mcp(tool_name, args)`
  - LLM 处理走 `self.call_llm(messages)`
  - 日志记录走 `self.add_log(state, message)`
- **工具函数**：添加新工具到 `common/mcp_server/tools.py`，同时在 `server.py` 注册
- **模拟数据**：添加新数据到 `common/mcp_server/mock_data/`
- **MCP 客户端**：`common/mcp_server/client.py` 的 `call_tool()` 是统一入口
- **LLM 调用**：默认 5 秒超时，超时自动走回退逻辑
