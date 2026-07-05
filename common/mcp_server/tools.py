"""MCP 旅游工具定义 — 四级降级：12306-mcp → smart-plan → 真实 API → 模拟数据。

每个工具都是异步函数，可从 MCP Server 注册，也可被 Agent 直接调用。

数据源优先级：
1. 12306-mcp（真实 12306 火车票数据，需 Node.js + ENABLE_12306_MCP=true）
2. mcp-travel-smart-plan（飞猪/高德/同程/途牛，零配置，需 uvx）
3. 自有 API Key（WEATHER_API_KEY / AMAP_API_KEY）
4. 本地模拟数据（mock_data/，仅在 USE_MOCK=true 时启用）
"""

import json
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

MOCK_DATA_DIR = Path(__file__).parent / "mock_data"

# 加载环境变量
from dotenv import load_dotenv

load_dotenv()

USE_MOCK = os.getenv("USE_MOCK", "false").strip().lower() == "true"
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "").strip()
AMAP_API_KEY = os.getenv("AMAP_API_KEY", "").strip()
ENABLE_12306_MCP = os.getenv("ENABLE_12306_MCP", "false").strip().lower() == "true"
MCP_12306_PORT = int(os.getenv("MCP_12306_PORT", "8080"))

# mcp-travel-smart-plan（零配置，优先尝试）
_HAVE_SMART_PLAN = False
try:
    from common.mcp_server.smart_plan import call_smart_plan

    _HAVE_SMART_PLAN = True
except ImportError:
    pass

# 中文城市名 → 拼音文件名映射
CITY_NAME_MAP = {
    "北京": "beijing",
    "上海": "shanghai",
    "成都": "chengdu",
    "西安": "xian",
    "广州": "guangzhou",
    "杭州": "hangzhou",
}

# 和风天气城市名 → Location ID（免费版仅支持 Location ID 查询）
# 注册地址：https://dev.qweather.com
QWEATHER_CITY_IDS = {
    "北京": "101010100",
    "上海": "101020100",
    "广州": "101280101",
    "深圳": "101280601",
    "成都": "101270101",
    "杭州": "101210101",
    "西安": "101110101",
    "重庆": "101040100",
    "武汉": "101200101",
    "南京": "101190101",
    "长沙": "101250101",
    "昆明": "101290101",
    "三亚": "101310201",
    "青岛": "101120201",
    "厦门": "101230201",
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


def _log_source(tool: str, source: str) -> None:
    """打印数据来源日志到 stderr（子进程 stdout=DEVNULL，stderr 可见）。"""
    print(f"[DATA] {tool} → {source}", file=sys.stderr)


def _parse_smart_weather(text: str, city: str) -> dict | None:
    """将 smart-plan 返回的天气文本解析为结构化 dict。

    输入格式示例：
      🌤️ 成都市 天气预报

      2026-06-29（1） 阵雨转阴 21°~31° 北1-3级
      2026-06-30（2） 多云转阵雨 21°~31° 北1-3级
      ...
    """
    import re

    daily = []
    has_rain = False
    has_hot = False
    for line in text.splitlines():
        line = line.strip()
        m = re.match(
            r"(\d{4}-\d{2}-\d{2})[（(]\d+[）)]\s+(.+?)\s+(\d+)°[~-](\d+)°",
            line,
        )
        if not m:
            continue
        date, condition, temp_low, temp_high = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
        rain_prob = None
        # 尝试在文本中找降水概率
        rain_m = re.search(r"(\d+)%", line)
        if rain_m:
            rain_prob = int(rain_m.group(1))

        if "雨" in condition:
            has_rain = True
            if rain_prob is None:
                rain_prob = random.randint(40, 80)
        else:
            if rain_prob is None:
                rain_prob = random.randint(0, 30)
        if temp_high > 32:
            has_hot = True

        daily.append(
            {
                "date": date,
                "temp_high": temp_high,
                "temp_low": temp_low,
                "condition": condition,
                "rain_prob": rain_prob,
            }
        )

    if not daily:
        return None

    clothing_advice = "根据天气穿着"
    if has_hot:
        clothing_advice += "，注意防晒补水"
    if has_rain:
        clothing_advice += "，建议携带雨具"

    has_heavy_rain = any(d["rain_prob"] > 70 for d in daily)
    impact = "天气总体适宜出行" if not has_heavy_rain else "部分日期可能有较强降水，建议备选室内景点"

    return {
        "city": city,
        "days": len(daily),
        "daily": daily,
        "clothing_advice": clothing_advice,
        "impact_on_travel": impact,
        "source": "高德地图（smart-plan）",
    }


# ──────────────────────────────────────────────
# 真实 API 调用函数（内部使用）
# ──────────────────────────────────────────────


async def _call_qweather_api(city: str, days: int) -> dict | None:
    """通过和风天气 API 查询实时天气预报。

    需要 WEATHER_API_KEY 环境变量。免费版需使用 Location ID 查询。
    参考文档: https://dev.qweather.com/docs/api/weather/weather-now/

    Returns:
        成功返回 dict，失败返回 None
    """
    import httpx

    location_id = QWEATHER_CITY_IDS.get(city)
    if not location_id:
        return None  # 城市不在支持列表

    # 3d = 3天预报，7d = 7天预报
    weather_type = "7d" if days > 3 else "3d"
    url = f"https://devapi.qweather.com/v7/weather/{weather_type}"

    params = {"location": location_id, "key": WEATHER_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, params=params)
            data = resp.json()
            if data.get("code") != "200":
                return None

            daily_list = data.get("daily", [])
            # 和风天气返回全天预报，切到指定天数
            daily_list = daily_list[:days]

            daily_forecast = []
            has_rain = False
            has_hot = False
            for d in daily_list:
                temp_high = int(d["tempMax"])
                temp_low = int(d["tempMin"])
                condition = d.get("textDay", "晴")

                if "雨" in condition:
                    has_rain = True
                if temp_high > 32:
                    has_hot = True

                daily_forecast.append(
                    {
                        "date": d["fxDate"],
                        "temp_high": temp_high,
                        "temp_low": temp_low,
                        "condition": condition,
                        "rain_prob": int(d.get("precip", 0)),
                    }
                )

            clothing_advice = "根据天气穿着"
            if has_hot:
                clothing_advice += "，注意防晒补水"
            if has_rain:
                clothing_advice += "，建议携带雨具"

            has_heavy_rain = any(d.get("rain_prob", 0) > 70 for d in daily_forecast)
            impact_on_travel = (
                "天气总体适宜出行"
                if not has_heavy_rain
                else "部分日期可能有较强降水，建议备选室内景点"
            )

            return {
                "city": city,
                "days": len(daily_forecast),
                "daily": daily_forecast,
                "clothing_advice": clothing_advice,
                "impact_on_travel": impact_on_travel,
                "source": "和风天气",
            }
    except Exception:
        return None


async def _call_amap_attractions_api(city: str, top_k: int) -> list[dict] | None:
    """通过高德地图 POI 搜索景点。

    需要 AMAP_API_KEY 环境变量，使用 keywords=景点 搜索。
    参考文档: https://lbs.amap.com/api/webservice/guide/api/search

    Returns:
        成功返回列表，失败返回 None
    """
    import httpx

    url = "https://restapi.amap.com/v3/place/text"
    params = {
        "keywords": "景点",
        "city": city,
        "offset": min(top_k, 25),  # 单页上限 25
        "page": 1,
        "extensions": "all",
        "key": AMAP_API_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, params=params)
            data = resp.json()
            if data.get("status") != "1":
                return None

            pois = data.get("pois", [])
            results = []
            for poi in pois[:top_k]:
                # 从 typecode 推断类别
                typecode = poi.get("typecode", "999999")
                category = _amap_typecode_to_category(typecode)

                # 从高德描述或业务区域提取简介
                description = (
                    poi.get("business_area", "") or poi.get("address", "") or f"{city}景点"
                )

                results.append(
                    {
                        "name": poi.get("name", ""),
                        "category": category,
                        "ticket_price": 0,  # 高德不提供票价
                        "duration": "2小时",  # 高德不提供游玩时长
                        "description": description,
                        "preferences": _category_to_preferences(category),
                        "location": poi.get("location", ""),
                        "address": poi.get("address", ""),
                        "source": "高德地图",
                    }
                )

            return results
    except Exception:
        return None


def _amap_typecode_to_category(typecode: str) -> str:
    """高德 typecode 转中文类别。"""
    type_map = {
        "060100": "博物馆",
        "060101": "博物馆",
        "060200": "展览馆",
        "060300": "美术馆",
        "050000": "餐饮",
        "050100": "餐饮",
        "050200": "餐饮",
        "110000": "购物",
        "110100": "购物",
        "110200": "购物",
        "100100": "公园",
        "100101": "公园",
        "100102": "公园",
        "100200": "自然风光",
        "100201": "自然风光",
        "100202": "自然风光",
        "100300": "历史遗迹",
        "100301": "历史遗迹",
        "100302": "历史遗迹",
        "100303": "历史遗迹",
        "100400": "宗教场所",
        "100500": "动物园",
        "100501": "动物园",
        "100600": "植物园",
        "100601": "植物园",
        "100700": "游乐场",
        "100701": "游乐场",
        "100702": "游乐园",
        "100800": "度假村",
        "100900": "剧院",
        "101000": "体育场馆",
        "101100": "文化场馆",
        "101200": "图书馆",
        "101300": "科技馆",
        "101400": "纪念馆",
    }
    return type_map.get(typecode, "景点")


def _category_to_preferences(category: str) -> list[str]:
    """类别 → 偏好标签。"""
    pref_map = {
        "博物馆": ["历史文化", "博物馆"],
        "展览馆": ["文化艺术"],
        "美术馆": ["文化艺术"],
        "公园": ["自然风光", "休闲"],
        "自然风光": ["自然风光"],
        "历史遗迹": ["历史文化"],
        "宗教场所": ["历史文化"],
        "动物园": ["亲子"],
        "植物园": ["自然风光"],
        "游乐场": ["亲子", "休闲"],
        "游乐园": ["亲子", "休闲"],
        "购物": ["购物"],
        "餐饮": ["美食"],
    }
    return pref_map.get(category, ["休闲"])


# ──────────────────────────────────────────────
# 模拟数据函数（内部使用 — 回退方案）
# ──────────────────────────────────────────────


def _get_mock_weather(city: str, days: int) -> dict:
    """使用本地 JSON 配置生成天气数据（无 API Key 时的回退方案）。"""
    data = _load_json("weather.json")
    city_weather = data.get(
        city,
        {
            "conditions": ["晴", "多云", "阴"],
            "temp_range": [20, 30],
            "humid": "中等",
            "clothing_advice_base": "天气适宜，穿着舒适即可",
        },
    )

    conditions = city_weather["conditions"]
    temp_min, temp_max = city_weather["temp_range"]
    advice_base = city_weather["clothing_advice_base"]

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

        daily_forecast.append(
            {
                "date": date,
                "temp_high": temp_high,
                "temp_low": temp_low,
                "condition": condition,
                "rain_prob": rain_prob,
            }
        )

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
        "source": "模拟数据",
    }


def _get_mock_attractions(city: str, preferences: list[str] | None, top_k: int) -> list[dict]:
    """从本地 JSON 文件读取景点数据，支持偏好匹配（无 API Key 时的回退方案）。"""
    file_path = MOCK_DATA_DIR / "attractions" / f"{_city_to_filename(city)}.json"
    if file_path.exists():
        with open(file_path, encoding="utf-8") as f:
            all_attractions = json.load(f)
    else:
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

    if preferences:
        for attr in all_attractions:
            attr_prefs = attr.get("preferences", [])
            score = sum(2 for p in preferences if p in attr_prefs)
            score += sum(1 for p in preferences if p in attr.get("description", ""))
            score += sum(1 for p in preferences if p in attr.get("name", ""))
            attr["score"] = score
        all_attractions.sort(key=lambda x: x.get("score", 0), reverse=True)
    else:
        for attr in all_attractions:
            attr["score"] = 1.0

    for attr in all_attractions:
        attr["source"] = "模拟数据"

    return all_attractions[:top_k]


# ──────────────────────────────────────────────
# 12306-mcp 数据源（外部 HTTP 服务，httpx 直调，不走 MCP 协议）
# ──────────────────────────────────────────────
#
# 本系统只有一个 MCP 端点（Python FastMCP 8765）。
# 12306-mcp 是 search_trains 的普通外部数据源，与和风天气 API 同级。
# 用户手动启动: npx -y 12306-mcp --port 8080
# .env 中 ENABLE_12306_MCP=true 后自动优先使用。

_12306_MCP_URL = None


async def _call_12306_mcp(tool_name: str, arguments: dict) -> list[dict] | None:
    """通过 httpx + JSON-RPC 直接调用 12306-mcp HTTP API。"""
    global _12306_MCP_URL
    if _12306_MCP_URL is None:
        _12306_MCP_URL = f"http://127.0.0.1:{MCP_12306_PORT}/mcp"

    import httpx
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                _12306_MCP_URL,
                json={"jsonrpc": "2.0", "method": "tools/call",
                      "params": {"name": tool_name, "arguments": arguments or {}}, "id": 1},
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            content = data.get("result", {}).get("content", [])
            parsed = []
            for item in content:
                if item.get("type") == "text":
                    try:
                        parsed.append(json.loads(item["text"]))
                    except (json.JSONDecodeError, TypeError):
                        parsed.append(item["text"])
            return parsed[0] if len(parsed) == 1 else (parsed or None)
    except Exception:
        return None


def _normalize_12306_trains(raw: list[dict], departure: str, destination: str) -> list[dict]:
    """将 12306-mcp 原始字段映射为系统统一格式。"""
    if not isinstance(raw, list):
        raw = [raw] if isinstance(raw, dict) else []
    normalized = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        train_no = item.get("train_no", item.get("trainNo", ""))
        dep_time = item.get("departure_time", item.get("departureTime", item.get("start_time", "")))
        arr_time = item.get("arrival_time", item.get("arrivalTime", item.get("end_time", "")))
        # 推断类型
        prefix = train_no[0] if train_no else ""
        type_map = {"G":"高铁","C":"城际","D":"动车","Z":"直达","T":"特快","K":"快速"}
        normalized.append({
            "train_no": train_no,
            "departure_station": item.get("departure_station", item.get("from_station", departure)),
            "arrival_station": item.get("arrival_station", item.get("to_station", destination)),
            "departure_time": dep_time,
            "arrival_time": arr_time,
            "duration": item.get("duration", ""),
            "price": item.get("price", 0),
            "type": f"{type_map.get(prefix, '普快')}（12306）",
            "source": "12306-mcp",
        })
    return normalized


async def _search_trains_12306(departure: str, destination: str, date: str | None = None) -> list[dict] | None:
    """从 12306-mcp 获取真实火车票数据。"""
    args = {"from": departure, "to": destination}
    if date:
        args["date"] = date
    raw = await _call_12306_mcp("search_tickets", args)
    if raw is None:
        return None
    result = _normalize_12306_trains(raw, departure, destination)
    if result:
        _log_source("search_trains", "12306-mcp（真实12306数据）")
    return result or None


# ──────────────────────────────────────────────
# 公开工具函数（Agent 和 MCP Server 调用入口）
# ──────────────────────────────────────────────


async def search_flights(
    departure: str,
    destination: str,
    date: str | None = None,
) -> list[dict]:
    """查询航班信息。

    数据源优先级：mcp-travel-smart-plan（飞猪） → 本地模拟数据

    Args:
        departure: 出发城市
        destination: 目的城市
        date: 出发日期 YYYY-MM-DD（可选）

    Returns:
        航班列表 [{flight_no, departure, arrival, departure_time, arrival_time, price, airline}]
    """
    # 1. 优先尝试 smart-plan（飞猪数据，零配置）
    if _HAVE_SMART_PLAN:
        raw = await call_smart_plan("search_flights", {"departure": departure, "destination": destination})
        if raw:
            import re

            flights = []
            for line in raw.splitlines():
                line = line.strip()
                m = re.match(r"\d+\.\s+(\w+)\s+(\S+)\s+(.+?)→(.+?)\s+(\d+:\d+)-(\d+:\d+)\s+¥(\d+)", line)
                if m:
                    flights.append(
                        {
                            "flight_no": m.group(1),
                            "airline": m.group(2),
                            "departure": m.group(3).strip(),
                            "arrival": m.group(4).strip(),
                            "departure_time": m.group(5),
                            "arrival_time": m.group(6),
                            "price": int(m.group(7)),
                        }
                    )
            if flights:
                _log_source("search_flights", "飞猪(smart-plan)")
                return flights

    # 2. 仅在 USE_MOCK 时回退到模拟数据
    if not USE_MOCK:
        _log_source("search_flights", "无可用数据源")
        return []
    data = _load_json("flights.json")
    key = f"{departure}-{destination}"
    reverse_key = f"{destination}-{departure}"
    results = data.get(key, data.get(reverse_key, []))

    if not results:
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

    for r in results:
        r.setdefault("source", "模拟数据")
    _log_source("search_flights", "模拟数据")
    return results


async def search_trains(
    departure: str,
    destination: str,
    date: str | None = None,
) -> list[dict]:
    """查询高铁/火车信息。

    数据源优先级：12306-mcp → smart-plan（飞猪） → 本地模拟数据

    Args:
        departure: 出发城市
        destination: 目的城市
        date: 出发日期 YYYY-MM-DD（可选）

    Returns:
        列车列表 [{train_no, departure_station, arrival_station, departure_time, arrival_time, duration, price, type}]
    """
    # 1. 优先尝试 12306-mcp（真实 12306 火车票数据）
    if ENABLE_12306_MCP:
        trains = await _search_trains_12306(departure, destination, date)
        if trains:
            return trains

    # 2. 尝试 smart-plan（飞猪数据，零配置）
    if _HAVE_SMART_PLAN:
        raw = await call_smart_plan("search_trains", {"departure": departure, "destination": destination})
        if raw:
            import re

            trains = []
            for line in raw.splitlines():
                line = line.strip()
                m = re.match(r"\d+\.\s+(\w+)\s+(.+?)→(.+?)\s+(\d+:\d+)-(\d+:\d+)\s+.*?¥(\d+)", line)
                if m:
                    # 计算时长
                    dep_hm = m.group(4).split(":")
                    arr_hm = m.group(5).split(":")
                    dep_min = int(dep_hm[0]) * 60 + int(dep_hm[1])
                    arr_min = int(arr_hm[0]) * 60 + int(arr_hm[1])
                    dur_min = arr_min - dep_min
                    if dur_min < 0:
                        dur_min += 24 * 60
                    hours, mins = divmod(dur_min, 60)
                    duration = f"{hours}h{mins}min" if hours else f"{mins}min"
                    if hours > 0 and mins == 0:
                        duration = f"{hours}小时"

                    # 推断类型
                    train_no = m.group(1)
                    train_type = "高铁" if train_no[0] in ("G", "C") else "动车" if train_no[0] == "D" else "快速" if train_no[0] == "K" else "特快" if train_no[0] == "T" else "直达" if train_no[0] == "Z" else "普快"

                    trains.append(
                        {
                            "train_no": train_no,
                            "departure_station": m.group(2).strip(),
                            "arrival_station": m.group(3).strip(),
                            "departure_time": m.group(4),
                            "arrival_time": m.group(5),
                            "duration": duration,
                            "price": int(m.group(6)),
                            "type": f"{train_type}（飞猪）",
                        }
                    )
            if trains:
                _log_source("search_trains", "飞猪(smart-plan)")
                return trains

    # 3. 仅在 USE_MOCK 时回退到模拟数据
    if not USE_MOCK:
        _log_source("search_trains", "无可用数据源")
        return []
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

    for r in results:
        r.setdefault("source", "模拟数据")
    _log_source("search_trains", "模拟数据")
    return results


async def search_hotels(
    city: str,
    check_in: str | None = None,
    check_out: str | None = None,
    max_price: float | None = None,
    preferences: list[str] | None = None,
) -> list[dict]:
    """搜索酒店。

    数据源优先级：mcp-travel-smart-plan（飞猪） → 本地模拟数据

    Args:
        city: 城市名
        check_in: 入住日期 YYYY-MM-DD（可选）
        check_out: 退房日期 YYYY-MM-DD（可选）
        max_price: 每晚最高价格（可选）
        preferences: 偏好关键词（可选）

    Returns:
        酒店列表 [{name, price, location, rating, distance_to_center}]
    """
    # 1. 优先尝试 smart-plan（飞猪数据，零配置）
    if _HAVE_SMART_PLAN:
        raw = await call_smart_plan("search_hotels", {"city": city})
        if raw:
            import re

            hotels = []
            for line in raw.splitlines():
                line = line.strip()
                m = re.match(r"\d+\.\s+(.+?)\s+(?:⭐|★)?([\d.]+)?\s*(?:¥|人均)([\d.]+)", line)
                if m:
                    name = m.group(1).strip()
                    rating = float(m.group(2)) if m.group(2) else 4.0
                    price = float(m.group(3)) if m.group(3) else 0
                    hotels.append(
                        {
                            "name": name,
                            "price": round(price),
                            "rating": rating,
                            "location": "",
                            "distance_to_center": 0,
                        }
                    )
            if hotels:
                if max_price is not None:
                    hotels = [h for h in hotels if h["price"] <= max_price]
                hotels.sort(key=lambda x: x["rating"], reverse=True)
                _log_source("search_hotels", "飞猪(smart-plan)")
                return hotels

    # 2. 仅在 USE_MOCK 时回退到模拟数据
    if not USE_MOCK:
        _log_source("search_hotels", "无可用数据源")
        return []
    data = _load_json("hotels.json")
    results = data.get(city, [])

    if max_price is not None:
        results = [h for h in results if h["price"] <= max_price]

    results = sorted(results, key=lambda x: x["rating"], reverse=True)
    for r in results:
        r.setdefault("source", "模拟数据")
    _log_source("search_hotels", "模拟数据")
    return results


async def get_weather(city: str, days: int = 3) -> dict:
    """查询天气预报。

    数据源优先级：mcp-travel-smart-plan（高德） → 和风天气 API → 模拟数据

    Args:
        city: 城市名
        days: 预报天数（1-7）

    Returns:
        天气预报 {daily: [{date, temp_high, temp_low, condition, rain_prob}], clothing_advice, impact_on_travel}
    """
    days = max(1, min(days, 7))

    # 1. 优先尝试 smart-plan（高德数据，零配置）
    if _HAVE_SMART_PLAN:
        raw = await call_smart_plan("get_weather", {"city": city})
        if raw:
            parsed = _parse_smart_weather(raw, city)
            if parsed:
                parsed["days"] = days
                parsed["daily"] = parsed["daily"][:days]
                _log_source("get_weather", "高德(smart-plan)")
                return parsed

    # 2. 有和风天气 API Key 时调用
    if WEATHER_API_KEY:
        result = await _call_qweather_api(city, days)
        if result is not None:
            _log_source("get_weather", "和风天气")
            return result

    # 3. 仅在 USE_MOCK 时回退到模拟数据
    if USE_MOCK:
        _log_source("get_weather", "模拟数据")
        return _get_mock_weather(city, days)
    _log_source("get_weather", "无可用数据源")
    return {"daily": [], "clothing_advice": "", "impact_on_travel": ""}


async def search_attractions(
    city: str,
    preferences: list[str] | None = None,
    top_k: int = 10,
) -> list[dict]:
    """搜索景点信息。

    数据源优先级：mcp-travel-smart-plan（飞猪） → 高德 POI API → 本地模拟数据

    Args:
        city: 城市名
        preferences: 偏好关键词列表，如 ["美食", "历史文化"]
        top_k: 返回数量上限

    Returns:
        景点列表 [{name, category, ticket_price, duration, description, score}]
    """
    top_k = max(1, min(top_k, 30))
    attractions = None

    # 1. 优先尝试 smart-plan（飞猪数据，零配置）
    if _HAVE_SMART_PLAN:
        raw = await call_smart_plan("search_attractions", {"city": city})
        if raw:
            import re

            parsed = []
            for line in raw.splitlines():
                line = line.strip()
                m = re.match(r"\d+\.\s+(.+?)(?:\s*[⭐★高价¥].*)?$", line)
                if m:
                    parsed.append(
                        {
                            "name": m.group(1).strip(),
                            "category": "景点",
                            "ticket_price": 0,
                            "duration": "2小时",
                            "description": "",
                            "preferences": ["休闲"],
                            "source": "飞猪（smart-plan）",
                        }
                    )
            if parsed and len(parsed) >= 2:
                attractions = parsed[:top_k]

    # 2. 有高德 API Key 时调用高德 POI
    if attractions is None and AMAP_API_KEY:
        attractions = await _call_amap_attractions_api(city, top_k)

    # 3. 仅在 USE_MOCK 时回退到模拟数据
    if attractions is None and USE_MOCK:
        attractions = _get_mock_attractions(city, preferences, top_k)
    if attractions is None:
        _log_source("search_attractions", "无可用数据源")
        return []

    # 偏好评分排序
    if preferences and attractions:
        for attr in attractions:
            attr_prefs = attr.get("preferences", [])
            score = sum(2 for p in preferences if p in attr_prefs)
            score += sum(1 for p in preferences if p in attr.get("description", ""))
            score += sum(1 for p in preferences if p in attr.get("name", ""))
            attr["score"] = score
        attractions.sort(key=lambda x: x.get("score", 0), reverse=True)
    elif attractions:
        for attr in attractions:
            attr.setdefault("score", 1.0)

    # 确定数据来源
    if attractions:
        src = attractions[0].get("source", "模拟数据")
        _log_source("search_attractions", src)
    else:
        _log_source("search_attractions", "模拟数据")

    return attractions[:top_k]
