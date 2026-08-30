# ============================================================
# 城市公共设施智能报修与派单系统 - 全局异常处理
# 作用：定义业务异常类 AppException，注册全局异常处理器；
#       所有异常统一返回 {code, msg, data} 格式，避免框架默认HTML响应
# ============================================================

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.schemas.common import ErrorCode


class AppException(Exception):
    """业务异常基类"""

    def __init__(self, code: int = ErrorCode.SERVER_ERROR, msg: str = "服务异常"):
        self.code = code
        self.msg = msg


class NotFoundException(AppException):
    """资源不存在"""
    def __init__(self, msg: str = "资源不存在"):
        super().__init__(code=ErrorCode.NOT_FOUND, msg=msg)


class ConflictException(AppException):
    """资源冲突（如重复报修、重复评价）"""
    def __init__(self, msg: str = "资源冲突"):
        super().__init__(code=ErrorCode.CONFLICT, msg=msg)


class BadRequestException(AppException):
    """参数错误"""
    def __init__(self, msg: str = "参数错误"):
        super().__init__(code=ErrorCode.BAD_REQUEST, msg=msg)


def register_exception_handlers(app: FastAPI):
    """注册全局异常处理器到 FastAPI 应用"""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=200,  # 业务异常统一返回200，通过code字段区分
            content={"code": exc.code, "msg": exc.msg, "data": None},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"code": ErrorCode.SERVER_ERROR, "msg": f"服务异常: {str(exc)}", "data": None},
        )
