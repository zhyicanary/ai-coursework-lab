# KCSJ Collection — 智能应用系统设计 课设作品集

同一技术底座，两种 Agent 范式：

| # | 项目 | 范式 | 前端 | 入口 |
|---|------|------|------|------|
| 1 | KnowSeeker | 单 Agent 深度推理 (Agentic RAG + 混合检索 + 重排序) | React + shadcn/ui | `frontend/app/knowseeker/` |
| 2 | TripMind | 多 Agent 协同编排 (Multi-Agent) | React + shadcn/ui + SSE | `frontend/app/tripmind/` |

两个项目共享 `common/` 模块，采用**三层架构**（推理层 + 向量化层 + 重排序层）。后端统一使用 FastAPI + SSE 流式推送，前端使用 Next.js 14 + React 18 + shadcn/ui + Tailwind CSS，前后端分离。

---

## 技术栈

- **Python 3.14** + **uv** 包管理
- **推理层**: DeepSeek API / Ollama（运行时热切换，OpenAI 兼容接口）
- **向量化层**: Ollama 本地模型（qwen3-embedding:8b）
- **重排序层**: sentence-transformers Cross-Encoder（可开关）
- **稀疏检索**: Okapi BM25（rank-bm25 库）
- **向量库**: ChromaDB（双集合：attractions + documents）
- **编排**: LangChain + LangGraph
- **协议**: MCP (Python MCP SDK, FastMCP)
- **后端**: FastAPI + SSE 流式 + MCP 生命周期自动管理
- **前端**: Next.js 14 + React 18 + shadcn/ui + Tailwind CSS

---

## 项目结构

```
ai-coursework-lab/
├── common/                          # 公共模块
│   ├── context.py                   # App Context — 全局服务上下文（LLM/Embedding/Reranker/BM25/ChromaDB）
│   ├── llm_client.py                # 推理层：LLM 客户端（DeepSeek/Ollama 热切换）
│   ├── embedding_client.py          # 向量化层：Embedding 客户端（Ollama 本地）
│   ├── reranker.py                  # 重排序层：Cross-Encoder 重排序（sentence-transformers）
│   ├── bm25_store.py                # 稀疏检索：Okapi BM25（rank-bm25 库）
│   ├── vector_store.py              # ChromaDB 向量存储操作（双集合）
│   ├── document_loader.py           # 多格式文档解析与分块
│   └── mcp_server/
│       ├── server.py                # FastMCP 主入口，注册 5 个工具
│       ├── tools.py                 # 工具函数实现（异步、读 JSON、偏好匹配）
│       ├── client.py                # MCP 客户端封装（优先MCP协议，失败回退到 tools.py）
│       ├── init_attractions.py      # 景点数据→ChromaDB 初始化脚本
│       ├── smart_plan.py            # 第三方真实数据源（飞猪+高德+同程+途牛）
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
├── backend/                         # FastAPI 后端
│   └── server.py                    # 13 个 REST API 端点 + MCP 生命周期管理 + 异步 RAG 任务
├── frontend/                        # React 前端
│   ├── app/                         # Next.js 14 App Router
│   │   ├── page.tsx                 # 首页（项目导航）
│   │   ├── knowseeker/page.tsx      # 知识问答界面
│   │   ├── tripmind/page.tsx        # 旅游规划界面（SSE 流式）
│   │   ├── settings/page.tsx        # 三层配置界面（推理+向量化+重排序）
│   │   └── layout.tsx               # 全局布局 + 侧边栏
│   ├── components/
│   │   ├── ui/                      # shadcn/ui 组件库
│   │   └── app-sidebar.tsx          # 应用侧边栏
│   ├── lib/
│   │   └── config.ts                # API 基础 URL 配置
│   └── package.json
├── tripmind/                        # 课设二：多 Agent 旅游规划
│   ├── orchestrator.py              # LangGraph 状态机编排器
│   ├── prompts.py                   # 6 个 Agent 系统提示词（含 JSON 输出格式）
│   ├── types.py                     # TravelRequest / TravelState 类型定义
│   └── agents/
│       ├── base.py                  # BaseAgent 基类（LLM + MCP + 日志 + 容错）
│       ├── transport.py             # TransportAgent：航班/高铁查询推荐
│       ├── hotel.py                 # HotelAgent：酒店搜索推荐
│       ├── weather.py               # WeatherAgent：天气预报分析
│       ├── itinerary.py             # ItineraryAgent：每日行程规划
│       ├── budget.py                # BudgetAgent：费用汇总预算检查
│       └── summarizer.py            # SummarizerAgent：Markdown 方案生成
├── knowseeker/                      # 课设一：单 Agent RAG 问答
│   ├── agent.py                     # LangGraph Agentic RAG 状态机
│   └── rag_chain.py                 # RAG 管道（混合检索 + RRF 融合 + 重排序）
├── design/                          # 设计文档
│   ├── 01-tech-stack.md
│   ├── 02-knowseeker.md
│   ├── 03-tripmind.md
│   ├── 04-tripmind-implementation.md
│   └── 05-tripmind-progress.md
├── data/
│   └── chromadb/                    # ChromaDB 持久化数据
├── .env.example
├── Makefile
├── pyproject.toml
└── README.md
```

---

## App Context — 三层架构

`common/context.py` 是全局服务上下文，集中管理所有服务实例，替代模块级单例：

```
AppContext
├── llm: LLMClient           # 推理层（DeepSeek/Ollama 热切换）
├── embedding: EmbeddingClient # 向量化层（Ollama 本地）
├── reranker: Reranker       # 重排序层（Cross-Encoder，可开关）
├── bm25: BM25Store          # 稀疏检索（Okapi BM25）
├── vector_store: VectorStore # 稠密检索（ChromaDB）
└── mcp_available: bool       # MCP 协议可用状态
```

获取方式：`from common.context import get_context` → `ctx = get_context()`

三层独立配置，各自持久化到 `.env`：
- 推理层：`LLM_BACKEND`, `OLLAMA_*`, `DEEPSEEK_*`
- 向量化层：`EMBEDDING_MODEL`, `OLLAMA_BASE_URL`
- 重排序层：`RERANKER_MODEL`, `RERANKER_ENABLED`

---

## KnowSeeker 架构详解

### LangGraph 状态流转

```
analyze_question → retrieve → evaluate_results
     ↑                          │
     └──── reformulate ←────────┘  (need_more_search=True)
                         │
                         └→ generate_answer → END
```

- `analyze_question` — LLM 分析问题，生成检索计划（关键词、策略、轮次数）
- `retrieve` — 混合检索：BM25 + ChromaDB 并行 → RRF 融合 → Cross-Encoder 重排序
- `evaluate_results` — LLM 判断检索结果是否足够回答
- `reformulate` — LLM 重构查询关键词，进行第二轮检索
- `generate_answer` — LLM 综合多轮结果生成回答 + 引用

### 混合检索 + 重排序流程

```
用户问题
  ├── BM25 Okapi 稀疏检索 (bm25_store.py)
  │     关键词匹配，擅长精确术语、专有名词
  │     → 返回 Top-K 候选
  │
  ├── ChromaDB 稠密向量检索 (vector_store.py)
  │     语义相似度，擅长理解意图、近义表达
  │     → 返回 Top-K 候选
  │
  └── RRF 融合 (rag_chain.py — _hybrid_merge)
        Reciprocal Rank Fusion: score = Σ 1/(k + rank_i)
        合并去重，兼顾两种检索优势
        → 融合候选集
           │
           └── Cross-Encoder 重排序 (reranker.py)
                 sentence-transformers 逐对打分精排
                 → 返回最终 Top-K
```

关键文件：
- `rag_chain.py` — `search()` 调用 `_hybrid_merge()` 执行混合检索 + RRF + 重排序
- `bm25_store.py` — `search(query, top_k)` 返回 `[{content, score, ...}]`
- `reranker.py` — `rerank(query, documents, top_k)` 返回精排后的 `[{content, score, ...}]`

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
    └── planning_agents       顺序执行（依赖前序结果）
        ├── ItineraryAgent    search_attractions + 天气+交通
        ├── BudgetAgent       汇总交通+住宿+行程费用
        │       ↓
        ├── route_after_budget  超预算？→ budget_adjust
        │       ↓
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
  │                          连续3次失败 → 标记不可用，永久回退到 tools.py
  │
  ├─ 2. call_llm(messages) ──→ LLM 分析/格式化结果
  │                               │
  │                         失败 → 捕获异常，回退到内置逻辑
  │
  └─ 3. 返回结构化结果 → 存入 state
```

关键设计：
- `safe_execute` 包裹 `execute`，单 Agent 失败不阻塞整体流程
- `_copy_state` 为每个子 Agent 清空 `agent_logs`，避免日志重复累加

### 6 个 Agent

| Agent | 文件 | MCP 工具 | LLM 角色 | 依赖 |
|-------|------|----------|----------|------|
| 天气 | `weather.py` | `get_weather` | 穿衣+出行建议 | 无 |
| 交通 | `transport.py` | `search_flights` + `search_trains` | 推荐最优方案 | 无 |
| 住宿 | `hotel.py` | `search_hotels` | 按预算筛选推荐 | 无 |
| 行程 | `itinerary.py` | `search_attractions` | 规划每日行程 | 天气 + 交通 |
| 预算 | `budget.py` | 无（聚合结果） | 超支分析建议 | 交通 + 住宿 + 行程 |
| 汇总 | `summarizer.py` | 无（聚合全部结果） | 生成 Markdown 方案 | 全部 |

---

## 运行

```bash
# 后端 API（自动管理 MCP Server 子进程）
uv run uvicorn backend.server:app --host 0.0.0.0 --port 8000

# 单独启动 MCP Server（可选，后端会自动启动）
uv run python -m common.mcp_server.server

# 初始化景点数据到 ChromaDB（可选，需要 Ollama 运行中）
ollama serve
uv run python -m common.mcp_server.init_attractions

# 前端（Next.js 14 + shadcn/ui）
cd frontend
pnpm install  # 首次安装依赖
pnpm dev  # 访问 http://localhost:3000
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

第三方真实数据源（`smart_plan.py`）：飞猪、高德、同程、途牛。`get_weather` 和 `search_attractions` 支持通过 `.env` 中的 `WEATHER_API_KEY` 和 `AMAP_API_KEY` 接入实时数据。

---

## API 端点

| 方法 | 路径 | 功能 |
|------|------|------|
| `POST` | `/api/chat` | 创建 RAG 问答异步任务，返回 `taskId` |
| `GET` | `/api/chat/{task_id}` | 轮询任务状态和结果 |
| `POST` | `/api/documents/upload` | 上传文档到知识库 |
| `GET` | `/api/documents` | 列出已索引文档 |
| `DELETE` | `/api/documents/{doc_id}` | 删除指定文档 |
| `POST` | `/api/travel/plan` | 一次性旅行规划 |
| `POST` | `/api/travel/plan/stream` | SSE 流式旅行规划 |
| `POST` | `/api/travel/adjust` | 追问调整旅行方案 |
| `GET` | `/api/models` | 获取可用模型列表 |
| `GET` | `/api/settings` | 获取三层配置（推理+向量化+重排序） |
| `POST` | `/api/settings` | 更新三层配置（持久化到 .env） |
| `GET` | `/api/health` | 健康检查 |

---

## 开发约定

- **Python 3.14** + **uv** 包管理（不用 pip）
- 类型标注 + 中文注释
- 配置通过 `.env` + `python-dotenv` 管理
- **服务获取**：统一通过 `get_context()` 获取 LLM / Embedding / Reranker / BM25 / ChromaDB 实例，不直接导入模块级单例
- **Agent 开发**：继承 `BaseAgent`，重写 `execute(state)` 方法
  - 数据获取走 `self.call_mcp(tool_name, args)`
  - LLM 处理走 `self.call_llm(messages)`
  - 日志记录走 `self.add_log(state, message)`
- **工具函数**：添加新工具到 `common/mcp_server/tools.py`，同时在 `server.py` 注册
- **模拟数据**：添加新数据到 `common/mcp_server/mock_data/`
- **MCP 客户端**：`common/mcp_server/client.py` 的 `call_tool()` 是统一入口
- **LLM 调用**：失败时自动走回退逻辑，确保功能可用
- **前端开发**：组件使用 shadcn/ui，页面放在 `frontend/app/` 下。API 基础 URL 统一在 `frontend/lib/config.ts` 中配置（`API_BASE` / `API_BASE_API`）
