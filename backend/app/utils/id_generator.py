# ============================================================
# 城市公共设施智能报修与派单系统 - 分布式ID生成器
# 作用：生成全局唯一的工单ID、结算ID等业务主键；
#       格式：{前缀} + YYYYMMDDHHmmss，如 TK20260625041305；
#       使用 Redis INCR 原子递增保证分布式唯一
# ============================================================

from app.utils.timezone import now_beijing


async def generate_id(redis_counter, prefix: str = "") -> str:
    """生成全局唯一业务ID（前缀 + 精确到秒 + Redis原子序列号兜底）"""
    now = now_beijing()
    base = f"{prefix}{now.strftime('%Y%m%d%H%M%S')}"  # 前缀 + 14位年月日时分秒

    # 同秒内冲突时，用 Redis 原子递增序列号兜底
    key = f"id_seq:{base}"
    seq = await redis_counter.incr(key)
    await redis_counter.expire(key, 3)  # 3秒后过期（只防同秒冲突）

    if seq == 1:
        # 该秒第一条，直接返回
        return base
    else:
        # 同秒第N条，追加序列号
        return f"{base}{seq:04d}"
