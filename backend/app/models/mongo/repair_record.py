# ============================================================
# 城市公共设施智能报修与派单系统 - repair_records 维修详情记录文档
# 作用：存储维修全流程详情——耗材数组（不同设施耗材种类差异大，数组结构灵活）、
#       工时填报、维修备注、前后对比照片URL、GPS签到坐标；
#       一体存储无需 MySQL 多表 JOIN，关联结算单核算材料成本
# 对应 MongoDB Collection：repair_records
# ============================================================

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.utils.timezone import now_beijing


class Material(BaseModel):
    """耗材明细"""
    name: str = Field(..., description="耗材名称")
    qty: float = Field(..., description="数量")
    unit: str = Field("个", description="单位")
    unit_cost: float = Field(0.0, description="单价")


class GPSCheckin(BaseModel):
    """签到 GPS 坐标"""
    lng: float
    lat: float


class RepairRecord(BaseModel):
    """维修详情记录文档结构"""
    ticket_id: str = Field(..., description="关联工单ID")
    worker_id: str = Field(..., description="维修员ID")
    materials: List[Material] = Field(default_factory=list, description="耗材清单（数组灵活存储）")
    labor_hours: float = Field(0.0, description="维修工时（小时）")
    work_notes: Optional[str] = Field(None, description="维修备注")
    before_photos: List[str] = Field(default_factory=list, description="维修前照片URL列表")
    after_photos: List[str] = Field(default_factory=list, description="完工照片URL列表")
    gps_checkin: Optional[GPSCheckin] = Field(None, description="到场签到GPS坐标")
    created_at: datetime = Field(default_factory=now_beijing)

    class Config:
        json_schema_extra = {
            "example": {
                "ticket_id": "TK20260621001",
                "worker_id": "W001",
                "materials": [
                    {"name": "LED灯泡", "qty": 2, "unit": "个", "unit_cost": 45.0},
                    {"name": "绝缘胶带", "qty": 1, "unit": "卷", "unit_cost": 8.0},
                ],
                "labor_hours": 1.5,
                "work_notes": "更换灯泡，检查线路正常",
                "gps_checkin": {"lng": 112.9388, "lat": 28.2282},
            }
        }
