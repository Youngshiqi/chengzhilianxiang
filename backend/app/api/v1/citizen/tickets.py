# ============================================================
# 城市公共设施智能报修与派单系统 - 市民端工单 API
# 作用：POST /api/v1/citizen/tickets — 市民提交AI智能报修工单；
#       GET /api/v1/citizen/tickets/{id} — 查询工单实时进度；
#       GET /api/v1/citizen/tickets — 查询历史工单列表；
#       PUT /api/v1/citizen/tickets/{id}/close — 市民确认完结工单
# 数据流：写MySQL tickets主表 → MongoDB存AI解析+图片元数据 → Redis缓存热状态 → RabbitMQ入队
# ============================================================

import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.config.mysql import get_db
from app.config.redis_client import get_redis_cache
from app.config.mongodb import get_mongo_db
from app.models.mysql.ticket import Ticket
from app.models.mysql.user import User
from app.schemas.citizen import TicketCreateRequest, TicketCreateResponse
from app.schemas.common import APIResponse, PaginationResponse
from app.core.security import get_current_user
from app.core.exceptions import NotFoundException, BadRequestException
from app.services.citizen.report_service import submit_repair_report
from app.services.ticket_detail_service import get_ticket_detail
from app.utils.timezone import now_beijing

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/tickets", response_model=APIResponse[TicketCreateResponse])
async def create_ticket(
    req: TicketCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    市民提交AI智能报修：
    1. 同步：MySQL tickets 落地 + Redis 缓存
    2. 异步：NLP解析 + MongoDB日志 + ES索引 + RabbitMQ派单入队
    所有异步操作容错设计，单个失败不影响主流程
    """
    result = await submit_repair_report(
        db=db,
        user_id=current_user["user_id"],
        description=req.description,
        facility_type=req.facility_type,
        location_lng=req.location_lng,
        location_lat=req.location_lat,
        address=req.address,
        image_urls=req.image_urls,
        emergency_level=req.emergency_level,
    )

    # 判断是否为重复提交
    is_duplicate = result.get("is_duplicate", False)

    return APIResponse(
        code=200,
        msg=result["message"],
        data=TicketCreateResponse(
            ticket_id=result["ticket_id"],
            status=result["status"],
            ai_category=result.get("ai_category"),
            message=result["message"],
        ),
    ).model_dump()


@router.get("/tickets/{ticket_id}", response_model=APIResponse[dict])
async def get_ticket_detail_citizen(
    ticket_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    市民端工单详情：
    - 返回完整报修信息（含报修照片）+ 维修信息（维修员/耗材/工时/完工照片）
    - 返回 AI 验收结果
    - 返回全流程处理进度时间轴
    - 结算信息（仅已完结工单）
    """
    detail = await get_ticket_detail(db=db, ticket_id=ticket_id)
    if not detail:
        raise NotFoundException("工单不存在")
    return APIResponse(data=detail).model_dump()


@router.get("/tickets", response_model=APIResponse[dict])
async def list_my_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="状态筛选：pending/dispatching/accepting/repairing/verifying/closed/cancelled/needs_evaluation"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询当前用户的历史工单列表（分页）+统计数据"""
    from app.models.mysql.evaluation import Evaluation

    offset = (page - 1) * page_size

    # 判断筛选类型
    needs_evaluation = (status == "needs_evaluation")
    closed_with_evaluation = (status == "closed")

    # 构建查询和计数查询
    if needs_evaluation:
        # 待评价：已完结且未评价
        query = (
            select(Ticket)
            .outerjoin(Evaluation, Ticket.ticket_id == Evaluation.ticket_id)
            .where(
                Ticket.user_id == current_user["user_id"],
                Ticket.status == "closed",
                Evaluation.ticket_id == None
            )
        )
        count_query = (
            select(func.count())
            .select_from(Ticket)
            .outerjoin(Evaluation, Ticket.ticket_id == Evaluation.ticket_id)
            .where(
                Ticket.user_id == current_user["user_id"],
                Ticket.status == "closed",
                Evaluation.ticket_id == None
            )
        )
    elif closed_with_evaluation:
        # 已完结：已完结且已评价
        query = (
            select(Ticket)
            .join(Evaluation, Ticket.ticket_id == Evaluation.ticket_id)
            .where(
                Ticket.user_id == current_user["user_id"],
                Ticket.status == "closed"
            )
        )
        count_query = (
            select(func.count())
            .select_from(Ticket)
            .join(Evaluation, Ticket.ticket_id == Evaluation.ticket_id)
            .where(
                Ticket.user_id == current_user["user_id"],
                Ticket.status == "closed"
            )
        )
    else:
        # 其他状态正常筛选
        base_where = [Ticket.user_id == current_user["user_id"]]
        if status:
            base_where.append(Ticket.status == status)
        query = select(Ticket).where(*base_where)
        count_query = select(func.count()).select_from(Ticket).where(*base_where)

    # 总数
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # 已完结数（不受状态筛选影响）
    closed_count_result = await db.execute(
        select(func.count()).select_from(Ticket).where(
            Ticket.user_id == current_user["user_id"],
            Ticket.status == "closed"
        )
    )
    closed_count = closed_count_result.scalar() or 0

    # 处理中数（不受状态筛选影响）
    processing_count_result = await db.execute(
        select(func.count()).select_from(Ticket).where(
            Ticket.user_id == current_user["user_id"],
            Ticket.status.in_(["pending", "dispatching", "accepting", "repairing", "verifying"])
        )
    )
    processing_count = processing_count_result.scalar() or 0

    # 列表
    query = query.order_by(Ticket.created_at.desc()).limit(page_size).offset(offset)
    result = await db.execute(query)
    tickets = result.scalars().all()

    # 查询用户信息
    user_result = await db.execute(
        select(User).where(User.user_id == current_user["user_id"])
    )
    user = user_result.scalar_one_or_none()

    # 批量查询评价状态（避免 N+1）
    ticket_ids = [t.ticket_id for t in tickets]
    evaluated_ids: set = set()
    if ticket_ids:
        eval_result = await db.execute(
            select(Evaluation.ticket_id).where(Evaluation.ticket_id.in_(ticket_ids))
        )
        evaluated_ids = set(eval_result.scalars().all())

    return APIResponse(
        data={
            "total": total,
            "closed_count": closed_count,
            "processing_count": processing_count,
            "page": page,
            "page_size": page_size,
            "items": [{
                "ticket_id": t.ticket_id,
                "status": t.status,
                "description": t.description[:50] if t.description else "",
                "facility_type": t.facility_type,
                "ai_category": t.ai_category,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "has_evaluation": t.ticket_id in evaluated_ids,
            } for t in tickets],
            "user_info": {
                "user_id": current_user["user_id"],
                "name": (user.nickname or user.username or "") if user else "",
                "phone": user.phone if user else "",
            }
        }
    ).model_dump()


@router.put("/tickets/{ticket_id}/close", response_model=APIResponse)
async def close_ticket_citizen(
    ticket_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    市民确认完结工单：
    - 仅 verifying 状态可完结
    - 仅报修人本人可操作
    - 调用 citizen_confirm 服务：关闭工单 + 自动生成结算单
    """
    result = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise NotFoundException("工单不存在")

    if ticket.user_id != current_user["user_id"]:
        raise BadRequestException("仅报修人本人可确认完结")

    if ticket.status != "verifying":
        raise BadRequestException(f"当前状态「{ticket.status}」不可完结，仅验收中的工单可完结")

    # 调用服务层完成关闭 + 结算生成
    from app.services.worker.repair_service import citizen_confirm
    service_result = await citizen_confirm(
        ticket_id=ticket_id,
        user_id=current_user["user_id"],
        db=db,
    )

    if not service_result["success"]:
        raise BadRequestException(service_result["msg"])

    # 获取 closed_at 时间
    result = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = result.scalar_one_or_none()
    closed_at = ticket.closed_at.isoformat() if ticket and ticket.closed_at else None

    return APIResponse(msg="工单已完结", data={"closed_at": closed_at}).model_dump()


@router.put("/tickets/{ticket_id}/cancel", response_model=APIResponse)
async def cancel_ticket_citizen(
    ticket_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    市民撤销报修工单：
    - 仅 pending 或 accepting 状态可撤销
    - 仅报修人本人可操作
    - 从 MySQL 数据库直接删除工单
    - 清理 Redis、ES、MongoDB 相关数据
    """
    result = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise NotFoundException("工单不存在")

    if ticket.user_id != current_user["user_id"]:
        raise BadRequestException("仅报修人本人可撤销")

    if ticket.status not in ("pending", "accepting"):
        raise BadRequestException(f"当前工单状态为「{ticket.status}」，不可撤销")

    now = now_beijing()

    # 从数据库删除工单
    await db.delete(ticket)
    await db.commit()

    # 清理 Redis 缓存
    try:
        redis_cache = get_redis_cache()
        await redis_cache.delete(f"ticket:{ticket_id}:info")

        # 从接单大厅移除
        await redis_cache.zrem("tickets:accepting", ticket_id)
    except Exception as e:
        logger.warning(f"Redis 缓存清理失败 ticket={ticket_id}: {e}")

    # 从 ES 删除工单
    try:
        from app.config.elasticsearch_client import get_es_client
        from app.config.settings import settings
        es = get_es_client()
        if es:
            await es.delete(
                index=f"{settings.ES_INDEX_PREFIX}_tickets",
                id=ticket_id,
                ignore_status=[404]
            )
    except Exception as e:
        logger.warning(f"ES 删除工单失败 ticket={ticket_id}: {e}")

    # 清理 MongoDB 相关数据（可选，根据实际需求）
    try:
        mongo_db = get_mongo_db()
        # 删除 AI 分析日志
        await mongo_db.ai_analysis_log.delete_many({"ticket_id": ticket_id})
        # 删除维修记录
        await mongo_db.repair_records.delete_many({"ticket_id": ticket_id})
        # 删除工单附件
        await mongo_db.ticket_attachments.delete_many({"ticket_id": ticket_id})
        # 删除通知
        await mongo_db.notifications.delete_many({"ticket_id": ticket_id})
        # 删除审计日志
        await mongo_db.audit_log.delete_many({"target_id": ticket_id, "target_type": "ticket"})
    except Exception as e:
        logger.warning(f"MongoDB 数据清理失败 ticket={ticket_id}: {e}")

    return APIResponse(msg="工单已销毁", data={"destroyed_at": now.isoformat()}).model_dump()
