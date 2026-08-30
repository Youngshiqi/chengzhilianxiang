# ============================================================
# 城市公共设施智能报修与派单系统 - audit_rules 结算规则配置表 ORM 模型
# 作用：后台热配置结算规则（不同设施类型基价、加班费率、紧急倍率）；
#       Redis config:* 缓存热读，修改即时生效无需重启服务
# 对应 MySQL 表：audit_rules
# ============================================================

from sqlalchemy import String, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mysql.base import Base


class AuditRule(Base):
    __tablename__ = "audit_rules"

    rule_id: Mapped[str] = mapped_column(String(32), primary_key=True, comment="规则唯一ID")
    facility_type: Mapped[str] = mapped_column(String(32), comment="设施品类")
    base_price: Mapped[float] = mapped_column(Float, default=50.0, comment="基础劳务单价")
    overtime_rate: Mapped[float] = mapped_column(Float, default=1.5, comment="加班费率倍数")
    emergency_multiplier: Mapped[float] = mapped_column(Float, default=2.0, comment="紧急工单倍率")
    night_subsidy: Mapped[float] = mapped_column(Float, default=30.0, comment="夜班补贴（元）")
