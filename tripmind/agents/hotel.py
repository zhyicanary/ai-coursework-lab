"""住宿 Agent - 推荐酒店"""

import random


async def hotel_agent(city: str, days: int, budget: float) -> dict:
    """
    搜索酒店
    实际项目中可接入携程/美团 API
    """
    max_price = (budget * 0.4) / days
    
    hotels = [
        {"name": "如家酒店", "price": 180, "location": "市中心", "rating": 4.2, "distance_to_center": 0.5},
        {"name": "汉庭酒店", "price": 200, "location": "火车站附近", "rating": 4.3, "distance_to_center": 1.2},
        {"name": "全季酒店", "price": 280, "location": "商业区", "rating": 4.5, "distance_to_center": 0.8},
        {"name": "亚朵酒店", "price": 350, "location": "景区附近", "rating": 4.6, "distance_to_center": 0.3},
        {"name": "民宿A", "price": 150, "location": "老城区", "rating": 4.4, "distance_to_center": 2.0},
    ]
    
    suitable = [h for h in hotels if h["price"] <= max_price]
    if not suitable:
        suitable = hotels[:3]
    
    recommended = max(suitable, key=lambda x: x["rating"])
    
    return {
        "city": city,
        "days": days,
        "budget_per_night": max_price,
        "options": suitable,
        "recommended": recommended,
        "total_cost": recommended["price"] * days,
        "advice": f"推荐{recommended['name']}，{recommended['price']}元/晚，评分{recommended['rating']}"
    }
