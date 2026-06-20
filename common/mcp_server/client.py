"""MCP 客户端封装 — 连接 MCP Server 并调用工具。

提供 ToolClient 单例，优先通过 MCP 协议调用工具，
如果 MCP Server 不可用，自动回退到直接调用 tools.py 函数。
"""

import sys
from pathlib import Path
from typing import Any

# 确保项目根目录在路径中
ROOT_DIR = Path(__file__).parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


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


async def call_tool_via_mcp(name: str, arguments: dict | None = None) -> Any:
    """通过 MCP 协议调用工具。

    启动 MCP Server 子进程，连接后调用工具，完成后自动关闭。
    """
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.session import ClientSession

    params = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "common.mcp_server.server"],
        cwd=str(ROOT_DIR),
    )

    async with stdio_client(params) as (read, write):
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


# MCP 可用状态缓存
_mcp_available: bool | None = None


async def call_tool(name: str, arguments: dict | None = None) -> Any:
    """智能调用 MCP 工具。

    首次调用尝试 MCP 协议，成功后缓存可用状态。
    如果 MCP 不可用，标记并永久回退到直接调用。

    这是 Agent 调用工具的推荐入口。
    """
    global _mcp_available

    # 如果 MCP 已标记为不可用，直接回退
    if _mcp_available is False:
        return await call_tool_direct(name, arguments)

    # 首次尝试 MCP 协议
    if _mcp_available is None:
        try:
            result = await call_tool_via_mcp(name, arguments)
            _mcp_available = True
            return result
        except Exception as e:
            _mcp_available = False
            print(f"[MCP] {name} 通过 MCP 失败 ({e.__class__.__name__})，永久回退到直接调用")
            return await call_tool_direct(name, arguments)

    # MCP 已确认可用
    try:
        return await call_tool_via_mcp(name, arguments)
    except Exception as e:
        _mcp_available = False
        print(f"[MCP] {name} 连接中断 ({e.__class__.__name__})，回退到直接调用")
        return await call_tool_direct(name, arguments)
