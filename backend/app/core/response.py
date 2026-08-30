# ============================================================
# 城市公共设施智能报修与派单系统 - 统一响应工具
# 作用：提供 success() / fail() 快捷函数，统一包装 API 返回值
# ============================================================

from typing import Any, Optional

from app.schemas.common import APIResponse, ErrorCode


def success(data: Any = None, msg: str = "ok") -> dict:
    """成功响应"""
    return APIResponse(code=ErrorCode.SUCCESS, msg=msg, data=data).model_dump()


def fail(code: int = ErrorCode.SERVER_ERROR, msg: str = "服务异常") -> dict:
    """失败响应"""
    return APIResponse(code=code, msg=msg, data=None).model_dump()
