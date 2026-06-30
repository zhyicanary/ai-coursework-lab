"""mcp-travel-smart-plan MCP 客户端 — 飞猪+高德+同程+途牛真实数据。

零配置，通过 uvx 启动子进程调用 MCP 工具。
每个工具返回原始文本结果，失败返回 None。

工具名映射（smart-plan → 我们的）：
  search_flight   → search_flights
  search_train    → search_trains
  search_hotel    → search_hotels
  search_weather  → get_weather
  search_poi      → search_attractions
"""

from typing import Any

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

# uvx 参数 — 首次安装后 uvx 会缓存，子进程启动约 1-2s
_SERVER_PARAMS = StdioServerParameters(
    command="uvx",
    args=["mcp-travel-smart-plan"],
)

# 我们的工具名 → smart-plan 工具名 + query 模板
_TOOL_MAP = {
    "search_flights": ("search_flight", "{departure}到{destination}机票"),
    "search_trains": ("search_train", "{departure}到{destination}高铁"),
    "search_hotels": ("search_hotel", "{city}酒店"),
    "get_weather": ("search_weather", "{city}天气预报"),
    "search_attractions": ("search_poi", "{city}景点门票"),
}


async def call_smart_plan(tool_name: str, arguments: dict[str, Any] | None) -> str | None:
    """调用 smart-plan 的 MCP 工具，返回文本结果。

    Args:
        tool_name: 我们的工具名（如 search_flights）
        arguments: 工具参数字典

    Returns:
        成功返回结果文本，失败返回 None
    """
    mapping = _TOOL_MAP.get(tool_name)
    if mapping is None:
        return None

    smart_tool, query_template = mapping
    query = _build_query(query_template, arguments or {})

    try:
        async with stdio_client(_SERVER_PARAMS) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(smart_tool, {"query": query})

                if result.isError:
                    return None

                # 合并所有 text 片段
                texts = [c.text for c in result.content if c.type == "text"]
                full = "\n".join(texts)

                # 检查是否包含错误信息
                if "搜索失败" in full or "异常" in full:
                    return None

                return full
    except Exception:
        return None


def _build_query(template: str, args: dict) -> str:
    """用参数填充 query 模板。"""
    # 只取模板中用到的字段
    used_keys = set()
    idx = 0
    while True:
        start = template.find("{", idx)
        if start == -1:
            break
        end = template.find("}", start)
        if end == -1:
            break
        used_keys.add(template[start + 1 : end])
        idx = end + 1

    kwargs = {}
    for k in used_keys:
        v = args.get(k, "")
        if isinstance(v, list):
            v = ",".join(v)
        kwargs[k] = v

    return template.format(**kwargs)
