"""预算 Agent — 汇总费用，检查预算，给出调整建议。"""

from tripmind.agents.base import BaseAgent
from tripmind.prompts import BUDGET_SYSTEM_PROMPT


class BudgetAgent(BaseAgent):
    """预算 Agent：汇总交通+住宿+行程费用，LLM 分析超支建议。"""

    name = "预算"
    emoji = "💰"
    system_prompt = BUDGET_SYSTEM_PROMPT

    async def execute(self, state: dict) -> dict:
        request = state["request"]
        transport = state.get("transport_result", {})
        hotel = state.get("hotel_result", {})
        itinerary = state.get("itinerary_result", {})

        # 1. 提取各项费用
        transport_cost = transport.get("total_cost_round", 0) if transport else 0
        hotel_cost = hotel.get("total_cost", 0) if hotel else 0
        ticket_cost = itinerary.get("total_ticket_cost", 0) if itinerary else 0

        days = request["days"]
        meal_cost = days * 120
        other_cost = days * 50

        total_cost = transport_cost + hotel_cost + ticket_cost + meal_cost + other_cost
        remaining = request["budget"] - total_cost
        is_over = remaining < 0

        # 2. 生成调整建议
        suggestions = []
        if is_over:
            suggestions.append(f"超预算 {abs(remaining)} 元")
            if hotel_cost > request["budget"] * 0.3:
                suggestions.append("可选择价格更低的酒店")
            if transport_cost > request["budget"] * 0.4:
                suggestions.append("可考虑更经济的交通方式")
            suggestions.append("适当减少景点门票支出")

        breakdown = {
            "transport": transport_cost,
            "hotel": hotel_cost,
            "tickets": ticket_cost,
            "meals": meal_cost,
            "other": other_cost,
        }

        # 3. 尝试用 LLM 优化建议
        try:
            user_msg = (
                f"总预算：{request['budget']}元\n"
                f"费用明细：{breakdown}\n"
                f"总计：{total_cost}元\n"
                f"是否超预算：{'是' if is_over else '否'}\n"
                f"当前建议：{suggestions}\n\n"
                f"请给出更详细的预算分析和调整建议。"
            )
            messages = self.build_llm_messages(user_msg)
            llm_result = await self.call_llm(messages, max_tokens=800)

            result = {
                "breakdown": breakdown,
                "total_cost": total_cost,
                "budget": request["budget"],
                "remaining": remaining,
                "is_over_budget": is_over,
                "suggestions": suggestions,
                "advice": f"总计 {total_cost} 元，{'超出' if is_over else '剩余'}预算 {abs(remaining)} 元",
                "llm_analysis": llm_result,
            }
        except Exception:
            result = {
                "breakdown": breakdown,
                "total_cost": total_cost,
                "budget": request["budget"],
                "remaining": remaining,
                "is_over_budget": is_over,
                "suggestions": suggestions,
                "advice": f"总计 {total_cost} 元，{'超出' if is_over else '剩余'}预算 {abs(remaining)} 元",
            }

        state["budget_result"] = result
        budget_status = "超预算" if is_over else "预算内"
        self.add_log(state, f"总计 {total_cost} 元（{budget_status}，剩余 {abs(remaining)} 元）")
        return state


# 导出实例
budget_agent = BudgetAgent()
