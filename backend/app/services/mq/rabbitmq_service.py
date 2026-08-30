# ============================================================
# 城市公共设施智能报修与派单系统 - RabbitMQ 消息队列服务
# 作用：管理 RabbitMQ 连接、交换器、队列的声明与绑定；
#       - publish_dispatch_task: 工单创建后发布到派单队列
#       - publish_timeout_check: 派单后发布延迟消息（10分钟超时检查）
#       - publish_review_task: 差评触发复核队列
#       - publish_es_sync: ES 同步消息（可靠异步投递，消费者全量加载 MySQL）
#       - consume_dispatch: 消费派单消息，执行智能派单逻辑
# ============================================================

import asyncio
import json
import logging
import aio_pika
from typing import Callable, Optional

from app.config.settings import settings

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# 交换器 & 队列名称
# ═══════════════════════════════════════════════════════════

EXCHANGE_NAME = "city_repair.direct"
DLX_EXCHANGE = "city_repair.dlx"

QUEUE_DISPATCH = "dispatch"
QUEUE_DISPATCH_TIMEOUT = "dispatch_timeout"
QUEUE_DISPATCH_TIMEOUT_DELAY = "dispatch_timeout.delay"
QUEUE_REVIEW = "review_queue"
QUEUE_ES_SYNC = "es_sync"
QUEUE_ES_SYNC_DLQ = "es_sync.dlq"
QUEUE_ES_SYNC_DELAY = "es_sync.delay"

_connection: Optional[aio_pika.RobustConnection] = None
_channel: Optional[aio_pika.RobustChannel] = None


async def _get_channel() -> aio_pika.Channel:
    """惰性获取 RabbitMQ Channel（首次使用时建立连接并声明拓扑）"""
    global _connection, _channel
    if _channel is None or _channel.is_closed:
        # 使用普通 connect 代替 connect_robust，避免无限重连
        try:
            _connection = await asyncio.wait_for(
                aio_pika.connect(
                    f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}"
                    f"@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/{settings.RABBITMQ_VHOST}"
                ),
                timeout=5
            )
            _channel = await _connection.channel()
        except Exception as e:
            logger.error(f"RabbitMQ 连接失败: {e}")
            raise

        # ── 声明交换器 ──
        # 业务主交换器，所有正常消息都路由到该交换器
        exchange = await _channel.declare_exchange(
            EXCHANGE_NAME, aio_pika.ExchangeType.DIRECT, durable=True
        )
        # 死信交换器，处理失败消息
        dlx_exchange = await _channel.declare_exchange(
            DLX_EXCHANGE, aio_pika.ExchangeType.DIRECT, durable=True
        )

        # ── 声明已有队列并绑定 ──
        for queue_name in [QUEUE_DISPATCH, QUEUE_DISPATCH_TIMEOUT, QUEUE_REVIEW]:
            queue = await _channel.declare_queue(queue_name, durable=True)
            await queue.bind(exchange, routing_key=queue_name)

        # ── 派单超时延迟队列（per-message TTL 过期后 DLX → dispatch_timeout） ──
        timeout_delay_queue = await _channel.declare_queue(
            QUEUE_DISPATCH_TIMEOUT_DELAY,
            durable=True,
            arguments={
                "x-dead-letter-exchange": EXCHANGE_NAME,
                "x-dead-letter-routing-key": QUEUE_DISPATCH_TIMEOUT,
            },
        )
        await timeout_delay_queue.bind(exchange, routing_key=QUEUE_DISPATCH_TIMEOUT_DELAY)

        # ── ES Sync 队列（DLX → city_repair.dlx） ──
        es_sync_queue = await _channel.declare_queue(
            QUEUE_ES_SYNC,
            durable=True,
            arguments={
                # 死信发往 city_repair.dlx
                "x-dead-letter-exchange": DLX_EXCHANGE,
                "x-dead-letter-routing-key": QUEUE_ES_SYNC,
            },
        )
        await es_sync_queue.bind(exchange, routing_key=QUEUE_ES_SYNC)

        # ── ES Sync 延迟队列（per-message TTL 过期后 DLX 回到 es_sync） ──
        es_sync_delay_queue = await _channel.declare_queue(
            QUEUE_ES_SYNC_DELAY,
            durable=True,
            arguments={
                "x-dead-letter-exchange": EXCHANGE_NAME,
                "x-dead-letter-routing-key": QUEUE_ES_SYNC,
            },
        )
        await es_sync_delay_queue.bind(exchange, routing_key=QUEUE_ES_SYNC_DELAY)

        # ── ES Sync 死信队列（重试耗尽后人工处理） ──
        es_sync_dlq_queue = await _channel.declare_queue(
            QUEUE_ES_SYNC_DLQ, durable=True
        )
        await es_sync_dlq_queue.bind(dlx_exchange, routing_key=QUEUE_ES_SYNC)

    return _channel


# ═══════════════════════════════════════════════════════════
# 发布函数
# ═══════════════════════════════════════════════════════════

async def publish_dispatch_task(ticket_id: str):
    """
    发布派单任务到 dispatch 队列。
    工单创建成功后调用，异步触发智能派单流程。
    """
    channel = await _get_channel()
    exchange = await channel.get_exchange(EXCHANGE_NAME)
    message = aio_pika.Message(
        body=json.dumps({"ticket_id": ticket_id, "action": "dispatch"}).encode(),
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )
    await exchange.publish(message, routing_key=QUEUE_DISPATCH)


async def publish_timeout_check(ticket_id: str, delay_minutes: int = 10):
    """
    发布超时检查消息（per-message TTL + DLX 延迟队列）。
    消息先进入 dispatch_timeout.delay，TTL 过期后 DLX 路由到 dispatch_timeout 被消费。
    delay_minutes 分钟后仍无人接单 → 自动升级强制指派。
    """
    channel = await _get_channel()
    exchange = await channel.get_exchange(EXCHANGE_NAME)
    delay_ms = delay_minutes * 60 * 1000
    message = aio_pika.Message(
        body=json.dumps({"ticket_id": ticket_id, "action": "timeout_check"}).encode(),
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        expiration=str(delay_ms),  # RabbitMQ expects per-message TTL as a millisecond string.
    )
    await exchange.publish(message, routing_key=QUEUE_DISPATCH_TIMEOUT_DELAY)
    logger.info(f"========== 已发布工单 {ticket_id} 的超时检查消息，延迟 {delay_minutes} 分钟 ==========")


async def publish_review_task(ticket_id: str, eval_id: str):
    """
    发布差评复核任务到 review_queue。
    市民评价2星及以下 → 延迟队列 → 管理员复核。
    """
    channel = await _get_channel()
    exchange = await channel.get_exchange(EXCHANGE_NAME)
    message = aio_pika.Message(
        body=json.dumps({"ticket_id": ticket_id, "eval_id": eval_id, "action": "review"}).encode(),
        content_type="application/json",
    )
    await exchange.publish(message, routing_key=QUEUE_REVIEW)


async def publish_es_sync(ticket_id: str):
    """
    发布 ES 同步请求到 es_sync 队列。
    调用方 fire-and-forget；消费者负责全量加载 MySQL → ES 索引 + 重试 + DLQ。

    参数:
      ticket_id: 需要同步到 ES 的工单 ID
    """
    # 1. 获取cannel
    channel = await _get_channel()
    # 2. 获取交换器
    exchange = await channel.get_exchange(EXCHANGE_NAME)
    # 消息体
    message = aio_pika.Message(
        body=json.dumps({"ticket_id": ticket_id}).encode(),
        content_type="application/json",
        # 持久化，重启不丢
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        # 重试计数器
        headers={"x-retry-count": 0},
    )
    # 发布到 es_sync 队列
    await exchange.publish(message, routing_key=QUEUE_ES_SYNC)


# ═══════════════════════════════════════════════════════════
# 消费函数
# ═══════════════════════════════════════════════════════════

async def consume_dispatch(callback: Callable):
    """
    消费派单队列消息，异步执行 AI 派单逻辑。
    callback 参数为 async 函数，接收 ticket_id 字符串。
    """
    channel = await _get_channel()
    queue = await channel.get_queue(QUEUE_DISPATCH)

    async def on_message(message: aio_pika.IncomingMessage):
        try:
            body = json.loads(message.body.decode())
            await callback(body["ticket_id"])
            await message.ack()
        except Exception:
            logger.exception("派单消费异常，消息重新入队")
            await message.nack(requeue=True)

    await queue.consume(on_message)

