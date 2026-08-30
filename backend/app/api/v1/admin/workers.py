# ============================================================
# 城市公共设施智能报修与派单系统 - 管理后台人员管理 API
# 作用：CRUD 维修员档案、技能标签配置、排班管理、在岗状态管控、角色权限分配；
#       变更后使 Redis worker:{id}:profile 缓存失效，下次读取重建
# ============================================================

import json
import random
import string
from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.config.mysql import get_db
from app.config.redis_client import get_redis_cache, get_redis_counter, get_redis_geo
from app.models.mysql.worker import Worker
from app.models.mysql.user import User
from app.schemas.common import APIResponse
from app.core.security import get_current_user, hash_password
from app.core.exceptions import BadRequestException

router = APIRouter()


@router.get("/workers/skills", response_model=APIResponse)
async def list_worker_skills(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有维修员真实存在的技能标签（从 workers 表 skills JSON 字段聚合去重）"""
    result = await db.execute(select(Worker.skills))
    rows = result.scalars().all()

    skill_set = set()
    for row in rows:
        if not row:
            continue
        if isinstance(row, list):
            skill_set.update(s for s in row if isinstance(s, str))
        elif isinstance(row, str):
            try:
                parsed = json.loads(row)
                if isinstance(parsed, list):
                    skill_set.update(s for s in parsed if isinstance(s, str))
            except json.JSONDecodeError:
                pass

    return APIResponse(data={"skills": sorted(skill_set)}).model_dump()


@router.get("/workers", response_model=APIResponse)
async def list_workers(
    page: int = 1,
    page_size: int = 20,
    district: str = "",
    name: str = "",
    skills: str = "",
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """维修员列表查询，支持按片区/姓名/技能筛选，追加 Redis 在线状态和今日接单数"""
    query = select(Worker)
    count_query = select(func.count(Worker.worker_id))
    if district:
        query = query.where(Worker.district == district)
        count_query = count_query.where(Worker.district == district)
    if name:
        query = query.where(Worker.name.like(f"%{name}%"))
        count_query = count_query.where(Worker.name.like(f"%{name}%"))
    if skills:
        # skills 可能存储为 JSON 数组 ["电路维修","路灯"] 或 JSON 字符串 "[\"电路维修\",\"路灯\"]"
        # JSON_SEARCH 递归搜索所有字符串值，两种格式均能匹配
        query = query.where(func.json_search(Worker.skills, "one", skills).is_not(None))
        count_query = count_query.where(func.json_search(Worker.skills, "one", skills).is_not(None))
    query = query.limit(page_size).offset((page - 1) * page_size)

    result = await db.execute(query)
    workers = result.scalars().all()

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Redis 在线状态、今日接单数、实时 Geo 位置
    r_cache = get_redis_cache()
    r_counter = get_redis_counter()
    r_geo = get_redis_geo()
    online_set = await r_cache.smembers("workers:online") or set()

    # 批量取 Geo 坐标
    worker_ids = [w.worker_id for w in workers]
    geo_positions = {}
    if worker_ids:
        positions = await r_geo.geopos("workers:geo", *worker_ids)
        for wid, pos in zip(worker_ids, positions or []):
            if pos:
                geo_positions[wid] = {"lng": float(pos[0]), "lat": float(pos[1])}

    items = []
    for w in workers:
        wid = w.worker_id
        today = await r_counter.get(f"worker:{wid}:daily_order")
        items.append({
            "worker_id": wid,
            "name": w.name,
            "skills": w.skills if isinstance(w.skills, list) else (w.skills or []),
            "district": w.district,
            "star_rating": w.star_rating,
            "max_daily_orders": w.max_daily_orders,
            "night_duty": w.night_duty,
            "is_active": w.is_active,
            "today_orders": int(today) if today else 0,
            "online": wid in online_set if isinstance(online_set, set) else False,
            "location": geo_positions.get(wid),
        })

    return APIResponse(data={
        "items": items,
        "total": total,
    }).model_dump()


@router.put("/workers/{worker_id}", response_model=APIResponse)
async def update_worker(
    worker_id: str,
    skills: list = Body(None),
    max_daily_orders: int = Body(None),
    night_duty: bool = Body(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    更新维修员档案：
    - 写 MySQL workers 表
    - 删除 Redis worker:{id}:profile 缓存，下次读取重建
    """
    result = await db.execute(select(Worker).where(Worker.worker_id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("维修员不存在")

    if skills is not None:
        worker.skills = skills
    if max_daily_orders is not None:
        worker.max_daily_orders = max_daily_orders
    if night_duty is not None:
        worker.night_duty = night_duty

    # 提交到 MySQL
    await db.commit()

    # 使 Redis 缓存失效，下次读取重建
    redis = get_redis_cache()
    await redis.delete(f"worker:{worker_id}:profile")

    return APIResponse(msg="更新成功").model_dump()


def _generate_random_password(length: int = 8) -> str:
    """生成随机初始密码：大小写字母 + 数字"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


async def _generate_next_worker_id(db: AsyncSession) -> str:
    """生成下一个维修员ID：W0001, W0002..."""
    # 查询当前最大的worker_id
    result = await db.execute(
        select(Worker.worker_id)
        .where(Worker.worker_id.like("W%"))
        .order_by(Worker.worker_id.desc())
        .limit(1)
    )
    last_id = result.scalar_one_or_none()

    if not last_id:
        return "W0001"

    # 提取数字部分并加1
    try:
        num = int(last_id[1:])
        return f"W{num + 1:04d}"
    except (ValueError, IndexError):
        return "W0001"


@router.post("/workers", response_model=APIResponse)
async def create_worker(
    username: str = Body(..., embed=True),
    name: str = Body(..., embed=True),
    phone: str = Body(..., embed=True),
    district: str = Body(..., embed=True),
    skills: list = Body(default_factory=list, embed=True),
    max_daily_orders: int = Body(20, embed=True),
    night_duty: bool = Body(False, embed=True),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    创建新维修员：
    1. 生成工号 W000X
    2. 生成随机初始密码
    3. 事务：创建 users 记录 + 创建 workers 记录
    4. 返回工号和初始密码
    """
    # 检查 username 是否已存在
    existing_user = await db.execute(select(User).where(User.username == username))
    if existing_user.scalar_one_or_none():
        raise BadRequestException("登录用户名已存在")

    # 生成工号和初始密码
    worker_id = await _generate_next_worker_id(db)
    raw_password = _generate_random_password()
    password_hash = hash_password(raw_password)

    # 事务：同时创建 user 和 worker
    try:
        # 创建 users 记录
        user = User(
            user_id=worker_id,
            username=username,
            password_hash=password_hash,
            phone=phone,  # 注意：实际项目中手机号应该脱敏
            role="worker",
            nickname=name,
            district=district,
        )
        db.add(user)

        # 创建 workers 记录
        worker = Worker(
            worker_id=worker_id,
            name=name,
            skills=skills or [],
            district=district,
            max_daily_orders=max_daily_orders,
            night_duty=night_duty,
        )
        db.add(worker)

        await db.commit()

    except Exception as e:
        await db.rollback()
        raise BadRequestException(f"创建失败: {str(e)}")

    return APIResponse(
        msg="创建成功",
        data={
            "worker_id": worker_id,
            "username": username,
            "password": raw_password,
        }
    ).model_dump()
