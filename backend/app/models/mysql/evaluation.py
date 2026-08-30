# ============================================================
# 城市公共设施智能报修与派单系统 - evaluations 市民评价表 ORM 模型
# 作用：存储市民对维修服务的星级+标签+文字评价；
#       ticket_id 唯一索引防重复评价；
#       2星及以下差评自动触发 RabbitMQ 延迟复核队列；
#       评价数据联动 ES workers_perf_index 更新维修员绩效
# 对应 MySQL 表：evaluations
# ============================================================

import datetime
from sqlalchemy import String, Integer, Text, DateTime, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mysql.base import Base
from app.utils.timezone import now_beijing


class Evaluation(Base):
    __tablename__ = "evaluations"

    eval_id: Mapped[str] = mapped_column(String(32), primary_key=True, comment="评价唯一ID")
    ticket_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, comment="关联工单ID（唯一）")
    user_id: Mapped[str] = mapped_column(String(32), comment="评价用户ID")
    star: Mapped[int] = mapped_column(Integer, comment="星级评分 1-5")
    tags: Mapped[str] = mapped_column(String(255), nullable=True, comment="快捷评价标签（逗号分隔）")
    comment: Mapped[str] = mapped_column(Text, nullable=True, comment="文字补充评价")
    is_appealed: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否申诉中")
    appeal_result: Mapped[str] = mapped_column(String(32), nullable=True, comment="申诉结果")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=now_beijing, comment="评价时间"
    )

    __table_args__ = (
        Index("idx_eval_ticket", "ticket_id", unique=True),
    )
