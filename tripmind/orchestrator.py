"""LangGraph 编排器 - 多 Agent 协同调度核心"""

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
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


def orchestrator_node(state: TravelState) -> TravelState:
    """调度者节点：分析需求，拆解任务"""
    logs = state.get("agent_logs", [])
    logs.append({"step": "orchestrator", "message": "需求分析完成，准备调度子任务"})
    return {**state, "agent_logs": logs, "current_step": "dispatch"}


def dispatch_to_agents(state: TravelState) -> dict:
    """条件路由：根据依赖关系决定下一步"""
    current = state.get("current_step", "")
    
    if current == "dispatch":
        return "parallel"
    elif current == "sequential":
        return "sequential"
    elif current == "done":
        return END
    return "parallel"


async def parallel_agents(state: TravelState) -> TravelState:
    """并行执行无依赖的 Agent（天气、交通、住宿）"""
    logs = state.get("agent_logs", [])
    logs.append({"step": "dispatcher", "message": "并行启动天气、交通、住宿 Agent"})
    
    request = state["request"]
    
    weather_result, transport_result, hotel_result = await asyncio.gather(
        weather_agent(request["destination"], request["days"]),
        transport_agent(request["departure_city"], request["destination"], request["days"]),
        hotel_agent(request["destination"], request["days"], request["budget"])
    )
    
    logs.append({"step": "weather", "message": "天气查询完成"})
    logs.append({"step": "transport", "message": "交通查询完成"})
    logs.append({"step": "hotel", "message": "住宿查询完成"})
    
    return {
        **state,
        "weather_result": weather_result,
        "transport_result": transport_result,
        "hotel_result": hotel_result,
        "agent_logs": logs,
        "current_step": "sequential"
    }


async def sequential_agents(state: TravelState) -> TravelState:
    """顺序执行有依赖的 Agent（行程、预算、汇总）"""
    logs = state.get("agent_logs", [])
    request = state["request"]
    
    logs.append({"step": "dispatcher", "message": "启动行程规划 Agent"})
    itinerary_result = await itinerary_agent(
        request["destination"],
        request["days"],
        state.get("weather_result"),
        state.get("transport_result")
    )
    logs.append({"step": "itinerary", "message": "行程规划完成"})
    
    logs.append({"step": "dispatcher", "message": "启动预算核算 Agent"})
    budget_result = await budget_agent(
        state.get("transport_result"),
        state.get("hotel_result"),
        itinerary_result,
        request["budget"]
    )
    logs.append({"step": "budget", "message": "预算核算完成"})
    
    logs.append({"step": "dispatcher", "message": "启动汇总生成 Agent"})
    final_plan = await summarizer_agent(
        request,
        state.get("weather_result"),
        state.get("transport_result"),
        state.get("hotel_result"),
        itinerary_result,
        budget_result
    )
    logs.append({"step": "summarizer", "message": "最终方案生成完成"})
    
    return {
        **state,
        "itinerary_result": itinerary_result,
        "budget_result": budget_result,
        "final_plan": final_plan,
        "agent_logs": logs,
        "current_step": "done"
    }


def build_travel_graph() -> StateGraph:
    """构建旅游助手 LangGraph 状态机"""
    workflow = StateGraph(TravelState)
    
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("parallel", parallel_agents)
    workflow.add_node("sequential", sequential_agents)
    
    workflow.add_edge(START, "orchestrator")
    workflow.add_conditional_edges(
        "orchestrator",
        dispatch_to_agents,
        {
            "parallel": "parallel",
            "sequential": "sequential",
            END: END,
        }
    )
    workflow.add_conditional_edges(
        "parallel",
        dispatch_to_agents,
        {
            "sequential": "sequential",
            END: END,
        }
    )
    workflow.add_conditional_edges(
        "sequential",
        dispatch_to_agents,
        {
            END: END,
            "sequential": "sequential",
        }
    )
    
    return workflow.compile()


async def run_travel_planner(request: TravelRequest) -> dict:
    """运行旅游规划器"""
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
        "current_step": "dispatch"
    }
    
    result = await graph.ainvoke(initial_state)
    return result
