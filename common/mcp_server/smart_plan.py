"""mcp-travel-smart-plan 直接调用 — 飞猪+高德+同程+途牛真实数据。

通过直接 import 函数调用代替 uvx 子进程 MCP 嵌套。
每个工具返回原始文本结果，失败返回 None。
"""

import asyncio
from typing import Any

from mcp_travel_smart_plan.server import (
    search_flight,
    search_train,
    search_hotel,
    search_weather,
    search_poi,
)

# 我们的工具名 → (smart-plan 函数, query 模板)
_TOOL_MAP: dict[str, tuple[Any, str]] = {
    "search_flights": (search_flight, "{departure}到{destination}机票"),
    "search_trains": (search_train, "{departure}到{destination}高铁"),
    "search_hotels": (search_hotel, "{city}酒店"),
    "get_weather": (search_weather, "{city}天气预报"),
    "search_attractions": (search_poi, "{city}景点门票"),
}

_QUERY_KEYS = {"departure", "destination", "city", "date", "preferences"}


async def call_smart_plan(tool_name: str, arguments: dict[str, Any] | None) -> str | None:
    """直接调用 smart-plan 的函数，返回文本结果。

    Args:
        tool_name: 我们的工具名（如 search_flights）
        arguments: 工具参数字典

    Returns:
        成功返回结果文本，失败返回 None
    """
    mapping = _TOOL_MAP.get(tool_name)
    if mapping is None:
        return None

    fn, query_template = mapping
    args = arguments or {}
    kwargs = {k: str(v) for k, v in args.items() if k in _QUERY_KEYS}
    query = query_template.format(**kwargs)

    try:
        # 函数是同步的，在 asyncio 线程池执行避免阻塞
        result = await asyncio.to_thread(fn, query=query)

        if not result:
            return None
        if "搜索失败" in result or "异常" in result:
            return None
        return result
    except Exception:
        return None
