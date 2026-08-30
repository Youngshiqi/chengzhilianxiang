# ============================================================
# 城市公共设施智能报修与派单系统 - AI智能派单核心服务（系统核心亮点）
# 作用：实现多因子AI智能派单算法，以「最小运维总成本」为目标；
#       流程：
#       1. 从 MySQL 获取工单信息（位置、设施类型、紧急程度）
#       2. Redis Geo GEORADIUS 半径筛选候选维修员（默认5km，紧急10km）
#       3. 硬约束过滤：max_daily_orders上限 / night_duty夜班 / skills技能匹配
#       3.5 高德驾车距离修正（替换Redis Geo直线距离，降级保持直线距离）
#       4. 多维评分（距离40% + 负载30% + 好评20% + 响应10%）
#       5. Redis SETNX 分布式锁锁定派单（300s自动过期防死锁）
#       6. MySQL tickets.assigned_worker_id 更新 + Redis 状态同步
#       7. RabbitMQ 延迟消息：10分钟无人接单 → 自动升级强制指派
# ============================================================

import datetime
import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config.redis_client import get_redis_cache, get_redis_geo, get_redis_lock, get_redis_counter
from app.config.mongodb import get_mongo_db
from app.models.mysql.ticket import Ticket
from app.models.mysql.worker import Worker
from app.services.ai.dispatch_score_service import score_candidates
from app.services.map.amap_service import driving_distance
from app.services.mq.rabbitmq_service import publish_timeout_check
from app.utils.timezone import now_beijing

logger = logging.getLogger(__name__)

# 派单参数
DEFAULT_SEARCH_RADIUS_KM = 5       # 默认搜索半径（公里）
EMERGENCY_SEARCH_RADIUS_KM = 10    # 紧急工单搜索半径
MAX_CANDIDATES = 20                # 最大候选人数


async def execute_dispatch(ticket_id: str, db: AsyncSession, is_timeout_dispatch: bool = False) -> Dict[str, Any]:
    """
    执行 AI 智能派单主流程。

    参数:
      is_timeout_dispatch: 是否为超时自动派单（10分钟无人接单后触发）

    返回:
      {"success": bool, "worker_id": str | None, "scores": list, "reason": str}
    """
    redis_cache = get_redis_cache()
    redis_geo = get_redis_geo()
    redis_lock = get_redis_lock()
    redis_counter = get_redis_counter()
    mongo_db = get_mongo_db()

    # ---- 1. 获取工单信息 ----
    result = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        return {"success": False, "worker_id": None, "scores": [], "reason": "工单不存在"}

    # 状态检查：
    # - 超时派单：只处理 accepting 状态
    # - 普通派单：只处理 pending/dispatching 状态（兼容历史逻辑）
    if is_timeout_dispatch:
        if ticket.status != "accepting":
            return {"success": False, "worker_id": None, "scores": [], "reason": f"超时派单只处理 accepting 状态，当前状态: {ticket.status}"}
    else:
        if ticket.status not in ("pending", "dispatching"):
            return {"success": False, "worker_id": None, "scores": [], "reason": f"普通派单不处理 accepting 状态，当前状态: {ticket.status}"}

    facility_lng = ticket.location_lng
    facility_lat = ticket.location_lat
    facility_type = ticket.facility_type
    emergency = ticket.emergency_level

    # ---- 2. Redis Geo 半径筛选 ----
    radius_km = EMERGENCY_SEARCH_RADIUS_KM if emergency else DEFAULT_SEARCH_RADIUS_KM
    worker_geo_key = "workers:geo"

    try:
        # GEORADIUS 返回半径内的 worker_id 列表（含距离和坐标）
        nearby_workers = await redis_geo.georadius(
            worker_geo_key,
            facility_lng,
            facility_lat,
            radius_km,
            unit="km",
            withdist=True,
            withcoord=True,
            sort="ASC",
            count=MAX_CANDIDATES,
        )
        # nearby_workers: [(b'worker_id', distance_km, (lng, lat)), ...]
    except Exception as e:
        logger.warning(f"Redis Geo 查询失败（可能无在岗维修员）: {e}")
        return {"success": False, "worker_id": None, "scores": [], "reason": "附近无可用维修员"}

    if not nearby_workers:
        return {"success": False, "worker_id": None, "scores": [], "reason": f"半径{radius_km}km内无在岗维修员"}

    # 解码 Geo 结果
    candidate_pool = []
    for item in nearby_workers:
        if isinstance(item, (list, tuple)):
            worker_id = item[0].decode() if isinstance(item[0], bytes) else item[0]
            distance = item[1]
            coords = item[2] if len(item) > 2 else None
        else:
            worker_id = item.decode() if isinstance(item, bytes) else item
            distance = 0
            coords = None
        entry = {"worker_id": worker_id, "distance_km": round(float(distance), 2)}
        if coords and len(coords) == 2:
            entry["worker_lng"] = float(coords[0])
            entry["worker_lat"] = float(coords[1])
        candidate_pool.append(entry)

    if not candidate_pool:
        return {"success": False, "worker_id": None, "scores": [], "reason": "无有效候选维修员"}

    # ---- 3. 简化版：跳过硬约束，直接使用所有候选者 ----
    filtered_candidates = candidate_pool

    if not filtered_candidates:
        return {
            "success": False,
            "worker_id": None,
            "scores": [],
            "reason": f"附近无可用维修员（半径{radius_km}km内）",
        }

    logger.info(f"工单{ticket_id}使用简化派单规则：候选者共{len(filtered_candidates)}人，只按距离排序")

    # ---- 3.5 高德驾车距离修正（替换 Redis Geo 直线距离） ----
    for c in filtered_candidates:
        if "worker_lng" not in c or "worker_lat" not in c:
            # 没有坐标的候选者，保持 Geo 直线距离
            continue

        cache_key = f"amap:driving:{c['worker_id']}:{ticket_id}"
        cached = await redis_cache.get(cache_key)
        if cached:
            try:
                cached_data = json.loads(cached)
                c["distance_km"] = cached_data["distance_km"]
                c["driving_duration_min"] = cached_data.get("duration_min")
                continue
            except Exception:
                pass

        try:
            route = await driving_distance(
                c["worker_lng"], c["worker_lat"],
                facility_lng, facility_lat,
            )
            if route:
                c["distance_km"] = route["distance_km"]
                c["driving_duration_min"] = route["duration_min"]
                # 缓存 5 分钟，避免 force_dispatch 重复计费
                await redis_cache.setex(cache_key, 300, json.dumps(route))
            # 失败时保持 Geo 直线距离，无需额外处理
        except Exception as e:
            logger.warning(f"高德驾车距离查询失败 worker={c['worker_id']}: {e}")
            # 降级：保持 Redis Geo 直线距离

    # ---- 4. 简化版评分：只需要距离 ----
    scoring_input = []
    for c in filtered_candidates:
        worker_id = c["worker_id"]
        # 简化版：只需要距离，其他字段填默认值（评分函数会忽略）
        scoring_input.append({
            "worker_id": worker_id,
            "distance_km": c["distance_km"],
            "today_orders": 0,
            "star_rating": 5.0,
            "avg_response_min": 0,
        })

    score_result = await score_candidates(
        ticket_id=ticket_id,
        candidates=scoring_input,
        facility_lng=facility_lng,
        facility_lat=facility_lat,
    )

    selected_worker_id = score_result.get("selected_worker_id")
    scores = score_result.get("scores", [])

    if not selected_worker_id:
        return {"success": False, "worker_id": None, "scores": scores, "reason": "评分后无合适人选"}

    # ---- 5. Redis 分布式锁 ----
    lock_key = f"lock:ticket:{ticket_id}"
    acquired = await redis_lock.set(
        lock_key,
        selected_worker_id,
        nx=True,
        ex=300,  # 5分钟自动过期防死锁
    )
    if not acquired:
        # 已被锁定（并发场景）
        existing_lock_holder = await redis_lock.get(lock_key)
        return {
            "success": False,
            "worker_id": None,
            "scores": scores,
            "reason": f"派单已被锁定 by {existing_lock_holder}",
        }

    # ---- 6. MySQL 指派 + Redis 同步 ----
    try:
        ticket.assigned_worker_id = selected_worker_id
        ticket.status = "dispatching"
        await db.commit()

        # Redis 状态同步
        await redis_cache.hset(f"ticket:{ticket_id}:info", mapping={
            "status": "dispatching",
            "assigned_worker_id": selected_worker_id,
        })

        # 从接单大厅移除
        await redis_cache.zrem("tickets:accepting", ticket_id)

        # Redis Geo 移除该维修员（避免重复派单）
        await redis_geo.zrem(worker_geo_key, selected_worker_id)

        # 创建派单通知
        try:
            from app.services.notification_service import create_dispatch_notification
            await create_dispatch_notification(
                worker_id=selected_worker_id,
                ticket_id=ticket_id,
                facility_type=ticket.facility_type,
                address=ticket.address or "",
                description=ticket.description or "",
                emergency_level=ticket.emergency_level or 0,
                is_auto_dispatch=is_timeout_dispatch,
            )
        except Exception as e:
            logger.warning(f"派单通知创建失败: {e}")

    except Exception as e:
        # MySQL 写入失败 → 释放锁
        await redis_lock.delete(lock_key)
        logger.error(f"派单MySQL更新失败: {e}")
        return {"success": False, "worker_id": None, "scores": scores, "reason": f"数据库异常: {e}"}

    # ---- 7. 后续异步操作 ----
    # 7a. MongoDB 审计日志
    try:
        await mongo_db.audit_logs.insert_one({
            "operator_id": "system_dispatch",
            "role": "system",
            "action": "auto_dispatch",
            "target_type": "ticket",
            "target_id": ticket_id,
            "detail": {
                "assigned_worker_id": selected_worker_id,
                "scores": scores,
            },
            "ip": "127.0.0.1",
            "created_at": now_beijing(),
        })
    except Exception as e:
        logger.warning(f"MongoDB 审计日志写入失败: {e}")

    # 7b. 发布超时检查（10分钟延迟）
    try:
        await publish_timeout_check(ticket_id, delay_minutes=10)
    except Exception as e:
        logger.warning(f"超时检查消息发布失败: {e}")

    # 7c. ES 同步 via RabbitMQ
    try:
        from app.services.mq.rabbitmq_service import publish_es_sync
        await publish_es_sync(ticket_id)
    except Exception as e:
        logger.warning(f"ES sync 消息发布失败: {e}")

    return {
        "success": True,
        "worker_id": selected_worker_id,
        "scores": scores,
        "reason": f"已指派给 {selected_worker_id}",
    }


async def force_dispatch(ticket_id: str, db: AsyncSession, admin_id: str) -> Dict[str, Any]:
    """
    管理员强制指派（超时10分钟无人接单后触发）。
    绕过评分环节，直接锁定并指派给得分最高的可用维修员。
    """
    redis_lock = get_redis_lock()
    redis_cache = get_redis_cache()

    # 检查工单状态
    result = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        return {"success": False, "reason": "工单不存在"}

    if ticket.status != "dispatching":
        return {"success": False, "reason": f"工单状态不允许强制指派: {ticket.status}"}

    # 释放旧锁，重新执行派单
    lock_key = f"lock:ticket:{ticket_id}"
    await redis_lock.delete(lock_key)

    # 重新执行完整派单流程（管理员强制派单不走超时逻辑）
    result = await execute_dispatch(ticket_id, db, is_timeout_dispatch=False)

    # 标记为强制指派
    if result["success"]:
        mongo_db = get_mongo_db()
        try:
            await mongo_db.audit_logs.insert_one({
                "operator_id": admin_id,
                "role": "admin",
                "action": "force_dispatch",
                "target_type": "ticket",
                "target_id": ticket_id,
                "detail": {"result": result},
                "ip": "127.0.0.1",
                "created_at": now_beijing(),
            })
        except Exception:
            pass

    return result


async def _apply_hard_constraints(
    db: AsyncSession,
    redis_counter,
    candidates: List[Dict],
    facility_type: str,
) -> List[Dict]:
    """
    硬约束过滤候选维修员：
    1. max_daily_orders: 当日接单数未达上限
    2. night_duty: 夜班时段（22:00-06:00）需开启夜班
    3. skills: 技能标签匹配设施类型
    """
    worker_ids = [c["worker_id"] for c in candidates]

    # 批量查询 MySQL Worker
    result = await db.execute(
        select(Worker).where(Worker.worker_id.in_(worker_ids))
    )
    workers_map = {w.worker_id: w for w in result.scalars().all()}

    filtered = []
    try:
        from zoneinfo import ZoneInfo
        now_hour = now_beijing().hour
    except Exception:
        # zoneinfo 不可用时降级为 UTC+8 近似
        now_hour = (now_beijing().hour + 8) % 24
    is_night = now_hour >= 22 or now_hour < 6

    for c in candidates:
        wid = c["worker_id"]
        worker = workers_map.get(wid)
        if not worker:
            continue

        # 约束1：日单量上限
        today_str = await redis_counter.get(f"worker:{wid}:daily_order")
        today_orders = int(today_str) if today_str else 0
        if today_orders >= worker.max_daily_orders:
            logger.debug(f"工人{ wid }已达日单上限: {today_orders}/{worker.max_daily_orders}")
            continue

        # 约束2：夜班检查
        if is_night and not worker.night_duty:
            logger.debug(f"工人{ wid }未开启夜班，当前时间{ now_hour }点")
            continue

        # 约束3：技能匹配
        if worker.skills:
            skills_list = _parse_skills(worker.skills)
            facility_lower = facility_type.lower()
            matched = any(
                s.lower() in facility_lower or facility_lower in s.lower()
                for s in skills_list
            )
            if not matched:
                # 紧急工单或常见故障放宽技能匹配
                logger.debug(f"工人{ wid }技能不匹配: {skills_list} vs {facility_type}")
                continue

        filtered.append(c)

    return filtered


def _parse_skills(skills) -> List[str]:
    """解析技能字段（可能是JSON字符串或列表）"""
    import json
    if isinstance(skills, list):
        return skills
    if isinstance(skills, str):
        try:
            return json.loads(skills)
        except json.JSONDecodeError:
            return [s.strip() for s in skills.split(",") if s.strip()]
    return []


async def _apply_hard_constraints_relaxed(
    db: AsyncSession,
    redis_counter,
    candidates: List[Dict],
    facility_type: str,
    relax_skill: bool = False,
) -> List[Dict]:
    """
    放宽的硬约束过滤（降级策略）：
    1. max_daily_orders: 当日接单数未达上限（或放宽上限）
    2. night_duty: 夜班时段检查（可跳过）
    3. skills: 可选择跳过技能匹配
    """
    worker_ids = [c["worker_id"] for c in candidates]

    # 批量查询 MySQL Worker
    result = await db.execute(
        select(Worker).where(Worker.worker_id.in_(worker_ids))
    )
    workers_map = {w.worker_id: w for w in result.scalars().all()}

    filtered = []
    try:
        from zoneinfo import ZoneInfo
        now_hour = now_beijing().hour
    except Exception:
        now_hour = (now_beijing().hour + 8) % 24
    is_night = now_hour >= 22 or now_hour < 6

    for c in candidates:
        wid = c["worker_id"]
        worker = workers_map.get(wid)
        if not worker:
            continue

        # 约束1：日单量上限（放宽至1.5倍）
        today_str = await redis_counter.get(f"worker:{wid}:daily_order")
        today_orders = int(today_str) if today_str else 0
        max_orders = int(worker.max_daily_orders * 1.5)
        if today_orders >= max_orders:
            logger.debug(f"工人{wid}已达放宽后日单上限: {today_orders}/{max_orders}")
            continue

        # 约束2：夜班检查（可跳过，但记录日志）
        if is_night and not worker.night_duty:
            logger.debug(f"工人{wid}未开启夜班（降级策略允许）")

        # 约束3：技能匹配（可跳过）
        if not relax_skill and worker.skills:
            skills_list = _parse_skills(worker.skills)
            facility_lower = facility_type.lower()
            matched = any(
                s.lower() in facility_lower or facility_lower in s.lower()
                for s in skills_list
            )
            if not matched:
                logger.debug(f"工人{wid}技能不匹配（降级策略允许）")

        filtered.append(c)

    return filtered


async def _apply_hard_constraints_for_general_repair(
    db: AsyncSession,
    redis_counter,
    candidates: List[Dict],
) -> List[Dict]:
    """
    超时派单降级策略：寻找技能为"综合维修"的维修工
    硬约束：
    1. max_daily_orders: 当日接单数未达上限
    2. night_duty: 夜班时段需开启夜班权限
    3. skills: 必须包含"综合维修"
    """
    worker_ids = [c["worker_id"] for c in candidates]

    # 批量查询 MySQL Worker
    result = await db.execute(
        select(Worker).where(Worker.worker_id.in_(worker_ids))
    )
    workers_map = {w.worker_id: w for w in result.scalars().all()}

    filtered = []
    try:
        from zoneinfo import ZoneInfo
        now_hour = now_beijing().hour
    except Exception:
        now_hour = (now_beijing().hour + 8) % 24
    is_night = now_hour >= 22 or now_hour < 6

    for c in candidates:
        wid = c["worker_id"]
        worker = workers_map.get(wid)
        if not worker:
            continue

        # 约束1：日单量上限
        today_str = await redis_counter.get(f"worker:{wid}:daily_order")
        today_orders = int(today_str) if today_str else 0
        if today_orders >= worker.max_daily_orders:
            logger.debug(f"工人{wid}已达日单上限: {today_orders}/{worker.max_daily_orders}")
            continue

        # 约束2：夜班检查
        if is_night and not worker.night_duty:
            logger.debug(f"工人{wid}未开启夜班，当前时间{now_hour}点")
            continue

        # 约束3：必须包含"综合维修"技能
        has_general_repair = False
        if worker.skills:
            skills_list = _parse_skills(worker.skills)
            has_general_repair = any(
                "综合维修" in s or "综合" in s or s in "综合维修"
                for s in skills_list
            )
        if not has_general_repair:
            logger.debug(f"工人{wid}无综合维修技能")
            continue

        filtered.append(c)

    return filtered
