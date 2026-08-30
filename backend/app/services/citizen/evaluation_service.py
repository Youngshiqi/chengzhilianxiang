# ============================================================
# 城市公共设施智能报修与派单系统 - 市民评价业务服务
# 作用：封装评价业务逻辑；
#       1. MySQL evaluations 写入（ticket_id唯一索引防重复）
#       2. 差评(star<=2) → RabbitMQ review_queue 触发管理员复核
#       3. ES workers_perf_index 更新维修员绩效指标
#       4. MongoDB notifications 写入评价通知
# ============================================================

import datetime
import logging
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.mongodb import get_mongo_db
from app.config.redis_client import get_redis_counter
from app.models.mysql.evaluation import Evaluation
from app.models.mysql.ticket import Ticket
from app.services.mq.rabbitmq_service import publish_review_task
from app.utils.id_generator import generate_id
from app.utils.timezone import now_beijing

logger = logging.getLogger(__name__)


async def submit_evaluation(
    db: AsyncSession,
    ticket_id: str,
    user_id: str,
    star: int,
    tags: str = "",
    comment: str = "",
) -> Dict[str, Any]:
    """
    市民提交服务评价：
    1. MySQL evaluations 写入（唯一索引防重复）
    2. 差评触发复核队列
    3. ES 绩效更新
    4. MongoDB 通知写入
    """
    redis_counter = get_redis_counter()
    mongo_db = get_mongo_db()
    eval_id = await generate_id(redis_counter, "EV")

    # 1. 写入 MySQL
    evaluation = Evaluation(
        eval_id=eval_id,
        ticket_id=ticket_id,
        user_id=user_id,
        star=star,
        tags=tags or "",
        comment=comment or "",
    )
    db.add(evaluation)
    await db.flush()
    await db.commit()

    # 2. 差评触发复核（异步容错）
    if star <= 2:
        try:
            await publish_review_task(ticket_id, eval_id)
            logger.info(f"差评触发复核: ticket={ticket_id} eval={eval_id} star={star}")
        except Exception as e:
            logger.error(f"差评复核消息发布失败: ticket={ticket_id} error={e}")

    # 3. MongoDB 评价通知（异步容错）
    try:
        # 获取工单关联的维修员
        from sqlalchemy import select
        result = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
        ticket = result.scalar_one_or_none()
        worker_id = ticket.assigned_worker_id if ticket else ""

        await mongo_db.notifications.insert_one({
            "recipient_id": worker_id,
            "recipient_role": "worker",
            "type": "evaluation",
            "title": f"收到新评价（{star}星）",
            "content": comment or "",
            "related_id": eval_id,
            "is_read": False,
            "created_at": now_beijing(),
        })
    except Exception as e:
        logger.warning(f"评价通知写入失败: {e}")

    # 4. ES 绩效更新（异步容错）
    try:
        await _sync_worker_perf_to_es(ticket_id, star, db)
    except Exception as e:
        logger.warning(f"ES 绩效同步失败: {e}")

    return {
        "eval_id": eval_id,
        "success": True,
    }


async def _sync_worker_perf_to_es(ticket_id: str, star: int, db: AsyncSession):
    """同步评价星级到 ES workers_perf_index"""
    from sqlalchemy import select
    from app.config.elasticsearch_client import get_es_client
    from app.config.settings import settings

    es = get_es_client()
    if not es:
        return

    result = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket or not ticket.assigned_worker_id:
        return

    worker_id = ticket.assigned_worker_id
    index_name = f"{settings.ES_INDEX_PREFIX}_workers_perf"

    await es.update(
        index=index_name,
        id=worker_id,
        body={
            "script": {
                "source": """
                    ctx._source.total_evals = (ctx._source.total_evals ?: 0) + 1;
                    ctx._source.avg_star = ((ctx._source.avg_star ?: 0) * (ctx._source.total_evals - 1) + params.star) / ctx._source.total_evals;
                """,
                "params": {"star": star},
            },
            "upsert": {
                "worker_id": worker_id,
                "total_evals": 1,
                "avg_star": star,
                "total_orders": 0,
                "avg_response_minutes": 0,
            },
        },
    )
