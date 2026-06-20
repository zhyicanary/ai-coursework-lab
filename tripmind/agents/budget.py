"""预算 Agent - 汇总费用、预算检查"""


async def budget_agent(
    transport: dict | None,
    hotel: dict | None,
    itinerary: dict | None,
    total_budget: float
) -> dict:
    """
    汇总所有费用，检查是否超预算
    """
    transport_cost = transport.get("total_cost_round", 0) if transport else 0
    hotel_cost = hotel.get("total_cost", 0) if hotel else 0
    ticket_cost = itinerary.get("total_ticket_cost", 0) if itinerary else 0
    days = itinerary.get("days", 3) if itinerary else 3
    meal_cost = days * 120
    other_cost = days * 50
    
    total_cost = transport_cost + hotel_cost + ticket_cost + meal_cost + other_cost
    remaining = total_budget - total_cost
    is_over = remaining < 0
    
    suggestions = []
    if is_over:
        suggestions.append(f"超预算 {abs(remaining)} 元")
        if hotel_cost > total_budget * 0.3:
            suggestions.append("可选择价格更低的酒店")
        if transport_cost > total_budget * 0.4:
            suggestions.append("可考虑更经济的交通方式")
        suggestions.append("适当减少景点门票支出")
    
    return {
        "breakdown": {
            "transport": transport_cost,
            "hotel": hotel_cost,
            "tickets": ticket_cost,
            "meals": meal_cost,
            "other": other_cost
        },
        "total_cost": total_cost,
        "budget": total_budget,
        "remaining": remaining,
        "is_over_budget": is_over,
        "suggestions": suggestions,
        "advice": f"总计 {total_cost} 元，{'超出' if is_over else '剩余'}预算 {abs(remaining)} 元"
    }
