"""行程 Agent - 规划每日行程"""


async def itinerary_agent(
    city: str,
    days: int,
    weather: dict | None,
    transport: dict | None
) -> dict:
    """
    规划每日行程
    依赖天气和交通信息
    """
    attractions = {
        "成都": [
            {"name": "宽窄巷子", "category": "历史街区", "ticket_price": 0, "duration": "2小时"},
            {"name": "锦里", "category": "商业街", "ticket_price": 0, "duration": "2小时"},
            {"name": "都江堰", "category": "历史遗迹", "ticket_price": 80, "duration": "3小时"},
            {"name": "青城山", "category": "自然风光", "ticket_price": 80, "duration": "4小时"},
            {"name": "成都博物馆", "category": "博物馆", "ticket_price": 0, "duration": "2小时"},
        ],
        "北京": [
            {"name": "故宫", "category": "历史遗迹", "ticket_price": 60, "duration": "3小时"},
            {"name": "长城", "category": "历史遗迹", "ticket_price": 40, "duration": "5小时"},
            {"name": "颐和园", "category": "皇家园林", "ticket_price": 30, "duration": "3小时"},
            {"name": "天坛", "category": "历史遗迹", "ticket_price": 15, "duration": "2小时"},
        ],
    }
    
    city_attractions = attractions.get(city, [
        {"name": "市中心景点", "category": "综合", "ticket_price": 0, "duration": "2小时"},
        {"name": "博物馆", "category": "博物馆", "ticket_price": 0, "duration": "2小时"},
    ])
    
    daily_plans = []
    arrival_time = "上午" if not transport else "根据交通时间"
    
    for day in range(1, days + 1):
        weather_info = weather["daily"][day - 1] if weather and day <= len(weather.get("daily", [])) else {"condition": "晴"}
        
        if "雨" in weather_info.get("condition", ""):
            indoor = [a for a in city_attractions if a["category"] in ["博物馆", "室内"]]
            selected = indoor[:2] if indoor else city_attractions[:2]
        else:
            selected = city_attractions[((day - 1) * 2) % len(city_attractions):(day * 2) % len(city_attractions) + 2]
            if not selected:
                selected = city_attractions[:2]
        
        daily_plans.append({
            "day": day,
            "date": f"第{day}天",
            "weather": weather_info.get("condition", "晴"),
            "morning": f"抵达{city}" if day == 1 else f"上午：{selected[0]['name'] if selected else '自由活动'}",
            "afternoon": f"下午：{selected[1]['name'] if len(selected) > 1 else '市区游览'}",
            "evening": "晚上：品尝当地美食",
            "attractions": selected,
            "ticket_cost": sum(a["ticket_price"] for a in selected)
        })
    
    total_ticket_cost = sum(d["ticket_cost"] for d in daily_plans)
    
    return {
        "city": city,
        "days": days,
        "daily_plans": daily_plans,
        "total_attractions": sum(len(d["attractions"]) for d in daily_plans),
        "total_ticket_cost": total_ticket_cost,
        "advice": f"共规划{days}天行程，{sum(len(d['attractions']) for d in daily_plans)}个景点"
    }
