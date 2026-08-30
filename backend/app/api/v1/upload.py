# ============================================================
# 城市公共设施智能报修与派单系统 - 图片上传接口（服务端转发）
# 作用：POST /api/v1/utils/upload-image — 接收前端文件，上传到阿里云 OSS，返回 URL；
#       认证：utils 前缀在 AuthMiddleware 白名单中，无需登录
# ============================================================

import logging
from fastapi import APIRouter, File, UploadFile

from app.schemas.common import APIResponse
from app.services.storage.oss_service import upload_file_to_oss

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(..., description="图片文件（JPG/PNG/GIF/WebP/BMP）")):
    """
    上传图片到阿里云 OSS（服务端转发）。

    前端用 FormData 发送文件，后端校验后写入 OSS，返回公网访问 URL。
    限制：最大 10MB，仅支持常见图片格式。

    返回示例：
    {
        "code": 200,
        "data": { "url": "https://city-repair-system-images.oss-cn-beijing.aliyuncs.com/tickets/2026/06/24/xxx.jpg" }
    }
    """
    try:
        url = await upload_file_to_oss(file, prefix="tickets")
        return APIResponse(
            code=200,
            msg="上传成功",
            data={"url": url},
        ).model_dump()
    except ValueError as e:
        return APIResponse(
            code=400,
            msg=str(e),
            data=None,
        ).model_dump()
    except RuntimeError as e:
        logger.error(f"OSS 上传异常: {e}")
        return APIResponse(
            code=500,
            msg=str(e),
            data=None,
        ).model_dump()
