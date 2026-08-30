#!/usr/bin/env python3
# ============================================================
# 城市公共设施智能报修与派单系统 - 数据库迁移：添加 accepting 状态
# 运行：cd backend && python scripts/migrate_add_accepting.py
# ============================================================

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.config.mysql import engine


async def migrate_add_accepting_status():
    """修改 tickets 表 status 枚举，添加 'accepting'"""
    print("=" * 60)
    print("数据库迁移：添加 accepting 工单状态")
    print("=" * 60)

    try:
        async with engine.begin() as conn:
            # 1. 先查看当前 status 列定义
            print("\n[1/2] 查看当前 status 列定义...")
            result = await conn.execute(text("SHOW COLUMNS FROM tickets LIKE 'status'"))
            row = result.fetchone()
            if row:
                print(f"    当前定义: {row[1]}")

            # 2. 修改枚举类型
            print("\n[2/2] 修改 status 列枚举...")
            await conn.execute(text("""
                ALTER TABLE tickets
                MODIFY COLUMN status ENUM(
                    'pending',
                    'accepting',
                    'dispatching',
                    'repairing',
                    'verifying',
                    'closed'
                ) DEFAULT 'pending'
                COMMENT '工单状态'
            """))

            # 3. 验证修改
            result = await conn.execute(text("SHOW COLUMNS FROM tickets LIKE 'status'"))
            row = result.fetchone()
            if row:
                print(f"    新定义: {row[1]}")
                if 'accepting' in row[1]:
                    print("    ✓ accepting 状态已成功添加！")
                else:
                    print("    ✗ 修改失败，未找到 accepting")

        print("\n" + "=" * 60)
        print("迁移完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(migrate_add_accepting_status())
