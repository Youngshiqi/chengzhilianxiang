# ============================================================
# 城市公共设施智能报修与派单系统 - Redis 客户端管理
# 作用：管理四个 Redis 连接实例（缓存/Geo/锁/计数器），各司其职；
#       - DB0: 工单状态缓存、维修员档案缓存、热配置
#       - DB1: Geo 空间坐标（维修员实时位置、Geo半径查询）
#       - DB2: 分布式锁（派单锁定、并发控制）
#       - DB3: 实时计数器（今日工单统计、积分累加、日单计数）
# ============================================================

import redis.asyncio as aioredis

from app.config.settings import settings

# 四个 Redis 实例，按职责分库隔离
redis_cache: aioredis.Redis = None      # DB0 - 热点缓存
redis_geo: aioredis.Redis = None        # DB1 - Geo 空间数据
redis_lock: aioredis.Redis = None       # DB2 - 分布式锁
redis_counter: aioredis.Redis = None    # DB3 - 计数器


async def init_redis():
    """应用启动时：创建四个 Redis 连接池"""
    global redis_cache, redis_geo, redis_lock, redis_counter

    base_config = {
        "host": settings.REDIS_HOST,
        "port": settings.REDIS_PORT,
        "password": settings.REDIS_PASSWORD or None,
        "decode_responses": True,
    }

    redis_cache = aioredis.Redis(db=settings.REDIS_DB_CACHE, **base_config)
    redis_geo = aioredis.Redis(db=settings.REDIS_DB_GEO, **base_config)
    redis_lock = aioredis.Redis(db=settings.REDIS_DB_LOCK, **base_config)
    redis_counter = aioredis.Redis(db=settings.REDIS_DB_COUNTER, **base_config)


async def close_redis():
    """应用关闭时：释放所有 Redis 连接"""
    for client in [redis_cache, redis_geo, redis_lock, redis_counter]:
        if client:
            await client.close()


def get_redis_cache() -> aioredis.Redis:
    """依赖注入：获取缓存 Redis"""
    return redis_cache


def get_redis_geo() -> aioredis.Redis:
    """依赖注入：获取 Geo Redis"""
    return redis_geo


def get_redis_lock() -> aioredis.Redis:
    """依赖注入：获取锁 Redis"""
    return redis_lock


def get_redis_counter() -> aioredis.Redis:
    """依赖注入：获取计数器 Redis"""
    return redis_counter
