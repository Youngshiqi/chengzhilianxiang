# ============================================================
# 城市公共设施智能报修与派单系统 - 管理后台 Schema
# 作用：定义管理后台 API 的请求体/响应体校验规则；
#       覆盖：驾驶舱实时指标、聚合统计、工单全文检索、审计日志、人工调度、结算审核
# ============================================================

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------- 驾驶舱 ----------
class DashboardRealtimeResponse(BaseModel):
    """驾驶舱实时指标"""
    today_new: int = Field(0, description="今日新增工单（created_at >= 今日00:00）")
    today_dispatching: int = Field(0, description="待受理存量（status='pending'，含历史遗留）")
    today_repairing: int = Field(0, description="处理中存量（status='repairing'，含历史遗留）")
    today_verifying: int = Field(0, description="验收中存量（status='verifying'，含历史遗留）")
    today_closed: int = Field(0, description="今日完结工单（closed_at >= 今日00:00）")
    online_workers: int = Field(0, description="在岗维修员")


class DashboardAnalyticsResponse(BaseModel):
    """驾驶舱聚合统计"""
    total_tickets: int = 0
    avg_response_minutes: float = 0.0
    avg_star: float = 0.0
    top_facility_types: List[Dict] = Field(default_factory=list, description="高频故障设施TOP10")
    district_distribution: List[Dict] = Field(default_factory=list, description="片区故障分布")
    trend_data: List[Dict] = Field(default_factory=list, description="趋势时间序列")


# ---------- 工单管理 ----------
class TicketSearchRequest(BaseModel):
    """工单全文检索请求"""
    keyword: Optional[str] = Field(None, description="搜索关键词（IK中文分词）")
    status: Optional[str] = None
    facility_type: Optional[str] = None
    district: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class ForceDispatchRequest(BaseModel):
    """人工强制指派请求"""
    ticket_id: str
    worker_id: str


# ---------- 审计日志 ----------
class AuditLogResponse(BaseModel):
    """审计日志响应"""
    operator_id: str
    role: str
    action: str
    target: Dict[str, Any]
    old_value: Optional[Dict]
    new_value: Optional[Dict]
    ip: str
    created_at: str


# ---------- 结算 ----------
class SettlementAuditRequest(BaseModel):
    """结算审核请求"""
    settlement_id: str
    action: str = Field(..., description="approved | rejected")
    remark: Optional[str] = None
