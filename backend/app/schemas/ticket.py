# ============================================================
# 城市公共设施智能报修与派单系统 - 工单通用 Schema
# 作用：工单状态流转、状态枚举等跨端共享的数据定义
# ============================================================

from enum import Enum
from pydantic import BaseModel, Field


class TicketStatus(str, Enum):
    """工单状态枚举（与MySQL tickets.status对齐）"""
    PENDING = "pending"           # 待受理
    ACCEPTING = "accepting"       # 派单中
    DISPATCHING = "dispatching"   # 已接单
    REPAIRING = "repairing"       # 维修中
    VERIFYING = "verifying"       # 验收中
    CLOSED = "closed"             # 已完结


class TicketStatusTransition(BaseModel):
    """工单状态流转记录"""
    from_status: str = Field(..., description="原状态")
    to_status: str = Field(..., description="新状态")
    timestamp: str = Field(..., description="发生时间")
    operator: str = Field(..., description="操作人")
    remark: str = Field("", description="备注")


STATUS_LABELS = {
    "pending": "待受理",
    "accepting": "派单中",
    "dispatching": "已接单",
    "repairing": "维修中",
    "verifying": "验收中",
    "closed": "已完结",
}


# ---------- 工单详情子结构（三端统一） ----------
class ReportInfo(BaseModel):
    """报修信息板块"""
    reporter_id: str = Field("", description="报修人ID")
    reporter_name: str = Field("", description="报修人昵称")
    reporter_phone: str = Field("", description="报修人手机号（脱敏）")
    description: str = Field("", description="故障描述")
    facility_type: str = Field("", description="设施品类")
    address: str = Field("", description="报修地址")
    location_lng: float = Field(0.0, description="经度")
    location_lat: float = Field(0.0, description="纬度")
    district: str = Field("", description="行政区")
    emergency_level: int = Field(0, description="紧急程度 0普通 1紧急")
    image_urls: list = Field(default_factory=list, description="报修现场照片URL列表")
    created_at: str = Field("", description="报修时间")


class WorkerInfo(BaseModel):
    """维修员信息"""
    worker_id: str = Field("", description="维修员ID")
    worker_name: str = Field("", description="维修员姓名")
    worker_phone: str = Field("", description="维修员手机号（脱敏）")
    worker_avatar: str = Field("", description="维修员头像URL")
    star_rating: float = Field(0.0, description="星级评分")
    total_orders: int = Field(0, description="历史总工单数")


class RepairMaterial(BaseModel):
    """耗材明细"""
    name: str = Field("", description="耗材名称")
    qty: float = Field(0.0, description="数量")
    unit: str = Field("个", description="单位")
    unit_cost: float = Field(0.0, description="单价（元）")


class RepairInfo(BaseModel):
    """维修信息板块"""
    worker: WorkerInfo | None = Field(None, description="维修员信息")
    materials: list[RepairMaterial] = Field(default_factory=list, description="耗材清单")
    labor_hours: float = Field(0.0, description="维修工时（小时）")
    work_notes: str = Field("", description="维修备注")
    completion_photos: list[str] = Field(default_factory=list, description="完工照片URL列表")
    checkin_lng: float | None = Field(None, description="签到经度")
    checkin_lat: float | None = Field(None, description="签到纬度")
    checkin_at: str = Field("", description="签到时间")
    completed_at: str = Field("", description="完工时间")


class AIResult(BaseModel):
    """AI 处理结果"""
    ai_category: str = Field("", description="AI识别故障分类")
    ai_confidence: float = Field(0.0, description="AI分类置信度")
    ai_verified: bool | None = Field(None, description="AI验收是否通过")
    ai_verify_confidence: float | None = Field(None, description="AI验收置信度")
    ai_verify_summary: str = Field("", description="AI验收摘要")


class TimelineEvent(BaseModel):
    """时间轴节点"""
    event: str = Field("", description="事件标识：reported/dispatched/accepted/checkin/completed/ai_verified/closed/evaluated")
    label: str = Field("", description="事件中文标签")
    time: str = Field("", description="事件时间")
    detail: str = Field("", description="事件详情文本")
    done: bool = Field(False, description="是否已完成")


class SettlementInfo(BaseModel):
    """结算信息（仅已完结工单）"""
    material_cost: float = Field(0.0, description="耗材费合计")
    labor_cost: float = Field(0.0, description="劳务费")
    total_cost: float = Field(0.0, description="合计费用")


# ---------- 统一详情响应 ----------
class TicketDetailResponse(BaseModel):
    """工单详情响应（三端统一）"""
    ticket_id: str = Field("", description="工单号")
    status: str = Field("", description="当前状态")
    status_label: str = Field("", description="状态中文标签")

    # 三大板块
    report: ReportInfo = Field(default_factory=ReportInfo, description="报修信息")
    repair: RepairInfo = Field(default_factory=RepairInfo, description="维修信息")
    ai: AIResult = Field(default_factory=AIResult, description="AI处理结果")

    # 时间轴
    timeline: list[TimelineEvent] = Field(default_factory=list, description="全流程时间轴")

    # 结算（仅已完结）
    settlement: SettlementInfo | None = Field(None, description="结算信息")

    # 时间戳
    created_at: str = Field("", description="报修时间")
    accepted_at: str = Field("", description="接单时间")
    started_at: str = Field("", description="签到时间")
    completed_at: str = Field("", description="完工时间")
    closed_at: str = Field("", description="完结时间")
