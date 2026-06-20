"""汇总 Agent — 整合所有 Agent 结果，生成 Markdown 旅行方案。"""

from tripmind.agents.base import BaseAgent
from tripmind.prompts import SUMMARIZER_SYSTEM_PROMPT


class SummarizerAgent(BaseAgent):
    """汇总 Agent：整合所有结果，LLM 生成 Markdown 旅行方案。"""

    name = "汇总"
    emoji = "📝"
    system_prompt = SUMMARIZER_SYSTEM_PROMPT

    async def execute(self, state: dict) -> dict:
        request = state["request"]
        weather = state.get("weather_result", {})
        transport = state.get("transport_result", {})
        hotel = state.get("hotel_result", {})
        itinerary = state.get("itinerary_result", {})
        budget = state.get("budget_result", {})

        # 1. 尝试用 LLM 生成方案
        try:
            user_msg = self._build_user_message(request, weather, transport, hotel, itinerary, budget)
            messages = self.build_llm_messages(user_msg)
            llm_result = await self.call_llm(messages, max_tokens=3000)
            state["final_plan"] = llm_result
        except Exception:
            # LLM 不可用，回退到模板拼接
            state["final_plan"] = self._build_fallback_plan(
                request, weather, transport, hotel, itinerary, budget
            )

        self.add_log(state, "最终旅行方案已生成")
        return state

    def _build_user_message(
        self, request: dict, weather: dict, transport: dict,
        hotel: dict, itinerary: dict, budget: dict,
    ) -> str:
        """构造 LLM 的 user message。"""
        lines = [f"# {request['destination']}{request['days']}日旅行方案生成请求\n"]
        lines.append(f"目的地：{request['destination']}")
        lines.append(f"天数：{request['days']}")
        lines.append(f"预算：{request['budget']}元")
        lines.append(f"出发地：{request['departure_city']}")
        lines.append(f"偏好：{request.get('preferences', [])}")
        lines.append("")

        lines.append("## 天气数据")
        lines.append(str(weather.get("daily", "暂无数据")))
        lines.append(f"穿衣建议：{weather.get('clothing_advice', '暂无数据')}")
        lines.append("")

        lines.append("## 交通数据")
        rec = transport.get("recommended", {})
        lines.append(f"推荐：{rec.get('name', '暂无数据')} {rec.get('type', '')} {rec.get('price', 0)}元")
        lines.append(f"往返总计：{transport.get('total_cost_round', 0)}元")
        lines.append("")

        lines.append("## 住宿数据")
        rec_h = hotel.get("recommended", {})
        lines.append(f"推荐：{rec_h.get('name', '暂无数据')} {rec_h.get('price', 0)}元/晚 评分{rec_h.get('rating', 0)}")
        lines.append(f"总计：{hotel.get('total_cost', 0)}元")
        lines.append("")

        lines.append("## 行程数据")
        for plan in itinerary.get("daily_plans", []):
            lines.append(f"  第{plan['day']}天（{plan.get('weather', '')}）：{plan['morning']} / {plan['afternoon']} / {plan['evening']}")
        lines.append(f"总门票：{itinerary.get('total_ticket_cost', 0)}元")
        lines.append("")

        lines.append("## 预算数据")
        breakdown = budget.get("breakdown", {})
        lines.append(f"明细：{breakdown}")
        lines.append(f"总计：{budget.get('total_cost', 0)}元 / 预算：{request['budget']}元")
        lines.append(f"建议：{budget.get('suggestions', [])}")
        lines.append("")

        lines.append("请按以下格式生成 Markdown 旅行方案：")
        lines.append("""
# {目的地}{天数}日旅行方案

## 预算概览
[预算总结]

## 一、行程总览
[每日行程表格]

## 二、交通安排
[交通详情]

## 三、住宿推荐
[住宿详情]

## 四、每日详细行程
[每日安排]

## 五、费用明细
[费用分类]

## 六、天气提醒与出行建议
[天气建议]
        """)

        return "\n".join(lines)

    def _build_fallback_plan(
        self, request: dict, weather: dict, transport: dict,
        hotel: dict, itinerary: dict, budget: dict,
    ) -> str:
        """LLM 不可用时的回退方案生成。"""
        destination = request["destination"]
        days = request["days"]
        budget_total = request["budget"]

        plan = f"# {destination}{days}日旅行方案\n\n"

        # 预算概览
        if budget.get("is_over_budget", False):
            plan += f"## ⚠️ 预算提醒：总计 {budget['total_cost']} 元，超出预算 {abs(budget['remaining'])} 元\n\n"
        else:
            plan += f"## ✅ 预算概览：总计 {budget['total_cost']} 元，剩余 {budget['remaining']} 元\n\n"

        # 行程总览
        plan += "## 一、行程总览\n\n"
        plan += "| 日期 | 天气 | 上午 | 下午 | 晚上 |\n"
        plan += "|------|------|------|------|------|\n"
        for day_plan in itinerary.get("daily_plans", []):
            plan += f"| {day_plan['date']} | {day_plan['weather']} | {day_plan['morning']} | {day_plan['afternoon']} | {day_plan['evening']} |\n"

        # 交通
        plan += "\n## 二、交通安排\n\n"
        if transport:
            rec = transport.get("recommended", {})
            plan += f"推荐：{rec.get('name', '未知')} ({rec.get('type', '未知')})\n"
            plan += f"价格：{rec.get('price', 0)} 元\n"
            plan += f"往返总计：{transport.get('total_cost_round', 0)} 元\n\n"

        # 住宿
        plan += "## 三、住宿推荐\n\n"
        if hotel:
            rec = hotel.get("recommended", {})
            plan += f"推荐：{rec.get('name', '未知')}\n"
            plan += f"价格：{rec.get('price', 0)} 元/晚\n"
            plan += f"评分：{rec.get('rating', 0)}\n"
            plan += f"总计：{hotel.get('total_cost', 0)} 元\n\n"

        # 详细行程
        plan += "## 四、每日详细行程\n\n"
        for day_plan in itinerary.get("daily_plans", []):
            plan += f"### {day_plan['date']} ({day_plan['weather']})\n"
            plan += f"- 上午：{day_plan['morning']}\n"
            plan += f"- 下午：{day_plan['afternoon']}\n"
            plan += f"- 晚上：{day_plan['evening']}\n\n"

        # 费用
        plan += "## 五、费用明细\n\n"
        if budget:
            bd = budget.get("breakdown", {})
            plan += f"- 交通：{bd.get('transport', 0)} 元\n"
            plan += f"- 住宿：{bd.get('hotel', 0)} 元\n"
            plan += f"- 门票：{bd.get('tickets', 0)} 元\n"
            plan += f"- 餐饮：{bd.get('meals', 0)} 元\n"
            plan += f"- 其他：{bd.get('other', 0)} 元\n"
            plan += f"- **总计：{budget.get('total_cost', 0)} 元**\n\n"
            if budget.get("suggestions"):
                plan += "### 调整建议\n"
                for s in budget["suggestions"]:
                    plan += f"- {s}\n"

        # 天气
        plan += "\n## 六、天气提醒与出行建议\n\n"
        if weather:
            plan += f"- {weather.get('clothing_advice', '天气适宜')}\n"
            plan += f"- {weather.get('impact_on_travel', '出行无影响')}\n"

        plan += "\n---\n"
        plan += "*方案由 TripMind 多 Agent 协同生成*\n"

        return plan


# 导出实例
summarizer_agent = SummarizerAgent()
