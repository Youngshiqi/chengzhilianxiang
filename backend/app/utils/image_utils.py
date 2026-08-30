# ============================================================
# 城市公共设施智能报修与派单系统 - 图片处理工具
# 作用：生成图片水印Hash（GPS+时间戳摘要）防篡改校验
# ============================================================

import hashlib
from datetime import datetime


def generate_watermark_hash(lng: float, lat: float, timestamp: datetime) -> str:
    """生成图片水印Hash：GPS坐标+时间戳的SHA256摘要，用于防篡改校验"""
    raw = f"{lng:.6f},{lat:.6f},{timestamp.isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def verify_watermark(lng: float, lat: float, timestamp: datetime, watermark_hash: str) -> bool:
    """校验水印Hash是否匹配（防篡改）"""
    expected = generate_watermark_hash(lng, lat, timestamp)
    return expected == watermark_hash
