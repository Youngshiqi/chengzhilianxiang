# ============================================================
# 城市公共设施智能报修与派单系统 - 维修员端 Schema
# 作用：定义维修员端 API 的请求体/响应体校验规则；
#       覆盖：工单大厅列表、接单确认、到场签到、完工提交、绩效查询
# ============================================================

from typing import List, Optional
from pydantic import BaseModel, Field


# ---------- 接单大厅 ----------
class TicketQueueResponse(BaseModel):
    """工单大厅列表（含状态，区分可接/已被接）"""
    ticket_id: str
    facility_type: str
    description: str
    address: str
    distance_meters: float = Field(..., description="距维修员距离（米）")
    emergency_level: int
    status: str = Field(..., description="工单当前状态")
    assigned_worker_id: Optional[str] = Field(None, description="已指派维修员ID")
    ai_category: Optional[str] = None
    created_at: str


# ---------- 接单 ----------
class TicketAcceptRequest(BaseModel):
    """维修员接单"""
    ticket_id: str = Field(..., description="工单ID")


# ---------- 签到 ----------
class CheckinRequest(BaseModel):
    """到场签到"""
    ticket_id: str
    lng: float
    lat: float


# ---------- 位置上报 ----------
class LocationUpdateRequest(BaseModel):
    """维修员实时位置上报"""
    lng: float = Field(..., description="经度")
    lat: float = Field(..., description="纬度")


# ---------- 完工 ----------
class CompletionRequest(BaseModel):
    """完工提交"""
    ticket_id: str
    materials: List[dict] = Field(default_factory=list, description="耗材清单 [{name, qty, unit_cost}]")
    labor_hours: float = Field(..., gt=0, description="维修工时")
    work_notes: Optional[str] = Field(None, description="维修备注")
    completion_photo_urls: List[str] = Field(default_factory=list, description="完工照片URL")


# ---------- 绩效 ----------
class WorkerPerformanceResponse(BaseModel):
    """维修员绩效"""
    worker_id: str
    name: str
    today_orders: int = 0
    month_orders: int = 0
    avg_star: float = 0.0
    avg_response_minutes: float = 0.0
    settlement_estimate: float = 0.0  # 历史总结算
