# ============================================================
# 城市公共设施智能报修与派单系统 - facilities 设施档案表 ORM 模型
# 作用：市政设施基础档案，存储1000条模拟点位；
#       (location_lng, location_lat) 组合索引支持地理范围查询兜底；
#       关联工单主表通过 facility_code 外键
# 对应 MySQL 表：facilities
# ============================================================

import datetime
from sqlalchemy import String, Float, DateTime, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mysql.base import Base


class Facility(Base):
    __tablename__ = "facilities"

    facility_code: Mapped[str] = mapped_column(String(32), primary_key=True, comment="设施唯一编码")
    type: Mapped[str] = mapped_column(String(32), index=True, comment="设施品类（路灯/井盖/护栏等）")
    location_lng: Mapped[float] = mapped_column(Float, comment="经度")
    location_lat: Mapped[float] = mapped_column(Float, comment="纬度")
    address: Mapped[str] = mapped_column(String(255), comment="详细地址")
    district: Mapped[str] = mapped_column(String(64), index=True, comment="所属行政区")
    install_date: Mapped[datetime.date] = mapped_column(DateTime, nullable=True, comment="安装日期")
    status: Mapped[str] = mapped_column(String(16), default="normal", comment="设施状态 normal/repairing/scrapped")
    total_faults: Mapped[int] = mapped_column(Integer, default=0, comment="累计故障次数")

    __table_args__ = (
        Index("idx_facility_location", "location_lng", "location_lat"),
    )
