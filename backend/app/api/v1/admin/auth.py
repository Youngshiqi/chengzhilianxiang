# ============================================================
# 城市公共设施智能报修与派单系统 - 管理后台认证 API
# 作用：POST /api/v1/admin/auth/login — 管理员账号密码登录，返回 JWT Token
# ============================================================

from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config.mysql import get_db
from app.models.mysql.user import User
from app.schemas.common import APIResponse
from app.schemas.citizen import LoginResponse
from app.core.security import create_access_token, verify_password
from app.core.exceptions import BadRequestException

router = APIRouter()


@router.post("/auth/login", response_model=APIResponse[LoginResponse])
async def admin_login(
    username: str = Body(...),
    password: str = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """管理员登录。"""
    result = await db.execute(
        select(User).where(User.username == username, User.role == "admin")
    )
    user = result.scalar_one_or_none()
    if not user:
        raise BadRequestException("账号不存在或非管理员角色")

    if not user.password_hash:
        raise BadRequestException("管理员账号未初始化密码")

    if not verify_password(password, user.password_hash):
        raise BadRequestException("账号或密码错误")

    token = create_access_token(user.user_id, user.role)
    return APIResponse(
        msg="登录成功",
        data=LoginResponse(token=token, user_id=user.user_id, role=user.role),
    ).model_dump()

