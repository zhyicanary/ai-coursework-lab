"""住宿 Agent — 搜索酒店并推荐最优方案。"""

from tripmind.agents.base import BaseAgent
from tripmind.prompts import HOTEL_SYSTEM_PROMPT


class HotelAgent(BaseAgent):
    """住宿 Agent：搜索酒店，按预算筛选，LLM 推荐。"""

    name = "住宿"
    emoji = "🏨"
    system_prompt = HOTEL_SYSTEM_PROMPT

    async def execute(self, state: dict) -> dict:
        request = state["request"]
        max_price_per_night = (request["budget"] * 0.4) / max(1, request["days"])

        # 1. 调用 MCP 工具获取酒店数据
        hotels = await self.call_mcp("search_hotels", {
            "city": request["destination"],
            "max_price": max_price_per_night,
        })

        # 2. 筛选推荐
        suitable = [h for h in hotels if h["price"] <= max_price_per_night]
        if not suitable:
            suitable = hotels[:3] if hotels else []

        recommended = max(suitable, key=lambda x: x["rating"]) if suitable else {}
        total_cost = recommended.get("price", 0) * request["days"]

        # 3. 尝试用 LLM 生成分析
        try:
            user_msg = (
                f"目的地：{request['destination']}\n"
                f"天数：{request['days']}\n"
                f"每晚预算上限：{max_price_per_night:.0f}元\n"
                f"偏好：{request.get('preferences', [])}\n\n"
                f"可用酒店：{hotels}\n"
            )
            messages = self.build_llm_messages(user_msg)
            llm_result = await self.call_llm(messages, max_tokens=1000)

            result = {
                "city": request["destination"],
                "days": request["days"],
                "budget_per_night": max_price_per_night,
                "options": suitable,
                "recommended": recommended,
                "total_cost": total_cost,
                "advice": f"推荐{recommended.get('name', '')}，{recommended.get('price', 0)}元/晚，评分{recommended.get('rating', 0)}",
                "llm_analysis": llm_result,
            }
        except Exception:
            result = {
                "city": request["destination"],
                "days": request["days"],
                "budget_per_night": max_price_per_night,
                "options": suitable,
                "recommended": recommended,
                "total_cost": total_cost,
                "advice": f"推荐{recommended.get('name', '')}，{recommended.get('price', 0)}元/晚，评分{recommended.get('rating', 0)}",
            }

        state["hotel_result"] = result
        self.add_log(state, f"找到 {len(suitable)} 家合适酒店，推荐 {recommended.get('name', '')}")
        return state


# 导出实例
hotel_agent = HotelAgent()
