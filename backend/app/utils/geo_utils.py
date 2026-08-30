# ============================================================
# 城市公共设施智能报修与派单系统 - 地理计算工具
# 作用：Haversine公式计算两点距离（Redis Geo 无法使用时兜底）；
#       GPS坐标偏移脱敏（市民端显示维修员位置时加随机偏移）
# ============================================================

import math
import random


def haversine_distance(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    """使用 Haversine 公式计算两点间地表距离（米）"""
    R = 6371000  # 地球半径（米）

    rad_lat1 = math.radians(lat1)
    rad_lat2 = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(rad_lat1) * math.cos(rad_lat2) * math.sin(delta_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def desensitize_gps(lng: float, lat: float, offset_meters: int = 200) -> tuple:
    """GPS坐标脱敏：在原始坐标附近随机偏移（市民端隐私保护）"""
    # 纬度方向随机偏移（1度约111km）
    lat_offset = (offset_meters * random.uniform(-1, 1)) / 111000.0
    # 经度方向随机偏移（1度约111km * cos(lat)）
    lng_offset = (offset_meters * random.uniform(-1, 1)) / (111000.0 * math.cos(math.radians(lat)))

    return (round(lng + lng_offset, 6), round(lat + lat_offset, 6))
