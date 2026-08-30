# ============================================================
# 城市公共设施智能报修与派单系统 - 时区工具
# 作用：统一提供北京时间当前时刻，全局替换 datetime.utcnow()
#       返回 naive datetime（无 tzinfo），与现有 ORM DateTime 列兼容
# ============================================================

import datetime
from zoneinfo import ZoneInfo

BEIJING_TZ = ZoneInfo("Asia/Shanghai")


def now_beijing() -> datetime.datetime:
    """返回北京时间当前时刻（naive datetime，兼容 MySQL DateTime 列）"""
    return datetime.datetime.now(BEIJING_TZ).replace(tzinfo=None)
