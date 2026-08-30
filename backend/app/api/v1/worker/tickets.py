# ============================================================
# 城市公共设施智能报修与派单系统 - 维修员端工单 API
# 作用：GET /api/v1/worker/tickets/queue — 实时工单接单大厅；
#       PUT /api/v1/worker/tickets/{id}/accept — 接单确认（释放Redis锁+更新MySQL）；
#       PUT /api/v1/worker/tickets/{id}/checkin — 到场签到（MongoDB存GPS坐标）；
#       PUT /api/v1/worker/tickets/{id}/complete — 完工提交（MongoDB维修记录+Dify AI验收）
# ============================================================

import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.config.mysql import get_db
from app.config.redis_client import get_redis_lock, get_redis_cache, get_redis_counter
from app.models.mysql.ticket import Ticket
from app.schemas.worker import (
    TicketAcceptRequest, CheckinRequest, CompletionRequest,
    LocationUpdateRequest, TicketQueueResponse,
)
from app.schemas.common import APIResponse, PaginationResponse
from app.core.security import get_current_user
from app.core.exceptions import NotFoundException, BadRequestException
from app.services.worker.repair_service import worker_checkin, worker_complete
from app.services.ticket_detail_service import get_ticket_detail
from app.utils.timezone import now_beijing

router = APIRouter()


@router.get("/tickets/queue", response_model=APIResponse[list[TicketQueueResponse]])
async def get_ticket_queue(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    维修员工单接单大厅：
    - 查询 accepting 状态工单（可抢单）
    - 按距离排序（Redis Geo实时计算）
    """
    from app.config.redis_client import get_redis_geo

    result = await db.execute(
        select(Ticket)
        .where(Ticket.status == "accepting")
        .order_by(Ticket.created_at.desc())
        .limit(30)
    )
    tickets = result.scalars().all()

    # 获取当前维修员位置
    worker_id = current_user["user_id"]
    worker_lng, worker_lat = None, None
    try:
        redis_geo = get_redis_geo()
        if redis_geo:
            pos = await redis_geo.geopos("workers:geo", worker_id)
            if pos and pos[0]:
                worker_lng, worker_lat = pos[0]
    except Exception:
        pass

    # 批量计算工单距离
    items = []
    for t in tickets:
        distance = 0.0
        if worker_lng is not None and worker_lat is not None:
            try:
                distance = await _calc_distance_km(
                    redis_geo, worker_lng, worker_lat,
                    t.location_lng, t.location_lat,
                ) * 1000  # 转为米
            except Exception:
                pass

        items.append(TicketQueueResponse(
            ticket_id=t.ticket_id,
            facility_type=t.facility_type,
            description=t.description[:100] if t.description else "",
            address=t.address or "",
            distance_meters=round(distance, 1),
            emergency_level=t.emergency_level or 0,
            status=t.status,
            assigned_worker_id=t.assigned_worker_id,
            ai_category=t.ai_category,
            created_at=t.created_at.isoformat() if t.created_at else "",
        ).model_dump())

    # 按紧急程度降序，再按距离升序排列
    items.sort(key=lambda x: (-x.get("emergency_level", 0), x.get("distance_meters", 0)))

    return APIResponse(data=items).model_dump()


@router.put("/tickets/{ticket_id}/accept", response_model=APIResponse)
async def accept_ticket(
    ticket_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    维修员接单确认：
    - 尝试获取 Redis 分布式锁 lock:ticket:{tid}（防并发双派）
    - 更新 MySQL tickets.assigned_worker_id + status → repairing
    - Redis 清理锁 + 更新状态缓存 + worker 当日计数+1
    """
    redis_lock = get_redis_lock()
    redis_cache = get_redis_cache()
    redis_counter = get_redis_counter()
    worker_id = current_user["user_id"]
    lock_key = f"lock:ticket:{ticket_id}"

    # 原子化获取分布式锁（300秒过期）
    acquired = await redis_lock.set(lock_key, worker_id, nx=True, ex=300)
    if not acquired:
        # 检查锁持有者
        existing = await redis_lock.get(lock_key)
        holder = existing.decode() if isinstance(existing, bytes) else (existing or "")
        if holder == worker_id:
            # 同一维修员重试 → 幂等返回成功（不再重复更新 MySQL）
            return APIResponse(msg="接单成功（已确认）").model_dump()
        raise BadRequestException("该工单已被其他维修员接单")

    # 更新 MySQL（锁已获取，原子执行）
    try:
        result = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise NotFoundException("工单不存在")

        if ticket.status not in ("pending", "accepting"):
            raise BadRequestException(f"工单状态 {ticket.status} 不允许接单")

        now = now_beijing()
        # 数据库级原子更新：仅当工单仍处于可接单状态时才指派，
        # 防止 Redis 锁 TTL 过期等极端场景下的并发双接（真正的乐观锁兜底）
        update_result = await db.execute(
            update(Ticket)
            .where(
                Ticket.ticket_id == ticket_id,
                Ticket.status.in_(("pending", "accepting")),
            )
            .values(
                assigned_worker_id=worker_id,
                status="repairing",
                accepted_at=now,
            )
        )
        await db.commit()

        # 受影响行数为 0 → 工单已被其他维修员抢先接走
        if update_result.rowcount == 0:
            raise BadRequestException("该工单已被其他维修员接单")

        # 更新 Redis 状态缓存
        await redis_cache.hset(f"ticket:{ticket_id}:info", mapping={
            "status": "repairing",
            "assigned_worker_id": worker_id,
            "accepted_at": now.isoformat(),
        })

        # 从接单大厅移除
        await redis_cache.zrem("tickets:accepting", ticket_id)

        # 维修员当日接单计数 +1
        await redis_counter.incr(f"worker:{worker_id}:daily_order")

        # ES 同步 via RabbitMQ
        try:
            from app.services.mq.rabbitmq_service import publish_es_sync
            await publish_es_sync(ticket_id)
        except Exception as e:
            logger.warning(f"ES sync 消息发布失败: {e}")

        return APIResponse(msg="接单成功").model_dump()

    finally:
        # 无论成功/失败都释放锁（成功时锁已完成使命，失败时不阻塞其他请求）
        await redis_lock.delete(lock_key)


@router.put("/tickets/{ticket_id}/checkin", response_model=APIResponse)
async def checkin_ticket(
    ticket_id: str,
    req: CheckinRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    维修员到场签到：
    - MongoDB repair_records 存 GPS 签到坐标
    - MySQL tickets 更新 started_at
    - Redis 更新维修员当前工单状态
    """
    result = await worker_checkin(
        ticket_id=ticket_id,
        worker_id=current_user["user_id"],
        lng=req.lng,
        lat=req.lat,
        db=db,
    )

    if not result["success"]:
        raise BadRequestException(result["msg"])

    return APIResponse(msg=result["msg"], data={"checkin_time": result.get("checkin_time")}).model_dump()


@router.put("/location", response_model=APIResponse)
async def update_location(
    req: LocationUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    维修员实时位置上报：
    - 更新 Redis Geo workers:geo 集合中的坐标
    - 用于派单半径筛选和距离计算
    """
    from app.config.redis_client import get_redis_geo

    redis_geo = get_redis_geo()
    await redis_geo.geoadd("workers:geo", (req.lng, req.lat, current_user["user_id"]))

    return APIResponse(msg="位置已更新", data={"lng": req.lng, "lat": req.lat}).model_dump()


@router.put("/tickets/{ticket_id}/complete", response_model=APIResponse)
async def complete_ticket(
    ticket_id: str,
    req: CompletionRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    维修员完工提交：
    1. MongoDB repair_records 存耗材+工时+完工照片
    2. 验收比对（异步容错，失败默认通过）
    3. AI验收通过 → MySQL 状态 → verifying
    4. Redis 缓存同步 + Geo 释放维修员
    """
    result = await worker_complete(
        ticket_id=ticket_id,
        worker_id=current_user["user_id"],
        materials=req.materials,
        labor_hours=req.labor_hours,
        work_notes=req.work_notes or "",
        completion_photo_urls=req.completion_photo_urls,
        db=db,
    )

    if not result["success"]:
        raise BadRequestException(result["msg"])

    return APIResponse(
        msg=result["msg"],
        data={
            "ai_verified": result.get("ai_verified"),
            "ai_confidence": result.get("ai_confidence"),
        },
    ).model_dump()


@router.get("/tickets", response_model=APIResponse[PaginationResponse])
async def list_my_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    维修员我的工单列表：
    - 查询 assigned_worker_id 为当前维修员的工单
    - 按创建时间倒序，分页返回
    """
    worker_id = current_user["user_id"]
    offset = (page - 1) * page_size

    count_result = await db.execute(
        select(func.count()).select_from(Ticket).where(
            Ticket.assigned_worker_id == worker_id
        )
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Ticket)
        .where(Ticket.assigned_worker_id == worker_id)
        .order_by(Ticket.accepted_at.desc(), Ticket.created_at.desc())
        .limit(page_size)
        .offset(offset)
    )
    tickets = result.scalars().all()

    return APIResponse(
        data=PaginationResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=[{
                "ticket_id": t.ticket_id,
                "status": t.status,
                "description": t.description[:80] if t.description else "",
                "facility_type": t.facility_type,
                "address": t.address or "",
                "emergency_level": t.emergency_level or 0,
                "ai_category": t.ai_category,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "accepted_at": t.accepted_at.isoformat() if t.accepted_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            } for t in tickets],
        ),
    ).model_dump()


@router.get("/tickets/{ticket_id}", response_model=APIResponse[dict])
async def get_ticket_detail_worker(
    ticket_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    维修员工单详情：
    - 返回完整报修信息（含报修照片）+ 维修信息（耗材/工时/完工照片）+ AI验收结果
    - 返回全流程处理进度时间轴
    - 不校验 assigned_worker_id（维修员可查看待接工单）
    """
    detail = await get_ticket_detail(db=db, ticket_id=ticket_id)
    if not detail:
        raise NotFoundException("工单不存在")
    return APIResponse(data=detail).model_dump()


async def _calc_distance_km(redis_geo, lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    """使用 Redis GEODIST 计算两点间距离（公里），失败时降级为 Haversine 近似"""
    import math

    try:
        # 临时存入再计算距离
        tmp_key = f"tmp:geodist:{lng1}:{lat1}"
        await redis_geo.geoadd(tmp_key, (lng1, lat1, "p1"))
        await redis_geo.geoadd(tmp_key, (lng2, lat2, "p2"))
        dist = await redis_geo.geodist(tmp_key, "p1", "p2", unit="km")
        await redis_geo.delete(tmp_key)
        return float(dist) if dist else _haversine_km(lng1, lat1, lng2, lat2)
    except Exception:
        return _haversine_km(lng1, lat1, lng2, lat2)


def _haversine_km(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    """Haversine 公式近似距离（公里）"""
    import math
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
