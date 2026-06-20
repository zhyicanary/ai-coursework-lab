"""LangGraph 编排器 — 多 Agent 协同调度核心。

使用 BaseAgent 实例，通过 MCP 协议调用工具，
支持自动回退到直接 tools.py 调用。
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
import asyncio

from tripmind.agents.transport import transport_agent
from tripmind.agents.hotel import hotel_agent
from tripmind.agents.weather import weather_agent
from tripmind.agents.itinerary import itinerary_agent
from tripmind.agents.budget import budget_agent
from tripmind.agents.summarizer import summarizer_agent


class TravelRequest(TypedDict):
    """用户旅行需求"""
    destination: str
    days: int
    budget: float
    preferences: list[str]
    departure_city: str


class TravelState(TypedDict):
    """Multi-Agent 协作全局状态"""
    request: TravelRequest
    weather_result: dict | None
    transport_result: dict | None
    hotel_result: dict | None
    itinerary_result: dict | None
    budget_result: dict | None
    final_plan: str | None
    agent_logs: list[dict]
    current_step: str


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
        "agent_logs": [],  # 清空日志，子 Agent 的日志在返回后由编排器合并
    }


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
        "sequential": "sequential",
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

    # 给每个 Agent 独立的 state 副本（避免日志共享污染）
    weather_result, transport_result, hotel_result = await asyncio.gather(
        AGENTS["weather"].safe_execute(_copy_state(state)),
        AGENTS["transport"].safe_execute(_copy_state(state)),
        AGENTS["hotel"].safe_execute(_copy_state(state)),
    )

    # 合并结果：保留非 None 的结果字段
    merged = {**state, "agent_logs": logs}

    for src_key, result in [
        ("weather_result", weather_result),
        ("transport_result", transport_result),
        ("hotel_result", hotel_result),
    ]:
        if result.get(src_key) is not None:
            merged[src_key] = result[src_key]
        # 合并日志
        merged["agent_logs"].extend(result.get("agent_logs", []))

    merged["current_step"] = "sequential"
    return merged


async def sequential_agents(state: TravelState) -> TravelState:
    """顺序执行有依赖的 Agent（行程 → 预算 → 汇总）。

    行程依赖天气和交通，预算依赖交通+住宿+行程，汇总依赖全部。
    """
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

    # 汇总 Agent（依赖全部）
    logs.append({"step": "🎯调度", "message": "启动 📝汇总生成 Agent"})
    sm_state = await AGENTS["summarizer"].safe_execute(_copy_state(state))
    state["final_plan"] = sm_state.get("final_plan")
    logs.extend(sm_state.get("agent_logs", []))

    state["agent_logs"] = logs
    state["current_step"] = "done"
    return state


def build_travel_graph() -> StateGraph:
    """构建旅游助手 LangGraph 状态机。

    执行流程：
      START → orchestrator → parallel(weather+transport+hotel) → sequential(itinerary→budget→summarizer) → END
    """
    workflow = StateGraph(TravelState)

    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("parallel", parallel_agents)
    workflow.add_node("sequential", sequential_agents)

    workflow.add_edge(START, "orchestrator")
    workflow.add_conditional_edges(
        "orchestrator",
        dispatch_to_agents,
        {"parallel": "parallel", "sequential": "sequential", END: END},
    )
    workflow.add_conditional_edges(
        "parallel",
        dispatch_to_agents,
        {"sequential": "sequential", END: END},
    )
    workflow.add_conditional_edges(
        "sequential",
        dispatch_to_agents,
        {END: END},
    )

    return workflow.compile()


async def run_travel_planner(request: TravelRequest) -> dict:
    """运行旅游规划器。

    初始化状态，通过 LangGraph 状态机编排所有 Agent 执行。
    """
    graph = build_travel_graph()

    initial_state: TravelState = {
        "request": request,
        "weather_result": None,
        "transport_result": None,
        "hotel_result": None,
        "itinerary_result": None,
        "budget_result": None,
        "final_plan": None,
        "agent_logs": [],
        "current_step": "dispatch",
    }

    result = await graph.ainvoke(initial_state)
    return result
