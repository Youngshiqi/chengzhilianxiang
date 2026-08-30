# ============================================================
# 城市公共设施智能报修与派单系统 - workers 维修员档案表 ORM 模型
# 作用：存储维修员技能标签（JSON字段）、最大日单量、夜班值守等属性；
#       关联绩效结算，是派单算法候选池的数据源
# 对应 MySQL 表：workers
# ============================================================

from sqlalchemy import String, Integer, Float, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mysql.base import Base


class Worker(Base):
    __tablename__ = "workers"

    worker_id: Mapped[str] = mapped_column(String(32), primary_key=True, comment="维修员ID（关联users.user_id）")
    name: Mapped[str] = mapped_column(String(32), comment="姓名")
    skills: Mapped[dict] = mapped_column(JSON, default=list, comment="技能标签JSON数组")
    max_daily_orders: Mapped[int] = mapped_column(Integer, default=20, comment="每日最大接单量")
    district: Mapped[str] = mapped_column(String(64), index=True, comment="所属片区")
    night_duty: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否值夜班")
    star_rating: Mapped[float] = mapped_column(Float, default=5.0, comment="综合星级评分")
    total_orders: Mapped[int] = mapped_column(Integer, default=0, comment="历史总工单数")
    avg_response_minutes: Mapped[float] = mapped_column(Float, default=0.0, comment="平均响应分钟数")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="在职状态")
