# ============================================================
# 城市公共设施智能报修与派单系统 - 高德地图 REST API 服务
# 作用：封装高德 Web API 调用（逆地理编码 / IP定位 / 地理编码）；
#       使用 httpx 异步客户端，带重试与降级容错；
#       三级降级: 浏览器GPS → 高德IP定位 → 默认长沙中心
# ============================================================

import logging
from typing import Any, Dict, Optional

import httpx

from app.config.settings import settings

logger = logging.getLogger(__name__)

AMAP_REST_BASE = "https://restapi.amap.com/v3"
AMAP_KEY = settings.AMAP_API_KEY
HTTP_TIMEOUT = 5.0   # 高德 API 超时秒数
MAX_RETRIES = 2      # 失败重试次数


async def _get(path: str, params: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """带重试的异步 GET → JSON，失败返回 None"""
    url = f"{AMAP_REST_BASE}{path}"
    params.setdefault("key", AMAP_KEY)

    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                body = resp.json()
                if body.get("status") == "1":
                    return body
                else:
                    logger.warning(f"高德 API 返回失败: {path} info={body.get('info')}")
                    return None
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                logger.debug(f"高德 API 重试 {attempt+1}/{MAX_RETRIES}: {path}")

    logger.warning(f"高德 API 请求失败（已重试）: {path} error={last_err}")
    return None


# ═══════════════════════════════════════════════════════════
# 1. 逆地理编码：GPS 坐标 → 结构化地址
# ═══════════════════════════════════════════════════════════

async def reverse_geocode(lng: float, lat: float) -> Optional[Dict[str, Any]]:
    """
    逆地理编码：将经纬度转换为详细地址。

    返回:
      {
        "formatted_address": "长沙市芙蓉区定王台街道...",
        "district": "芙蓉区",
        "city": "长沙市",
        "province": "湖南省",
        "adcode": "430102",
        "township": "定王台街道",
        "street_number": "五一大道1号",
        "lng": 112.9884,
        "lat": 28.1938,
      }
      失败返回 None
    """
    body = await _get("/geocode/regeo", {
        "location": f"{lng:.6f},{lat:.6f}",
        "extensions": "base",
    })
    if not body:
        return None

    try:
        regeo = body["regeocode"]
        comp = regeo.get("addressComponent", {})

        # 街道门牌号信息（extensions=base 下可能为空）
        street = comp.get("streetNumber", {}).get("street") or comp.get("streetNumber", {}).get("name") or ""

        return {
            "formatted_address": regeo.get("formatted_address", ""),
            "district": comp.get("district", ""),
            "city": comp.get("city", []) if isinstance(comp.get("city"), list) else comp.get("city", ""),
            "province": comp.get("province", ""),
            "adcode": comp.get("adcode", ""),
            "township": comp.get("township", ""),
            "street_number": street,
            "lng": lng,
            "lat": lat,
        }
    except Exception as e:
        logger.warning(f"逆地理编码解析失败: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# 2. IP 定位：客户端 IP → 大致地理位置
# ═══════════════════════════════════════════════════════════

async def ip_location(client_ip: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    IP 定位：根据 IP 地址获取大致地理位置（维修员无GPS时的降级方案）。
    不传 ip 则使用请求方出口 IP。

    返回:
      {
        "lng": 112.9388,
        "lat": 28.2282,
        "city": "长沙市",
        "province": "湖南省",
        "adcode": "430100",
        "rectangle": "112.5000,27.8000;113.3000,28.6000"
      }
      失败返回 None
    """
    params: Dict[str, str] = {}
    if client_ip:
        params["ip"] = client_ip

    body = await _get("/ip", params)
    if not body:
        return None

    try:
        # rect 格式: "left,bottom;right,top" → 取中心点
        rect = body.get("rectangle", "")
        lng, lat = _rect_center(rect) if rect else (112.9388, 28.2282)

        return {
            "lng": round(lng, 6),
            "lat": round(lat, 6),
            "city": body.get("city", ""),
            "province": body.get("province", ""),
            "adcode": body.get("adcode", ""),
            "rectangle": rect,
        }
    except Exception as e:
        logger.warning(f"IP定位解析失败: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# 3. 地理编码：地址文本 → GPS 坐标（备用）
# ═══════════════════════════════════════════════════════════

async def geocode(address: str, city: str = "") -> Optional[Dict[str, Any]]:
    """
    地理编码：将文字地址转换为 GPS 坐标。

    返回:
      {
        "lng": 112.9884,
        "lat": 28.1938,
        "formatted_address": "长沙市芙蓉区...",
        "district": "芙蓉区",
        "adcode": "430102",
      }
      失败返回 None
    """
    params: Dict[str, str] = {"address": address}
    if city:
        params["city"] = city

    body = await _get("/geocode/geo", params)
    if not body:
        return None

    try:
        geocodes = body.get("geocodes", [])
        if not geocodes:
            logger.warning(f"地理编码无结果: address={address}")
            return None

        g = geocodes[0]
        loc = g.get("location", "")
        lng_str, lat_str = loc.split(",")[0], loc.split(",")[1] if "," in loc else ("0", "0")
        lng, lat = float(lng_str), float(lat_str)

        return {
            "lng": round(lng, 6),
            "lat": round(lat, 6),
            "formatted_address": g.get("formatted_address", address),
            "district": g.get("district", ""),
            "adcode": g.get("adcode", ""),
        }
    except Exception as e:
        logger.warning(f"地理编码解析失败: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════

def _rect_center(rect: str) -> tuple:
    """
    将高德 IP 定位返回的 rectangle "left,bottom;right,top" 解析为中心点。
    """
    try:
        left_bottom, right_top = rect.split(";")
        left, bottom = map(float, left_bottom.split(","))
        right, top = map(float, right_top.split(","))
        return ((left + right) / 2, (bottom + top) / 2)
    except Exception:
        return (112.9388, 28.2282)


# ═══════════════════════════════════════════════════════════
# 4. 驾车路径规划：两点之间实际路面距离
# ═══════════════════════════════════════════════════════════

async def driving_distance(
    origin_lng: float,
    origin_lat: float,
    dest_lng: float,
    dest_lat: float,
) -> Optional[Dict[str, Any]]:
    """
    驾车路径规划：获取两点之间的实际路面行驶距离与预估时间。

    返回:
      {
        "distance_km": 5.23,      # 行驶距离（公里）
        "duration_min": 12.5,     # 预估行驶时间（分钟）
      }
      失败返回 None（调用方应降级为直线距离）
    """
    body = await _get("/direction/driving", {
        "origin": f"{origin_lng:.6f},{origin_lat:.6f}",
        "destination": f"{dest_lng:.6f},{dest_lat:.6f}",
        "extensions": "base",
        "strategy": "32",          # 高德推荐：速度最快
    })
    if not body:
        return None

    try:
        path = body["route"]["paths"][0]
        return {
            "distance_km": round(int(path["distance"]) / 1000.0, 2),
            "duration_min": round(int(path["duration"]) / 60.0, 1),
        }
    except (KeyError, IndexError, ValueError, TypeError) as e:
        logger.warning(f"驾车距离解析失败: {e}")
        return None
