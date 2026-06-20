"""MCP 旅游工具定义 — 读取模拟数据并返回结果。

每个工具都是异步函数，可从 MCP Server 注册，也可被 Agent 直接调用。
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

MOCK_DATA_DIR = Path(__file__).parent / "mock_data"

# 中文城市名 → 拼音文件名映射
CITY_NAME_MAP = {
    "北京": "beijing",
    "上海": "shanghai",
    "成都": "chengdu",
    "西安": "xian",
    "广州": "guangzhou",
    "杭州": "hangzhou",
}


def _city_to_filename(city: str) -> str:
    """中文城市名转拼音文件名。"""
    return CITY_NAME_MAP.get(city, city)


def _load_json(filename: str) -> dict:
    """加载 JSON 模拟数据文件"""
    path = MOCK_DATA_DIR / filename
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


async def search_flights(
    departure: str,
    destination: str,
    date: str | None = None,
) -> list[dict]:
    """查询航班信息。

    Args:
        departure: 出发城市
        destination: 目的城市
        date: 出发日期 YYYY-MM-DD（可选，模拟数据不依赖实际日期）

    Returns:
        航班列表 [{flight_no, departure, arrival, departure_time, arrival_time, price, airline}]
    """
    data = _load_json("flights.json")
    key = f"{departure}-{destination}"
    reverse_key = f"{destination}-{departure}"
    results = data.get(key, data.get(reverse_key, []))

    if not results:
        # 没有匹配路线时返回默认选项
        results = [
            {
                "flight_no": "CA0000",
                "departure": departure,
                "arrival": destination,
                "departure_time": "08:00",
                "arrival_time": "10:30",
                "price": 1000,
                "airline": "国航（模拟）",
            },
            {
                "flight_no": "MU0000",
                "departure": departure,
                "arrival": destination,
                "departure_time": "14:00",
                "arrival_time": "16:30",
                "price": 850,
                "airline": "东航（模拟）",
            },
        ]

    return results


async def search_trains(
    departure: str,
    destination: str,
    date: str | None = None,
) -> list[dict]:
    """查询高铁/火车信息。

    Args:
        departure: 出发城市
        destination: 目的城市
        date: 出发日期 YYYY-MM-DD（可选）

    Returns:
        列车列表 [{train_no, departure_station, arrival_station, departure_time, arrival_time, duration, price, type}]
    """
    data = _load_json("trains.json")
    key = f"{departure}-{destination}"
    reverse_key = f"{destination}-{departure}"
    results = data.get(key, data.get(reverse_key, []))

    if not results:
        results = [
            {
                "train_no": "G0000",
                "departure_station": f"{departure}站",
                "arrival_station": f"{destination}站",
                "departure_time": "08:00",
                "arrival_time": "15:00",
                "duration": "7小时",
                "price": 650,
                "type": "高铁（模拟）",
            },
            {
                "train_no": "K0000",
                "departure_station": f"{departure}站",
                "arrival_station": f"{destination}站",
                "departure_time": "21:00",
                "arrival_time": "08:00+1",
                "duration": "11小时",
                "price": 200,
                "type": "快速（模拟）",
            },
        ]

    return results


async def search_hotels(
    city: str,
    check_in: str | None = None,
    check_out: str | None = None,
    max_price: float | None = None,
    preferences: list[str] | None = None,
) -> list[dict]:
    """搜索酒店。

    Args:
        city: 城市名
        check_in: 入住日期 YYYY-MM-DD（可选）
        check_out: 退房日期 YYYY-MM-DD（可选）
        max_price: 每晚最高价格（可选）
        preferences: 偏好关键词（可选）

    Returns:
        酒店列表 [{name, price, location, rating, distance_to_center}]
    """
    data = _load_json("hotels.json")
    results = data.get(city, [])

    if max_price is not None:
        results = [h for h in results if h["price"] <= max_price]

    # 按评分降序排列
    results = sorted(results, key=lambda x: x["rating"], reverse=True)

    return results


async def get_weather(city: str, days: int = 3) -> dict:
    """查询天气预报。

    Args:
        city: 城市名
        days: 预报天数（1-7）

    Returns:
        天气预报 {daily: [{date, temp_high, temp_low, condition, rain_prob}], clothing_advice, impact_on_travel}
    """
    data = _load_json("weather.json")
    city_weather = data.get(city, {
        "conditions": ["晴", "多云", "阴"],
        "temp_range": [20, 30],
        "humid": "中等",
        "clothing_advice_base": "天气适宜，穿着舒适即可",
    })

    conditions = city_weather["conditions"]
    temp_min, temp_max = city_weather["temp_range"]
    advice_base = city_weather["clothing_advice_base"]

    # 限制天数
    days = max(1, min(days, 7))

    daily_forecast = []
    has_rain = False
    has_hot = False

    for i in range(days):
        date = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
        condition = random.choice(conditions)
        temp_high = random.randint(temp_min, temp_max)
        temp_low = temp_high - random.randint(5, 10)
        rain_prob = random.randint(0, 100) if "雨" in condition else random.randint(0, 30)

        if "雨" in condition:
            has_rain = True
        if temp_high > 32:
            has_hot = True

        daily_forecast.append({
            "date": date,
            "temp_high": temp_high,
            "temp_low": temp_low,
            "condition": condition,
            "rain_prob": rain_prob,
        })

    # 生成建议
    clothing_advice = advice_base
    if has_hot:
        clothing_advice += "，注意防晒补水"
    if has_rain:
        clothing_advice += "，建议携带雨具"

    has_heavy_rain = any(d["rain_prob"] > 70 for d in daily_forecast)
    impact_on_travel = (
        "天气总体适宜出行"
        if not has_heavy_rain
        else "部分日期可能有较强降水，建议备选室内景点"
    )

    return {
        "city": city,
        "days": days,
        "daily": daily_forecast,
        "clothing_advice": clothing_advice,
        "impact_on_travel": impact_on_travel,
    }


async def search_attractions(
    city: str,
    preferences: list[str] | None = None,
    top_k: int = 10,
) -> list[dict]:
    """搜索景点信息。

    从本地 JSON 文件读取景点数据，支持按偏好关键词筛选和排序。
    实际项目中此处对接 ChromaDB 向量检索。

    Args:
        city: 城市名
        preferences: 偏好关键词列表，如 ["美食", "历史文化"]
        top_k: 返回数量上限

    Returns:
        景点列表 [{name, category, ticket_price, duration, description, score}]
    """
    # 尝试读取 JSON 文件（中文城市名转拼音文件名）
    file_path = MOCK_DATA_DIR / "attractions" / f"{_city_to_filename(city)}.json"
    if file_path.exists():
        with open(file_path, encoding="utf-8") as f:
            all_attractions = json.load(f)
    else:
        # 没有对应城市文件时返回默认景点
        all_attractions = [
            {
                "name": "城市中心广场",
                "category": "地标",
                "ticket_price": 0,
                "duration": "1小时",
                "description": f"{city}的城市中心广场，市民休闲好去处。",
                "preferences": ["休闲"],
            },
            {
                "name": "城市博物馆",
                "category": "博物馆",
                "ticket_price": 0,
                "duration": "2小时",
                "description": f"了解{city}历史文化的好地方。",
                "preferences": ["历史文化", "博物馆"],
            },
        ]

    # 如果有偏好，计算匹配度
    if preferences:
        for attr in all_attractions:
            attr_prefs = attr.get("preferences", [])
            score = sum(2 for p in preferences if p in attr_prefs)
            # 也在 description 和 name 中匹配
            score += sum(1 for p in preferences if p in attr["description"])
            score += sum(1 for p in preferences if p in attr["name"])
            attr["score"] = score

        all_attractions.sort(key=lambda x: x.get("score", 0), reverse=True)
    else:
        for attr in all_attractions:
            attr["score"] = 1.0

    return all_attractions[:top_k]
