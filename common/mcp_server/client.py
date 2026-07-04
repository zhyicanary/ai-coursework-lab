"""MCP 客户端封装 — 连接 MCP HTTP Server 并调用工具。

提供 ToolClient 单例，优先通过 Streamable HTTP 协议调用工具，
如果 MCP Server 不可用，自动回退到直接调用 tools.py 函数。
"""

import sys
from pathlib import Path
from typing import Any

# 确保项目根目录在路径中
ROOT_DIR = Path(__file__).parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from common.mcp_server.server import MCP_HOST, MCP_PORT

# MCP Server HTTP 端点 URL
MCP_SERVER_URL = f"http://{MCP_HOST}:{MCP_PORT}/mcp"


async def call_tool_direct(name: str, arguments: dict | None = None) -> Any:
    """直接调用 tools.py 中的函数（回退方案）。"""
    from common.mcp_server.tools import (
        search_flights,
        search_trains,
        search_hotels,
        get_weather,
        search_attractions,
    )

    tool_map = {
        "search_flights": search_flights,
        "search_trains": search_trains,
        "search_hotels": search_hotels,
        "get_weather": get_weather,
        "search_attractions": search_attractions,
    }

    func = tool_map.get(name)
    if func is None:
        raise ValueError(f"未知工具：{name}")

    args = arguments or {}
    return await func(**args)


async def call_tool_via_http(name: str, arguments: dict | None = None) -> Any:
    """通过 Streamable HTTP 协议调用 MCP 工具。

    连接常驻的 MCP HTTP Server，复用已建立的连接会话。
    """
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    async with streamable_http_client(MCP_SERVER_URL) as (read, write, _get_session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(name, arguments or {})

            if result.isError:
                error_msg = result.content[0].text if result.content else "未知错误"
                raise RuntimeError(f"工具 {name} 调用失败：{error_msg}")

            # 解析返回内容
            import json

            parsed = []
            for item in result.content:
                if item.type == "text":
                    try:
                        parsed.append(json.loads(item.text))
                    except (json.JSONDecodeError, TypeError):
                        parsed.append(item.text)

            if len(parsed) == 1:
                return parsed[0]
            return parsed


from common.context import get_context


async def call_tool(name: str, arguments: dict | None = None) -> Any:
    """智能调用 MCP 工具。

    优先通过 Streamable HTTP 连接常驻 MCP Server，
    连续失败超过阈值后回退到直接调用 tools.py 函数。

    这是 Agent 调用工具的推荐入口。
    """
    ctx = get_context()

    # 已确认 HTTP 不可用，直接回退
    if ctx.mcp_available is False:
        return await call_tool_direct(name, arguments)

    # 首次探测或之前成功过
    try:
        result = await call_tool_via_http(name, arguments)
        ctx.mark_mcp_success()
        return result
    except Exception as e:
        if ctx.mcp_available is None:
            print(
                f"[MCP] {name} 通过 HTTP 失败 ({e.__class__.__name__})，"
                f"已回退到直接调用（将重试 HTTP）"
            )
        elif ctx.mark_mcp_failure():
            print(
                f"[MCP] HTTP 连续失败，"
                f"永久回退到直接调用（可通过 context.reset_mcp_state() 恢复）"
            )
        else:
            print(
                f"[MCP] {name} HTTP 调用失败 ({e.__class__.__name__})，"
                f"本次回退到直接调用"
            )
        return await call_tool_direct(name, arguments)
