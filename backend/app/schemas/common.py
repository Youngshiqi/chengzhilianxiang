# ============================================================
# 城市公共设施智能报修与派单系统 - 通用 Schema
# 作用：定义统一响应体 {code, msg, data}、分页请求/响应、错误码枚举；
#       所有 API 返回值统一包装，前端按 code 判断成功/失败
# ============================================================

from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """统一响应体"""
    code: int = Field(200, description="状态码: 200成功 401鉴权失效 403权限不足 400参数错误 500服务异常")
    msg: str = Field("ok", description="提示文案")
    data: Optional[T] = Field(None, description="业务数据")


class PaginationRequest(BaseModel):
    """分页请求"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页条数")


class PaginationResponse(BaseModel):
    """分页响应"""
    total: int = Field(..., description="总条数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页条数")
    items: List[Any] = Field(..., description="数据列表")


class ErrorCode:
    """错误码常量"""
    SUCCESS = 200
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    BAD_REQUEST = 400
    NOT_FOUND = 404
    CONFLICT = 409
    SERVER_ERROR = 500
