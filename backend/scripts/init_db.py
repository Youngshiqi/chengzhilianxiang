#!/usr/bin/env python3
# ============================================================
# 城市公共设施智能报修与派单系统 - 数据库初始化脚本
# 作用：创建MySQL全部建表语句、MongoDB Collection索引、ES Index Mapping；
#       在 docker-compose up -d 后运行此脚本完成基础设施初始化
# 运行：cd backend && python scripts/init_db.py
# ============================================================

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.config.mysql import engine, Base
from app.config.settings import settings
from app.config.mongodb import init_mongodb, close_mongodb
from app.config.elasticsearch_client import init_es, close_es


async def ensure_database_charset():
    """确保数据库级字符集为 utf8mb4"""
    async with engine.begin() as conn:
        await conn.execute(text(
            f"ALTER DATABASE `{settings.MYSQL_DATABASE}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        ))
    print("  ✓ 数据库字符集已设置为 utf8mb4_unicode_ci")


async def ensure_table_charsets():
    """将核心业务表统一转为 utf8mb4（幂等操作）"""
    async with engine.begin() as conn:
        tables = await conn.execute(text(
            "SELECT TABLE_NAME FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = :db AND TABLE_COLLATION != 'utf8mb4_unicode_ci'",
        ), {"db": settings.MYSQL_DATABASE})
        bad_tables = [row[0] for row in tables.fetchall()]

        for tbl in bad_tables:
            print(f"  ! 表 {tbl} 字符集不是 utf8mb4，正在转换...")
            await conn.execute(text(
                f"ALTER TABLE `{tbl}` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            ))
            print(f"  ✓ 表 {tbl} 已转为 utf8mb4_unicode_ci")

    if not bad_tables:
        print("  ✓ 所有表字符集正确（utf8mb4_unicode_ci）")


async def init_all():
    """初始化所有数据存储"""
    print("=" * 60)
    print("城市公共设施智能报修与派单系统 - 数据库初始化")
    print("=" * 60)

    # 1. MySQL 字符集 + 建表
    print("\n[1/3] 初始化 MySQL 表结构...")
    await ensure_database_charset()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await ensure_table_charsets()
    print("    - users (用户账号表)")
    print("    - tickets (工单主表)")
    print("    - facilities (设施档案表)")
    print("    - workers (维修员档案表)")
    print("    - settlements (结算单表)")
    print("    - evaluations (市民评价表)")
    print("    - audit_rules (结算规则配置表)")

    # 2. MongoDB 索引
    print("\n[2/3] 初始化 MongoDB Collection 索引...")
    await init_mongodb()
    print("  ✓ MongoDB Collection 索引创建完成")
    print("    - ticket_attachments (工单附件)")
    print("    - ai_analysis_logs (AI解析日志)")
    print("    - repair_records (维修记录)")
    print("    - audit_logs (审计日志)")
    print("    - notifications (消息通知)")
    await close_mongodb()

    # 3. ES Index
    print("\n[3/3] 初始化 Elasticsearch Index Mapping...")
    await init_es()
    print("  ✓ ES Index 创建完成（含IK中文分词器配置）")
    print("    - tickets_index (工单检索)")
    print("    - facilities_index (设施检索)")
    print("    - workers_perf_index (绩效聚合)")
    print("    - audit_log_index (审计检索)")
    await close_es()

    print("\n" + "=" * 60)
    print("数据库初始化全部完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(init_all())
