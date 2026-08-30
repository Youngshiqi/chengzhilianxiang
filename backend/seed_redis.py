# ============================================================
# Redis 缓存数据补充脚本
# 作用：基于已有 MySQL workers 数据，重新填充 Redis Geo + Profile + Online
# 运行方式：cd backend && python seed_redis.py
# ============================================================
import asyncio
import json
import random
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import select
from app.config.mysql import async_session_factory
from app.config.redis_client import init_redis, get_redis_cache, get_redis_geo, get_redis_counter
from app.models.mysql.worker import Worker

# 长沙市各区中心坐标与偏移半径（与 seed_data.py 保持一致）
DISTRICTS = [
    ("芙蓉区", 28.1938, 112.9895, 0.06),
    ("天心区", 28.1125, 112.9969, 0.06),
    ("岳麓区", 28.2136, 112.9438, 0.07),
    ("开福区", 28.2565, 112.9856, 0.07),
    ("雨花区", 28.1354, 113.0416, 0.06),
    ("望城区", 28.3614, 112.8307, 0.10),
    ("长沙县", 28.2469, 113.0802, 0.10),
    ("浏阳市", 28.1639, 113.6432, 0.12),
    ("宁乡市", 28.2774, 112.5538, 0.12),
]

DEFAULT_CENTER_LAT = 28.2282
DEFAULT_CENTER_LNG = 112.9388


def _random_location(center_lat, center_lng, offset=0.02):
    return (
        round(center_lat + random.uniform(-offset, offset), 6),
        round(center_lng + random.uniform(-offset, offset), 6),
    )


async def main():
    print("=" * 50)
    print("Redis 缓存数据补充")
    print("=" * 50)

    await init_redis()

    r_cache = get_redis_cache()
    r_geo = get_redis_geo()
    r_counter = get_redis_counter()

    # 从 MySQL 读取所有维修员
    async with async_session_factory() as session:
        result = await session.execute(select(Worker))
        workers = result.scalars().all()

    print(f"读取到 {len(workers)} 名维修员")

    # 清空旧 Redis 数据
    await r_geo.delete("workers:geo")
    await r_cache.delete("workers:online")

    for w in workers:
        wid = w.worker_id

        # 根据片区生成随机坐标
        district_info = next((d for d in DISTRICTS if d[0] == w.district), None)
        if district_info:
            lat, lng = _random_location(district_info[1], district_info[2], district_info[3])
        else:
            lat, lng = _random_location(DEFAULT_CENTER_LAT, DEFAULT_CENTER_LNG, 0.08)

        # Geo 坐标
        await r_geo.geoadd("workers:geo", (lng, lat, wid))

        # 档案缓存
        await r_cache.hset(f"worker:{wid}:profile", mapping={
            "name": w.name,
            "skills": w.skills if isinstance(w.skills, str) else json.dumps(w.skills, ensure_ascii=False),
            "district": w.district,
            "star": str(w.star_rating),
            "max_daily": str(w.max_daily_orders),
            "night_duty": "1" if w.night_duty else "0",
            "avg_response_min": str(w.avg_response_minutes),
        })
        await r_cache.expire(f"worker:{wid}:profile", 86400 * 30)

        # 在线状态（60%概率在线）
        if random.random() < 0.6:
            await r_cache.sadd("workers:online", wid)

        # 当日计数
        await r_counter.set(f"worker:{wid}:daily_order", random.randint(0, 15))
        await r_counter.expire(f"worker:{wid}:daily_order", 86400)

    # 验证
    geo_count = await r_geo.zcard("workers:geo")
    online_count = await r_cache.scard("workers:online")
    print(f"[OK] Redis Geo: {geo_count} 人")
    print(f"[OK] Redis Online: {online_count} 人")
    print(f"[OK] Redis Profile: {len(workers)} 条")
    print("Redis 数据补充完成！")


if __name__ == "__main__":
    asyncio.run(main())
