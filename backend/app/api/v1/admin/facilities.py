# ============================================================
# 城市公共设施智能报修与派单系统 - 管理后台设施管理 API
# 作用：GET /api/v1/admin/facilities — 设施档案列表查询；
#       ES facilities_index 全文检索 + GeoPoint 空间查询；
#       系统内置1000条模拟市政设施点位
# ============================================================

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.config.mysql import get_db
from app.models.mysql.facility import Facility
from app.schemas.common import APIResponse
from app.core.security import get_current_user

router = APIRouter()


@router.get("/facilities", response_model=APIResponse)
async def list_facilities(
    district: str = "",
    facility_type: str = "",
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    设施档案列表：
    - MySQL 查询基础档案（GIS一张图数据源）
    - ES facilities_index 支持全文检索 + GeoPoint 空间查询
    """
    query = select(Facility)
    count_query = select(func.count(Facility.facility_code))
    if district:
        query = query.where(Facility.district == district)
        count_query = count_query.where(Facility.district == district)
    if facility_type:
        query = query.where(Facility.type == facility_type)
        count_query = count_query.where(Facility.type == facility_type)
    query = query.limit(page_size).offset((page - 1) * page_size)

    result = await db.execute(query)
    facilities = result.scalars().all()

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return APIResponse(data={
        "items": [{
            "facility_code": f.facility_code,
            "type": f.type,
            "address": f.address,
            "location": {"lng": f.location_lng, "lat": f.location_lat},
            "district": f.district,
            "status": f.status,
            "total_faults": f.total_faults,
        } for f in facilities],
        "total": total,
    }).model_dump()
