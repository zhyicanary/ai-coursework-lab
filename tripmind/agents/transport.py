"""交通 Agent — 查询航班/高铁并推荐最优方案。"""

from tripmind.agents.base import BaseAgent
from tripmind.prompts import TRANSPORT_SYSTEM_PROMPT


class TransportAgent(BaseAgent):
    """交通 Agent：查询航班+高铁信息，LLM 分析推荐。"""

    name = "交通"
    emoji = "✈️"
    system_prompt = TRANSPORT_SYSTEM_PROMPT

    async def execute(self, state: dict) -> dict:
        request = state["request"]

        # 1. 调用 MCP 工具获取交通数据
        flights = await self.call_mcp("search_flights", {
            "departure": request["departure_city"],
            "destination": request["destination"],
        })
        trains = await self.call_mcp("search_trains", {
            "departure": request["departure_city"],
            "destination": request["destination"],
        })

        # 2. 合并数据，选择最便宜方案
        all_options = []
        if flights:
            for f in flights:
                all_options.append({**f, "type": "航班"})
        if trains:
            for t in trains:
                all_options.append({**t, "type": t.get("type", "高铁")})

        # 按价格升序排列
        all_options.sort(key=lambda x: x.get("price", 9999))
        recommended = all_options[0] if all_options else {"type": "未知", "price": 0}
        total_round = recommended["price"] * 2 if recommended["price"] else 0

        # 3. 尝试用 LLM 生成分析
        try:
            user_msg = (
                f"出发地：{request['departure_city']}\n"
                f"目的地：{request['destination']}\n"
                f"天数：{request['days']}\n"
                f"预算：{request['budget']}元\n\n"
                f"可用航班：{flights}\n"
                f"可用火车：{trains}\n"
            )
            messages = self.build_llm_messages(user_msg)
            llm_result = await self.call_llm(messages, max_tokens=1000)

            result = {
                "departure": request["departure_city"],
                "destination": request["destination"],
                "options": all_options,
                "recommended": recommended,
                "total_cost_round": total_round,
                "advice": f"推荐{recommended.get('type', '')}：{recommended.get('name', '')}，{recommended.get('price', 0)}元",
                "llm_analysis": llm_result,
            }
        except Exception:
            # LLM 不可用时使用内置逻辑
            result = {
                "departure": request["departure_city"],
                "destination": request["destination"],
                "options": all_options,
                "recommended": recommended,
                "total_cost_round": total_round,
                "advice": f"推荐{recommended.get('type', '')}：{recommended.get('name', '')}，{recommended.get('price', 0)}元",
            }

        state["transport_result"] = result
        self.add_log(state, f"找到 {len(all_options)} 个交通方案，推荐 {recommended.get('name', '')}")
        return state


# 导出实例，供编排器使用
transport_agent = TransportAgent()
