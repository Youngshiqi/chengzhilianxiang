# ============================================================
# 城市公共设施智能报修与派单系统 - tickets 工单主表 ORM 模型
# 作用：工单全生命周期主记录，status 枚举流转：
#       pending → dispatching → repairing → verifying → closed；
#       联合索引 (status + created_at) 支持状态分页查询；
#       索引 assigned_worker_id 支持维修员快速查询
# 对应 MySQL 表：tickets
# ============================================================

import datetime
from sqlalchemy import String, Text, DateTime, Float, Integer, Index, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mysql.base import Base
from app.utils.timezone import now_beijing


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id: Mapped[str] = mapped_column(String(32), primary_key=True, comment="工单唯一ID")
    user_id: Mapped[str] = mapped_column(String(32), index=True, comment="报修用户ID")
    facility_code: Mapped[str] = mapped_column(String(32), index=True, comment="关联设施编码")
    facility_type: Mapped[str] = mapped_column(String(32), comment="设施品类")
    district: Mapped[str] = mapped_column(String(64), nullable=True, default="", index=True, comment="所属行政区（冗余字段，避免JOIN）")
    status: Mapped[str] = mapped_column(
        SAEnum("pending", "accepting", "dispatching", "repairing", "verifying", "closed", "cancelled", name="ticket_status"),
        default="pending",
        index=True,
        comment="工单状态",
    )
    description: Mapped[str] = mapped_column(Text, comment="故障文字描述")
    address: Mapped[str] = mapped_column(String(255), comment="报修地址（GPS反查）")
    location_lng: Mapped[float] = mapped_column(Float, comment="经度")
    location_lat: Mapped[float] = mapped_column(Float, comment="纬度")
    emergency_level: Mapped[int] = mapped_column(Integer, default=0, comment="紧急程度 0普通 1紧急")
    assigned_worker_id: Mapped[str] = mapped_column(
        String(32), nullable=True, index=True, comment="指派维修员ID"
    )
    ai_category: Mapped[str] = mapped_column(String(64), nullable=True, comment="AI解析故障分类")
    ai_confidence: Mapped[float] = mapped_column(Float, nullable=True, comment="AI置信度")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=now_beijing, comment="创建时间"
    )
    accepted_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True, comment="接单时间")
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True, comment="到场时间")
    completed_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True, comment="完工时间")
    closed_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True, comment="完结时间")

    # 联合索引：工单状态分页查询（高频场景）
    __table_args__ = (
        Index("idx_status_created", "status", "created_at"),
    )
