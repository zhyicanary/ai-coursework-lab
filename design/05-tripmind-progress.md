# TripMind 实现进度报告

> 更新时间：2026-06-20

---

## 一、当前状态总览

| Phase | 状态 | 完成度 |
|-------|------|--------|
| Phase 1 - 公共模块 | ✅ 已完成 | 100% |
| Phase 2 - MCP Server | ❌ 未开始 | 0% |
| Phase 3 - LangGraph 编排器 | ✅ 已完成 | 90% |
| Phase 4 - Agent 实现 | ✅ 基本完成 | 75% |
| Phase 5 - Gradio 前端 | ⚠️ 主体完成 | 70% |

**总体进度：约 67%**（相比上次更新大幅推进）

---

## 二、已实现功能

### Phase 1 - 公共模块 ✅

| 文件 | 功能 | 状态 |
|------|------|------|
| `common/llm_client.py` | DeepSeek/Ollama LLM 客户端（支持动态切换后端/模型/API Key） | ✅ 完成 |
| `common/embedding_client.py` | BGE 中文向量化（BAAI/bge-small-zh-v1.5） | ✅ 完成 |
| `common/vector_store.py` | ChromaDB 向量存储 | ✅ 完成 |

### Phase 3 - LangGraph 编排器 ✅

| 文件 | 功能 | 状态 |
|------|------|------|
| `tripmind/orchestrator.py` | LangGraph 状态机编排器 | ✅ 完成 |

**编排器核心功能：**

| 功能 | 状态 | 实现方式 |
|------|------|----------|
| DAG 依赖调度 | ✅ | orchestrator → parallel(weather/transport/hotel) → sequential(itinerary/budget/summarizer) |
| 并行执行无依赖任务 | ✅ | `asyncio.gather` 同时启动 3 个 Agent |
| 状态汇聚 | ✅ | TravelState 全局状态在各节点间传递 |
| 条件路由 | ✅ | `dispatch_to_agents` 根据 `current_step` 路由 |
| 超预算分支 | ⚠️ 基础 | budget_agent 有 `is_over_budget` 字段和 suggestions，但未做独立条件边 |
| 追问调整机制 | ❌ 未实现 | UC-05 核心功能待实现 |

### Phase 4 - Agent 实现 ✅

| 文件 | Agent | 状态 | 说明 |
|------|-------|------|------|
| `tripmind/agents/weather.py` | 天气 Agent | ✅ 完成 | 模拟随机天气，提供穿衣/出行建议 |
| `tripmind/agents/transport.py` | 交通 Agent | ✅ 完成 | 内置路线表（北京→成都、上海→成都），推荐最低价方案 |
| `tripmind/agents/hotel.py` | 住宿 Agent | ✅ 完成 | 按预算 40% 筛选酒店，评分最高推荐 |
| `tripmind/agents/itinerary.py` | 行程 Agent | ✅ 完成 | 依赖天气+交通，雨天自动选室内景点 |
| `tripmind/agents/budget.py` | 预算 Agent | ✅ 完成 | 五类费用汇总，超预算时生成调整建议 |
| `tripmind/agents/summarizer.py` | 汇总 Agent | ✅ 完成 | 整合所有结果生成 Markdown 旅行方案 |

**当前 Agent 实现特点：**
- ✅ 全部是 `async def` 异步函数，支持并行
- ✅ 防御性获取数据（`dict.get(key, default)` + None 检查）
- ✅ 数据流走函数参数传递（而非 LLM 调用），执行速度快
- ❌ 没有统一的 `BaseAgent` 基类
- ❌ 不经过 MCP 协议（直接 Python 函数调用）
- ❌ 不经过 LLM（纯模拟数据）

### Phase 5 - Gradio 前端 ⚠️

| 文件 | 功能 | 状态 |
|------|------|------|
| `tripmind/app.py` | LLM 后端切换（DeepSeek/Ollama） | ✅ 完成 |
| `tripmind/app.py` | 模型下拉框动态获取 | ✅ 完成 |
| `tripmind/app.py` | API Key 配置 | ✅ 完成 |
| `tripmind/app.py` | 基础聊天功能 | ✅ 完成 |
| `tripmind/app.py` | 旅行需求输入表单 | ✅ **新增完成** |
| `tripmind/app.py` | Agent 执行状态面板（✅/❌） | ✅ **新增完成** |
| `tripmind/app.py` | Agent 通信日志 | ✅ **新增完成** |
| `tripmind/app.py` | 旅行方案展示（Markdown 渲染） | ✅ **新增完成** |
| `tripmind/app.py` | 追问调整功能 | ❌ 未实现 |

**当前前端布局：**
- Tab 1: **旅行规划** — 表单(目的地/天数/预算/出发地/偏好) → 开始规划 → 状态面板 + 日志 + 方案
- Tab 2: **对话** — 聊天交互
- Tab 3: **设置** — LLM 后端配置

---

## 三、未实现功能

### Phase 2 - MCP Server ❌（最优先级）

| 文件 | 功能 | 优先级 |
|------|------|--------|
| `common/mcp_server/server.py` | MCP Server 主入口（FastMCP） | 🔴 高 |
| `common/mcp_server/tools.py` | 5个旅游工具定义 | 🔴 高 |
| `common/mcp_server/mock_data/flights.json` | 航班模拟数据 | 🔴 高 |
| `common/mcp_server/mock_data/trains.json` | 高铁模拟数据 | 🔴 高 |
| `common/mcp_server/mock_data/hotels.json` | 酒店模拟数据 | 🔴 高 |
| `common/mcp_server/mock_data/weather.json` | 天气模拟数据 | 🟡 中 |
| `common/mcp_server/mock_data/attractions/*.json` | 景点数据（6城市） | 🔴 高 |
| `common/mcp_server/init_attractions.py` | 景点数据→ChromaDB 初始化脚本 | 🟡 中 |

**当前问题：** Agent 是直接函数模拟，没有经过 MCP 协议，不满足课程要求。

### Phase 3 遗留

| 功能 | 优先级 |
|------|--------|
| `tripmind/types.py` 独立数据结构文件 | 🟢 低（目前在 orchestrator.py 内） |
| `tripmind/prompts.py` Agent 系统提示词 | 🟡 中（设计文档有完整版，尚未抽取） |
| 追问调整机制（UC-05） | 🔴 高 |
| 超预算条件分支边 | 🟡 中 |

### Phase 4 遗留

| 功能 | 优先级 |
|------|--------|
| `tripmind/agents/base.py` Agent 基类 | 🟡 中（统一 LLM 调用 + 日志） |
| 通过 LLM + MCP 工具生成真实方案（当前是纯模拟） | 🔴 高（课程要求） |
| 容错机制（单 Agent 失败不阻塞） | 🟡 中 |

### Phase 5 遗留

| 功能 | 优先级 |
|------|--------|
| 追问调整 UI（输入框 + 调整按钮） | 🟡 中 |
| 实时状态推送（当前是全部完成后一次性展示） | 🟢 低 |
| 下载方案 | 🟢 低 |

---

## 四、当前架构说明

### 实际实现路径（快速验证版本）

```
你走的是"快速验证路径"——跳过 MCP 层，Agent 直接调用 Python 函数：

用户表单 → plan_travel()
  → run_travel_planner(request)
    → LangGraph 状态机
      → parallel_agents: weather() + transport() + hotel()    ← 直接函数调用
      → sequential_agents: itinerary() → budget() → summarizer() ← 同上
    → 返回完整 state
  → 提取日志+状态+方案 → Gradio 渲染
```

### 设计文档预期的架构（含 MCP）

```
Agent → MCP 客户端 → MCP Server → 模拟数据/ChromaDB
                   (统一标准化协议)
```

### 两者的核心差距

| 维度 | 当前实现 | 设计文档要求 |
|------|----------|-------------|
| Agent 通信 | Python 直接函数调用 | 通过 LLM + MCP 工具调用 |
| 数据来源 | 硬编码在 py 文件中 | 外置 JSON 模拟数据 |
| 知识库 | 硬编码景点列表 | ChromaDB 向量检索 |
| 方案质量 | 模板拼接 | LLM 生成 + 人工再润色 |

---

## 五、下一步行动

### 优先级 1（课程硬性要求）

1. **Phase 2**: 创建 MCP Server
   - `common/mcp_server/server.py` + `tools.py`
   - `mock_data/` 模拟数据（flights/trains/hotels/weather/attractions）
   - `init_attractions.py` 景点导入脚本
2. **重构 Agent**: 将当前直接函数调用改为通过 MCP 协议调用
   - 或用 `BaseAgent` 基类统一封装 LLM 调用 + MCP 工具调用

### 优先级 2（核心用例）

3. **追问调整**（UC-05）：用户可对方案提出调整指令，仅重算受影响 Agent

### 优先级 3（质量提升）

4. 抽取 `prompts.py`（设计文档有完整 6 套 system prompt）
5. 容错机制
6. 超预算分支条件边

---

## 六、文件清单

### 当前已存在

```
common/
├── __init__.py
├── llm_client.py
├── embedding_client.py
├── vector_store.py
└── mcp_server/
    └── __init__.py

tripmind/
├── __init__.py
├── app.py                       ← 新增旅行规划 Tab
├── orchestrator.py               ← 新增 LangGraph 编排器
├── README.md
├── README_EN.md
└── agents/
    ├── __init__.py               ← 新增 6 个 Agent 导出
    ├── transport.py              ← 新增 交通 Agent
    ├── hotel.py                  ← 新增 住宿 Agent
    ├── weather.py                ← 新增 天气 Agent
    ├── itinerary.py              ← 新增 行程 Agent
    ├── budget.py                 ← 新增 预算 Agent
    └── summarizer.py             ← 新增 汇总 Agent

design/
├── 01-tech-stack.md
├── 02-knowseeker.md
├── 03-tripmind.md
├── 04-tripmind-implementation.md
└── 05-tripmind-progress.md       ← 本文件（已更新）
```

### 计划中需创建

```
common/mcp_server/
├── server.py
├── tools.py
├── init_attractions.py
└── mock_data/
    ├── flights.json
    ├── trains.json
    ├── hotels.json
    ├── weather.json
    └── attractions/
        ├── chengdu.json
        ├── beijing.json
        ├── shanghai.json
        ├── xian.json
        ├── guangzhou.json
        └── hangzhou.json

tripmind/
├── types.py            （可选，数据结构现内嵌在 orchestrator.py）
├── prompts.py           （Agent 系统提示词）
└── agents/
    ├── base.py          （Agent 基类）
```
