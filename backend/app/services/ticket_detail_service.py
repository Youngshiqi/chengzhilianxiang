# ============================================================
# 城市公共设施智能报修与派单系统 - 工单详情服务（三端统一）
# 作用：聚合 MySQL/Redis/MongoDB 四库数据，构建完整的工单详情响应；
#       包含三大板块：报修信息（含照片）、维修信息（含耗材+完工照）、处理进度时间轴；
#       被 admin/worker/citizen 三端 API 复用
# ============================================================

import datetime
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config.mongodb import get_mongo_db
from app.config.redis_client import get_redis_cache
from app.models.mysql.ticket import Ticket
from app.models.mysql.user import User
from app.models.mysql.worker import Worker
from app.models.mysql.settlement import Settlement
from app.models.mysql.evaluation import Evaluation

logger = logging.getLogger(__name__)


async def get_ticket_detail(
    db: AsyncSession,
    ticket_id: str,
) -> Optional[Dict[str, Any]]:
    """
    获取工单完整详情（三端统一）。

    聚合数据源：
      1. MySQL tickets  — 工单主数据
      2. MySQL users    — 报修人信息（nickname, phone, avatar）
      3. MySQL workers  — 维修员信息（name, star_rating, total_orders）
      4. MongoDB ticket_attachments — 报修照片 + 完工照片
      5. MongoDB repair_records     — 耗材/工时/签到GPS/完工照片
      6. MongoDB ai_analysis_logs   — AI分类 + AI验收结果
      7. Redis  ticket:{id}:info    — 热缓存（辅助加速）

    返回: TicketDetailResponse 字典，或 None（工单不存在）
    """
    mongo_db = get_mongo_db()
    redis_cache = get_redis_cache()

    # ---- 1. MySQL 工单主数据 ----
    result = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        return None

    # ---- 2. 报修人信息 ----
    reporter_name = ""
    reporter_phone = ""
    reporter_avatar = ""
    if ticket.user_id:
        try:
            user_result = await db.execute(select(User).where(User.user_id == ticket.user_id))
            reporter = user_result.scalar_one_or_none()
            if reporter:
                reporter_name = reporter.nickname or ""
                reporter_phone = reporter.phone or ""
                reporter_avatar = reporter.avatar_url or ""
        except Exception as e:
            logger.warning(f"查询报修人信息失败 ticket={ticket_id}: {e}")

    # ---- 3. 维修员信息 ----
    worker_info = None
    if ticket.assigned_worker_id:
        try:
            w_result = await db.execute(
                select(Worker).where(Worker.worker_id == ticket.assigned_worker_id)
            )
            worker = w_result.scalar_one_or_none()
            if worker:
                # 从 User 表获取 phone/avatar
                w_user_result = await db.execute(
                    select(User).where(User.user_id == ticket.assigned_worker_id)
                )
                w_user = w_user_result.scalar_one_or_none()
                worker_info = {
                    "worker_id": worker.worker_id,
                    "worker_name": worker.name,
                    "worker_phone": w_user.phone if w_user else "",
                    "worker_avatar": w_user.avatar_url if w_user else "",
                    "star_rating": round(worker.star_rating, 1),
                    "total_orders": worker.total_orders,
                }
        except Exception as e:
            logger.warning(f"查询维修员信息失败 ticket={ticket_id}: {e}")

    # ---- 4. MongoDB 报修照片 ----
    report_image_urls = []
    try:
        before_doc = await mongo_db.ticket_attachments.find_one(
            {"ticket_id": ticket_id, "stage": "report"}
        )
        if before_doc:
            report_image_urls = before_doc.get("image_urls", []) or []
    except Exception as e:
        logger.warning(f"查询报修照片失败 ticket={ticket_id}: {e}")

    # ---- 5. MongoDB 维修记录（耗材/工时/完工照片/签到GPS） ----
    repair_doc = None
    try:
        repair_doc = await mongo_db.repair_records.find_one({"ticket_id": ticket_id})
    except Exception as e:
        logger.warning(f"查询维修记录失败 ticket={ticket_id}: {e}")

    materials = []
    labor_hours = 0.0
    work_notes = ""
    completion_photos = []
    checkin_lng = None
    checkin_lat = None
    checkin_at = ""
    completed_at_repair = ""

    if repair_doc:
        raw_materials = repair_doc.get("materials", []) or []
        materials = [
            {
                "name": m.get("name", ""),
                "qty": float(m.get("qty", 0)),
                "unit": m.get("unit", "个"),
                "unit_cost": float(m.get("unit_cost", 0)),
            }
            for m in raw_materials
        ]
        labor_hours = float(repair_doc.get("labor_hours", 0))
        work_notes = repair_doc.get("work_notes", "") or ""
        completion_photos = repair_doc.get("after_photos", []) or []

        gps = repair_doc.get("gps_checkin")
        if gps:
            checkin_lng = gps.get("lng")
            checkin_lat = gps.get("lat")
        checkin_at = _format_time(repair_doc.get("gps_checkin_at"))
        completed_at_repair = _format_time(repair_doc.get("completed_at"))

    # ---- 6. MongoDB AI 结果 ----
    ai_category = ticket.ai_category or ""
    ai_confidence = ticket.ai_confidence or 0.0
    ai_verified = None
    ai_verify_confidence = None
    ai_verify_summary = ""
    nlp_output = {}

    try:
        ai_nlp_log = await mongo_db.ai_analysis_logs.find_one(
            {"ticket_id": ticket_id, "workflow": "nlp_parse"},
            sort=[("created_at", -1)],
        )
        if ai_nlp_log:
            nlp_output = ai_nlp_log.get("output", {}) or {}
    except Exception as e:
        logger.warning(f"查询AI分类日志失败 ticket={ticket_id}: {e}")

    try:
        ai_verify_log = await mongo_db.ai_analysis_logs.find_one(
            {"ticket_id": ticket_id, "workflow": "ai_verify"},
            sort=[("created_at", -1)],
        )
        if ai_verify_log:
            output = ai_verify_log.get("output", {})
            ai_verified = output.get("verified")
            ai_verify_confidence = output.get("confidence")
            ai_verify_summary = output.get("diff_summary", "") or ""
    except Exception as e:
        logger.warning(f"查询AI验收日志失败 ticket={ticket_id}: {e}")

    # ---- 7. 构建时间轴 ----
    timeline = _build_full_timeline(ticket, repair_doc, ai_verified)

    # ---- 8. 结算信息（查询 MySQL settlements 表） ----
    settlement = None
    try:
        stmt_result = await db.execute(
            select(Settlement).where(Settlement.ticket_id == ticket_id)
        )
        stmt = stmt_result.scalar_one_or_none()
        if stmt:
            settlement = {
                "settlement_id": stmt.settlement_id,
                "material_cost": round(stmt.material_cost, 2),
                "labor_cost": round(stmt.labor_cost, 2),
                "total_cost": round(stmt.total, 2),
                "audit_status": stmt.audit_status,
            }
    except Exception as e:
        logger.warning(f"查询结算信息失败 ticket={ticket_id}: {e}")

    # ---- 9. 市民评价信息（查询 MySQL evaluations 表） ----
    evaluation = None
    try:
        eval_result = await db.execute(
            select(Evaluation).where(Evaluation.ticket_id == ticket_id)
        )
        eval_record = eval_result.scalar_one_or_none()
        if eval_record:
            evaluation = {
                "eval_id": eval_record.eval_id,
                "star": eval_record.star,
                "tags": eval_record.tags.split(",") if eval_record.tags else [],
                "comment": eval_record.comment or "",
                "created_at": _format_time(eval_record.created_at),
            }
    except Exception as e:
        logger.warning(f"查询评价信息失败 ticket={ticket_id}: {e}")

    # ---- 组装响应 ----
    status = ticket.status or "pending"
    return {
        "ticket_id": ticket.ticket_id,
        "status": status,
        "status_label": {
            "pending": "待受理",
            "accepting": "派单中",
            "dispatching": "已接单",
            "repairing": "维修中",
            "verifying": "验收中",
            "closed": "已完结",
        }.get(status, status),

        "report": {
            "reporter_id": ticket.user_id or "",
            "reporter_name": reporter_name,
            "reporter_phone": reporter_phone,
            "description": ticket.description or "",
            "facility_type": ticket.facility_type or "",
            "address": ticket.address or "",
            "location_lng": ticket.location_lng or 0.0,
            "location_lat": ticket.location_lat or 0.0,
            "district": ticket.district or "",
            "emergency_level": ticket.emergency_level or 0,
            "image_urls": report_image_urls,
            "created_at": _format_time(ticket.created_at),
        },

        "repair": {
            "worker": worker_info,
            "materials": materials,
            "labor_hours": labor_hours,
            "work_notes": work_notes,
            "completion_photos": completion_photos,
            "checkin_lng": checkin_lng,
            "checkin_lat": checkin_lat,
            "checkin_at": checkin_at,
            "completed_at": completed_at_repair,
        },

        "ai": {
            "ai_category": ai_category,
            "ai_confidence": ai_confidence,
            "ai_verified": ai_verified,
            "ai_verify_confidence": ai_verify_confidence,
            "ai_verify_summary": ai_verify_summary,
            "category": nlp_output.get("category") or ai_category,
            "sub_category": nlp_output.get("sub_category") or nlp_output.get("subcategory") or "",
            "issue_category": nlp_output.get("issue_category") or nlp_output.get("category") or ai_category,
            "subcategory": nlp_output.get("subcategory") or nlp_output.get("sub_category") or "",
            "urgency_level": nlp_output.get("urgency_level", ticket.emergency_level or 0),
            "urgency_reason": nlp_output.get("urgency_reason", ""),
            "key_info": nlp_output.get("key_info") or [],
            "suggested_action": nlp_output.get("suggested_action", ""),
            "priority_score": nlp_output.get("priority_score", 0),
            "emergency_level": nlp_output.get("emergency_level", ticket.emergency_level or 0),
            "repair_knowledge": nlp_output.get("repair_knowledge") or [],
            "tools_needed": nlp_output.get("tools_needed") or [],
            "safety_tips": nlp_output.get("safety_tips") or [],
            "parts_needed": nlp_output.get("parts_needed") or [],
        },

        "timeline": timeline,

        "settlement": settlement,
        "evaluation": evaluation,

        "created_at": _format_time(ticket.created_at),
        "accepted_at": _format_time(ticket.accepted_at),
        "started_at": _format_time(ticket.started_at),
        "completed_at": _format_time(ticket.completed_at),
        "closed_at": _format_time(ticket.closed_at),
    }


def _build_full_timeline(
    ticket: Ticket,
    repair_doc: Optional[Dict],
    ai_verified: Optional[bool],
) -> List[Dict[str, Any]]:
    """
    构建工单全流程时间轴，按时间顺序排列所有已完成事件。
    从 MySQL 主表时间戳 + MongoDB 维修记录构建。
    """
    events = []

    # 1. 市民报修（一定有）
    events.append({
        "event": "reported",
        "label": "市民报修",
        "time": _format_time(ticket.created_at),
        "detail": ticket.description[:80] if ticket.description else "",
        "done": True,
    })

    # 2. AI 智能分类
    if ticket.ai_category:
        events.append({
            "event": "ai_categorized",
            "label": "AI 智能分类",
            "time": _format_time(ticket.created_at),  # 与报修同时
            "detail": f"识别为「{ticket.ai_category}」，置信度 {ticket.ai_confidence or 0:.0%}",
            "done": True,
        })

    # 3. 派单
    if ticket.assigned_worker_id:
        dispatched = ticket.status not in ("pending",)
        events.append({
            "event": "dispatched",
            "label": "系统派单",
            "time": _format_time(ticket.accepted_at) if ticket.accepted_at else "",
            "detail": f"指派维修员 {ticket.assigned_worker_id}",
            "done": dispatched,
        })

    # 4. 维修员接单
    if ticket.accepted_at:
        events.append({
            "event": "accepted",
            "label": "维修员接单",
            "time": _format_time(ticket.accepted_at),
            "detail": "",
            "done": True,
        })
    else:
        events.append({
            "event": "accepted",
            "label": "维修员接单",
            "time": "",
            "detail": "",
            "done": False,
        })

    # 5. 到场签到
    checkin_time = None
    if repair_doc:
        checkin_time = repair_doc.get("gps_checkin_at")
        gps = repair_doc.get("gps_checkin")
        gps_detail = ""
        if gps:
            gps_detail = f"GPS: {gps.get('lng', '')}, {gps.get('lat', '')}"
        events.append({
            "event": "checkin",
            "label": "到场签到",
            "time": _format_time(checkin_time),
            "detail": gps_detail,
            "done": checkin_time is not None,
        })
    else:
        events.append({
            "event": "checkin",
            "label": "到场签到",
            "time": "",
            "detail": "",
            "done": False,
        })

    # 6. 维修完工
    completed_time = repair_doc.get("completed_at") if repair_doc else None
    if completed_time:
        events.append({
            "event": "completed",
            "label": "维修完工",
            "time": _format_time(completed_time),
            "detail": f"工时 {repair_doc.get('labor_hours', 0)}h，耗材 {len(repair_doc.get('materials', []))} 项",
            "done": True,
        })
    else:
        events.append({
            "event": "completed",
            "label": "维修完工",
            "time": "",
            "detail": "",
            "done": False,
        })

    # 7. AI 验收
    if ai_verified is not None:
        events.append({
            "event": "ai_verified",
            "label": "AI 智能验收",
            "time": _format_time(completed_time) if completed_time else "",
            "detail": "验收通过" if ai_verified else "验收未通过，退回重做",
            "done": True,
        })
    else:
        events.append({
            "event": "ai_verified",
            "label": "AI 智能验收",
            "time": "",
            "detail": "",
            "done": False,
        })

    # 8. 完结
    closed = ticket.status == "closed"
    events.append({
        "event": "closed",
        "label": "工单完结",
        "time": _format_time(ticket.closed_at) if ticket.closed_at else "",
        "detail": "市民确认完结" if ticket.closed_at else ("等待市民确认" if ticket.status == "verifying" else ""),
        "done": closed,
    })

    return events


def _format_time(dt) -> str:
    """安全格式化时间为 ISO 字符串"""
    if dt is None:
        return ""
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime.datetime):
        return dt.isoformat()
    return str(dt)
