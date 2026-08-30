# ============================================================
# 城市公共设施智能报修与派单系统 - 安全认证模块
# 作用：JWT Token 生成与校验、密码哈希、RBAC 权限验证；
#       create_access_token: 登录时签发 Token；
#       get_current_user: 依赖注入，从请求头解析用户身份
# ============================================================

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Header, Request
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config.settings import settings
from app.schemas.common import ErrorCode
from app.utils.timezone import now_beijing

# bcrypt 密码哈希上下文
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """对明文密码进行 bcrypt 哈希"""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码与哈希值是否匹配"""
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str, role: str) -> str:
    """生成 JWT Access Token"""
    expire = now_beijing() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
        "iat": now_beijing(),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """解析 JWT Token，返回 payload 或 None"""
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


async def get_current_user(request: Request = None, authorization: str = Header(None)) -> dict:
    """FastAPI 依赖注入：优先从 AuthMiddleware 注入的 request.state 读取用户身份（避免重复解码 JWT）。
    兼容直接调用场景：若 state 无数据则降级自行解析 Token。"""
    # 优先从中间件注入的 request.state 读取（避免重复 JWT 解码）
    if request and hasattr(request.state, "user_id") and hasattr(request.state, "role"):
        return {"user_id": request.state.user_id, "role": request.state.role}

    # 降级：自行解析 Authorization Header
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": ErrorCode.UNAUTHORIZED, "msg": "鉴权失效"})

    token = authorization[7:]
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail={"code": ErrorCode.UNAUTHORIZED, "msg": "Token无效或已过期"})

    return {"user_id": payload["sub"], "role": payload["role"]}


def require_role(*roles: str):
    """RBAC 权限校验装饰器工厂：仅允许指定角色访问"""
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in roles:
            raise HTTPException(status_code=403, detail={"code": ErrorCode.FORBIDDEN, "msg": "权限不足"})
        return current_user

    return role_checker
