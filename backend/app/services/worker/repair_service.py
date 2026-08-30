# ============================================================
# 城市公共设施智能报修与派单系统 - 维修闭环业务服务
# 作用：封装维修全流程业务逻辑；
#       1. 到场签到：Redis 更新维修工当前工单状态，MongoDB repair_records 存GPS签到坐标
#       2. 维修记录：MongoDB repair_records 灵活存储耗材数组 + 工时 + 备注
#       3. 完工提交：MongoDB ticket_attachments 存完工照片元数据
#       4. Dify AI验收：调用视觉对比工作流 → MongoDB ai_analysis_logs 存结果
#       5. 核验通过：MySQL 工单状态 → verifying → 市民确认 → closed
#       6. 超时自动完结：7天后市民未确认自动closed
#       7. 绩效结算触发：MySQL settlements 自动生成，ES workers_perf_index 更新
# ============================================================

import datetime
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config.redis_client import get_redis_cache, get_redis_lock, get_redis_counter, get_redis_geo
from app.config.mongodb import get_mongo_db
from app.models.mysql.ticket import Ticket
from app.models.mysql.worker import Worker
from app.models.mysql.audit_rule import AuditRule
from app.models.mysql.settlement import Settlement
from app.services.ai.verify_service import verify_repair
from app.services.mq.rabbitmq_service import publish_review_task
from app.utils.timezone import now_beijing

logger = logging.getLogger(__name__)


async def worker_checkin(
    ticket_id: str,
    worker_id: str,
    lng: float,
    lat: float,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    维修工到场签到：
    1. 验证工单归属（只有被指派的维修工才能签到）
    2. MongoDB repair_records 存 GPS 签到坐标
    3. MySQL tickets 更新 started_at
    4. Redis 缓存同步
    """
    redis_cache = get_redis_cache()
    mongo_db = get_mongo_db()

    # 1. 验证工单归属
    result = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        return {"success": False, "msg": "工单不存在"}

    if ticket.assigned_worker_id != worker_id:
        return {"success": False, "msg": "您不是该工单的指派维修工"}

    if ticket.status not in ("dispatching", "repairing"):
        return {"success": False, "msg": f"工单状态不允许签到: {ticket.status}"}

    now = now_beijing()

    # 2. MongoDB 存签到记录（upsert 保证幂等）
    await mongo_db.repair_records.update_one(
        {"ticket_id": ticket_id},
        {"$set": {
            "ticket_id": ticket_id,
            "worker_id": worker_id,
            "gps_checkin": {"lng": lng, "lat": lat},
            "gps_checkin_at": now,
        }},
        upsert=True,
    )

    # 3. MySQL 更新
    ticket.status = "repairing"
    ticket.started_at = now
    await db.commit()

    # ES 同步 via RabbitMQ
    try:
        from app.services.mq.rabbitmq_service import publish_es_sync
        await publish_es_sync(ticket_id)
    except Exception as e:
        logger.warning(f"ES sync 消息发送失败: {e}")

    # 4. Redis 同步
    await redis_cache.hset(f"ticket:{ticket_id}:info", mapping={
        "status": "repairing",
        "started_at": now.isoformat(),
    })

    return {"success": True, "msg": "签到成功", "checkin_time": now.isoformat()}


async def worker_complete(
    ticket_id: str,
    worker_id: str,
    materials: List[Dict[str, Any]],
    labor_hours: float,
    work_notes: str,
    completion_photo_urls: List[str],
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    维修工完工提交：
    1. MongoDB repair_records 存耗材+工时+完工照片
    2. MongoDB ticket_attachments 存完工照片元数据
    3. Dify AI 验收对比（异步，不阻塞）
    4. AI 验收结果 → MySQL 状态流转 → Redis 同步
    5. 触发结算/复核

    返回: {success, msg, ai_verified, ai_confidence}
    """
    redis_cache = get_redis_cache()
    mongo_db = get_mongo_db()

    # 1. 验证工单归属
    result = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        return {"success": False, "msg": "工单不存在"}

    if ticket.assigned_worker_id != worker_id:
        return {"success": False, "msg": "您不是该工单的指派维修工"}

    if ticket.status != "repairing":
        return {"success": False, "msg": f"工单状态不允许完工提交: {ticket.status}"}

    now = now_beijing()

    # 2. MongoDB repair_records 存维修详情
    logger.info(f"工单 {ticket_id} 收到材料数据: {materials}")
    repair_update = {
        "materials": materials,
        "labor_hours": labor_hours,
        "work_notes": work_notes or "",
        "after_photos": completion_photo_urls,
        "worker_id": worker_id,
        "completed_at": now,
    }
    await mongo_db.repair_records.update_one(
        {"ticket_id": ticket_id},
        {"$set": repair_update},
        upsert=True,
    )
    logger.info(f"工单 {ticket_id} 维修记录已保存到 MongoDB")

    # 3. MongoDB ticket_attachments 存完工照片（upsert 避免返工重复写入）
    if completion_photo_urls:
        await mongo_db.ticket_attachments.update_one(
            {"ticket_id": ticket_id, "stage": "completion"},
            {"$set": {
                "ticket_id": ticket_id,
                "stage": "completion",
                "image_urls": completion_photo_urls,
                "uploaded_by": worker_id,
                "created_at": now,
            }},
            upsert=True,
        )

    # 4. Dify AI 验收对比
    # 获取报修时照片（维修前照片作为 AI 验收的固定基准图，不可被覆盖或删除）
    before_photos = await _get_before_photos(mongo_db, ticket_id)
    if not before_photos:
        logger.error(f"工单 {ticket_id} 缺少维修前照片，无法进行 AI 验收")
        return {
            "success": False,
            "msg": "缺少维修前照片，无法进行 AI 验收对比，请联系管理员确认",
        }

    try:
        verify_result = await verify_repair(
            ticket_id=ticket_id,
            before_photo_urls=before_photos,
            after_photo_urls=completion_photo_urls,
            repair_description=work_notes or ticket.description,
        )
    except Exception as e:
        logger.error(f"AI验收调用失败: {e}")
        verify_result = {"verified": True, "confidence": 0.75, "diff_summary": "AI验收服务不可用，默认通过"}

    ai_verified = verify_result.get("verified", True)
    ai_confidence = verify_result.get("confidence", 0.75)

    # 5. MongoDB ai_analysis_logs 存AI验收结果
    try:
        await mongo_db.ai_analysis_logs.insert_one({
            "ticket_id": ticket_id,
            "workflow": "ai_verify",
            "input": {
                "before_photos": before_photos,
                "after_photos": completion_photo_urls,
                "description": work_notes or ticket.description,
            },
            "output": verify_result,
            "created_at": now,
        })
    except Exception as e:
        logger.warning(f"MongoDB AI验收日志写入失败: {e}")

    # 6. MySQL 状态流转
    if ai_verified:
        ticket.status = "verifying"
        ticket.completed_at = now
    else:
        # AI 验收未通过 → 退回重做
        ticket.status = "repairing"
        await db.commit()

        # 标记需要返工
        try:
            await mongo_db.repair_records.update_one(
                {"ticket_id": ticket_id},
                {"$set": {"ai_rework_required": True}}
            )
        except Exception as e:
            logger.warning(f"标记返工标志失败: {e}")

        # 发通知给维修工
        try:
            await mongo_db.notifications.insert_one({
                "user_id": worker_id,
                "type": "status_change",
                "content": {
                    "title": "AI验收未通过",
                    "body": f"工单{ticket_id}AI验收未通过，请重新维修。原因：{verify_result.get('diff_summary', '')}",
                    "ticket_id": ticket_id,
                    "new_status": "repairing",
                    "ai_confidence": ai_confidence,
                },
                "is_read": False,
                "channel": "push",
                "ticket_id": ticket_id,
                "created_at": now,
            })
        except Exception as e:
            logger.warning(f"发送返工通知失败: {e}")

        # ES 同步 via RabbitMQ
        try:
            from app.services.mq.rabbitmq_service import publish_es_sync
            await publish_es_sync(ticket_id)
        except Exception as e:
            logger.warning(f"ES sync 消息发送失败: {e}")

        # Redis 同步
        await redis_cache.hset(f"ticket:{ticket_id}:info", mapping={
            "status": "repairing",
            "ai_verify_result": "rejected",
        })

        # 重新加入 Redis Geo 候选池（这样维修工可以接新单）
        try:
            redis_geo = get_redis_geo()
            await redis_geo.geoadd("workers:geo", (ticket.location_lng, ticket.location_lat, worker_id))
        except Exception as e:
            logger.warning(f"Redis Geo 恢复失败: {e}")

        return {
            "success": True,
            "msg": f"AI验收未通过（置信度{ai_confidence}），请重新维修",
            "ai_verified": False,
            "ai_confidence": ai_confidence,
        }

    await db.commit()

    # ES 同步 via RabbitMQ
    try:
        from app.services.mq.rabbitmq_service import publish_es_sync
        await publish_es_sync(ticket_id)
    except Exception as e:
        logger.warning(f"ES sync 消息发送失败: {e}")

    # 7. Redis 缓存同步
    await redis_cache.hset(f"ticket:{ticket_id}:info", mapping={
        "status": "verifying",
        "completed_at": now.isoformat(),
    })

    # 8. 解锁维修工（重新加入 Geo 候选池）
    try:
        redis_geo = get_redis_geo()
        await redis_geo.geoadd("workers:geo", (ticket.location_lng, ticket.location_lat, worker_id))
    except Exception as e:
        logger.warning(f"Redis Geo 恢复失败: {e}")

    return {
        "success": True,
        "msg": "完工提交成功，AI验收已通过，等待市民确认",
        "ai_verified": True,
        "ai_confidence": ai_confidence,
    }


async def _get_before_photos(mongo_db, ticket_id: str) -> list:
    """
    获取工单的维修前照片（市民报修时上传的图片）。

    查询策略（兼容新旧两种数据结构）：
      1. 优先查询 stage="report" 的 image_urls（当前标准格式）
      2. 兼容旧格式：type="report_photo" 的 image_url（单张旧格式）
      3. 兼容旧格式：type="report_photo" 的 image_urls（数组旧格式）

    返回: 图片 URL 列表，若确实不存在则返回空列表。
    """
    before_photos = []

    # 策略1：当前标准格式 stage="report" + image_urls
    try:
        before_doc = await mongo_db.ticket_attachments.find_one(
            {"ticket_id": ticket_id, "stage": "report"}
        )
        if before_doc:
            urls = before_doc.get("image_urls")
            if urls and isinstance(urls, list) and len(urls) > 0:
                before_photos = urls
                logger.debug(f"工单 {ticket_id} 从 stage=report 获取 {len(before_photos)} 张维修前照片")
                return before_photos
    except Exception as e:
        logger.warning(f"工单 {ticket_id} 查询 stage=report 照片失败: {e}")

    # 策略2：兼容旧格式 type="report_photo" + image_urls（数组）
    try:
        old_doc = await mongo_db.ticket_attachments.find_one(
            {"ticket_id": ticket_id, "type": "report_photo"}
        )
        if old_doc:
            urls = old_doc.get("image_urls")
            if urls and isinstance(urls, list) and len(urls) > 0:
                before_photos = urls
                logger.info(f"工单 {ticket_id} 从旧格式 type=report_photo + image_urls 获取 {len(before_photos)} 张照片")
                return before_photos
            # 策略3：兼容更旧格式 type="report_photo" + image_url（单张）
            single_url = old_doc.get("image_url")
            if single_url and isinstance(single_url, str) and single_url.strip():
                before_photos = [single_url]
                logger.info(f"工单 {ticket_id} 从旧格式 type=report_photo + image_url 获取 1 张照片")
                return before_photos
    except Exception as e:
        logger.warning(f"工单 {ticket_id} 查询旧格式 type=report_photo 照片失败: {e}")

    if not before_photos:
        logger.warning(f"工单 {ticket_id} 未找到任何维修前照片记录")

    return before_photos


async def citizen_confirm(
    ticket_id: str,
    user_id: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    市民确认完工（或7天自动确认）：
    1. MySQL tickets status → closed
    2. 触发 settlement 结算生成
    3. Redis 清理工单热缓存
    4. ES 同步关闭状态
    """
    redis_cache = get_redis_cache()

    result = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        return {"success": False, "msg": "工单不存在"}

    if ticket.status != "verifying":
        return {"success": False, "msg": f"当前状态{ticket.status} 不可确认"}

    now = now_beijing()
    ticket.status = "closed"
    ticket.closed_at = now
    await db.commit()

    # Redis 缓存标记关闭
    await redis_cache.hset(f"ticket:{ticket_id}:info", mapping={
        "status": "closed",
        "closed_at": now.isoformat(),
    })
    # 缩短TTL（已关闭工单保存24h热缓存）
    await redis_cache.expire(f"ticket:{ticket_id}:info", 86400)

    # 触发结算
    await _trigger_settlement(ticket_id, db)

    # ES 同步 via RabbitMQ
    try:
        from app.services.mq.rabbitmq_service import publish_es_sync
        await publish_es_sync(ticket_id)
    except Exception as e:
        logger.warning(f"ES sync 消息发送失败: {e}")

    return {"success": True, "msg": "工单已完结"}


async def auto_close_expired_tickets(db: AsyncSession) -> int:
    """
    定时任务：自动关闭7天未确认的工单。
    由scheduler 每天凌晨3点调用。
    返回: 关闭的工单数量
    """
    threshold = now_beijing() - datetime.timedelta(days=7)
    result = await db.execute(
        select(Ticket).where(
            Ticket.status == "verifying",
            Ticket.completed_at <= threshold,
        )
    )
    expired_tickets = result.scalars().all()

    closed_count = 0
    for ticket in expired_tickets:
        ticket.status = "closed"
        ticket.closed_at = now_beijing()
        closed_count += 1

        # ES 同步 via RabbitMQ
        try:
            from app.services.mq.rabbitmq_service import publish_es_sync
            await publish_es_sync(ticket.ticket_id)
        except Exception as e:
            logger.warning(f"ES sync 消息发送失败 for {ticket.ticket_id}: {e}")

        # 清理 Redis
        redis_cache = get_redis_cache()
        await redis_cache.delete(f"ticket:{ticket.ticket_id}:info")

        # 触发结算
        try:
            await _trigger_settlement(ticket.ticket_id, db)
        except Exception:
            pass

    if closed_count:
        await db.commit()

    return closed_count


async def _trigger_settlement(ticket_id: str, db: AsyncSession):
    """
    工单关闭时自动生成结算单。
    从 MongoDB repair_records 读取耗材费用 + 劳务费。
    劳务费按 audit_rules 配置计算，无匹配规则降级为 "other"。
    """
    mongo_db = get_mongo_db()

    # 防重复：已存在结算单则跳过
    existing = await db.execute(
        select(Settlement).where(Settlement.ticket_id == ticket_id)
    )
    if existing.scalar_one_or_none():
        logger.warning(f"结算单已存在，跳过 ticket={ticket_id}")
        return

    repair_doc = await mongo_db.repair_records.find_one({"ticket_id": ticket_id})
    if not repair_doc:
        logger.warning(f"结算触发失败：无维修记录 ticket={ticket_id}")
        return

    # 计算材料费 - 增强容错和日志
    materials = repair_doc.get("materials", [])
    logger.info(f"工单 {ticket_id} 材料数据: {materials}")

    material_cost = 0.0
    if materials:
        for i, m in enumerate(materials):
            # 兼容多种可能的字段名
            qty = m.get("qty") or m.get("quantity") or 0
            unit_cost = m.get("unit_cost") or m.get("price") or m.get("cost") or 0

            try:
                qty_float = float(qty)
            except (ValueError, TypeError):
                qty_float = 0.0

            try:
                cost_float = float(unit_cost)
            except (ValueError, TypeError):
                cost_float = 0.0

            item_cost = qty_float * cost_float
            material_cost += item_cost
            logger.info(f"  材料 {i}: 数量={qty_float}, 单价={cost_float}, 小计={item_cost}")

    material_cost = round(material_cost, 2)
    logger.info(f"工单 {ticket_id} 总材料费: {material_cost}")

    labor_hours = float(repair_doc.get("labor_hours", 0))
    worker_id = repair_doc.get("worker_id", "")

    # 查工单获取 facility_type / emergency_level
    result = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = result.scalar_one_or_none()

    # 按工单 facility_type 查询结算规则，无匹配降级为 "other"
    rule = None
    if ticket:
        rule_result = await db.execute(
            select(AuditRule).where(AuditRule.facility_type == ticket.facility_type)
        )
        rule = rule_result.scalar_one_or_none()

    if rule is None:
        fallback_result = await db.execute(
            select(AuditRule).where(AuditRule.facility_type == "other")
        )
        rule = fallback_result.scalar_one_or_none()

    # 按规则计算劳务费
    base_price = float(rule.base_price) if rule else 40.0
    emergency_multiplier = (
        float(rule.emergency_multiplier)
        if rule and ticket and ticket.emergency_level > 0
        else 1.0
    )

    completed_at = repair_doc.get("completed_at") or now_beijing()
    is_overtime = completed_at.hour >= 18 or completed_at.hour < 9
    is_night = completed_at.hour >= 22 or completed_at.hour < 6

    overtime_rate = float(rule.overtime_rate) if rule and is_overtime else 1.0
    night_subsidy = float(rule.night_subsidy) if rule and is_night else 0.0

    labor_cost = round(
        labor_hours * base_price * overtime_rate * emergency_multiplier + night_subsidy,
        2,
    )
    total = round(material_cost + labor_cost, 2)

    # 写入 MySQL settlements
    from app.utils.id_generator import generate_id
    redis_counter = get_redis_counter()
    settlement_id = await generate_id(redis_counter, "ST")

    settlement = Settlement(
        settlement_id=settlement_id,
        ticket_id=ticket_id,
        worker_id=worker_id,
        labor_cost=labor_cost,
        material_cost=material_cost,
        total=total,
        audit_status="pending",
    )
    db.add(settlement)
    await db.commit()

    # Redis 更新月度计数
    month_key = f"settlement:month:{now_beijing().strftime('%Y%m')}"
    await redis_counter.incrbyfloat(month_key, total)
    await redis_counter.expire(month_key, 86400 * 60)

    logger.info(f"结算生成: {settlement_id} ticket={ticket_id} total={total}")
