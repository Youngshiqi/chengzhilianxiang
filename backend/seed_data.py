# ============================================================
# 城市公共设施智能报修与派单系统 - 种子数据生成脚本
# 作用：在首次部署 / 重置环境后，一键填充模拟数据：
#       1. MySQL: 1000 个设施点位 + 20 名维修员 + 测试用户
#       2. Redis: Geo 坐标入库 + 维修员档案缓存 + 在线状态
#       3. MongoDB: 空 Collection 索引预热（索引已在 init_mongodb 创建）
#       4. ES: 设施索引批量导入
#
# 运行方式：
#   cd backend && python seed_data.py
#   cd backend && python seed_data.py --reset   # 清空旧数据后重新生成
# ============================================================

import argparse
import asyncio
import datetime
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import select
from app.config.settings import settings
from app.config.mysql import engine, async_session_factory, Base
from app.config.redis_client import (
    init_redis,
    get_redis_cache,
    get_redis_geo,
    get_redis_lock,
    get_redis_counter,
)
from app.config.mongodb import init_mongodb
from app.config.elasticsearch_client import init_es, get_es_client
from app.models.mysql.user import User
from app.models.mysql.facility import Facility
from app.models.mysql.worker import Worker
from app.core.security import create_access_token, hash_password
from app.utils.timezone import now_beijing

# ---- 长沙市数据池 ----
# (区名, 中心纬度, 中心经度, 随机偏移半径/度)
# 偏移半径越大，数据越分散；中心城区 0.05-0.08，外围区县 0.10-0.14
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

# 长沙市中心兜底坐标（用于 Redis Geo fallback）
DEFAULT_CENTER_LAT = 28.2282
DEFAULT_CENTER_LNG = 112.9388

FACILITY_TYPES = [
    "路灯", "井盖", "护栏", "信号灯", "公交站牌",
    "消防栓", "公厕", "指示牌", "垃圾桶", "健身器材",
]

# 每个区 3 个真实地址与坐标，全部通过高德 geocoding API 获取
DISTRICT_SITES = {
    "芙蓉区": [
        {"address": "芙蓉区五一大道80号", "lat": 28.194439, "lng": 113.00769},
        {"address": "芙蓉区芙蓉中路一段168号", "lat": 28.2207, "lng": 112.986948},
        {"address": "芙蓉区解放西路18号", "lat": 28.191997, "lng": 112.974197},
    ],
    "天心区": [
        {"address": "天心区韶山南路123号", "lat": 28.143245, "lng": 112.995514},
        {"address": "天心区书院南路306号", "lat": 28.150078, "lng": 112.973137},
        {"address": "天心区劳动西路289号", "lat": 28.175935, "lng": 112.980662},
    ],
    "岳麓区": [
        {"address": "岳麓区岳麓大道142号", "lat": 28.227054, "lng": 112.94741},
        {"address": "岳麓区麓山南路932号", "lat": 28.168544, "lng": 112.93061},
        {"address": "岳麓区枫林三路1099号", "lat": 28.19877, "lng": 112.861673},
    ],
    "开福区": [
        {"address": "开福区三一大道66号", "lat": 28.228936, "lng": 112.991962},
        {"address": "开福区芙蓉北路二段200号", "lat": 28.229685, "lng": 112.988067},
        {"address": "开福区湘江北路1500号", "lat": 28.238718, "lng": 112.978925},
    ],
    "雨花区": [
        {"address": "雨花区长沙大道598号", "lat": 28.167394, "lng": 113.0461},
        {"address": "雨花区韶山南路633号", "lat": 28.129291, "lng": 113.004837},
        {"address": "雨花区香樟路819号", "lat": 28.137697, "lng": 113.032703},
    ],
    "望城区": [
        {"address": "望城区雷锋大道999号", "lat": 28.281533, "lng": 112.875936},
        {"address": "望城区金星北路四段89号", "lat": 28.314245, "lng": 112.890015},
        {"address": "望城区望城大道100号", "lat": 28.339665, "lng": 112.828461},
    ],
    "长沙县": [
        {"address": "长沙县星沙大道188号", "lat": 28.250066, "lng": 113.08799},
        {"address": "长沙县开元中路45号", "lat": 28.246723, "lng": 113.085175},
        {"address": "长沙县板仓路200号", "lat": 28.241654, "lng": 113.078354},
    ],
    "浏阳市": [
        {"address": "浏阳市浏阳大道11号", "lat": 28.155944, "lng": 113.632985},
        {"address": "浏阳市花炮大道88号", "lat": 28.162385, "lng": 113.606397},
        {"address": "浏阳市金沙中路100号", "lat": 28.136992, "lng": 113.627456},
    ],
    "宁乡市": [
        {"address": "宁乡市金洲大道宁乡段", "lat": 28.273499, "lng": 112.556661},
        {"address": "宁乡市玉潭中路50号", "lat": 28.253184, "lng": 112.561509},
        {"address": "宁乡市一环北路20号", "lat": 28.25868, "lng": 112.543838},
    ],
}
SKILLS_POOL = [
    ["电路维修", "路灯"],
    ["管道维修", "井盖", "消防栓"],
    ["土木修补", "护栏", "指示牌"],
    ["信号灯", "电路维修"],
    ["管道维修", "公厕"],
    ["土木修补", "垃圾桶", "健身器材"],
    ["电路维修", "信号灯", "路灯"],
    ["管道维修", "井盖"],
    ["土木修补", "护栏"],
    ["综合维修"],
]

LAST_NAMES = ["张", "李", "王", "赵", "陈", "刘", "杨", "黄", "周", "吴",
              "郑", "马", "朱", "胡", "何", "罗", "高", "林", "孙", "许"]
FIRST_NAMES = ["建国", "明远", "守义", "铁柱", "志强", "伟", "磊", "涛", "军", "勇",
               "海峰", "晓明", "大伟", "永强", "文博", "鹏", "飞", "俊杰", "浩然", "子轩"]

# ---- 测试账号（市民/维修员/管理员）----
TEST_USERS = [
    # 市民
    {"user_id": "U0001", "nickname": "市民张三", "role": "citizen", "phone": "138****0001", "district": "芙蓉区", "username": "zhangsan", "password": "123456"},
    {"user_id": "U0002", "nickname": "市民李四", "role": "citizen", "phone": "138****0002", "district": "天心区", "username": "lisi",     "password": "123456"},
    {"user_id": "U0003", "nickname": "市民王五", "role": "citizen", "phone": "138****0003", "district": "岳麓区", "username": "wangwu",   "password": "123456"},
    {"user_id": "U0004", "nickname": "市民赵六", "role": "citizen", "phone": "138****0004", "district": "雨花区", "username": "zhaoliu",  "password": "123456"},
    {"user_id": "U0005", "nickname": "市民陈七", "role": "citizen", "phone": "138****0005", "district": "开福区", "username": "chenqi",   "password": "123456"},
    # 维修员（与 workers 表 W0001-W0005 对应，方便登录测试）
    {"user_id": "W0001", "nickname": "维修员张建国", "role": "worker", "phone": "139****0001", "district": "芙蓉区", "username": "worker1", "password": "123456"},
    {"user_id": "W0002", "nickname": "维修员李明远", "role": "worker", "phone": "139****0002", "district": "天心区", "username": "worker2", "password": "123456"},
    {"user_id": "W0003", "nickname": "维修员王强",   "role": "worker", "phone": "139****0003", "district": "岳麓区", "username": "worker3", "password": "123456"},
    {"user_id": "W0004", "nickname": "维修员赵铁柱", "role": "worker", "phone": "139****0004", "district": "雨花区", "username": "worker4", "password": "123456"},
    {"user_id": "W0005", "nickname": "维修员陈勇",   "role": "worker", "phone": "139****0005", "district": "开福区", "username": "worker5", "password": "123456"},
    # 管理员
    {"user_id": "A0001", "nickname": "管理员", "role": "admin", "phone": "138****0000", "district": "芙蓉区", "username": "admin", "password": "admin123"},
]


def _random_location(center_lat: float, center_lng: float, offset: float = 0.02):
    """在中心点周围生成随机经纬度"""
    return (
        round(center_lat + random.uniform(-offset, offset), 6),
        round(center_lng + random.uniform(-offset, offset), 6),
    )


def parse_args():
    parser = argparse.ArgumentParser(description="城市公共设施智能报修与派单系统 - 种子数据生成")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="清空 MySQL / Redis 旧数据后重新生成（危险：会删除当前库中所有业务数据）",
    )
    return parser.parse_args()


async def reset_data():
    """清空 MySQL 全表与 Redis 分库数据"""
    print("\n[!] 正在重置数据...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("  [OK] MySQL 表已清空")

    r_cache = get_redis_cache()
    r_geo = get_redis_geo()
    r_lock = get_redis_lock()
    r_counter = get_redis_counter()
    await r_cache.flushdb()
    await r_geo.flushdb()
    await r_lock.flushdb()
    await r_counter.flushdb()
    print("  [OK] Redis 已清空")


async def seed_users():
    """创建测试用户（市民 + 维修员 + 管理员）"""
    async with async_session_factory() as session:
        for u in TEST_USERS:
            existing = await session.execute(
                select(User).where(User.user_id == u["user_id"])
            )
            if existing.scalar_one_or_none():
                continue

            user = User(
                user_id=u["user_id"],
                username=u["username"],
                password_hash=hash_password(u["password"]),
                nickname=u["nickname"],
                role=u["role"],
                phone=u["phone"],
                district=u["district"],
                is_active=True,
                created_at=now_beijing(),
            )
            session.add(user)
        await session.commit()

    print(f"[OK] 创建 {len(TEST_USERS)} 个测试用户")

    # 打印登录凭据（方便 curl/前端测试）
    print("  --- 测试账号 ---")
    for u in TEST_USERS:
        token = create_access_token(u["user_id"], u["role"])
        print(f"  {u['role']:8s} {u['username']:10s} 密码:{u['password']:10s}  Token:{token[:50]}...")


async def seed_facilities():
    """每个区生成 3 个地址/坐标一致的设施点位（共 27 个）"""
    async with async_session_factory() as session:
        # 检查是否已有数据
        existing = await session.execute(select(Facility).limit(1))
        if existing.scalar_one_or_none():
            print(f"[WARN] 设施数据已存在，跳过生成")
            return

        facilities = []
        idx = 1
        for district_name, sites in DISTRICT_SITES.items():
            for site in sites:
                facility_type = random.choice(FACILITY_TYPES)
                install_date = datetime.date.today() - datetime.timedelta(days=random.randint(365, 365 * 8))
                status = random.choices(
                    ["normal", "normal", "normal", "repairing", "scrapped"],
                    weights=[70, 15, 10, 3, 2]
                )[0]

                facilities.append(Facility(
                    facility_code=f"FC{idx:06d}",
                    type=facility_type,
                    address=site["address"],
                    district=district_name,
                    location_lng=site["lng"],
                    location_lat=site["lat"],
                    status=status,
                    total_faults=random.randint(0, 12),
                    install_date=install_date,
                ))
                idx += 1

        session.add_all(facilities)
        await session.commit()

    print(f"[OK] 生成 {len(facilities)} 个设施点位（{len(DISTRICT_SITES)} 行政区 × 3 个）")

    # ES 同步：先删除旧索引，再全量写入当前 1000 条，避免残留北京数据
    try:
        es = get_es_client()
        if es:
            prefix = settings.ES_INDEX_PREFIX
            index_name = f"{prefix}_facilities"
            if await es.indices.exists(index=index_name):
                await es.indices.delete(index=index_name)
                print(f"[OK] 已删除旧 ES 设施索引 {index_name}")
            for fc in facilities:
                await es.index(
                    index=index_name,
                    id=fc.facility_code,
                    body={
                        "facility_code": fc.facility_code,
                        "type": fc.type,
                        "address": fc.address,
                        "district": fc.district,
                        "location": {"lat": fc.location_lat, "lon": fc.location_lng},
                        "install_date": fc.install_date.isoformat() if fc.install_date else None,
                        "fault_count": fc.total_faults,
                    },
                )
            print(f"[OK] ES 设施索引同步完成（{len(facilities)} 条）")
    except Exception as e:
        print(f"[WARN] ES 同步跳过: {e}")


async def seed_workers(count: int = 20):
    """生成 20 名维修员 + Redis Geo + Profile + Online"""
    async with async_session_factory() as session:
        existing = await session.execute(select(Worker).limit(1))
        if existing.scalar_one_or_none():
            print(f"[WARN] 维修员数据已存在，跳过生成")
            return

        workers = []
        worker_districts = {}  # wid -> (lng, lat) for Redis Geo
        for i in range(1, count + 1):
            wid = f"W{i:04d}"
            district_info = random.choice(DISTRICTS)
            district_name = district_info[0]
            lat, lng = _random_location(district_info[1], district_info[2], district_info[3])
            worker_districts[wid] = (lng, lat)

            skills = random.choice(SKILLS_POOL)
            star = round(random.uniform(3.5, 5.0), 1)
            night_duty = random.choice([True, False, False])

            workers.append(Worker(
                worker_id=wid,
                name=f"{random.choice(LAST_NAMES)}{random.choice(FIRST_NAMES)}",
                skills=skills,  # 直接传 list，SQLAlchemy JSON 列自动序列化为 JSON 数组
                max_daily_orders=random.randint(15, 25),
                district=district_name,
                night_duty=night_duty,
                star_rating=star,
                total_orders=random.randint(50, 500),
                avg_response_minutes=round(random.uniform(3, 20), 1),
                is_active=True,
            ))

        session.add_all(workers)
        await session.commit()

    print(f"[OK] 生成 {count} 名维修员")

    # Redis 数据初始化
    r_cache = get_redis_cache()
    r_geo = get_redis_geo()
    r_counter = get_redis_counter()

    for w in workers:
        wid = w.worker_id
        lng, lat = worker_districts.get(wid, (DEFAULT_CENTER_LNG, DEFAULT_CENTER_LAT))

        # Geo 坐标（所有维修员都加入Geo集合）
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
        is_online = random.random() < 0.6
        if is_online:
            await r_cache.sadd("workers:online", wid)

        # 当日接单计数
        await r_counter.set(f"worker:{wid}:daily_order", random.randint(0, 15))
        await r_counter.expire(f"worker:{wid}:daily_order", 86400)

    print(f"[OK] Redis Geo/Profile/Online 初始化完成")


async def seed_auth_tokens():
    """打印各角色测试 Token 并写入文件"""
    tokens = {}
    for acct in TEST_USERS:
        tokens[acct["username"]] = create_access_token(acct["user_id"], acct["role"])

    filepath = os.path.join(os.path.dirname(__file__), "test_tokens.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("# 城市设施运维系统 - 测试账号与Token（有效期24小时）\n")
        f.write(f"# 生成时间: {now_beijing()}\n\n")
        f.write("# ---- 用户名/密码登录 ----\n")
        for acct in TEST_USERS:
            f.write(f"# {acct['role']:8s}  用户名: {acct['username']:10s}  密码: {acct['password']:10s}\n")
        f.write("\n# ---- JWT Token ----\n")
        for acct in TEST_USERS:
            f.write(f"{acct['username']} = {tokens[acct['username']]}\n")

    print(f"\n[OK] Token 已写入 {filepath}")


async def main():
    args = parse_args()

    print("=" * 60)
    print("城市公共设施智能报修与派单系统 — 种子数据生成")
    print(f"MySQL={settings.MYSQL_HOST}:{settings.MYSQL_PORT}")
    print(f"Redis={settings.REDIS_HOST}:{settings.REDIS_PORT}")
    print(f"MongoDB={settings.MONGO_HOST}:{settings.MONGO_PORT}")
    print("=" * 60)

    if args.reset:
        print("\n[!] 已启用 --reset：将先清空 MySQL / Redis 现有数据！")

    # 1. 初始化连接
    print("\n[1/5] 初始化 Redis / MongoDB / ES...")
    await init_redis()
    await init_mongodb()
    try:
        await init_es()
    except Exception as e:
        print(f"[WARN] ES 连接失败（跳过ES相关操作）: {e}")

    # 2. 如需重置，清空数据
    if args.reset:
        print("\n[2/5] 重置数据...")
        await reset_data()
    else:
        print("\n[2/5] 跳过重置（如需清空旧数据请加上 --reset）")

    # 3. 建表
    print("\n[3/5] 创建 MySQL 表结构...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[OK] 表结构就绪")

    # 4. 用户 + 维修员
    print("\n[4/5] 创建测试用户...")
    await seed_users()

    # 5. 设施
    print("\n[5/5] 生成设施点位...")
    await seed_facilities()

    # 6. 维修员 + Redis 数据
    print("\n[6/6] 生成维修员 + Redis 初始化...")
    await seed_workers(20)

    # Token
    await seed_auth_tokens()

    print("\n" + "=" * 60)
    print("种子数据生成完成！下面可以启动后端：")
    print("  cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
