# ============================================================
# 城市公共设施智能报修与派单系统 — FastAPI 应用主入口
# 作用：创建 FastAPI 实例，注册中间件、路由、生命周期事件；
#       启动时连接 MySQL/Redis/MongoDB/ES/RabbitMQ，关闭时释放资源；
#       启动 RabbitMQ 派单消费者 + ES 同步消费者后台任务 + 自动完结工单调度器
# ============================================================

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.config.mysql import init_mysql, close_mysql, get_async_session_factory
from app.config.redis_client import init_redis, close_redis
from app.config.mongodb import init_mongodb, close_mongodb
from app.config.elasticsearch_client import init_es, close_es
from app.api.v1.router import api_router
from app.middleware.auth import AuthMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.core.exceptions import register_exception_handlers

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 后台任务引用（用于优雅关闭）
_background_tasks = []


async def _start_dispatch_consumer():
    """启动 RabbitMQ 派单消费者（后台常驻任务，指数退避重连）"""
    import aio_pika
    from app.services.mq.rabbitmq_service import (
        EXCHANGE_NAME, QUEUE_DISPATCH, QUEUE_DISPATCH_TIMEOUT, QUEUE_REVIEW,
        _get_channel,
    )
    from app.services.worker.dispatch_service import execute_dispatch

    logger.info("========== 派单消费者任务启动 ==========")
    # 等待基础设施就绪
    await asyncio.sleep(3)
    logger.info("开始连接 RabbitMQ...")

    async def handle_dispatch(message: aio_pika.IncomingMessage):
        """消费派单消息，执行 AI 智能派单（仅处理历史遗留的 pending/dispatching 工单）"""
        import json
        from app.config.mysql import get_async_session_factory

        try:
            body = json.loads(message.body.decode())
            ticket_id = body.get("ticket_id")
            logger.info(f"收到派单消息: {ticket_id}")

            # 新建数据库会话
            session_factory = get_async_session_factory()
            async with session_factory() as db:
                result = await execute_dispatch(ticket_id, db, is_timeout_dispatch=False)
                if result["success"]:
                    logger.info(f"派单成功: {ticket_id} -> {result['worker_id']}")
                else:
                    logger.warning(f"派单失败: {ticket_id} reason={result['reason']}")
            await message.ack()
        except Exception as e:
            logger.error(f"派单消费异常: {e}")
            await message.nack(requeue=True)

    async def handle_timeout(message: aio_pika.IncomingMessage):
        """消费超时消息：检查工单状态，如仍在接单大厅则自动派单"""
        import json
        from sqlalchemy import select
        from app.config.mysql import get_async_session_factory
        from app.models.mysql.ticket import Ticket
        from app.services.worker.dispatch_service import execute_dispatch
        from app.config.redis_client import get_redis_cache

        try:
            body = json.loads(message.body.decode())
            ticket_id = body.get("ticket_id")
            logger.info(f"========== 收到超时检查消息: {ticket_id} ==========")

            session_factory = get_async_session_factory()
            async with session_factory() as db:
                # 先检查工单状态
                result = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
                ticket = result.scalar_one_or_none()

                if not ticket:
                    logger.warning(f"超时检查：工单 {ticket_id} 不存在")
                    await message.ack()
                    return

                logger.info(f"工单 {ticket_id} 当前状态: {ticket.status}")

                if ticket.status == "accepting":
                    # 仍在接单大厅，执行自动派单
                    logger.info(f"工单 {ticket_id} 10分钟无接单，开始自动派单")

                    # 从接单大厅移除（先移除，避免并发问题）
                    try:
                        redis_cache = get_redis_cache()
                        await redis_cache.zrem("tickets:accepting", ticket_id)
                    except Exception:
                        pass

                    # 执行超时派单（is_timeout_dispatch=True，不强制降级）
                    dispatch_result = await execute_dispatch(ticket_id, db, is_timeout_dispatch=True)
                    if dispatch_result["success"]:
                        logger.info(f"自动派单成功: {ticket_id} -> {dispatch_result['worker_id']}")
                    else:
                        logger.warning(f"自动派单失败: {ticket_id} reason={dispatch_result['reason']}")

                elif ticket.status in ("dispatching", "repairing", "verifying", "closed"):
                    logger.info(f"工单 {ticket_id} 状态为 {ticket.status}，已被处理，跳过自动派单")

                else:
                    logger.warning(f"工单 {ticket_id} 状态为 {ticket.status}，跳过自动派单")

            await message.ack()
        except Exception as e:
            logger.error(f"超时消费异常: {e}")
            await message.nack(requeue=True)

    # 无限循环重连（后台常驻）
    base_delay = 5
    max_delay = 60
    retry_count = 0

    while True:
        channel = None
        try:
            retry_count += 1
            logger.info(f"尝试连接 RabbitMQ (第{retry_count}次)...")
            channel = await _get_channel()
            logger.info("RabbitMQ 连接成功！")

            # 绑定消费者
            dispatch_queue = await channel.get_queue(QUEUE_DISPATCH)
            timeout_queue = await channel.get_queue(QUEUE_DISPATCH_TIMEOUT)

            await dispatch_queue.consume(handle_dispatch)
            await timeout_queue.consume(handle_timeout)

            logger.info("========== RabbitMQ 派单消费者已启动，等待消息... ==========")

            # 保持消费者运行（通过 asyncio.Event 阻塞）
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                logger.info("RabbitMQ 消费者收到取消信号")
                raise

        except asyncio.CancelledError:
            logger.info("派单消费者任务被取消")
            raise
        except Exception as e:
            delay = min(base_delay * (2 ** min(retry_count, 5)), max_delay)
            logger.error(f"RabbitMQ 消费者出错（{delay}s后重试）: {e}", exc_info=True)
            await asyncio.sleep(delay)


async def _start_es_sync_consumer():
    """启动 ES 同步消费者（后台常驻任务，指数退避重试 + DLQ 死信）"""
    import aio_pika
    import json as json_mod
    from app.services.mq.rabbitmq_service import (
        EXCHANGE_NAME, DLX_EXCHANGE, QUEUE_ES_SYNC, QUEUE_ES_SYNC_DELAY,
        _get_channel,
    )
    from app.services.es.search_service import sync_ticket_to_es
    from app.config.elasticsearch_client import get_es_client
    from app.config.mysql import get_async_session_factory
    from app.models.mysql.ticket import Ticket
    from sqlalchemy import select

    # 等待基础设施就绪
    await asyncio.sleep(3)

    # 指数退避重连
    max_retries = 5
    base_delay = 3
    channel = None
    for attempt in range(max_retries):
        try:
            channel = await _get_channel()
            break
        except Exception as e:
            delay = base_delay * (2 ** attempt)
            logger.warning(f"ES Sync 消费者 RabbitMQ 连接失败（第{attempt+1}/{max_retries}次，{delay}s后重试）: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
            else:
                logger.error("ES Sync 消费者启动失败，放弃")
                return

    max_retry = settings.ES_SYNC_MAX_RETRIES
    base_backoff = settings.ES_SYNC_BASE_DELAY_SEC
    max_backoff = settings.ES_SYNC_MAX_DELAY_SEC

    async def handle_es_sync(message: aio_pika.IncomingMessage):
        ticket_id = None
        try:
            body = json_mod.loads(message.body.decode())
            ticket_id = body.get("ticket_id")

            # 从 MySQL 加载完整工单（解决部分字段覆盖问题）
            session_factory = get_async_session_factory()
            async with session_factory() as db:
                result = await db.execute(
                    select(Ticket).where(Ticket.ticket_id == ticket_id)
                )
                ticket = result.scalar_one_or_none()

            if not ticket:
                logger.error(f"ES sync: ticket {ticket_id} not found in MySQL, discarding")
                await message.ack()
                return

            # 构建完整 ES 文档
            doc = {
                "ticket_id": ticket.ticket_id,
                "user_id": ticket.user_id,
                "facility_type": ticket.facility_type,
                "status": ticket.status,
                "description": ticket.description or "",
                "address": ticket.address or "",
                "district": ticket.district or "",
                "emergency_level": ticket.emergency_level or 0,
                "ai_category": ticket.ai_category,
                "assigned_worker_id": ticket.assigned_worker_id,
                "location": {"lat": ticket.location_lat, "lon": ticket.location_lng},
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
            }

            es = get_es_client()
            if not es:
                raise RuntimeError("ES client not available")

            await sync_ticket_to_es(es, doc)
            await message.ack()
            logger.info(f"ES synced: {ticket_id} status={ticket.status}")

        except Exception as e:
            retry_count = 0
            if message.headers:
                rc = message.headers.get("x-retry-count", 0)
                if isinstance(rc, (bytes, bytearray)):
                    retry_count = int(rc)
                else:
                    retry_count = int(rc) if rc else 0

            logger.warning(
                f"ES sync failed for {ticket_id} (retry {retry_count}/{max_retry}): {e}"
            )

            if retry_count >= max_retry:
                # 重试耗尽 → 路由到 DLQ
                try:
                    dlq_exchange = await channel.get_exchange(DLX_EXCHANGE)
                    await dlq_exchange.publish(
                        aio_pika.Message(
                            body=message.body,
                            content_type="application/json",
                            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                            headers={"x-final-failure": str(e)[:500]},
                        ),
                        routing_key=QUEUE_ES_SYNC,
                    )
                    logger.error(f"ES sync exhausted retries for {ticket_id}, sent to DLQ")
                except Exception as dlq_err:
                    logger.critical(f"Failed to route {ticket_id} to DLQ: {dlq_err}")
                await message.ack()
            else:
                # 发布到延迟队列（指数退避）
                delay_sec = min(base_backoff * (2 ** retry_count), max_backoff)
                try:
                    retry_msg = aio_pika.Message(
                        body=message.body,
                        content_type="application/json",
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                        headers={"x-retry-count": retry_count + 1},
                        expiration=str(int(delay_sec * 1000)),  # RabbitMQ expects per-message TTL as a millisecond string.
                    )
                    exchange = await channel.get_exchange(EXCHANGE_NAME)
                    await exchange.publish(retry_msg, routing_key=QUEUE_ES_SYNC_DELAY)
                except Exception as pub_err:
                    logger.error(f"Failed to republish {ticket_id} to delay queue: {pub_err}")
                await message.ack()  # ack 原消息；延迟消息会 DLX 回到 es_sync

    queue = await channel.get_queue(QUEUE_ES_SYNC)
    await queue.consume(handle_es_sync)
    logger.info("ES Sync 消费者已启动（重试策略: %s/%ss/%ss max）", max_retry, base_backoff, max_backoff)

    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logger.info("ES Sync 消费者收到取消信号")
        raise


async def _start_auto_close_scheduler():
    """启动自动完结工单调度器（每天凌晨3点执行）"""
    from app.services.worker.repair_service import auto_close_expired_tickets
    from app.config.mysql import get_async_session_factory

    logger.info("自动完结工单调度器已启动")

    try:
        while True:
            # 计算距离下一个凌晨3点的时间
            now = datetime.now()
            next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)
            if now >= next_run:
                next_run += timedelta(days=1)
            wait_seconds = (next_run - now).total_seconds()

            logger.info(f"下次自动完结工单时间: {next_run}, 等待 {wait_seconds:.1f}s")

            # 等待到下一个执行时间
            await asyncio.sleep(wait_seconds)

            # 执行自动完结
            try:
                session_factory = get_async_session_factory()
                async with session_factory() as db:
                    closed_count = await auto_close_expired_tickets(db)
                    if closed_count > 0:
                        logger.info(f"自动完结工单完成，共关闭 {closed_count} 个工单")
                    else:
                        logger.info("自动完结工单完成，无需要关闭的工单")
            except Exception as e:
                logger.error(f"自动完结工单执行失败: {e}")

    except asyncio.CancelledError:
        logger.info("自动完结工单调度器收到取消信号")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化所有数据源连接，关闭时优雅释放"""
    # ---- 启动阶段 ----
    print("=" * 60)
    print("[DEBUG] lifespan 开始执行")
    logger.info("=" * 60)
    logger.info("开始初始化 MySQL...")
    await init_mysql()
    logger.info("开始初始化 Redis...")
    await init_redis()
    logger.info("开始初始化 MongoDB...")
    await init_mongodb()
    logger.info("开始初始化 Elasticsearch...")
    await init_es()

    logger.info("=" * 60)
    logger.info("启动 RabbitMQ 派单消费者（后台任务）...")
    print("[DEBUG] 准备创建派单消费者任务")
    # 启动 RabbitMQ 派单消费者（后台任务）
    consumer_task = asyncio.create_task(_start_dispatch_consumer(), name="dispatch-consumer")
    _background_tasks.append(consumer_task)
    logger.info(f"派单消费者任务已创建: {consumer_task}")
    print(f"[DEBUG] 派单消费者任务已创建: {consumer_task}")

    logger.info("启动 ES 同步消费者（后台任务）...")
    # 启动 ES 同步消费者（后台任务）
    es_sync_task = asyncio.create_task(_start_es_sync_consumer(), name="es-sync-consumer")
    _background_tasks.append(es_sync_task)

    logger.info("启动自动完结工单调度器（后台任务）...")
    # 启动自动完结工单调度器（后台任务）
    auto_close_task = asyncio.create_task(_start_auto_close_scheduler(), name="auto-close-scheduler")
    _background_tasks.append(auto_close_task)

    logger.info("=" * 60)
    logger.info("City Repair System v3.0 启动完成")
    logger.info("=" * 60)
    print("[DEBUG] lifespan 启动阶段完成")
    print("=" * 60)

    yield

    # ---- 关闭阶段 ----
    # 取消后台任务
    for task in _background_tasks:
        task.cancel()
    for task in _background_tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass

    await close_mysql()
    await close_redis()
    await close_mongodb()
    await close_es()
    logger.info("City Repair System 已关闭")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="城市公共设施智能报修与派单系统 — 四库分层存储架构",
    lifespan=lifespan,
)

# CORS 跨域（三端前端域名）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 自定义中间件
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)

# 注册异常处理器
register_exception_handlers(app)

# 注册 API 路由（/api/v1/citizen, /api/v1/worker, /api/v1/admin）
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health_check():
    """健康检查接口，供 Docker / K8s 探活"""
    return {"status": "ok", "version": settings.APP_VERSION}

