# ============================================================
# 城市公共设施智能报修与派单系统 - 管理后台驾驶舱 API
# 作用：GET /api/v1/admin/dashboard/realtime — 实时运营指标（Redis counter:today 毫秒级）；
#       GET /api/v1/admin/dashboard/analytics — 历史聚合统计（ES Aggregation）
# 数据源：Redis 实时计数器 + ES 历史聚合 + MySQL 结算报表
# ============================================================

from fastapi import APIRouter, Depends
from sqlalchemy import select, text, func

from app.config.redis_client import get_redis_counter
from app.schemas.admin import DashboardRealtimeResponse, DashboardAnalyticsResponse
from app.schemas.common import APIResponse
from app.core.security import get_current_user

router = APIRouter()


@router.get("/dashboard/realtime", response_model=APIResponse[DashboardRealtimeResponse])
async def get_realtime_dashboard(current_user: dict = Depends(get_current_user)):
    """
    驾驶舱实时指标（MySQL 实时查询）：
    - today_new: 今日创建工单数（created_at >= CURDATE）
    - today_dispatching: 待派发存量（status IN ('pending','dispatching')，含历史遗留）
    - today_repairing: 当前全部处理中工单（status='repairing'）
    - today_verifying: 当前全部验收中工单（status='verifying'）
    - today_closed: 今日完结工单数（closed_at >= CURDATE）
    - online_workers: Redis SCARD workers:online
    """
    from app.config.mysql import async_session_factory
    from app.models.mysql.ticket import Ticket

    async with async_session_factory() as db:
        # ── 今日新增工单（created_at >= 今天 00:00） ──
        today_new_result = await db.execute(
            select(func.count(Ticket.ticket_id)).where(
                Ticket.created_at >= func.curdate()
            )
        )
        today_new = today_new_result.scalar() or 0

        # ── 待派发存量：pending + dispatching（所有等待工人接单的工单） ──
        pending_result = await db.execute(
            select(func.count(Ticket.ticket_id)).where(
                Ticket.status.in_(["pending", "dispatching"])
            )
        )
        today_pending = pending_result.scalar() or 0

        # ── 当前存量：按 status 分组（repairing / verifying） ──
        status_result = await db.execute(
            select(
                Ticket.status,
                func.count(Ticket.ticket_id).label("cnt"),
            ).where(
                Ticket.status.in_(["repairing", "verifying"])
            ).group_by(Ticket.status)
        )
        status_map = {row[0]: row[1] for row in status_result.all()}
        today_repairing = status_map.get("repairing", 0)
        today_verifying = status_map.get("verifying", 0)

        # ── 今日完结工单（closed_at >= 今天 00:00） ──
        today_closed_result = await db.execute(
            select(func.count(Ticket.ticket_id)).where(
                Ticket.status == "closed",
                Ticket.closed_at >= func.curdate(),
            )
        )
        today_closed = today_closed_result.scalar() or 0

    # ── 在岗维修员 ──
    from app.config.redis_client import get_redis_cache
    online = await get_redis_cache().scard("workers:online")

    return APIResponse(
        data=DashboardRealtimeResponse(
            today_new=today_new,
            today_dispatching=today_pending,
            today_repairing=today_repairing,
            today_verifying=today_verifying,
            today_closed=today_closed,
            online_workers=online,
        ),
    ).model_dump()


@router.get("/dashboard/analytics", response_model=APIResponse[DashboardAnalyticsResponse])
async def get_analytics_dashboard(
    date_from: str = None,
    date_to: str = None,
    current_user: dict = Depends(get_current_user),
):
    """
    驾驶舱聚合统计（MySQL 聚合查询）：
    - 总工单量、平均响应时长、好评率
    - 高频故障设施 TOP10
    - 片区故障分布
    - 趋势时间序列（近6个月按月统计）
    """
    from app.config.mysql import async_session_factory
    from app.models.mysql.ticket import Ticket
    from app.models.mysql.evaluation import Evaluation

    async with async_session_factory() as db:
        # 总工单量
        total_result = await db.execute(select(func.count(Ticket.ticket_id)))
        total_tickets = total_result.scalar() or 0

        # 平均响应时长（已完结工单的 created_at → closed_at 分钟差）
        avg_resp_result = await db.execute(
            select(func.avg(
                func.timestampdiff(text("MINUTE"), Ticket.created_at, Ticket.closed_at)
            )).where(Ticket.status == "closed")
        )
        avg_response_minutes = round(float(avg_resp_result.scalar() or 0), 1)

        # 好评率
        avg_star_result = await db.execute(
            select(func.avg(Evaluation.star)).where(Evaluation.star > 0)
        )
        avg_star = round(float(avg_star_result.scalar() or 0), 1)

        # 高频故障设施 TOP10
        top_result = await db.execute(
            select(Ticket.facility_type, func.count(Ticket.ticket_id).label("cnt"))
            .group_by(Ticket.facility_type)
            .order_by(text("cnt DESC"))
            .limit(10)
        )
        top_facility_types = [
            {"name": row[0] or "其他", "count": row[1]}
            for row in top_result.all()
        ]

        # 片区故障分布（使用 Ticket.district 冗余字段，避免 JOIN）
        district_result = await db.execute(
            select(Ticket.district, func.count(Ticket.ticket_id).label("cnt"))
            .where(Ticket.district.isnot(None))
            .where(Ticket.district != "")
            .group_by(Ticket.district)
            .order_by(text("cnt DESC"))
        )
        district_distribution = [
            {"name": row[0], "count": row[1]}
            for row in district_result.all()
        ] if district_result else []

        # 趋势时间序列：近6个月按月统计新增/完结工单
        trend_result = await db.execute(
            select(
                func.date_format(Ticket.created_at, "%Y-%m").label("month"),
                func.count(Ticket.ticket_id).label("new_count"),
                func.sum(func.if_(Ticket.status == "closed", 1, 0)).label("closed_count"),
            )
            .where(Ticket.created_at >= func.date_sub(func.curdate(), text("INTERVAL 6 MONTH")))
            .group_by(text("month"))
            .order_by(text("month ASC"))
        )
        trend_data = [
            {"month": row[0], "new_count": row[1], "closed_count": row[2] or 0}
            for row in trend_result.all()
        ]

    return APIResponse(
        data=DashboardAnalyticsResponse(
            total_tickets=total_tickets,
            avg_response_minutes=avg_response_minutes,
            avg_star=avg_star,
            top_facility_types=top_facility_types,
            district_distribution=district_distribution,
            trend_data=trend_data,
        ),
    ).model_dump()
