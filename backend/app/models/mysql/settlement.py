# ============================================================
# 城市公共设施智能报修与派单系统 - settlements 结算单表 ORM 模型
# 作用：自动生成结算单，记录劳务费+材料费+合计金额；
#       全流程审计留痕，支持导出PDF/Excel
# 对应 MySQL 表：settlements
# ============================================================

import datetime
from sqlalchemy import String, Float, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mysql.base import Base
from app.utils.timezone import now_beijing


class Settlement(Base):
    __tablename__ = "settlements"

    settlement_id: Mapped[str] = mapped_column(String(32), primary_key=True, comment="结算单ID")
    ticket_id: Mapped[str] = mapped_column(String(32), index=True, comment="关联工单ID")
    worker_id: Mapped[str] = mapped_column(String(32), index=True, comment="维修员ID")
    labor_cost: Mapped[float] = mapped_column(Float, default=0.0, comment="劳务费")
    material_cost: Mapped[float] = mapped_column(Float, default=0.0, comment="材料费")
    total: Mapped[float] = mapped_column(Float, comment="合计金额")
    audit_status: Mapped[str] = mapped_column(
        SAEnum("pending", "approved", "rejected", name="audit_status"),
        default="pending",
        comment="审核状态",
    )
    auditor_id: Mapped[str] = mapped_column(String(32), nullable=True, comment="审核人ID")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=now_beijing, comment="生成时间"
    )
