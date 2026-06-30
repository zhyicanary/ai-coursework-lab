"""MCP Server 主入口 — 注册并启动 FastMCP 服务。

使用方式：
  # 启动 Streamable HTTP 传输（常驻服务，端口 8765）
  uv run python -m common.mcp_server.server

  # 或作为模块导入集成到应用中
  from common.mcp_server.server import mcp_server, run_server
"""

import asyncio
import sys
from pathlib import Path

# 确保项目根目录在路径中
ROOT_DIR = Path(__file__).parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from mcp.server.fastmcp import FastMCP

from common.mcp_server.tools import (
    search_flights,
    search_trains,
    search_hotels,
    get_weather,
    search_attractions,
)

# MCP Server 配置
MCP_HOST = "127.0.0.1"
MCP_PORT = 8765

# 创建 MCP Server 实例
mcp_server = FastMCP(
    name="TripMind Tools",
    instructions="""TripMind 旅游助手工具集。

提供航班查询、高铁查询、酒店搜索、天气预报、景点检索五大功能。
数据源三级降级：mcp-travel-smart-plan（飞猪/高德）→ 自有 API Key → 本地模拟数据。
""",
    host=MCP_HOST,
    port=MCP_PORT,
)


def register_tools():
    """将所有工具注册到 MCP Server。"""
    _ = mcp_server

    @_.tool(
        name="search_flights",
        description="""查询航班信息。
根据出发城市和目的城市，查询可用的航班选项。
返回航班号、出发/到达时间、价格和航空公司。
如果日期未指定，返回通用班期信息。""",
    )
    async def _search_flights(departure: str, destination: str, date: str | None = None) -> list[dict]:
        return await search_flights(departure, destination, date)

    @_.tool(
        name="search_trains",
        description="""查询高铁/火车信息。
根据出发城市和目的城市，查询可用的火车选项。
返回车次、出发/到达站、时间、历时、价格和类型（高铁/动车/直达/快速）。""",
    )
    async def _search_trains(departure: str, destination: str, date: str | None = None) -> list[dict]:
        return await search_trains(departure, destination, date)

    @_.tool(
        name="search_hotels",
        description="""搜索酒店。
根据城市名搜索可用酒店，支持按最高价格过滤。
返回酒店名称、价格、位置、评分和距离市中心距离。
按评分降序排列。""",
    )
    async def _search_hotels(
        city: str,
        check_in: str | None = None,
        check_out: str | None = None,
        max_price: float | None = None,
        preferences: list[str] | None = None,
    ) -> list[dict]:
        return await search_hotels(city, check_in, check_out, max_price, preferences)

    @_.tool(
        name="get_weather",
        description="""查询天气预报。
根据城市名和天数查询天气预报。
返回每日温度、天气状况、降水概率、穿衣建议和出行影响评估。
最多支持查询7天预报。""",
    )
    async def _get_weather(city: str, days: int = 3) -> dict:
        return await get_weather(city, days)

    @_.tool(
        name="search_attractions",
        description="""搜索景点信息。
根据城市名搜索景点，支持按偏好关键词筛选（如"美食"、"历史文化"、"自然风光"）。
返回景点名称、类别、门票价格、游玩时长、详细介绍和偏好匹配度。""",
    )
    async def _search_attractions(
        city: str,
        preferences: list[str] | None = None,
        top_k: int = 10,
    ) -> list[dict]:
        return await search_attractions(city, preferences, top_k)


# 注册所有工具
register_tools()


async def run_server():
    """以 Streamable HTTP 模式运行 MCP Server。"""
    await mcp_server.run_streamable_http_async()


def main():
    """CLI 入口（阻塞式，供子进程启动）。"""
    mcp_server.run(transport="streamable-http")


if __name__ == "__main__":
    main()
