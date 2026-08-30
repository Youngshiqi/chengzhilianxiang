# ============================================================
# 鍩庡競鍏叡璁炬柦鏅鸿兘鎶ヤ慨涓庢淳鍗曠郴缁?- 绠＄悊鍚庡彴宸ュ崟绠＄悊 API
# 浣滅敤锛欸ET /api/v1/admin/tickets/search 鈥?宸ュ崟鍏ㄦ枃妫€绱紙ES IK涓枃鍒嗚瘝锛夛紱
#       POST /api/v1/admin/tickets/{id}/dispatch 鈥?浜哄伐寮哄埗鎸囨淳锛圧edis閿侀噴鏀?MongoDB瀹¤锛?# ============================================================

import datetime
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config.mysql import get_db
from app.config.redis_client import get_redis_lock, get_redis_cache
from app.config.mongodb import get_mongo_db
from app.models.mysql.ticket import Ticket
from app.models.mysql.worker import Worker
from app.schemas.admin import TicketSearchRequest, ForceDispatchRequest
from app.schemas.common import APIResponse
from app.core.security import get_current_user
from app.core.exceptions import NotFoundException
from app.services.ticket_detail_service import get_ticket_detail
from app.utils.timezone import now_beijing

logger = logging.getLogger(__name__)
router = APIRouter()


async def _resolve_worker_names(db, items: list) -> list:
    """为工单列表补充维修员真实姓名"""
    worker_ids = [it["assigned_worker_id"] for it in items if it.get("assigned_worker_id")]
    if not worker_ids:
        for it in items:
            it["worker_name"] = ""
        return items
    result = await db.execute(select(Worker.worker_id, Worker.name).where(Worker.worker_id.in_(worker_ids)))
    id_to_name = {row.worker_id: row.name for row in result.all()}
    for it in items:
        it["worker_name"] = id_to_name.get(it.get("assigned_worker_id"), "")
    return items


@router.get("/tickets/search", response_model=APIResponse[dict])
async def search_tickets(
    keyword: str = "",
    status: str = "",
    facility_type: str = "",
    district: str = "",
    date_from: str = "",
    date_to: str = "",
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """
    宸ュ崟鍏ㄦ枃妫€绱紙ES 浼樺厛 + MySQL 闄嶇骇锛夛細
    - 鏀寔鍏抽敭璇嶃€佺姸鎬併€佽鏂藉搧绫汇€佽鏀垮尯銆佸垱寤烘椂闂磋寖鍥村缁村害绛涢€?    - ES 杩斿洖缁撴灉浼氫笌 MySQL 浜ゅ弶鏍￠獙锛岃繃婊ゅ兊灏告暟鎹?    """
    from sqlalchemy import func, or_
    from app.config.mysql import async_session_factory
    from app.config.elasticsearch_client import get_es_client
    from app.config.settings import settings

    # ES 浼樺厛鎼滅储
    es = get_es_client()
    if es:
        try:
            es_query = {
                "from": (page - 1) * page_size,
                "size": page_size,
                "sort": [{"ticket_id": {"order": "desc"}}],
                "query": {"bool": {"must": [], "filter": []}},
            }
            if keyword:
                es_query["query"]["bool"]["must"].append({
                    "multi_match": {"query": keyword, "fields": ["description", "address"]}
                })
            else:
                es_query["query"] = {"bool": {"filter": []}}
            if status:
                es_query["query"]["bool"]["filter"].append({"term": {"status": status}})
            if facility_type:
                es_query["query"]["bool"]["filter"].append({"term": {"facility_type": facility_type}})
            if district:
                es_query["query"]["bool"]["filter"].append({"term": {"district": district}})
            if date_from or date_to:
                range_filter = {"created_at": {}}
                if date_from:
                    range_filter["created_at"]["gte"] = date_from
                if date_to:
                    range_filter["created_at"]["lte"] = f"{date_to}T23:59:59"
                es_query["query"]["bool"]["filter"].append({"range": range_filter})

            es_result = await es.search(
                index=f"{settings.ES_INDEX_PREFIX}_tickets",
                body=es_query,
            )
            hits = es_result["hits"]["hits"]
            es_total = es_result["hits"]["total"]["value"]
            es_ticket_ids = [h["_source"]["ticket_id"] for h in hits]

            # 涓?MySQL 浜ゅ弶鏍￠獙锛氳繃婊?ES 涓瓨鍦ㄤ絾 MySQL 宸插垹闄ょ殑鍍靛案宸ュ崟
            if es_ticket_ids:
                async with async_session_factory() as db:
                    mysql_result = await db.execute(
                        select(Ticket).where(Ticket.ticket_id.in_(es_ticket_ids))
                    )
                    mysql_tickets = {t.ticket_id: t for t in mysql_result.scalars().all()}

                # 鍙繚鐣?MySQL 涓瓨鍦ㄧ殑宸ュ崟
                items = []
                for h in hits:
                    tid = h["_source"]["ticket_id"]
                    if tid not in mysql_tickets:
                        logger.warning("ES 鍍靛案宸ュ崟宸茶繃婊? %s", tid)
                        continue
                    t = mysql_tickets[tid]
                    items.append({
                        "ticket_id": t.ticket_id,
                        "user_id": t.user_id,
                        "facility_type": t.facility_type,
                        "status": t.status,
                        "description": t.description,
                        "address": t.address,
                        "district": t.district,
                        "location_lng": t.location_lng,
                        "location_lat": t.location_lat,
                        "emergency_level": t.emergency_level,
                        "assigned_worker_id": t.assigned_worker_id,
                        "ai_category": t.ai_category,
                        "created_at": t.created_at.isoformat() if t.created_at else None,
                        "closed_at": t.closed_at.isoformat() if t.closed_at else None,
                    })

                # total 浠?MySQL 閲嶆柊璁＄畻锛堥伩鍏?ES 鍍靛案鏁版嵁铏氬璁℃暟锛?                count_query = select(func.count(Ticket.ticket_id))
                count_conditions = []
                if status:
                    count_conditions.append(Ticket.status == status)
                if facility_type:
                    count_conditions.append(Ticket.facility_type == facility_type)
                if district:
                    count_conditions.append(Ticket.district == district)
                if date_from:
                    try:
                        count_conditions.append(Ticket.created_at >= datetime.datetime.fromisoformat(date_from))
                    except ValueError:
                        pass
                if date_to:
                    try:
                        dt_end = datetime.datetime.fromisoformat(date_to) + datetime.timedelta(days=1)
                        count_conditions.append(Ticket.created_at < dt_end)
                    except ValueError:
                        pass
                if count_conditions:
                    count_query = count_query.where(*count_conditions)
                count_result = await db.execute(count_query)
                total = count_result.scalar() or 0
            else:
                items = []
                total = 0

            # 补充维修员姓名
            items = await _resolve_worker_names(db, items)
            return APIResponse(data={"items": items, "total": total}).model_dump()
        except Exception as e:
            logger.warning("ES 搜索失败，降级到 MySQL: %s", e)

    # MySQL 闄嶇骇鏌ヨ
    async with async_session_factory() as db:
        base_query = select(Ticket)
        count_query = select(func.count(Ticket.ticket_id))

        conditions = []
        if keyword:
            conditions.append(or_(
                Ticket.description.like(f"%{keyword}%"),
                Ticket.address.like(f"%{keyword}%"),
                Ticket.ticket_id.like(f"%{keyword}%"),
            ))
        if status:
            conditions.append(Ticket.status == status)
        if facility_type:
            conditions.append(Ticket.facility_type == facility_type)
        if district:
            conditions.append(Ticket.district == district)
        if date_from:
            try:
                dt_from = datetime.datetime.fromisoformat(date_from)
                conditions.append(Ticket.created_at >= dt_from)
            except ValueError:
                pass
        if date_to:
            try:
                dt_to = datetime.datetime.fromisoformat(date_to)
                # 鍖呭惈褰撴棩鍏ㄥぉ锛?1澶?- 1绉?                dt_to = dt_to + datetime.timedelta(days=1) - datetime.timedelta(seconds=1)
                conditions.append(Ticket.created_at <= dt_to)
            except ValueError:
                pass

        if conditions:
            base_query = base_query.where(*conditions)
            count_query = count_query.where(*conditions)

        # 鎬绘暟
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # 鍒嗛〉
        base_query = base_query.order_by(Ticket.ticket_id.desc())
        base_query = base_query.limit(page_size).offset((page - 1) * page_size)
        result = await db.execute(base_query)
        tickets = result.scalars().all()

        items = [{
            "ticket_id": t.ticket_id,
            "user_id": t.user_id,
            "facility_type": t.facility_type,
            "status": t.status,
            "description": t.description,
            "address": t.address,
            "district": t.district,
            "location_lng": t.location_lng,
            "location_lat": t.location_lat,
            "emergency_level": t.emergency_level,
            "assigned_worker_id": t.assigned_worker_id,
            "ai_category": t.ai_category,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "closed_at": t.closed_at.isoformat() if t.closed_at else None,
        } for t in tickets]

        # 补充维修员姓名
        items = await _resolve_worker_names(db, items)

    return APIResponse(data={"items": items, "total": total}).model_dump()


@router.get("/tickets/{ticket_id}", response_model=APIResponse[dict])
async def get_ticket_detail_admin(
    ticket_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    绠＄悊鍚庡彴宸ュ崟璇︽儏锛?    - 杩斿洖瀹屾暣鎶ヤ慨淇℃伅锛堟姤淇汉/鏃堕棿/鍦扮偣/鎻忚堪/鍥剧墖锛?    - 杩斿洖缁翠慨淇℃伅锛堢淮淇憳/鑰楁潗/宸ユ椂/瀹屽伐鐓х墖/AI楠屾敹锛?    - 杩斿洖鍏ㄦ祦绋嬪鐞嗚繘搴︽椂闂磋酱
    """
    detail = await get_ticket_detail(db=db, ticket_id=ticket_id)
    if not detail:
        raise NotFoundException("工单不存在")
    return APIResponse(data=detail).model_dump()


@router.post("/tickets/{ticket_id}/dispatch", response_model=APIResponse)
async def force_dispatch(
    ticket_id: str,
    req: ForceDispatchRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    mongo_db=Depends(get_mongo_db),
):
    """
    浜哄伐寮哄埗鎸囨淳宸ュ崟锛?    - Redis 寮哄埗閲婃斁鍘熷垎甯冨紡閿?    - MySQL 鏇存柊 assigned_worker_id
    - MongoDB audit_logs 记录强制指派操作（不可篡改）
    """
    redis_lock = get_redis_lock()
    redis_cache = get_redis_cache()

    # 释放原锁 + 设置新锁
    await redis_lock.delete(f"lock:ticket:{ticket_id}")
    await redis_lock.set(f"lock:ticket:{ticket_id}", req.worker_id, ex=300)

    # 鏇存柊 MySQL
    result = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("工单不存在")

    # Only tickets still waiting in the dispatch pool can be assigned manually.
    if ticket.status != "accepting":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"当前工单状态为「{ticket.status}」，仅派单中的工单可指派")

    old_worker = ticket.assigned_worker_id
    ticket.assigned_worker_id = req.worker_id
    ticket.status = "dispatching"
    await db.commit()

    # MongoDB 审计日志（容错，不影响主流程）
    try:
        await mongo_db.audit_logs.insert_one({
            "operator_id": current_user["user_id"],
            "role": "admin",
            "action": "force_dispatch",
            "target": {"type": "ticket", "id": ticket_id},
            "old_value": {"assigned_worker_id": old_worker},
            "new_value": {"assigned_worker_id": req.worker_id},
            "ip": "",
            "ua": "",
            "created_at": now_beijing(),
        })
    except Exception as e:
        logger.warning("审计日志写入失败（不影响指派）: %s", e)

    # Redis 缓存同步
    await redis_cache.hset(f"ticket:{ticket_id}:info", "assigned_worker_id", req.worker_id)

    # ES 同步 via RabbitMQ
    try:
        from app.services.mq.rabbitmq_service import publish_es_sync
        await publish_es_sync(ticket_id)
    except Exception as e:
        logger.warning(f"ES sync 消息发布失败: {e}")

    return APIResponse(msg="强制指派成功").model_dump()

