# ============================================================
# 城市公共设施智能报修与派单系统 - 阿里云 OSS 客户端管理
# 作用：初始化 oss2 Bucket 客户端，提供服务端直传能力；
#       提供 get_oss_bucket() 单例，与 mongodb.py/redis_client.py 风格一致
# ============================================================

import logging
from typing import Optional

import oss2
from oss2 import Auth, Bucket

from app.config.settings import settings

logger = logging.getLogger(__name__)

_bucket: Optional[Bucket] = None


def get_oss_bucket() -> Optional[Bucket]:
    """获取阿里云 OSS Bucket 客户端单例"""
    global _bucket
    if _bucket is not None:
        return _bucket

    if not settings.OSS_ACCESS_KEY_ID or not settings.OSS_ACCESS_KEY_SECRET:
        logger.warning("OSS 未配置（缺少 OSS_ACCESS_KEY_ID / OSS_ACCESS_KEY_SECRET），上传功能不可用")
        return None

    try:
        auth = Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
        _bucket = Bucket(auth, settings.OSS_ENDPOINT, settings.OSS_BUCKET)
        logger.info(f"OSS Bucket 客户端初始化成功: {settings.OSS_BUCKET}")
        return _bucket
    except Exception as e:
        logger.error(f"OSS Bucket 客户端初始化失败: {e}")
        return None


def close_oss_client():
    """关闭 OSS 客户端（oss2 为同步客户端，无需异步清理）"""
    global _bucket
    _bucket = None
    logger.info("OSS 客户端已关闭")
