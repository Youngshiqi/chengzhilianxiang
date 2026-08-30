# ============================================================
# 城市公共设施智能报修与派单系统 - 维修员端绩效 API
# 作用：GET /api/v1/worker/performance — 查询个人绩效数据；
#       MySQL 实时统计：今日接单 / 本月工单 / 好评率 / 预估结算
# ============================================================

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.config.mysql import get_db
from app.config.redis_client import get_redis_counter
from app.models.mysql.ticket import Ticket
from app.models.mysql.worker import Worker
from app.models.mysql.user import User
from app.models.mysql.evaluation import Evaluation
from app.models.mysql.settlement import Settlement
from app.schemas.worker import WorkerPerformanceResponse
from app.schemas.common import APIResponse
from app.core.security import get_current_user
from app.utils.timezone import now_beijing

router = APIRouter()


@router.get("/performance", response_model=APIResponse[WorkerPerformanceResponse])
async def get_my_performance(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    查询个人绩效（MySQL 实时统计）：
    - Redis: 今日接单数（实时计数器）
    - MySQL tickets: 本月工单数
    - MySQL evaluations: 好评率（关联 tickets 取该维修员的评价）
    - MySQL settlements: 本月预估结算
    """
    worker_id = current_user["user_id"]
    now = now_beijing()

    # ── 今日接单（MySQL 统计：今日接单或今日分配的工单） ──
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(func.count(Ticket.ticket_id)).where(
            and_(
                Ticket.assigned_worker_id == worker_id,
                # 条件：accepted_at 在今天，或者(accepted_at为空且created_at在今天)
                (Ticket.accepted_at >= today_start) |
                ((Ticket.accepted_at == None) & (Ticket.created_at >= today_start))
            )
        )
    )
    today_orders = today_result.scalar() or 0

    # ── 本月工单数 ──
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_result = await db.execute(
        select(func.count(Ticket.ticket_id)).where(
            and_(
                Ticket.assigned_worker_id == worker_id,
                Ticket.status != "pending",
                Ticket.created_at >= month_start,
            )
        )
    )
    month_orders = month_result.scalar() or 0

    # ── 好评率（所有已评价工单的星级均值） ──
    avg_star_result = await db.execute(
        select(func.avg(Evaluation.star)).where(
            Evaluation.ticket_id.in_(
                select(Ticket.ticket_id).where(
                    Ticket.assigned_worker_id == worker_id
                )
            )
        )
    )
    avg_star_raw = avg_star_result.scalar()
    avg_star = round(float(avg_star_raw), 1) if avg_star_raw else 0.0

    # ── 总结算（全部历史） ──
    settlement_result = await db.execute(
        select(func.coalesce(func.sum(Settlement.total), 0.0)).where(
            Settlement.worker_id == worker_id,
        )
    )
    settlement_estimate = round(float(settlement_result.scalar() or 0), 2)

    # ── 维修员姓名 ──
    worker_name = "维修员"
    try:
        w_result = await db.execute(
            select(Worker).where(Worker.worker_id == worker_id)
        )
        worker = w_result.scalar_one_or_none()
        if worker and worker.name:
            worker_name = worker.name
        else:
            u_result = await db.execute(
                select(User).where(User.user_id == worker_id)
            )
            user = u_result.scalar_one_or_none()
            if user:
                worker_name = user.nickname or user.username or "维修员"
    except Exception:
        pass

    return APIResponse(
        data=WorkerPerformanceResponse(
            worker_id=worker_id,
            name=worker_name,
            today_orders=today_orders,
            month_orders=month_orders,
            avg_star=avg_star,
            avg_response_minutes=0.0,
            settlement_estimate=settlement_estimate,
        ),
    ).model_dump()
