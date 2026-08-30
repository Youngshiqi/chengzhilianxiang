# ============================================================
# 城市公共设施智能报修与派单系统 - 工具类 API
# 作用：提供前端通用工具接口（逆地理编码等），不依赖角色权限
# ============================================================

from fastapi import APIRouter, Query

from app.schemas.common import APIResponse
from app.services.map.amap_service import reverse_geocode

router = APIRouter()


@router.get("/reverse-geocode", response_model=APIResponse[dict])
async def reverse_geocode_api(
    lng: float = Query(..., description="经度"),
    lat: float = Query(..., description="纬度"),
):
    """
    逆地理编码：GPS坐标 → 结构化地址。
    供市民端/维修员端获取当前位置的可读地址。
    """
    rgc = await reverse_geocode(lng, lat)
    if not rgc:
        return APIResponse(code=500, msg="逆地理编码失败", data=None).model_dump()

    return APIResponse(
        msg="ok",
        data={
            "address": rgc.get("formatted_address", ""),
            "district": rgc.get("district", ""),
            "city": rgc.get("city", ""),
            "province": rgc.get("province", ""),
            "adcode": rgc.get("adcode", ""),
            "township": rgc.get("township", ""),
            "lng": lng,
            "lat": lat,
        },
    ).model_dump()
