# ============================================================
# 结算规则配置数据补充脚本
# 运行方式：cd backend && python seed_audit_rules.py
# ============================================================
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import select
from app.config.mysql import async_session_factory
from app.models.mysql.audit_rule import AuditRule

RULES = [
    # (type, base_price, overtime_rate, emergency_multiplier, night_subsidy)
    ("路灯",      40.0, 1.5, 2.0, 20.0),
    ("井盖",      60.0, 1.5, 2.0, 20.0),
    ("护栏",      45.0, 1.5, 2.0, 20.0),
    ("信号灯",    50.0, 1.5, 2.0, 20.0),
    ("公交站牌",  35.0, 1.5, 1.5, 20.0),
    ("消防栓",    55.0, 1.5, 2.0, 20.0),
    ("公厕",      45.0, 1.5, 1.5, 20.0),
    ("指示牌",    30.0, 1.5, 1.5, 20.0),
    ("垃圾桶",    25.0, 1.5, 1.5, 15.0),
    ("健身器材",  35.0, 1.5, 1.5, 15.0),
    ("other",     40.0, 1.5, 1.5, 20.0),  # 默认
]


async def main():
    async with async_session_factory() as session:
        existing = await session.execute(select(AuditRule).limit(1))
        if existing.scalar_one_or_none():
            print("⚠ audit_rules 已有数据，跳过")
            return

        for i, (ftype, base, ot, em, ns) in enumerate(RULES, 1):
            session.add(AuditRule(
                rule_id=f"AR{i:04d}",
                facility_type=ftype,
                base_price=base,
                overtime_rate=ot,
                emergency_multiplier=em,
                night_subsidy=ns,
            ))

        await session.commit()
    print(f"✓ audit_rules 写入 {len(RULES)} 条结算规则")


if __name__ == "__main__":
    asyncio.run(main())
