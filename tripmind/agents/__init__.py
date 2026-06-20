"""TripMind 多 Agent 模块。

每个 Agent 继承 BaseAgent，通过 MCP 协议调用工具 + LLM 分析。
如果 MCP Server 不可用，自动回退到 tools.py 直接调用。
"""

from tripmind.agents.transport import transport_agent
from tripmind.agents.hotel import hotel_agent
from tripmind.agents.weather import weather_agent
from tripmind.agents.itinerary import itinerary_agent
from tripmind.agents.budget import budget_agent
from tripmind.agents.summarizer import summarizer_agent

__all__ = [
    "transport_agent",
    "hotel_agent",
    "weather_agent",
    "itinerary_agent",
    "budget_agent",
    "summarizer_agent",
]
