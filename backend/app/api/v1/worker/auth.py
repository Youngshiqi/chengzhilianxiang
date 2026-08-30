# ============================================================
# 城市公共设施智能报修与派单系统 - 维修员端认证 API
# 作用：POST /api/v1/worker/auth/login — 维修员账号密码登录，返回 JWT Token
#       登录成功后将维修员加入 Redis workers:online 在岗集合
#       PUT /api/v1/worker/auth/change-password — 修改密码
# ============================================================

from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config.mysql import get_db
from app.config.redis_client import get_redis_cache, get_redis_geo
from app.models.mysql.user import User
from app.schemas.common import APIResponse
from app.schemas.citizen import LoginResponse
from app.core.security import create_access_token, verify_password, hash_password, get_current_user
from app.core.exceptions import BadRequestException

router = APIRouter()


@router.post("/auth/login", response_model=APIResponse[LoginResponse])
async def worker_login(
    worker_id: str = Body(...),
    password: str = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """
    维修员登录：
    - 校验账号有效性
    - 加入 Redis workers:online Set
    - 初始化 Geo 位置
    """
    result = await db.execute(
        select(User).where(User.user_id == worker_id, User.role == "worker")
    )
    user = result.scalar_one_or_none()
    if not user:
        raise BadRequestException("账号不存在或非维修员角色")

    if not user.password_hash:
        raise BadRequestException("该账号未设置密码，请联系管理员初始化")

    if not verify_password(password, user.password_hash):
        raise BadRequestException("账号或密码错误")

    token = create_access_token(user.user_id, user.role)

    redis_cache = get_redis_cache()
    await redis_cache.sadd("workers:online", worker_id)

    redis_geo = get_redis_geo()
    await redis_geo.geoadd("workers:geo", (112.9388, 28.2282, worker_id))

    return APIResponse(
        msg="登录成功",
        data=LoginResponse(token=token, user_id=user.user_id, role=user.role),
    ).model_dump()


@router.put("/auth/change-password", response_model=APIResponse)
async def change_password(
    old_password: str = Body(...),
    new_password: str = Body(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    修改密码：
    - 验证旧密码
    - 更新为新密码
    """
    user_id = current_user["user_id"]

    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise BadRequestException("账号不存在")

    if not verify_password(old_password, user.password_hash):
        raise BadRequestException("原密码错误")

    if len(new_password) < 6:
        raise BadRequestException("新密码长度至少6位")

    user.password_hash = hash_password(new_password)
    await db.commit()

    return APIResponse(msg="密码修改成功").model_dump()
