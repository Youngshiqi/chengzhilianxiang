# ============================================================
# 城市公共设施智能报修与派单系统 - 阿里云 OSS 服务（服务端直传）
# 作用：接收文件字节流，直接上传到阿里云 OSS，返回公网访问 URL；
#       按日期分目录，生成唯一文件名，限制文件大小和类型
# ============================================================

import uuid
import logging
from datetime import datetime
from io import BytesIO
from typing import Optional

from fastapi import UploadFile

from app.config.settings import settings
from app.config.oss_client import get_oss_bucket
from app.utils.timezone import now_beijing

logger = logging.getLogger(__name__)

# 允许的图片 MIME 类型
ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/bmp": "bmp",
}

MAX_FILE_SIZE = settings.OSS_MAX_FILE_SIZE_MB * 1024 * 1024  # 字节


def _generate_object_key(prefix: str = "tickets", extension: str = "jpg") -> str:
    """生成 OSS 对象存储路径：{prefix}/{YYYY}/{MM}/{DD}/{uuid}.{ext}"""
    now = now_beijing()
    date_path = now.strftime("%Y/%m/%d")
    file_id = uuid.uuid4().hex[:12]
    return f"{prefix}/{date_path}/{file_id}.{extension}"


def _generate_public_url(object_key: str) -> str:
    """根据 OSS 对象 Key 生成公网访问 URL"""
    if settings.OSS_PUBLIC_BASE_URL:
        base = settings.OSS_PUBLIC_BASE_URL.rstrip("/")
        return f"{base}/{object_key}"
    return f"https://{settings.OSS_BUCKET}.{settings.OSS_ENDPOINT}/{object_key}"


async def upload_file_to_oss(file: UploadFile, prefix: str = "tickets") -> str:
    """
    将上传的文件写入阿里云 OSS，返回公网访问 URL。

    Args:
        file: FastAPI UploadFile 对象
        prefix: OSS 对象 Key 前缀，默认 "tickets"

    Returns:
        str: OSS 公网访问 URL

    Raises:
        ValueError: 文件类型不支持或大小超限
        RuntimeError: OSS 未配置或上传失败
    """
    bucket = get_oss_bucket()
    if bucket is None:
        raise RuntimeError("OSS 未配置，无法上传文件")

    # 1. 校验文件类型
    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        allowed = ", ".join(ALLOWED_CONTENT_TYPES.keys())
        raise ValueError(f"不支持的图片格式：{content_type or '未知'}，仅支持 {allowed}")

    # 2. 读取文件内容并校验大小
    contents = await file.read()
    file_size = len(contents)

    if file_size > MAX_FILE_SIZE:
        size_mb = file_size / (1024 * 1024)
        raise ValueError(f"图片过大（{size_mb:.1f}MB），最大允许 {settings.OSS_MAX_FILE_SIZE_MB}MB")

    if file_size == 0:
        raise ValueError("文件为空，请选择有效图片")

    # 3. 生成对象 Key 并上传
    ext = ALLOWED_CONTENT_TYPES[content_type]
    object_key = _generate_object_key(prefix, ext)

    try:
        bucket.put_object(
            key=object_key,
            data=BytesIO(contents),
            headers={"Content-Type": content_type},
        )
        logger.info(f"OSS 上传成功: {object_key} ({file_size / 1024:.1f}KB)")

        # 4. 返回公网 URL
        public_url = _generate_public_url(object_key)
        return public_url

    except Exception as e:
        logger.error(f"OSS 上传失败 object_key={object_key}: {e}")
        raise RuntimeError(f"图片上传失败，请稍后重试") from e
