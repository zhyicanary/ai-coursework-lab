"""LangGraph 编排器 — 多 Agent 协同调度核心。

使用 BaseAgent 实例，通过 MCP 协议调用工具，
支持自动回退到直接 tools.py 调用。
支持 astream 实时进度流，用于前端渐进更新。
"""

import re
from langgraph.graph import StateGraph, START, END
import asyncio

from tripmind.types import TravelRequest, TravelState
from tripmind.agents.transport import transport_agent
from tripmind.agents.hotel import hotel_agent
from tripmind.agents.weather import weather_agent
from tripmind.agents.itinerary import itinerary_agent
from tripmind.agents.budget import budget_agent
from tripmind.agents.summarizer import summarizer_agent


# 所有 Agent 实例
AGENTS = {
    "weather": weather_agent,
    "transport": transport_agent,
    "hotel": hotel_agent,
    "itinerary": itinerary_agent,
    "budget": budget_agent,
    "summarizer": summarizer_agent,
}


def _copy_state(state: TravelState) -> TravelState:
    """为子 Agent 创建干净的 state 副本（清空调试日志，避免重复累加）。"""
    return {
        **state,
        "agent_logs": [],
    }


# ─── 图节点 ─────────────────────────────────────────────


def orchestrator_node(state: TravelState) -> TravelState:
    """调度者节点：初始化编排，记录启动日志。"""
    logs = state.get("agent_logs", [])
    logs.append({"step": "🎯调度", "message": f"需求分析完成，准备调度 {len(AGENTS)} 个子任务"})
    return {**state, "agent_logs": logs, "current_step": "dispatch"}


def dispatch_to_agents(state: TravelState) -> str:
    """条件路由：根据 current_step 决定下一步。"""
    current = state.get("current_step", "")
    routing = {
        "dispatch": "parallel",
        "parallel": "parallel",
        "planning": "planning",
        "budget_check": "budget_check",
        "budget_adjust": "budget_adjust",
        "summarizer": "summarizer",
        "done": END,
    }
    return routing.get(current, "parallel")


async def parallel_agents(state: TravelState) -> TravelState:
    """并行执行无依赖的 Agent（天气、交通、住宿）。

    使用 asyncio.gather 同时启动三个独立 Agent，
    每个 Agent 通过深拷贝的 state 避免日志串扰。
    """
    logs = list(state.get("agent_logs", []))
    logs.append({"step": "🎯调度", "message": "并行启动 🌤️天气 ✈️交通 🏨住宿 Agent"})

    weather_result, transport_result, hotel_result = await asyncio.gather(
        AGENTS["weather"].safe_execute(_copy_state(state)),
        AGENTS["transport"].safe_execute(_copy_state(state)),
        AGENTS["hotel"].safe_execute(_copy_state(state)),
    )

    merged = {**state, "agent_logs": logs}

    for src_key, result in [
        ("weather_result", weather_result),
        ("transport_result", transport_result),
        ("hotel_result", hotel_result),
    ]:
        if result.get(src_key) is not None:
            merged[src_key] = result[src_key]
        merged["agent_logs"].extend(result.get("agent_logs", []))

    merged["current_step"] = "planning"
    return merged


async def planning_agents(state: TravelState) -> TravelState:
    """规划节点：顺序执行行程 → 预算（预算依赖行程门票数据）。"""
    logs = list(state.get("agent_logs", []))

    # 行程 Agent（依赖天气+交通）
    logs.append({"step": "🎯调度", "message": "启动 🗺️行程规划 Agent"})
    it_state = await AGENTS["itinerary"].safe_execute(_copy_state(state))
    state["itinerary_result"] = it_state.get("itinerary_result")
    logs.extend(it_state.get("agent_logs", []))

    # 预算 Agent（依赖交通+住宿+行程）
    logs.append({"step": "🎯调度", "message": "启动 💰预算核算 Agent"})
    bd_state = await AGENTS["budget"].safe_execute(_copy_state(state))
    state["budget_result"] = bd_state.get("budget_result")
    logs.extend(bd_state.get("agent_logs", []))

    state["agent_logs"] = logs
    state["current_step"] = "budget_check"
    return state


def route_after_budget(state: TravelState) -> str:
    """预算条件路由：超预算 → budget_adjust 节点，预算内 → 直接汇总。"""
    budget_result = state.get("budget_result", {})
    if budget_result and budget_result.get("is_over_budget", False):
        return "budget_adjust"
    return "summarizer"


async def budget_adjust_node(state: TravelState) -> TravelState:
    """超预算调整节点：生成调整提示，标记已调整状态让汇总 Agent 输出预警。"""
    budget_result = state.get("budget_result", {})
    logs = list(state.get("agent_logs", []))
    remaining = budget_result.get("remaining", 0)

    logs.append({
        "step": "💰预算调整",
        "message": f"超预算 {abs(remaining)} 元，已标记预算预警，汇总时将给出调整建议",
        "status": "done",
    })

    state["budget_adjusted"] = True
    state["agent_logs"] = logs
    state["current_step"] = "summarizer"
    return state


async def summarizer_node(state: TravelState) -> TravelState:
    """汇总节点：运行汇总 Agent 生成最终方案。"""
    logs = list(state.get("agent_logs", []))
    logs.append({"step": "🎯调度", "message": "启动 📝汇总生成 Agent"})
    sm_state = await AGENTS["summarizer"].safe_execute(_copy_state(state))
    state["final_plan"] = sm_state.get("final_plan")
    logs.extend(sm_state.get("agent_logs", []))

    state["agent_logs"] = logs
    state["current_step"] = "done"
    return state


# ─── 图构建 ─────────────────────────────────────────────


def build_travel_graph() -> StateGraph:
    """构建旅游助手 LangGraph 状态机。

    执行流程：
      START → orchestrator → parallel
        → planning(itinerary→budget) → check_budget
          ├─ 超预算 → budget_adjust → summarizer → END
          └─ 预算内 → summarizer → END
    """
    workflow = StateGraph(TravelState)

    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("parallel", parallel_agents)
    workflow.add_node("planning", planning_agents)
    workflow.add_node("budget_adjust", budget_adjust_node)
    workflow.add_node("summarizer", summarizer_node)

    workflow.add_edge(START, "orchestrator")
    workflow.add_conditional_edges(
        "orchestrator",
        dispatch_to_agents,
        {"parallel": "parallel"},
    )
    workflow.add_edge("parallel", "planning")
    workflow.add_conditional_edges(
        "planning",
        route_after_budget,
        {"budget_adjust": "budget_adjust", "summarizer": "summarizer"},
    )
    workflow.add_edge("budget_adjust", "summarizer")
    workflow.add_edge("summarizer", END)

    return workflow.compile()


def _build_initial_state(request: TravelRequest) -> TravelState:
    """构造 LangGraph 初始状态。"""
    return {
        "request": request,
        "weather_result": None,
        "transport_result": None,
        "hotel_result": None,
        "itinerary_result": None,
        "budget_result": None,
        "final_plan": None,
        "agent_logs": [],
        "current_step": "dispatch",
        "budget_adjusted": False,
        "adjustment_history": [],
    }


async def run_travel_planner(request: TravelRequest) -> dict:
    """运行旅游规划器（一次性返回最终结果）。

    使用 graph.ainvoke 执行完整流程，适合不需要中间进度的场景。
    """
    graph = build_travel_graph()
    result = await graph.ainvoke(_build_initial_state(request))
    return result


# ─── 节点名→进度映射 ──────────────────────────────────

_NODE_PROGRESS = {
    "orchestrator": (0.05, "🎯 调度分析"),
    "parallel": (0.35, "🌤️✈️🏨 并行获取数据"),
    "planning": (0.65, "🗺️💰 行程与预算规划"),
    "budget_adjust": (0.80, "💰 预算调整"),
    "summarizer": (0.95, "📝 方案汇总生成"),
}


def _report_progress(progress, node_name: str):
    """向 gr.Progress 回调报告节点进度。"""
    if progress is None:
        return
    pct, desc = _NODE_PROGRESS.get(node_name, (None, ""))
    if pct is not None:
        progress(pct, desc)


async def run_travel_planner_stream(request: TravelRequest, progress=None):
    """运行旅游规划器（逐 Agent 流式返回中间状态）。

    不使用 graph.astream（按节点 yield），改为手动编排，
    每个 Agent 完成后立即 yield，让前端实时更新单个 Agent 状态。

    DAG 依赖：
      并行层: weather, transport, hotel（无依赖，可并行）
      规划层: itinerary（依赖 weather+transport）→ budget（依赖 transport+hotel+itinerary）
      汇总层: summarizer（依赖全部）
    """
    state = _build_initial_state(request)

    # ── 1. 并行层：weather, transport, hotel ──
    _report_progress(progress, "parallel")

    # 每个 Agent 对应的 result key
    parallel_specs = [
        ("weather", "weather_result"),
        ("transport", "transport_result"),
        ("hotel", "hotel_result"),
    ]

    # 创建并行任务
    tasks = {
        key: asyncio.create_task(AGENTS[name].safe_execute(_copy_state(state)))
        for name, key in parallel_specs
    }

    # 逐个等待完成（哪个先完成就先 yield）
    remaining = dict(tasks)
    while remaining:
        done_keys = []
        for key, task in remaining.items():
            if task.done():
                done_keys.append(key)
        if not done_keys:
            # 没有完成的，等最快的一个
            await asyncio.wait(remaining.values(), return_when=asyncio.FIRST_COMPLETED)
            for key, task in remaining.items():
                if task.done():
                    done_keys.append(key)

        for key in done_keys:
            result = remaining[key].result()
            if result.get(key) is not None:
                state[key] = result[key]
                yield {key: result[key]}
            del remaining[key]

    # ── 2. 规划层：itinerary → budget（顺序）──
    _report_progress(progress, "planning")

    it_state = await AGENTS["itinerary"].safe_execute(_copy_state(state))
    if it_state.get("itinerary_result") is not None:
        state["itinerary_result"] = it_state["itinerary_result"]
        yield {"itinerary_result": it_state["itinerary_result"]}

    bd_state = await AGENTS["budget"].safe_execute(_copy_state(state))
    if bd_state.get("budget_result") is not None:
        state["budget_result"] = bd_state["budget_result"]
        yield {"budget_result": bd_state["budget_result"]}

    # ── 3. 预算检查 ──
    budget_result = state.get("budget_result", {})
    if budget_result and budget_result.get("is_over_budget", False):
        _report_progress(progress, "budget_adjust")
        state["budget_adjusted"] = True

    # ── 4. 汇总层：summarizer ──
    _report_progress(progress, "summarizer")
    sm_state = await AGENTS["summarizer"].safe_execute(_copy_state(state))
    if sm_state.get("final_plan") is not None:
        state["final_plan"] = sm_state["final_plan"]
        yield {"final_plan": sm_state["final_plan"]}


# ─── 追问调整（UC-05）───────────────────────────────────

# Agent 依赖关系（用于确定重算范围）
_AGENT_DEPENDENCIES = {
    "weather": [],
    "transport": [],
    "hotel": [],
    "itinerary": ["weather", "transport"],
    "budget": ["transport", "hotel", "itinerary"],
    "summarizer": ["weather", "transport", "hotel", "itinerary", "budget"],
}


async def adjust_plan(previous_state: dict, instruction: str) -> dict:
    """追问调整：根据用户调整指令，重新运行受影响 Agent。

    Args:
        previous_state: 上次规划返回的完整 state
        instruction: 用户调整指令，如"预算提高到 5000"、"换便宜的酒店"

    Returns:
        更新后的 state
    """
    # 1. 解析指令，确定受影响 Agent
    affected = _parse_adjustment(instruction)
    request = dict(previous_state["request"])
    request = _apply_adjustment(instruction, request)

    # 2. 补齐依赖 Agent
    to_run = set(affected)
    for agent in list(to_run):
        deps = _AGENT_DEPENDENCIES.get(agent, [])
        for dep in deps:
            # 如果依赖项在旧 state 中不存在或也被影响，也要重跑
            result_key = f"{dep}_result"
            if previous_state.get(result_key) is None or dep in to_run:
                to_run.add(dep)

    # 3. 准备新 state：保留未受影响的旧结果
    new_state = dict(previous_state)
    new_state["request"] = request
    new_state["agent_logs"] = []
    new_state["current_step"] = "adjust"
    history = list(new_state.get("adjustment_history", []))
    history.append(instruction)
    new_state["adjustment_history"] = history

    # 清空需要重算的 Agent 结果
    for agent in to_run:
        new_state[f"{agent}_result"] = None
    if "summarizer" in to_run:
        new_state["final_plan"] = None

    # 4. 记录调整日志
    logs = []
    logs.append({
        "step": "🔄追问调整",
        "message": f"收到调整指令：「{instruction}」，重算 Agent：{', '.join(to_run)}",
        "status": "start",
    })

    # 5. 第一次并行：依赖无关的 Agent（weather, transport, hotel）
    parallel_batch = [a for a in to_run if a in ("weather", "transport", "hotel")]
    if parallel_batch:
        logs.append({"step": "🎯调度", "message": f"并行启动 {' '.join(f'🌤️天气' if a=='weather' else '✈️交通' if a=='transport' else '🏨住宿' for a in parallel_batch)} Agent"})
        tasks = [AGENTS[a].safe_execute(_copy_state(new_state)) for a in parallel_batch]
        results = await asyncio.gather(*tasks)
        for agent, result in zip(parallel_batch, results):
            rkey = f"{agent}_result"
            if result.get(rkey) is not None:
                new_state[rkey] = result[rkey]
            logs.extend(result.get("agent_logs", []))

    # 6. 顺序执行：itinerary → budget → summarizer
    if "itinerary" in to_run:
        logs.append({"step": "🎯调度", "message": "启动 🗺️行程规划 Agent"})
        it_state = await AGENTS["itinerary"].safe_execute(_copy_state(new_state))
        if it_state.get("itinerary_result") is not None:
            new_state["itinerary_result"] = it_state["itinerary_result"]
        logs.extend(it_state.get("agent_logs", []))

    if "budget" in to_run:
        logs.append({"step": "🎯调度", "message": "启动 💰预算核算 Agent"})
        bd_state = await AGENTS["budget"].safe_execute(_copy_state(new_state))
        if bd_state.get("budget_result") is not None:
            new_state["budget_result"] = bd_state["budget_result"]
        logs.extend(bd_state.get("agent_logs", []))

    if "summarizer" in to_run:
        logs.append({"step": "🎯调度", "message": "启动 📝汇总生成 Agent"})
        sm_state = await AGENTS["summarizer"].safe_execute(_copy_state(new_state))
        if sm_state.get("final_plan") is not None:
            new_state["final_plan"] = sm_state["final_plan"]
        logs.extend(sm_state.get("agent_logs", []))

    new_state["agent_logs"] = logs
    new_state["current_step"] = "done"
    return new_state


def _parse_adjustment(instruction: str) -> list[str]:
    """解析调整指令，返回需要重新运行的 Agent key 列表。

    Keywords → 受影响 Agent 映射：
      - 酒店/住宿/民宿 → hotel
      - 预算/加钱/省钱 → hotel, budget
      - 行程/景点/偏好 → itinerary
      - 交通/飞机/高铁 → transport
      - 天气 → weather
      - 天数/延长/缩短 → weather, hotel, itinerary
      - 目的地/城市/改到 → weather, transport, hotel, itinerary
    """
    instr = instruction.lower()
    affected = set()

    patterns = [
        (["酒店", "住宿", "民宿", "旅馆"], ["hotel"]),
        (["预算", "加钱", "省钱", "便宜", "涨价", "降价",
          "提高预算", "降低预算", "增加预算", "减少预算",
          "控制预算", "节省"], ["hotel", "budget"]),
        (["行程", "景点", "想去", "玩", "参观", "游览",
          "偏好", "美食", "文化", "自然", "喜欢",
          "感兴趣"], ["itinerary"]),
        (["交通", "飞机", "高铁", "动车", "航班", "火车",
          "打车", "自驾"], ["transport"]),
        (["天气"], ["weather"]),
        (["天数", "延长", "缩短", "增加一天", "减少一天",
          "多一天", "少一天"], ["weather", "hotel", "itinerary"]),
        (["目的地", "城市", "换个", "改到", "改成",
          "去", "换个地方"], ["weather", "transport", "hotel", "itinerary"]),
    ]

    for keywords, agents in patterns:
        if any(kw in instr for kw in keywords):
            affected.update(agents)

    # 任何调整都需要重算 budget + summarizer（除非只改天气）
    if affected and affected != {"weather"}:
        affected.add("budget")
        affected.add("summarizer")
    elif affected == {"weather"}:
        affected.add("itinerary")
        affected.add("budget")
        affected.add("summarizer")

    # 默认：匹配不到关键词时走行程重算
    if not affected:
        affected = {"itinerary", "budget", "summarizer"}

    return list(affected)


def _apply_adjustment(instruction: str, request: dict) -> dict:
    """解析调整指令并修改 request 中的对应字段。

    支持：
      - "预算提高到 5000" → 修改 budget
      - "5天" / "改到 4天" → 修改 days
      - "去西安" / "改成上海" → 修改 destination
      - "偏好美食、历史" → 修改 preferences
    """
    instr = instruction
    request = dict(request)  # 拷贝，避免修改原始引用

    # 预算调整："预算提高到 5000" / "预算 5000" / "5000元"
    budget_match = re.search(r'预算(?:提高|增加|改为|调到|升到|加到|调整)?[到至]?\s*(\d+)', instr)
    if not budget_match:
        budget_match = re.search(r'(\d+)\s*元', instr)
    if budget_match:
        request["budget"] = float(budget_match.group(1))

    # 天数调整："N天"
    days_match = re.search(r'(\d+)\s*天', instr)
    if days_match:
        request["days"] = int(days_match.group(1))

    # 目的地调整："去西安" / "改成西安" / "改成去西安"
    dest_match = re.search(r'(?:改成去|换成去|改成|改到|改去|换个|换成|去)(\S{2,4})', instr)
    if dest_match:
        candidate = dest_match.group(1)
        if candidate not in ("玩", "看看", "旅行", "旅游", "哪里", "哪儿"):
            request["destination"] = candidate

    # 偏好调整："偏好XX、XX"
    pref_match = re.search(r'偏好[设为是]?\s*([^。，\d]+)', instr)
    if pref_match:
        prefs = [p.strip() for p in re.split(r'[、,，/]', pref_match.group(1)) if p.strip()]
        if prefs:
            request["preferences"] = prefs

    return request
