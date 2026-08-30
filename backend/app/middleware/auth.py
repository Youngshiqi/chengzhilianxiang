# ============================================================
# 城市公共设施智能报修与派单系统 - 认证中间件
# 作用：在请求进入路由前解析 JWT Token，将用户信息注入 request.state；
#       排除白名单路径（登录、健康检查），其余路径强制鉴权
# ============================================================

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.security import decode_token
from app.schemas.common import ErrorCode

# 无需鉴权的白名单路径
AUTH_WHITELIST = [
    "/health",
    "/api/v1/auth",
    "/api/v1/citizen/auth",
    "/api/v1/worker/auth",
    "/api/v1/admin/auth",
    "/api/v1/utils",
    "/docs",
    "/openapi.json",
    "/redoc",
]


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT 鉴权中间件"""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 白名单路径跳过鉴权
        if any(path.startswith(p) for p in AUTH_WHITELIST):
            return await call_next(request)

        # OPTIONS 预检请求跳过
        if request.method == "OPTIONS":
            return await call_next(request)

        # 从 Authorization Header 提取 Token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=200,
                content={"code": ErrorCode.UNAUTHORIZED, "msg": "请先登录", "data": None},
            )

        token = auth_header[7:]
        payload = decode_token(token)
        if payload is None:
            return JSONResponse(
                status_code=200,
                content={"code": ErrorCode.UNAUTHORIZED, "msg": "Token无效或已过期", "data": None},
            )

        # 将用户信息注入 request.state，后续路由通过 request.state.user 获取
        request.state.user_id = payload.get("sub")
        request.state.role = payload.get("role")

        return await call_next(request)
