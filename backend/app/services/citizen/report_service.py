# ============================================================
# 城市公共设施智能报修与派单系统 - 市民报修业务服务
# 作用：编排报修流程的四库数据写入序列：
#       1. Dify NLP 解析（异步，不阻塞主流程）
#       2. MySQL tickets 主表落地（返回工单ID和受理回执）
#       3. MongoDB ai_analysis_logs 存AI解析结果
#       4. MongoDB ticket_attachments 存图片元数据
#       5. Redis ticket:{tid}:info 缓存工单热状态
#       6. ES tickets_index 同步（最终一致性，异步）
#       7. RabbitMQ dispatch 队列入队（触发异步派单）
# 设计原则：MySQL 写为唯一同步阻断点，其余操作全异步/容错
# ============================================================

import asyncio
import datetime
import hashlib
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config.redis_client import get_redis_cache
from app.config.mongodb import get_mongo_db
from app.models.mysql.ticket import Ticket
from app.services.ai.nlp_service import analyze_repair_request
from app.services.mq.rabbitmq_service import publish_dispatch_task, publish_timeout_check
from app.utils.id_generator import generate_id
from app.utils.timezone import now_beijing
from app.services.map.amap_service import reverse_geocode

logger = logging.getLogger(__name__)

# 防重复提交配置
DUPLICATE_CHECK_WINDOW_SECONDS = 300  # 5分钟内的重复提交将被拦截


def _generate_duplicate_check_key(
    user_id: str,
    description: str,
    location_lng: float,
    location_lat: float,
) -> str:
    """生成防重复提交的哈希键"""
    # 对位置进行精度截取（保留5位小数，约1米精度），避免轻微移动导致无法匹配
    lng_key = f"{location_lng:.5f}"
    lat_key = f"{location_lat:.5f}"

    # 组合关键信息生成哈希
    content = f"{user_id}:{description}:{lng_key}:{lat_key}"
    hash_obj = hashlib.md5(content.encode("utf-8"))
    return f"duplicate:report:{hash_obj.hexdigest()}"


async def submit_repair_report(
    db: AsyncSession,
    user_id: str,
    description: str,
    facility_type: Optional[str],
    location_lng: float,
    location_lat: float,
    address: Optional[str],
    image_urls: List[str],
    emergency_level: int = 0,
) -> Dict[str, Any]:
    """
    市民报修主流程编排。

    同步阶段（必须成功）：
      0. 防重复提交检查
      1. 生成唯一工单ID
      2. 写入 MySQL tickets 表
      3. 写入 Redis 热状态缓存

    异步阶段（容错，不影响主流程）：
      4. NLP 解析（不阻塞，解析结果异步回写MySQL ai_category）
      5. MongoDB 存AI日志 + 图片元数据
      6. ES 索引同步
      7. RabbitMQ 派单消息入队

    返回: {ticket_id, status, ai_category, message, is_duplicate}
    """
    redis_cache = get_redis_cache()
    mongo_db = get_mongo_db()

    # ---- 阶段0：防重复提交检查 ----
    duplicate_key = _generate_duplicate_check_key(
        user_id=user_id,
        description=description,
        location_lng=location_lng,
        location_lat=location_lat,
    )

    # 检查是否存在重复提交记录
    existing_ticket_id = await redis_cache.get(duplicate_key)
    if existing_ticket_id:
        # 存在重复提交，返回已有工单信息
        existing_ticket_id_str = existing_ticket_id.decode() if isinstance(existing_ticket_id, bytes) else existing_ticket_id

        # 尝试获取已有工单的状态
        existing_ticket = None
        try:
            result = await db.execute(select(Ticket).where(Ticket.ticket_id == existing_ticket_id_str))
            existing_ticket = result.scalar_one_or_none()
        except Exception as e:
            logger.warning(f"查询重复工单失败: {e}")

        logger.info(f"拦截到重复提交: user={user_id}, existing_ticket={existing_ticket_id_str}")

        return {
            "ticket_id": existing_ticket_id_str,
            "status": existing_ticket.status if existing_ticket else "pending",
            "ai_category": existing_ticket.ai_category if existing_ticket else "",
            "message": "您刚才已提交过类似报修，请不要重复提交",
            "is_duplicate": True,
        }

    # ---- 第一阶段：同步落地 ----

    # 1. 生成工单ID
    from app.config.redis_client import get_redis_counter
    ticket_id = await generate_id(get_redis_counter(), "TK")

    # 1.5. 逆地理编码：GPS坐标 → 可读地址 + 行政区（容错，不阻塞主流程）
    resolved_address = address or ""
    resolved_district = ""
    try:
        rgc = await reverse_geocode(location_lng, location_lat)
        if rgc:
            resolved_address = rgc.get("formatted_address") or address or f"{location_lng:.6f}, {location_lat:.6f}"
            resolved_district = rgc.get("district", "")
            logger.info(f"工单 {ticket_id} 逆地理编码成功: district={resolved_district}")
        else:
            # 降级：用旧方法从地址字符串推断
            resolved_district = _infer_district(address, location_lng, location_lat)
    except Exception as e:
        logger.warning(f"工单 {ticket_id} 逆地理编码失败，降级字符串推断: {e}")
        resolved_district = _infer_district(address, location_lng, location_lat)

    # 2. 写入 MySQL（事务保障，唯一同步阻断点）
    now = now_beijing()
    ticket = Ticket(
        ticket_id=ticket_id,
        user_id=user_id,
        facility_type=facility_type or "other",
        facility_code="",  # NLP解析后回填
        description=description,
        address=resolved_address,
        location_lng=location_lng,
        location_lat=location_lat,
        district=resolved_district,
        emergency_level=emergency_level,
        status="accepting",  # 进入接单大厅
        created_at=now,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)

    # 2.5. 设置防重复提交锁（成功写入数据库后再设置，避免误拦截）
    await redis_cache.setex(duplicate_key, DUPLICATE_CHECK_WINDOW_SECONDS, ticket_id)

    # 3. Redis 缓存工单热状态
    await redis_cache.hset(
        f"ticket:{ticket_id}:info",
        mapping={
            "status": "accepting",
            "user_id": user_id,
            "description": description[:200],
            "facility_type": facility_type or "other",
            "district": resolved_district,
            "address": resolved_address,
            "emergency_level": str(emergency_level),
            "created_at": now.isoformat(),
            "assigned_worker_id": "",
            "ai_category": "",
        },
    )
    await redis_cache.expire(f"ticket:{ticket_id}:info", 86400 * 14)  # 14天TTL

    # 将工单加入接单大厅列表（按时间排序）
    await redis_cache.zadd("tickets:accepting", {ticket_id: now.timestamp()})
    await redis_cache.expire("tickets:accepting", 86400 * 7)

    # ---- 第二阶段：异步增强（容错，单个失败不影响主流程） ----

    # 4. NLP 解析（异步触发，不阻塞）
    ai_category = None
    ai_sub_category = None
    ai_confidence = 0.0
    ai_emergency_level = emergency_level
    nlp_result: Dict[str, Any] = {}
    try:
        nlp_result = await analyze_repair_request(
            text=description,
            image_urls=image_urls,
            lng=location_lng,
            lat=location_lat,
        )
        ai_category = nlp_result.get("category", "其他设施")
        ai_sub_category = nlp_result.get("sub_category", "")
        ai_confidence = nlp_result.get("confidence", 0.5)
        ai_emergency_level = nlp_result.get("emergency_level", emergency_level)
        district = nlp_result.get("district", "") or resolved_district

        # 回写 MySQL ai_category + district；不新增字段，扩展 AI 结果存 MongoDB
        ticket.ai_category = ai_category
        ticket.ai_confidence = ai_confidence
        ticket.district = district
        ticket.emergency_level = ai_emergency_level
        if not facility_type or facility_type == "other":
            ticket.facility_type = ai_category
        await db.commit()

        # 更新 Redis
        await redis_cache.hset(f"ticket:{ticket_id}:info", mapping={
            "ai_category": ai_category,
            "district": district,
            "emergency_level": str(ai_emergency_level),
        })
    except Exception as e:
        logger.warning(f"NLP解析失败（使用默认值）: {e}")
        ai_category = "其他设施"

    # 5. MongoDB 异步写入 AI 分析日志
    try:
        await mongo_db.ai_analysis_logs.insert_one({
            "ticket_id": ticket_id,
            "workflow": "nlp_parse",
            "input": {
                "text": description,
                "image_urls": image_urls,
                "lng": location_lng,
                "lat": location_lat,
            },
            "output": {
                **(nlp_result if isinstance(nlp_result, dict) else {}),
                "category": ai_category,
                "sub_category": ai_sub_category,
                "confidence": ai_confidence,
                "emergency_level": ai_emergency_level,
            },
            "created_at": now,
        })
    except Exception as e:
        logger.warning(f"MongoDB AI日志写入失败: {e}")

    # 6. MongoDB 存图片元数据（带重试，最多3次）
    if image_urls:
        last_error = None
        for attempt in range(3):
            try:
                await mongo_db.ticket_attachments.insert_one({
                    "ticket_id": ticket_id,
                    "stage": "report",
                    "image_urls": image_urls,
                    "ai_ocr_result": None,
                    "created_at": now,
                })
                break
            except Exception as e:
                last_error = e
                if attempt < 2:
                    await asyncio.sleep(0.5 * (attempt + 1))
        else:
            logger.error(
                f"MongoDB 图片元数据写入失败（重试3次后放弃） ticket={ticket_id} error={last_error}"
            )

    # 7. ES 同步 via RabbitMQ（可靠异步投递，消费者全量加载 MySQL → ES）
    try:
        from app.services.mq.rabbitmq_service import publish_es_sync
        await publish_es_sync(ticket_id)
    except Exception as e:
        logger.warning(f"ES sync 消息发布失败（工单已受理，ES 将在下次全量同步时补回）: {e}")

    # 8. RabbitMQ 超时检查消息入队（10分钟后检查是否已接单，未接单则自动派单）
    try:
        logger.info(f"========== 开始发布工单 {ticket_id} 的超时检查消息 ==========")
        await publish_timeout_check(ticket_id, delay_minutes=10)
    except Exception as e:
        logger.error(f"RabbitMQ 超时检查入队失败: {e}")

    return {
        "ticket_id": ticket_id,
        "status": "accepting",
        "ai_category": ai_category,
        "message": f"您的工单已受理",
        "is_duplicate": False,
    }


async def get_ticket_progress(
    db: AsyncSession,
    ticket_id: str,
    user_id: str,
) -> Optional[Dict[str, Any]]:
    """
    查询工单实时进度。

    数据源优先级：
      1. Redis ticket:{tid}:info 热缓存（毫秒级）
      2. MySQL tickets 主表（缓存未命中降级）
      3. MongoDB repair_records（维修详情）
    """
    redis_cache = get_redis_cache()

    # 1. Redis 热缓存
    cached = await redis_cache.hgetall(f"ticket:{ticket_id}:info")
    if cached and cached.get("status"):
        timeline = await _build_timeline(ticket_id)
        return {
            "ticket_id": ticket_id,
            "status": cached.get("status", "unknown"),
            "description": cached.get("description", ""),
            "facility_type": cached.get("facility_type", ""),
            "ai_category": cached.get("ai_category", ""),
            "assigned_worker_id": cached.get("assigned_worker_id", ""),
            "created_at": cached.get("created_at", ""),
            "timeline": timeline,
        }

    # 2. MySQL 降级查询
    result = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        return None

    # 回填 Redis
    await redis_cache.hset(
        f"ticket:{ticket_id}:info",
        mapping={
            "status": ticket.status,
            "user_id": ticket.user_id,
            "description": ticket.description[:200],
            "facility_type": ticket.facility_type,
            "district": ticket.district or "",
            "ai_category": ticket.ai_category or "",
            "assigned_worker_id": ticket.assigned_worker_id or "",
            "created_at": ticket.created_at.isoformat() if ticket.created_at else "",
        },
    )
    await redis_cache.expire(f"ticket:{ticket_id}:info", 86400 * 14)

    return {
        "ticket_id": ticket.ticket_id,
        "status": ticket.status,
        "description": ticket.description,
        "facility_type": ticket.facility_type,
        "ai_category": ticket.ai_category,
        "assigned_worker_id": ticket.assigned_worker_id,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "timeline": await _build_timeline(ticket_id),
    }


async def _build_timeline(ticket_id: str) -> List[Dict[str, Any]]:
    """从 MongoDB repair_records 构建工单全流程时间轴"""
    try:
        mongo_db = get_mongo_db()
        doc = await mongo_db.repair_records.find_one({"ticket_id": ticket_id})
        if not doc:
            return []
        timeline = []
        events = {
            "gps_checkin": ("维修员到场签到", doc.get("gps_checkin_at")),
            "repair_completed": ("维修完工", doc.get("completed_at")),
            "ai_verified": ("AI验收通过", doc.get("verified_at")),
        }
        for event_name, (label, timestamp) in events.items():
            if timestamp:
                timeline.append({
                    "event": event_name,
                    "label": label,
                    "time": timestamp.isoformat() if isinstance(timestamp, datetime.datetime) else str(timestamp),
                })
        return timeline
    except Exception as e:
        logger.warning(f"构建时间轴失败 ticket={ticket_id}: {e}")
        return []


def _infer_district(address: Optional[str], lng: float, lat: float) -> str:
    """从地址字符串推断行政区（简易实现，生产环境应调用地图API反查）"""
    if address:
        for district in ["芙蓉区", "天心区", "岳麓区", "开福区", "雨花区",
                          "望城区", "长沙县", "浏阳市", "宁乡市"]:
            if district in address:
                return district
    return ""
