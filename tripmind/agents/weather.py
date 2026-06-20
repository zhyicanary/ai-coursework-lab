"""天气 Agent — 查询天气预报并评估出行影响。"""

from tripmind.agents.base import BaseAgent
from tripmind.prompts import WEATHER_SYSTEM_PROMPT


class WeatherAgent(BaseAgent):
    """天气 Agent：查询天气预报，给出穿衣和出行建议。"""

    name = "天气"
    emoji = "🌤️"
    system_prompt = WEATHER_SYSTEM_PROMPT

    async def execute(self, state: dict) -> dict:
        request = state["request"]

        # 1. 调用 MCP 工具获取天气数据
        weather_data = await self.call_mcp("get_weather", {
            "city": request["destination"],
            "days": request["days"],
        })

        # 2. 尝试用 LLM 优化分析
        try:
            daily = weather_data.get("daily", [])
            user_msg = (
                f"城市：{request['destination']}\n"
                f"天数：{request['days']}\n"
                f"天气预报数据：{daily}\n"
            )
            messages = self.build_llm_messages(user_msg)
            llm_result = await self.call_llm(messages, max_tokens=500)

            result = {
                **weather_data,
                "city": request["destination"],
                "llm_analysis": llm_result,
            }
        except Exception:
            result = {
                **weather_data,
                "city": request["destination"],
            }

        state["weather_result"] = result
        daily = result.get("daily", [])
        summary = f"{request['destination']}{request['days']}天天气"
        if daily:
            conditions = [d.get("condition", "") for d in daily]
            summary += f"：{'/'.join(conditions)}"
        self.add_log(state, summary)
        return state


# 导出实例
weather_agent = WeatherAgent()
