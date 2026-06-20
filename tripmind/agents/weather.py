"""天气 Agent - 查询天气预报"""

import random
from datetime import datetime, timedelta


async def weather_agent(city: str, days: int) -> dict:
    """
    查询天气预报
    实际项目中可接入和风天气 API
    """
    conditions = ["晴", "多云", "阴", "小雨", "中雨", "大雨", "雷阵雨"]
    
    daily_forecast = []
    for i in range(days):
        date = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
        condition = random.choice(conditions)
        temp_high = random.randint(25, 35)
        temp_low = temp_high - random.randint(5, 10)
        rain_prob = random.randint(0, 100) if "雨" in condition else random.randint(0, 30)
        
        daily_forecast.append({
            "date": date,
            "temp_high": temp_high,
            "temp_low": temp_low,
            "condition": condition,
            "rain_prob": rain_prob
        })
    
    clothing_advice = "天气温暖，建议穿轻薄衣物"
    if any(d["temp_high"] > 32 for d in daily_forecast):
        clothing_advice = "天气炎热，注意防晒补水"
    if any("雨" in d["condition"] for d in daily_forecast):
        clothing_advice += "，建议携带雨具"
    
    return {
        "city": city,
        "days": days,
        "daily": daily_forecast,
        "clothing_advice": clothing_advice,
        "impact_on_travel": "天气总体适宜出行" if not any(d["rain_prob"] > 70 for d in daily_forecast) else "部分日期可能有雨，建议备选室内景点"
    }
