"""TripMind 核心数据结构定义 — 所有 TypedDict 集中管理。

由 Tripmind 的 5 个阶段（Phase 3-5）共享的类型定义。
"""

from typing import TypedDict


class TravelRequest(TypedDict):
    """用户旅行需求。"""
    destination: str
    days: int
    budget: float
    preferences: list[str]
    departure_city: str


class TravelState(TypedDict):
    """Multi-Agent 协作全局状态，在 LangGraph 图中传递。

    所有 Agent 读取/写入此状态，编排器负责调度和汇聚。
    """
    request: TravelRequest
    weather_result: dict | None
    transport_result: dict | None
    hotel_result: dict | None
    itinerary_result: dict | None
    budget_result: dict | None
    final_plan: str | None
    agent_logs: list[dict]
    current_step: str
    budget_adjusted: bool          # 是否已执行预算调整
    adjustment_history: list[str]  # 追问调整记录
