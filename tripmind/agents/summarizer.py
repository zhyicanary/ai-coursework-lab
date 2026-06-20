"""汇总 Agent - 生成最终旅行方案"""


async def summarizer_agent(
    request: dict,
    weather: dict | None,
    transport: dict | None,
    hotel: dict | None,
    itinerary: dict | None,
    budget: dict | None
) -> str:
    """
    将所有 Agent 的结果整合为一份完整的旅行方案
    """
    destination = request.get("destination", "未知")
    days = request.get("days", 3)
    budget_total = request.get("budget", 0)
    
    plan = f"# {destination}{days}日旅行方案\n\n"
    
    if budget.get("is_over_budget", False):
        plan += f"## ⚠️ 预算提醒：总计 {budget['total_cost']} 元，超出预算 {abs(budget['remaining'])} 元\n\n"
    else:
        plan += f"## ✅ 预算概览：总计 {budget['total_cost']} 元，剩余 {budget['remaining']} 元\n\n"
    
    plan += "## 一、行程总览\n\n"
    plan += "| 日期 | 天气 | 上午 | 下午 | 晚上 |\n"
    plan += "|------|------|------|------|------|\n"
    
    if itinerary:
        for day_plan in itinerary.get("daily_plans", []):
            plan += f"| {day_plan['date']} | {day_plan['weather']} | {day_plan['morning']} | {day_plan['afternoon']} | {day_plan['evening']} |\n"
    
    plan += "\n## 二、交通安排\n\n"
    if transport:
        rec = transport.get("recommended", {})
        plan += f"推荐：{rec.get('name', '未知')} ({rec.get('type', '未知')})\n"
        plan += f"时间：{rec.get('departure_time', '未知')} - {rec.get('arrival_time', '未知')}\n"
        plan += f"价格：{rec.get('price', 0)} 元\n"
        plan += f"往返总计：{transport.get('total_cost_round', 0)} 元\n\n"
    
    plan += "## 三、住宿推荐\n\n"
    if hotel:
        rec = hotel.get("recommended", {})
        plan += f"推荐：{rec.get('name', '未知')}\n"
        plan += f"价格：{rec.get('price', 0)} 元/晚\n"
        plan += f"位置：{rec.get('location', '未知')}\n"
        plan += f"评分：{rec.get('rating', 0)}\n"
        plan += f"总计：{hotel.get('total_cost', 0)} 元\n\n"
    
    plan += "## 四、每日详细行程\n\n"
    if itinerary:
        for day_plan in itinerary.get("daily_plans", []):
            plan += f"### {day_plan['date']} ({day_plan['weather']})\n"
            plan += f"- 上午：{day_plan['morning']}\n"
            plan += f"- 下午：{day_plan['afternoon']}\n"
            plan += f"- 晚上：{day_plan['evening']}\n\n"
    
    plan += "## 五、费用明细\n\n"
    if budget:
        breakdown = budget.get("breakdown", {})
        plan += f"- 交通：{breakdown.get('transport', 0)} 元\n"
        plan += f"- 住宿：{breakdown.get('hotel', 0)} 元\n"
        plan += f"- 门票：{breakdown.get('tickets', 0)} 元\n"
        plan += f"- 餐饮：{breakdown.get('meals', 0)} 元\n"
        plan += f"- 其他：{breakdown.get('other', 0)} 元\n"
        plan += f"- **总计：{budget.get('total_cost', 0)} 元**\n\n"
        
        if budget.get("suggestions"):
            plan += "### 调整建议\n"
            for s in budget["suggestions"]:
                plan += f"- {s}\n"
    
    plan += "\n## 六、天气提醒与出行建议\n\n"
    if weather:
        plan += f"- {weather.get('clothing_advice', '天气适宜')}\n"
        plan += f"- {weather.get('impact_on_travel', '出行无影响')}\n"
    
    plan += "\n---\n"
    plan += "*方案由 TripMind 多 Agent 协同生成*"
    
    return plan
