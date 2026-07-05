"""行程 Agent — 规划每日行程，依赖天气和交通信息。"""

from tripmind.agents.base import BaseAgent
from tripmind.prompts import ITINERARY_SYSTEM_PROMPT


class ItineraryAgent(BaseAgent):
    """行程 Agent：依赖天气+交通结果，调用景点搜索，LLM 规划每日行程。"""

    name = "行程"
    emoji = "🗺️"
    system_prompt = ITINERARY_SYSTEM_PROMPT

    async def execute(self, state: dict) -> dict:
        request = state["request"]
        weather = state.get("weather_result")
        transport = state.get("transport_result")

        # 1. 调用 MCP 工具获取景点数据
        attractions = await self.call_mcp("search_attractions", {
            "city": request["destination"],
            "preferences": request.get("preferences", []),
            "top_k": 12,
        })

        # 2. 尝试用 LLM 规划行程
        try:
            weather_info = ""
            if weather and "daily" in weather:
                weather_info = str(weather["daily"])

            transport_info = ""
            if transport and "recommended" in transport:
                t = transport["recommended"]
                transport_info = f"{t.get('type', '')} {t.get('flight_no', '') or t.get('train_no', '')} 到达{t.get('arrival_time', '')}"

            user_msg = (
                f"目的地：{request['destination']}\n"
                f"天数：{request['days']}\n"
                f"用户偏好：{request.get('preferences', [])}\n"
                f"天气信息：{weather_info}\n"
                f"交通信息：{transport_info}\n"
                f"可用景点：{attractions}\n\n"
                f"请规划每日行程，输出 JSON 格式。"
            )
            messages = self.build_llm_messages(user_msg)
            llm_result = await self.call_llm(messages, max_tokens=2000)

            result = {
                "city": request["destination"],
                "days": request["days"],
                "daily_plans": self._extract_daily_plans(llm_result),
                "total_ticket_cost": self._calc_ticket_cost(llm_result, attractions),
                "advice": f"共规划{request['days']}天行程",
                "llm_analysis": llm_result,
                "available_attractions": attractions,
            }
        except Exception:
            # LLM 不可用，回退到内置行程规划
            result = self._build_fallback_plan(request, weather, attractions)

        state["itinerary_result"] = result
        self.add_log(state, f"行程规划完成，共{request['days']}天")
        return state

    def _extract_daily_plans(self, llm_text: str) -> list:
        """从 LLM 输出中提取 daily_plans。"""
        import json
        import re

        # 尝试提取 JSON
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', llm_text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if "daily_plans" in data:
                    return data["daily_plans"]
            except json.JSONDecodeError:
                pass

        # 直接尝试解析整个文本为 JSON
        try:
            data = json.loads(llm_text)
            if isinstance(data, list):
                return data
            if "daily_plans" in data:
                return data["daily_plans"]
        except (json.JSONDecodeError, TypeError):
            pass

        return []

    def _calc_ticket_cost(self, llm_text: str, attractions: list) -> float:
        """计算总门票费用。"""
        plans = self._extract_daily_plans(llm_text)
        if plans:
            return sum(p.get("ticket_cost", 0) for p in plans)
        # 回退：从景点数据估算
        return sum(a.get("ticket_price", 0) for a in attractions[:2]) * 3

    def _build_fallback_plan(self, request: dict, weather: dict | None, attractions: list) -> dict:
        """LLM 不可用时的回退行程规划。"""
        daily_plans = []

        for day in range(1, request["days"] + 1):
            weather_cond = "晴"
            if weather and "daily" in weather and day <= len(weather["daily"]):
                weather_cond = weather["daily"][day - 1].get("condition", "晴")

            if "雨" in weather_cond:
                indoor = [a for a in attractions if a.get("category") in ("博物馆", "室内")]
                selected = indoor[:2] if indoor else attractions[:2]
            else:
                idx = (day - 1) * 2
                selected = attractions[idx:idx + 2] if idx < len(attractions) else attractions[:2]

            ticket_cost = sum(a.get("ticket_price", 0) for a in selected)

            daily_plans.append({
                "day": day,
                "date": f"第{day}天",
                "weather": weather_cond,
                "morning": f"抵达{request['destination']}" if day == 1 else f"上午：{selected[0]['name'] if selected else '自由活动'}",
                "afternoon": f"下午：{selected[1]['name'] if len(selected) > 1 else '市区游览'}",
                "evening": "晚上：品尝当地美食",
                "attractions": selected,
                "ticket_cost": ticket_cost,
            })

        return {
            "city": request["destination"],
            "days": request["days"],
            "daily_plans": daily_plans,
            "total_ticket_cost": sum(d["ticket_cost"] for d in daily_plans),
            "advice": f"共规划{request['days']}天行程，{sum(len(d.get('attractions', [])) for d in daily_plans)}个景点",
        }


# 导出实例
itinerary_agent = ItineraryAgent()
