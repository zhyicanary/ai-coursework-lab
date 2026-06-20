"""交通 Agent - 查询航班/高铁"""

import random


async def transport_agent(departure: str, destination: str, days: int) -> dict:
    """
    查询交通信息
    实际项目中可接入携程/12306 API
    """
    routes = {
        ("北京", "成都"): [
            {"type": "高铁", "name": "G89", "departure_time": "07:00", "arrival_time": "14:00", "duration": "7小时", "price": 780},
            {"type": "航班", "name": "CA1401", "departure_time": "08:00", "arrival_time": "10:30", "duration": "2小时30分", "price": 1200},
        ],
        ("上海", "成都"): [
            {"type": "高铁", "name": "G1970", "departure_time": "06:30", "arrival_time": "15:30", "duration": "9小时", "price": 850},
            {"type": "航班", "name": "MU5401", "departure_time": "07:30", "arrival_time": "10:00", "duration": "2小时30分", "price": 1100},
        ],
    }
    
    key = (departure, destination)
    if key in routes:
        options = routes[key]
    else:
        options = [
            {"type": "高铁", "name": "G1234", "departure_time": "08:00", "arrival_time": "15:00", "duration": "7小时", "price": 750},
            {"type": "航班", "name": "CA1234", "departure_time": "09:00", "arrival_time": "11:30", "duration": "2小时30分", "price": 1150},
        ]
    
    recommended = min(options, key=lambda x: x["price"])
    
    return {
        "departure": departure,
        "destination": destination,
        "options": options,
        "recommended": recommended,
        "total_cost_round": recommended["price"] * 2,
        "advice": f"推荐{recommended['type']}：{recommended['name']}，{recommended['price']}元"
    }
