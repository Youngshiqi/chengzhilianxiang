# ============================================================
# 城市公共设施智能报修与派单系统 - 阿里云号码认证服务
# 作用：封装阿里云 DypnsAPI 短信验证码接口；
#       云端生成验证码 + 云端校验，无需本地 Redis 存储验证码；
#       SDK 为同步调用，外层用 asyncio.to_thread() 包装
# ============================================================

import json
import logging
from typing import Optional

from alibabacloud_dypnsapi20170525.client import Client as DypnsClient
from alibabacloud_dypnsapi20170525 import models as dypns_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

from app.config.settings import settings
from app.config.redis_client import get_redis_cache

logger = logging.getLogger(__name__)

_client: Optional[DypnsClient] = None


def _get_client() -> Optional[DypnsClient]:
    """获取 DypnsAPI 客户端单例（懒加载）"""
    global _client
    if _client is not None:
        return _client

    if not settings.DYPNS_ACCESS_KEY_ID or not settings.DYPNS_ACCESS_KEY_SECRET:
        logger.warning("号码认证未配置（缺少 DYPNS_ACCESS_KEY_ID / DYPNS_ACCESS_KEY_SECRET）")
        return None

    try:
        config = open_api_models.Config(
            access_key_id=settings.DYPNS_ACCESS_KEY_ID,
            access_key_secret=settings.DYPNS_ACCESS_KEY_SECRET,
            region_id=settings.DYPNS_REGION,
            endpoint="dypnsapi.aliyuncs.com",
        )
        _client = DypnsClient(config)
        logger.info(f"DypnsAPI 客户端初始化成功 region={settings.DYPNS_REGION}")
        return _client
    except Exception as e:
        logger.error(f"DypnsAPI 客户端初始化失败: {e}")
        return None


# ---------------------------------------------------------------------------
# 发送验证码（云端生成）
# ---------------------------------------------------------------------------

def send_sms_code(
    phone_number: str,
    sign_name: str = None,
    template_code: str = None,
    scheme_name: str = None,
) -> None:
    """
    调用 SendSmsVerifyCode API 发送短信验证码。
    验证码由阿里云端自动生成，TemplateParam 使用 ##code## 占位符。

    Args:
        phone_number: 11 位手机号
        sign_name:    签名名称（默认读配置）
        template_code: 模板 CODE（默认读配置）
        scheme_name:   方案名称（可选）

    Raises:
        RuntimeError: 发送失败时抛出
    """
    client = _get_client()
    if client is None:
        raise RuntimeError("验证码服务未配置")

    sn = sign_name or settings.DYPNS_SMS_SIGN_NAME
    tc = template_code or settings.DYPNS_SMS_TEMPLATE_CODE

    if not sn or not tc:
        raise RuntimeError("短信签名或模板未配置，请在 .env 中设置 DYPNS_SMS_SIGN_NAME / DYPNS_SMS_TEMPLATE_CODE")

    # 使用 ##code## 占位符，让阿里云自动生成 6 位验证码
    # min=5 对应模板中的 ${min} 变量（5 分钟有效期）
    template_param = json.dumps(
        {"code": "##code##", "min": "5"},
        ensure_ascii=False,
    )

    req = dypns_models.SendSmsVerifyCodeRequest(
        phone_number=phone_number,
        sign_name=sn,
        template_code=tc,
        template_param=template_param,
        country_code="86",
        code_type=1,          # 纯数字
        code_length=6,         # 6 位
        valid_time=300,        # 5 分钟有效期
        interval=60,           # 60 秒防重发
        duplicate_policy=1,     # 覆盖旧验证码
    )
    if scheme_name:
        req.scheme_name = scheme_name

    runtime = util_models.RuntimeOptions()
    try:
        resp = client.send_sms_verify_code_with_options(req, runtime)
    except Exception as e:
        logger.warning(f"SendSmsVerifyCode 调用异常 phone={phone_number[:3]}****: {e}")
        raise RuntimeError("短信发送失败，请稍后重试") from e

    if resp.body.code != "OK":
        logger.warning(
            f"SendSmsVerifyCode 返回失败: code={resp.body.code} "
            f"message={resp.body.message} phone={phone_number[:3]}****"
        )
        # 根据错误码返回友好提示
        msg = resp.body.message or "短信发送失败，请稍后重试"
        if "FREQUENCY" in (resp.body.code or ""):
            msg = "发送过于频繁，请稍后再试"
        raise RuntimeError(msg)

    logger.info(f"SendSmsVerifyCode 成功 phone={phone_number[:3]}****")


# ---------------------------------------------------------------------------
# 校验验证码（云端校验）
# ---------------------------------------------------------------------------

def check_sms_code(
    phone_number: str,
    verify_code: str,
    scheme_name: str = None,
) -> bool:
    """
    调用 CheckSmsVerifyCode API 在阿里云端校验验证码。
    无需本地存储验证码，阿里云管理完整生命周期。

    Args:
        phone_number: 11 位手机号
        verify_code: 用户提交的验证码
        scheme_name:  方案名称（需与发送时一致）

    Returns:
        bool: 校验是否通过

    Raises:
        RuntimeError: API 调用失败时抛出
    """
    client = _get_client()
    if client is None:
        raise RuntimeError("验证码服务未配置")

    req = dypns_models.CheckSmsVerifyCodeRequest(
        phone_number=phone_number,
        verify_code=verify_code,
        country_code="86",
        case_auth_policy=1,   # 不区分大小写
    )
    if scheme_name:
        req.scheme_name = scheme_name

    runtime = util_models.RuntimeOptions()
    try:
        resp = client.check_sms_verify_code_with_options(req, runtime)
    except Exception as e:
        logger.warning(f"CheckSmsVerifyCode 调用异常 phone={phone_number[:3]}****: {e}")
        raise RuntimeError("验证码校验失败，请稍后重试") from e

    if resp.body.code != "OK":
        logger.warning(
            f"CheckSmsVerifyCode 返回失败: code={resp.body.code} "
            f"message={resp.body.message} phone={phone_number[:3]}****"
        )
        return False

    # 关键：Code=OK 只代表接口调用成功，校验结果看 Model.VerifyResult
    if resp.body.model is not None:
        model_dict = resp.body.model.to_map()
        verify_result = model_dict.get("VerifyResult")
    else:
        verify_result = None
    if verify_result == "PASS":
        logger.info(f"CheckSmsVerifyCode 校验通过 phone={phone_number[:3]}****")
        return True
    else:
        logger.info(f"CheckSmsVerifyCode 校验失败 phone={phone_number[:3]}**** result={verify_result}")
        return False


# ---------------------------------------------------------------------------
# Redis 辅助：API 级频控（防止恶意刷接口，与阿里云频控互补）
# ---------------------------------------------------------------------------

async def check_rate_limit(phone_number: str, ttl: int = 60) -> bool:
    """
    检查手机号是否在 60 秒内已发送过（Redis 级频控）。
    返回 True 表示可以发送，False 表示需要等待。

    注意：阿里云端也有 Interval=60 的频控，此为本地额外防护层。
    """
    redis = get_redis_cache()
    if redis is None:
        return True   # Redis 不可用时不阻断

    key = f"sms_api_limit:{phone_number}"
    exists = await redis.get(key)
    if exists:
        return False
    await redis.setex(key, ttl, "1")
    return True
