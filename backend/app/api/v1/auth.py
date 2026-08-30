# ============================================================
# 城市公共设施智能报修与派单系统 - 统一认证 API
# 作用：POST /api/v1/auth/login — 用户名+密码登录，返回 JWT Token；
#       POST /api/v1/auth/send-sms-code — 发送短信验证码（云端生成）
#       POST /api/v1/auth/sms-login — 短信验证码登录（云端校验）
#       POST /api/v1/auth/register — 用户注册（云端校验）
# ============================================================

import uuid
import asyncio
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config.mysql import get_db
from app.config.redis_client import get_redis_cache, get_redis_geo
from app.models.mysql.user import User
from app.schemas.citizen import (
    UsernameLoginRequest,
    RegisterRequest,
    SendSmsCodeRequest,
    SmsLoginRequest,
    LoginResponse,
)
from app.schemas.common import APIResponse
from app.core.security import create_access_token, verify_password, hash_password
from app.core.exceptions import BadRequestException

logger = logging.getLogger(__name__)

router = APIRouter()

# 云端校验模式：无需本地 Redis 存储验证码
# 保留 API 级频控 key（防止恶意刷阿里云接口）
SMS_API_LIMIT_PREFIX = "sms:api_limit:"
SMS_API_LIMIT_TTL = 60


async def _find_user_by_phone(db: AsyncSession, phone_number: str):
    result = await db.execute(select(User).where(User.phone_normalized == phone_number))
    return result.scalar_one_or_none()


@router.post("/login", response_model=APIResponse[LoginResponse])
async def username_login(req: UsernameLoginRequest, db: AsyncSession = Depends(get_db)):
    """用户名+密码统一登录入口。"""
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    if user is None:
        raise BadRequestException("用户名或密码错误")

    if user.password_hash is None:
        raise BadRequestException("该账号未设置密码")

    if not verify_password(req.password, user.password_hash):
        raise BadRequestException("用户名或密码错误")

    if not user.is_active:
        raise BadRequestException("账号已被禁用")

    token = create_access_token(user.user_id, user.role)

    if user.role == "worker":
        redis_cache = get_redis_cache()
        await redis_cache.sadd("workers:online", user.user_id)

        from app.services.map.amap_service import ip_location

        lng, lat = 112.9388, 28.2282
        source = "default"

        if req.lng is not None and req.lat is not None:
            lng, lat = req.lng, req.lat
            source = "gps"
        else:
            ip_loc = await ip_location()
            if ip_loc:
                lng, lat = ip_loc["lng"], ip_loc["lat"]
                source = "ip"

        redis_geo = get_redis_geo()
        await redis_geo.geoadd("workers:geo", (lng, lat, user.user_id))
        logger.info(
            f"维修员 {user.user_id} Geo 初始化 source={source} lng={lng:.4f} lat={lat:.4f}"
        )

    return APIResponse(
        msg="登录成功",
        data=LoginResponse(
            token=token, user_id=user.user_id, role=user.role,
            name=user.nickname or user.username or "",
        ),
    ).model_dump()


@router.post("/register", response_model=APIResponse[LoginResponse])
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册：云端校验短信验证码。"""
    if not req.phone or len(req.phone) != 11:
        raise BadRequestException("请输入正确的手机号")

    if not req.verify_code:
        raise BadRequestException("请输入短信验证码")

    result = await db.execute(select(User).where(User.username == req.username))
    existing = result.scalar_one_or_none()
    if existing:
        raise BadRequestException("用户名已存在")

    phone_existing = await _find_user_by_phone(db, req.phone)
    if phone_existing:
        raise BadRequestException("该手机号已注册")

    # 云端校验验证码（阿里云 CheckSmsVerifyCode）
    from app.services.auth.aliyun_auth_service import check_sms_code as check_code

    try:
        passed = await asyncio.to_thread(check_code, req.phone, req.verify_code)
    except RuntimeError as e:
        raise BadRequestException(str(e))

    if not passed:
        raise BadRequestException("验证码错误或已过期")

    user_id = f"USR{uuid.uuid4().hex[:16].upper()}"
    user = User(
        user_id=user_id,
        username=req.username,
        password_hash=hash_password(req.password),
        nickname=req.nickname or req.username,
        phone=req.phone,
        phone_normalized=req.phone,
        role="citizen",
    )
    db.add(user)
    await db.commit()

    token = create_access_token(user_id, "citizen")
    return APIResponse(
        msg="注册成功",
        data=LoginResponse(
            token=token,
            user_id=user_id,
            role="citizen",
            name=user.nickname or user.username or "",
        ),
    ).model_dump()


@router.post("/send-sms-code", response_model=APIResponse[dict])
async def send_sms_code(req: SendSmsCodeRequest, db: AsyncSession = Depends(get_db)):
    """发送短信验证码（云端生成，无需本地存储）。"""
    from app.services.auth.aliyun_auth_service import send_sms_code as send_sms
    from app.services.auth.aliyun_auth_service import check_rate_limit

    # 本地 Redis 频控（60 秒防重发，与阿里云 Interval 互补）
    can_send = await check_rate_limit(req.phone_number)
    if not can_send:
        raise BadRequestException("发送过于频繁，请稍后再试")

    if req.scene == "login":
        user = await _find_user_by_phone(db, req.phone_number)
        if user is None:
            raise BadRequestException("该手机号没有创建账号，请先注册")
    else:
        user = await _find_user_by_phone(db, req.phone_number)
        if user is not None:
            raise BadRequestException("该手机号已注册，请直接登录")

    try:
        await asyncio.to_thread(send_sms, req.phone_number)
    except RuntimeError as e:
        raise BadRequestException(str(e))

    logger.info(f"发送短信验证码成功 scene={req.scene} phone={req.phone_number[:3]}****")
    return APIResponse(msg="验证码已发送").model_dump()


@router.post("/sms-login", response_model=APIResponse[LoginResponse])
async def sms_login(req: SmsLoginRequest, db: AsyncSession = Depends(get_db)):
    """短信验证码登录（云端校验）。"""
    from app.services.auth.aliyun_auth_service import check_sms_code as check_code

    try:
        passed = await asyncio.to_thread(check_code, req.phone_number, req.verify_code)
    except RuntimeError as e:
        raise BadRequestException(str(e))

    if not passed:
        raise BadRequestException("验证码错误或已过期")

    user = await _find_user_by_phone(db, req.phone_number)
    if user is None:
        raise BadRequestException("该手机号没有创建账号，请先注册")

    if not user.is_active:
        raise BadRequestException("账号已被禁用")

    token = create_access_token(user.user_id, user.role)
    return APIResponse(
        msg="登录成功",
        data=LoginResponse(
            token=token,
            user_id=user.user_id,
            role=user.role,
            name=user.nickname or user.username or "",
        ),
    ).model_dump()
