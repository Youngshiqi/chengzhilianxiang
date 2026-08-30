# ============================================================
# 城市公共设施智能报修与派单系统 - 接口限流中间件
# 作用：基于 Redis 滑动窗口的接口级限流；
#       防止恶意刷接口，核心报修接口限制每分钟10次
# ============================================================

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config.redis_client import get_redis_cache

# 限流规则：路径前缀 -> (窗口秒数, 最大请求数)
RATE_LIMIT_RULES = {
    "/api/v1/citizen/tickets": (60, 10),  # 报修接口：60s内最多10次
    "/api/v1/citizen/evaluations": (60, 5),  # 评价：60s内最多5次
    "/api/v1/worker/tickets": (60, 20),  # 接单大厅：60s内最多20次
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis 滑动窗口限流中间件"""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 查找匹配的限流规则
        rule = None
        for prefix, r in RATE_LIMIT_RULES.items():
            if path.startswith(prefix):
                rule = r
                break

        if rule is None:
            return await call_next(request)

        window_secs, max_requests = rule
        user_id = getattr(request.state, "user_id", "anonymous")
        key = f"rate_limit:{user_id}:{path}"

        try:
            redis = get_redis_cache()
            now = int(time.time())
            window_start = now - window_secs

            # 滑动窗口：删除过期记录 + 统计当前窗口内请求数
            await redis.zremrangebyscore(key, 0, window_start)
            count = await redis.zcard(key)

            if count >= max_requests:
                return JSONResponse(
                    status_code=200,
                    content={"code": 429, "msg": "请求过于频繁，请稍后再试", "data": None},
                )

            # 记录本次请求
            await redis.zadd(key, {str(now): now})
            await redis.expire(key, window_secs + 10)
        except Exception:
            # Redis 不可用时降级放行
            pass

        return await call_next(request)
