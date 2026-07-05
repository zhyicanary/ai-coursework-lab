"""Agent 基类 — 统一封装 LLM 调用、MCP 工具调用和日志记录。

所有领域 Agent 继承此类，实现 execute 方法即可。
"""

from abc import ABC, abstractmethod
from typing import Any

from common.context import get_context
from common.mcp_server.client import call_tool as mcp_call_tool


class BaseAgent(ABC):
    """Agent 基类。

    子类需定义：
    - name: Agent 中文名
    - emoji: 前端显示 emoji
    - system_prompt: 系统提示词（来自 prompts.py）

    子类需实现：
    - execute(state): 执行 Agent 逻辑，更新 state
    """

    name: str = ""
    emoji: str = ""
    system_prompt: str = ""

    @abstractmethod
    async def execute(self, state: dict) -> dict:
        """执行 Agent 逻辑，返回更新后的 state。"""
        ...

    # -------- 工具方法 --------

    async def call_llm(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """调用 LLM。

        Args:
            messages: 消息列表 [{"role": "...", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            LLM 返回的文本
        """
        return await get_context().llm.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def call_mcp(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """调用 MCP 工具（自动回退到直接调用）。

        Args:
            tool_name: 工具名
            arguments: 工具参数

        Returns:
            工具返回的结果
        """
        return await mcp_call_tool(tool_name, arguments)

    def add_log(
        self,
        state: dict,
        message: str,
        status: str = "done",
    ):
        """添加执行日志到 state。

        Args:
            state: 全局状态
            message: 日志消息
            status: 状态标识（start / done / error）
        """
        logs = state.get("agent_logs", [])
        logs.append({
            "step": f"{self.emoji}{self.name}",
            "message": message,
            "status": status,
        })

    def build_llm_messages(self, user_content: str) -> list[dict]:
        """构造 LLM 消息列表（system + user）。

        Args:
            user_content: 用户消息内容

        Returns:
            [{"role": "system", "content": ...}, {"role": "user", "content": ...}]
        """
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content},
        ]

    async def safe_execute(self, state: dict) -> dict:
        """安全执行 execute，失败时记录错误不阻塞。

        供编排器调用，确保单 Agent 失败不影响整体流程。
        """
        try:
            self.add_log(state, f"{self.name} Agent 启动", "start")
            state = await self.execute(state)
            return state
        except Exception as e:
            self.add_log(state, f"执行失败：{e}", "error")
            # 设置失败结果，标注暂无数据
            result_key = f"{self._result_key()}_result"
            if result_key not in state:
                state[result_key] = {"error": str(e), "source": f"{self.name} Agent"}
            return state

    def _result_key(self) -> str:
        """根据 name 生成 result 的 key 名。"""
        name_map = {
            "天气": "weather",
            "交通": "transport",
            "住宿": "hotel",
            "行程": "itinerary",
            "预算": "budget",
            "汇总": "summary",
        }
        return name_map.get(self.name, self.name.lower())
