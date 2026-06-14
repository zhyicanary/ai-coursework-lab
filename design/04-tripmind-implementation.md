# TripMind 实现计划

> 基于 `design/03-tripmind.md` 需求分析与软件设计文档生成

---

## 一、实现总览

### 1.1 目录结构（最终状态）

```
ai-coursework-lab/
├── common/                              # 公共模块（与课设一复用）
│   ├── __init__.py
│   ├── llm_client.py                    # [Phase 1] DeepSeek API 封装
│   ├── embedding.py                     # [Phase 1] bge-small-zh 向量化
│   ├── vector_store.py                  # [Phase 1] ChromaDB 操作
│   ├── document_loader.py               # [Phase 1] 文档解析（与课设一复用）
│   └── mcp_server/
│       ├── __init__.py
│       ├── server.py                    # [Phase 2] MCP Server 主入口
│       ├── tools.py                     # [Phase 2] 旅游工具定义
│       └── mock_data/                   # [Phase 2] 模拟数据
│           ├── flights.json
│           ├── trains.json
│           ├── hotels.json
│           ├── weather.json
│           └── attractions/
│               ├── chengdu.json
│               ├── beijing.json
│               └── ...
├── tripmind/                            # 课设二
│   ├── __init__.py
│   ├── types.py                         # [Phase 3] 核心数据结构
│   ├── orchestrator.py                  # [Phase 3] LangGraph 编排器
│   ├── prompts.py                       # [Phase 3] 所有 Agent 系统提示词
│   ├── app.py                           # [Phase 5] Gradio 前端
│   └── agents/
│       ├── __init__.py
│       ├── base.py                      # [Phase 4] Agent 基类
│       ├── transport.py                 # [Phase 4] 交通 Agent
│       ├── hotel.py                     # [Phase 4] 住宿 Agent
│       ├── weather.py                   # [Phase 4] 天气 Agent
│       ├── itinerary.py                 # [Phase 4] 行程 Agent
│       ├── budget.py                    # [Phase 4] 预算 Agent
│       └── summarizer.py               # [Phase 4] 汇总 Agent
├── design/
│   ├── 01-tech-stack.md
│   ├── 02-knowseeker.md
│   ├── 03-tripmind.md
│   └── 04-tripmind-implementation.md    # 本文件
├── .env.example
├── pyproject.toml
└── README.md
```

### 1.2 实现阶段

| Phase | 内容 | 依赖 | 预计工作量 |
|-------|------|------|-----------|
| Phase 1 | 公共模块（LLM/Embedding/向量库） | 无 | 中 |
| Phase 2 | MCP Server + 模拟数据 | Phase 1 | 中 |
| Phase 3 | LangGraph 编排器 + 数据结构 | Phase 1 | 高 |
| Phase 4 | 6 个 Agent 实现 | Phase 1, 2, 3 | 高 |
| Phase 5 | Gradio 前端 | Phase 3, 4 | 中 |

---

## 二、Phase 1 — 公共模块

### 2.1 LLM 客户端 `common/llm_client.py`

**职责：** 封装 DeepSeek API 调用，供所有 Agent 使用

**接口设计：**

```python
from openai import AsyncOpenAI

client: AsyncOpenAI  # 全局单例，从 .env 读取 DEEPSEEK_API_KEY

async def chat_completion(
    messages: list[dict],
    model: str = "deepseek-chat",
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> str:
    """调用 DeepSeek API，返回文本响应"""
```

**实现要点：**
- 使用 `openai` 库（DeepSeek 兼容 OpenAI 接口）
- 异步调用（`AsyncOpenAI`），支持 Agent 并行执行
- 从 `.env` 读取 `DEEPSEEK_API_KEY` 和 `DEEPSEEK_BASE_URL`
- 统一异常处理：超时、限流、网络错误

### 2.2 Embedding `common/embedding.py`

**职责：** 文本向量化，用于景点知识库检索

**接口设计：**

```python
from sentence_transformers import SentenceTransformer

model: SentenceTransformer  # 全局单例，懒加载

def embed_text(text: str) -> list[float]:
    """单条文本向量化"""

def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量文本向量化"""
```

**实现要点：**
- 模型：`BAAI/bge-small-zh-v1.5`，维度 512
- 首次调用自动下载，后续使用缓存
- 向量归一化（cosine similarity 需要）

### 2.3 向量存储 `common/vector_store.py`

**职责：** ChromaDB 操作，存储和检索景点信息

**接口设计：**

```python
import chromadb

client: chromadb.ClientAPI  # 全局单例
COLLECTION_NAME = "attractions"

def init_collection():
    """初始化/获取 collection"""

def add_attractions(city: str, attractions: list[dict]):
    """批量添加景点（id, 文档, 元数据）"""

def search_attractions(
    city: str,
    query: str,
    top_k: int = 10,
    preferences: list[str] = [],
) -> list[dict]:
    """向量检索景点，返回 [{name, category, ticket_price, duration, description, score}]"""
```

**实现要点：**
- 使用 `chromadb.PersistentClient`（持久化到 `data/chromadb/`）
- 元数据过滤：按 `city` 字段过滤
- 支持 `preferences` 关键词过滤（在 `where` 条件中）

---

## 三、Phase 2 — MCP Server + 模拟数据

### 3.1 MCP Server `common/mcp_server/server.py`

**职责：** 暴露旅游工具为 MCP 协议，供 Agent 调用

**实现方式：** 使用 Python MCP SDK 的 `FastMCP` 类

```python
from mcp.server.fastmcp import FastMCP

server = FastMCP("TripMind Tools")

# 注册工具（见 tools.py）
```

**启动方式：** 作为子进程启动，Agent 通过 MCP 客户端连接

### 3.2 工具定义 `common/mcp_server/tools.py`

**职责：** 定义 5 个 MCP 工具，对应设计文档 4.3 节

| 工具 | 函数签名 | 返回格式 | 数据来源 |
|------|---------|---------|---------|
| `search_flights` | `(departure, destination, date)` | `[{flight_no, departure_time, arrival_time, price, airline}]` | 模拟数据 |
| `search_trains` | `(departure, destination, date)` | `[{train_no, departure_time, arrival_time, price, duration}]` | 模拟数据 |
| `search_hotels` | `(city, check_in, check_out, max_price, preferences)` | `[{name, price, location, rating, distance_to_center}]` | 模拟数据 |
| `get_weather` | `(city, days)` | `{daily: [{date, temp_high, temp_low, condition, rain_prob}]}` | 模拟数据 / API |
| `search_attractions` | `(city, preferences, top_k)` | `[{name, category, ticket_price, duration, description}]` | ChromaDB 向量检索 |

### 3.3 模拟数据 `common/mcp_server/mock_data/`

**文件结构：**

```
mock_data/
├── flights.json          # 航班数据（京蓉、沪蓉、广蓉等热门线路）
├── trains.json           # 高铁数据（G/D 字头）
├── hotels.json           # 酒店数据（按城市分组）
├── weather.json          # 天气数据（按城市分组）
└── attractions/          # 景点数据（按城市分文件，导入 ChromaDB）
    ├── chengdu.json
    ├── beijing.json
    ├── shanghai.json
    ├── xian.json
    ├── guangzhou.json
    └── hangzhou.json
```

**数据格式示例（flights.json）：**

```json
{
  "北京-成都": [
    {"flight_no": "CA1401", "departure": "北京首都", "arrival": "成都天府", "departure_time": "08:00", "arrival_time": "10:30", "price": 1200, "airline": "国航"},
    {"flight_no": "MU5401", "departure": "北京大兴", "arrival": "成都天府", "departure_time": "14:00", "arrival_time": "16:45", "price": 980, "airline": "东航"}
  ],
  "上海-成都": [...]
}
```

**景点数据格式示例（chengdu.json）：**

```json
[
  {
    "name": "宽窄巷子",
    "category": "历史街区",
    "ticket_price": 0,
    "duration": "2-3小时",
    "description": "成都著名的历史文化街区，由宽巷子、窄巷子和井巷子组成，保留了清朝古街道的格局。",
    "preferences": ["历史文化", "美食", "购物"]
  },
  {
    "name": "都江堰",
    "category": "世界遗产",
    "ticket_price": 80,
    "duration": "3-4小时",
    "description": "世界文化遗产，始建于秦昭王末年，是全世界迄今为止年代最久、唯一留存、以无坝引水为特征的水利工程。",
    "preferences": ["历史文化", "自然风光"]
  }
]
```

### 3.4 景点数据初始化

**脚本：** `common/mcp_server/init_attractions.py`

```python
"""初始化景点知识库：读取 attractions/*.json → 向量化 → 存入 ChromaDB"""
import json
from pathlib import Path
from common.embedding import embed_texts
from common.vector_store import add_attractions

def init():
    attractions_dir = Path(__file__).parent / "mock_data" / "attractions"
    for city_file in attractions_dir.glob("*.json"):
        city = city_file.stem
        attractions = json.loads(city_file.read_text())
        texts = [f"{a['name']} {a['category']} {a['description']}" for a in attractions]
        add_attractions(city, attractions, texts)
```

---

## 四、Phase 3 — LangGraph 编排器

### 4.1 核心数据结构 `tripmind/types.py`

**对应设计文档 3.3 节：**

```python
from typing import TypedDict

class TravelRequest(TypedDict):
    destination: str
    days: int
    budget: float
    preferences: list[str]
    departure_city: str

class SubTask(TypedDict):
    id: str
    agent: str           # "transport" | "hotel" | "weather" | "itinerary" | "budget" | "summarizer"
    description: str
    dependencies: list[str]
    status: str          # "pending" | "running" | "done" | "failed"

class AgentLog(TypedDict):
    timestamp: str
    agent: str
    message: str
    status: str          # "start" | "done" | "error"

class TravelState(TypedDict):
    request: TravelRequest
    sub_tasks: list[SubTask]
    weather_result: dict | None
    transport_result: dict | None
    hotel_result: dict | None
    itinerary_result: dict | None
    budget_result: dict | None
    final_plan: str | None
    agent_logs: list[AgentLog]
    current_phase: str   # "analyze" | "decompose" | "dispatch" | "execute" | "summarize" | "done"
    revision_count: int  # 追问调整次数
```

### 4.2 Agent 系统提示词 `tripmind/prompts.py`

**对应设计文档 4.2 节：**

```python
ORCHESTRATOR_PROMPT = """你是旅行规划调度者。
任务：理解用户需求，拆解为子任务，按依赖关系调度执行。
输出格式：JSON 格式的子任务列表"""

TRANSPORT_SYSTEM_PROMPT = """你是交通出行专家。..."""  # 完整提示词见设计文档 4.2

HOTEL_SYSTEM_PROMPT = """你是住宿推荐专家。..."""

WEATHER_SYSTEM_PROMPT = """你是天气分析专家。..."""

ITINERARY_SYSTEM_PROMPT = """你是行程规划专家。..."""

BUDGET_SYSTEM_PROMPT = """你是预算管理专家。..."""

SUMMARIZER_SYSTEM_PROMPT = """你是旅行方案撰写专家。..."""
```

### 4.3 编排器 `tripmind/orchestrator.py`

**对应设计文档 3.2 节和 4.4 节：**

**核心类：**

```python
class TravelOrchestrator:
    """LangGraph 状态机编排器"""

    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self) -> CompiledGraph:
        """构建状态机（对应设计文档 3.2 节状态图）"""
        workflow = StateGraph(TravelState)

        # 节点
        workflow.add_node("analyze", self._analyze_request)      # 解析用户需求
        workflow.add_node("decompose", self._decompose_tasks)    # 拆解子任务 + 生成 DAG
        workflow.add_node("dispatch", self._dispatch_parallel)   # 并行调度无依赖任务
        workflow.add_node("transport", self._run_transport)      # 交通 Agent
        workflow.add_node("hotel", self._run_hotel)              # 住宿 Agent
        workflow.add_node("weather", self._run_weather)          # 天气 Agent
        workflow.add_node("itinerary", self._run_itinerary)      # 行程 Agent
        workflow.add_node("budget", self._run_budget)            # 预算 Agent
        workflow.add_node("summarize", self._run_summarizer)     # 汇总 Agent
        workflow.add_node("check_budget", self._check_budget)    # 预算检查
        workflow.add_node("adjust", self._suggest_adjustment)    # 超预算调整建议

        # 边（对应设计文档 3.2 节状态图）
        workflow.add_edge(START, "analyze")
        workflow.add_edge("analyze", "decompose")
        workflow.add_edge("decompose", "dispatch")

        # 并行调度：dispatch 根据 DAG 决定启动哪些 Agent
        workflow.add_conditional_edges("dispatch", self._route_to_agents, {
            "parallel": ["transport", "hotel", "weather"],  # 无依赖，并行
        })

        # Agent 完成后回到 orchestrator
        workflow.add_edge("transport", "check_budget")
        workflow.add_edge("hotel", "check_budget")
        workflow.add_edge("weather", "check_budget")

        # check_budget 检查是否所有并行任务完成
        workflow.add_conditional_edges("check_budget", self._check_all_parallel_done, {
            "itinerary": "itinerary",       # 并行任务全完成 → 启动行程
            "wait": "check_budget",         # 未完成 → 等待
        })

        workflow.add_edge("itinerary", "budget")
        workflow.add_edge("budget", "summarize")
        workflow.add_edge("summarize", "check_budget_final")

        # 最终预算检查
        workflow.add_conditional_edges("check_budget_final", self._final_budget_check, {
            "done": END,
            "over_budget": "adjust",
        })
        workflow.add_edge("adjust", END)

        return workflow.compile()

    async def run(self, user_input: str, on_log: Callable = None) -> TravelState:
        """执行完整规划流程"""
        initial_state = TravelState(
            request={}, sub_tasks=[],
            weather_result=None, transport_result=None, hotel_result=None,
            itinerary_result=None, budget_result=None, final_plan=None,
            agent_logs=[], current_phase="analyze", revision_count=0,
        )
        # 运行状态机，通过 on_log 回调实时推送日志给前端
        final_state = await self.graph.ainvoke(initial_state, config={"callbacks": [...]})
        return final_state
```

**关键设计点：**

1. **DAG 依赖调度** — `decompose` 节点生成 `sub_tasks`，`dispatch` 根据依赖关系决定并行/顺序
2. **并行执行** — 交通/住宿/天气三者无依赖，LangGraph 支持并行节点
3. **状态汇聚** — `check_budget` 节点等待所有并行任务完成后再启动行程 Agent
4. **超预算分支** — 最终检查超预算时，生成调整建议（对应设计文档状态图的"超预算？"判断）
5. **追问调整** — UC-05 的实现：修改 `request` 后重新运行，仅重算受影响的 Agent

### 4.4 追问调整机制（UC-05）

**场景：** 用户说"换个便宜点的酒店"

**实现方式：**

```python
async def revise(self, state: TravelState, instruction: str) -> TravelState:
    """追问调整：仅重算受影响的 Agent"""
    # 1. LLM 理解调整指令，确定受影响的 Agent
    affected_agents = await self._parse_revision(instruction)
    # 例：instruction="换个便宜点的酒店" → affected_agents=["hotel", "budget", "summarizer"]

    # 2. 标记受影响的子任务为 pending
    for task in state["sub_tasks"]:
        if task["agent"] in affected_agents:
            task["status"] = "pending"
            # 清除对应结果
            state[f"{task['agent']}_result"] = None

    # 3. 重新执行受影响的 Agent（按依赖顺序）
    for agent_name in affected_agents:
        state = await self._run_agent(agent_name, state)

    state["revision_count"] += 1
    return state
```

---

## 五、Phase 4 — Agent 实现

### 5.1 Agent 基类 `tripmind/agents/base.py`

```python
from abc import ABC, abstractmethod
from common.llm_client import chat_completion

class BaseAgent(ABC):
    """Agent 基类，封装 LLM 调用和日志记录"""

    name: str          # Agent 名称
    emoji: str         # 前端显示 emoji
    system_prompt: str # 系统提示词

    @abstractmethod
    async def execute(self, state: TravelState) -> TravelState:
        """执行 Agent 逻辑，更新 state"""
        pass

    async def call_llm(self, user_message: str) -> str:
        """调用 LLM"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]
        return await chat_completion(messages)

    def add_log(self, state: TravelState, message: str, status: str = "done"):
        """添加执行日志"""
        state["agent_logs"].append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "agent": f"{self.emoji}{self.name}",
            "message": message,
            "status": status,
        })
```

### 5.2 各 Agent 实现

#### 交通 Agent `tripmind/agents/transport.py`

```python
class TransportAgent(BaseAgent):
    name = "交通"
    emoji = "✈️"
    system_prompt = TRANSPORT_SYSTEM_PROMPT

    async def execute(self, state: TravelState) -> TravelState:
        req = state["request"]
        # 构造查询参数
        user_msg = f"查询从{req['departure_city']}到{req['destination']}的交通方式，共{req['days']}天，预算{req['budget']}元"
        # 调用 LLM（LLM 内部会调用 MCP 工具 search_flights/search_trains）
        result = await self.call_llm(user_msg)
        state["transport_result"] = {"raw": result, "source": "transport_agent"}
        self.add_log(state, f"找到交通方案：{result[:50]}...")
        return state
```

#### 住宿 Agent `tripmind/agents/hotel.py`

```python
class HotelAgent(BaseAgent):
    name = "住宿"
    emoji = "🏨"
    system_prompt = HOTEL_SYSTEM_PROMPT

    async def execute(self, state: TravelState) -> TravelState:
        req = state["request"]
        max_price_per_night = req["budget"] * 0.4 / req["days"]  # 住宿不超过预算40%
        user_msg = f"推荐{req['destination']}的酒店，{req['days']}晚，每晚不超过{max_price_per_night:.0f}元，偏好：{req['preferences']}"
        result = await self.call_llm(user_msg)
        state["hotel_result"] = {"raw": result, "source": "hotel_agent"}
        self.add_log(state, f"推荐酒店：{result[:50]}...")
        return state
```

#### 天气 Agent `tripmind/agents/weather.py`

```python
class WeatherAgent(BaseAgent):
    name = "天气"
    emoji = "🌤️"
    system_prompt = WEATHER_SYSTEM_PROMPT

    async def execute(self, state: TravelState) -> TravelState:
        req = state["request"]
        user_msg = f"查询{req['destination']}未来{req['days']}天的天气预报"
        result = await self.call_llm(user_msg)
        state["weather_result"] = {"raw": result, "source": "weather_agent"}
        self.add_log(state, f"天气查询完成：{result[:50]}...")
        return state
```

#### 行程 Agent `tripmind/agents/itinerary.py`

```python
class ItineraryAgent(BaseAgent):
    name = "行程"
    emoji = "🗺️"
    system_prompt = ITINERARY_SYSTEM_PROMPT

    async def execute(self, state: TravelState) -> TravelState:
        req = state["request"]
        # 汇聚依赖 Agent 的结果
        weather = state["weather_result"]["raw"]
        transport = state["transport_result"]["raw"]
        user_msg = f"""规划{req['destination']} {req['days']}天行程。
天气信息：{weather}
交通信息：{transport}
用户偏好：{req['preferences']}"""
        result = await self.call_llm(user_msg)
        state["itinerary_result"] = {"raw": result, "source": "itinerary_agent"}
        self.add_log(state, f"行程规划完成：{result[:50]}...")
        return state
```

#### 预算 Agent `tripmind/agents/budget.py`

```python
class BudgetAgent(BaseAgent):
    name = "预算"
    emoji = "💰"
    system_prompt = BUDGET_SYSTEM_PROMPT

    async def execute(self, state: TravelState) -> TravelState:
        req = state["request"]
        transport = state["transport_result"]["raw"]
        hotel = state["hotel_result"]["raw"]
        itinerary = state["itinerary_result"]["raw"]
        user_msg = f"""汇总费用，预算{req['budget']}元。
交通：{transport}
住宿：{hotel}
行程：{itinerary}"""
        result = await self.call_llm(user_msg)
        state["budget_result"] = {"raw": result, "source": "budget_agent"}
        self.add_log(state, f"预算核算完成：{result[:50]}...")
        return state
```

#### 汇总 Agent `tripmind/agents/summarizer.py`

```python
class SummarizerAgent(BaseAgent):
    name = "汇总"
    emoji = "📝"
    system_prompt = SUMMARIZER_SYSTEM_PROMPT

    async def execute(self, state: TravelState) -> TravelState:
        req = state["request"]
        user_msg = f"""整合所有结果，生成{req['destination']} {req['days']}天旅行方案。
交通：{state['transport_result']['raw']}
住宿：{state['hotel_result']['raw']}
天气：{state['weather_result']['raw']}
行程：{state['itinerary_result']['raw']}
预算：{state['budget_result']['raw']}
预算上限：{req['budget']}元

要求：
1. 所有数据标注来源 Agent
2. 如某项数据缺失，标注"暂无数据"
3. 语言生动，有代入感"""
        result = await self.call_llm(user_msg)
        state["final_plan"] = result
        self.add_log(state, "最终方案已生成")
        return state
```

---

## 六、Phase 5 — Gradio 前端

### 6.1 前端入口 `tripmind/app.py`

**对应设计文档第六节 Gradio 布局：**

```python
import gradio as gr
from tripmind.orchestrator import TravelOrchestrator

orchestrator = TravelOrchestrator()

def plan_trip(destination, days, budget, departure, preferences):
    """主规划函数"""
    # 1. 构造 TravelRequest
    request = TravelRequest(
        destination=destination, days=int(days), budget=float(budget),
        departure_city=departure, preferences=preferences.split(","),
    )
    # 2. 运行编排器
    state = orchestrator.run(request)
    # 3. 返回结果
    return (
        state["final_plan"],           # 旅行方案
        format_agent_logs(state),      # Agent 日志
        format_agent_status(state),    # Agent 状态面板
    )

def revise_plan(instruction, current_state):
    """追问调整"""
    new_state = orchestrator.revise(current_state, instruction)
    return new_state["final_plan"], format_agent_logs(new_state)

# Gradio 布局（对应设计文档 6.1 节）
with gr.Blocks(title="TripMind", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# ✈️ TripMind — 智能旅游助手")

    with gr.Row():
        with gr.Column(scale=1):
            destination = gr.Textbox(label="目的地", placeholder="成都")
            days = gr.Number(label="天数", value=3)
            budget = gr.Number(label="预算（元）", value=3000)
            departure = gr.Textbox(label="出发地", placeholder="北京")
            preferences = gr.Textbox(label="偏好", placeholder="美食,历史文化")
            plan_btn = gr.Button("▶ 开始规划", variant="primary")

        with gr.Column(scale=2):
            agent_status = gr.JSON(label="📊 Agent 执行状态")
            agent_logs = gr.Textbox(label="📨 Agent 通信日志", lines=15)
            final_plan = gr.Markdown(label="📄 旅行方案")

    with gr.Row():
        revise_input = gr.Textbox(label="💬 追问调整", placeholder="换个便宜点的酒店")
        revise_btn = gr.Button("🔄 调整")

    # 事件绑定
    plan_btn.click(plan_trip, [destination, days, budget, departure, preferences], [final_plan, agent_logs, agent_status])
    revise_btn.click(revise_plan, [revise_input, gr.State(None)], [final_plan, agent_logs])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7861)
```

### 6.2 前端功能点

| 功能 | 对应用例 | 实现方式 |
|------|---------|---------|
| 需求输入 | UC-01 | Gradio 表单组件 |
| Agent 状态面板 | UC-03 非功能需求 | `gr.JSON` 实时更新 |
| Agent 通信日志 | UC-03 非功能需求 | `gr.Textbox` 追加日志 |
| 旅行方案展示 | UC-04 | `gr.Markdown` 渲染 |
| 追问调整 | UC-05 | 独立输入框 + 调整按钮 |
| 重新规划 | — | 复用规划按钮 |

---

## 七、容错机制

**对应设计文档非功能需求：**

```python
async def _safe_execute(self, agent: BaseAgent, state: TravelState) -> TravelState:
    """容错执行：单 Agent 失败不阻塞"""
    try:
        return await agent.execute(state)
    except Exception as e:
        # 记录错误日志
        agent.add_log(state, f"执行失败：{str(e)}", status="error")
        # 设置失败结果，标注"暂无数据"
        result_key = f"{agent.name}_result"
        state[result_key] = {"raw": "暂无数据", "source": agent.name, "error": str(e)}
        return state
```

---

## 八、数据流验证

**对应设计文档第五节完整执行流程：**

```
输入: "成都 3天 3000元 喜欢美食和历史文化，从北京出发"

Phase 1 (analyze): 提取 TravelRequest
Phase 2 (decompose): 生成 6 个 SubTask
Phase 3 (dispatch): 并行启动 交通/住宿/天气
Phase 4 (execute):
  ├── 交通 Agent → search_trains("北京","成都") → 高铁G89 ￥780
  ├── 住宿 Agent → search_hotels("成都", max_price=360) → 3家推荐
  └── 天气 Agent → get_weather("成都", 3) → 晴/多云/小雨
Phase 5 (itinerary): 汇聚天气+交通 → 规划行程
Phase 6 (budget): 汇聚交通+住宿+行程 → 核算费用 ￥3170
Phase 7 (summarize): 整合所有结果 → 生成 Markdown 方案
Phase 8 (check): 超预算 ￥170 → 生成调整建议
```

---

## 九、依赖安装

```bash
# 已在 pyproject.toml 中管理
uv add langchain langgraph langchain-community
uv add openai              # DeepSeek 兼容接口
uv add chromadb            # 向量数据库
uv add sentence-transformers  # Embedding
uv add mcp                 # MCP 协议
uv add gradio              # 前端
uv add python-dotenv       # 环境变量
```

---

## 十、实现顺序检查清单

- [ ] Phase 1.1: `common/llm_client.py`
- [ ] Phase 1.2: `common/embedding.py`
- [ ] Phase 1.3: `common/vector_store.py`
- [ ] Phase 2.1: `common/mcp_server/server.py`
- [ ] Phase 2.2: `common/mcp_server/tools.py`
- [ ] Phase 2.3: 模拟数据文件（flights/trains/hotels/weather/attractions）
- [ ] Phase 2.4: `common/mcp_server/init_attractions.py`
- [ ] Phase 3.1: `tripmind/types.py`
- [ ] Phase 3.2: `tripmind/prompts.py`
- [ ] Phase 3.3: `tripmind/orchestrator.py`
- [ ] Phase 4.1: `tripmind/agents/base.py`
- [ ] Phase 4.2: `tripmind/agents/transport.py`
- [ ] Phase 4.3: `tripmind/agents/hotel.py`
- [ ] Phase 4.4: `tripmind/agents/weather.py`
- [ ] Phase 4.5: `tripmind/agents/itinerary.py`
- [ ] Phase 4.6: `tripmind/agents/budget.py`
- [ ] Phase 4.7: `tripmind/agents/summarizer.py`
- [ ] Phase 5.1: `tripmind/app.py`
- [ ] 集成测试：端到端运行验证
