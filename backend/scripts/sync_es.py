#!/usr/bin/env python3
# ============================================================
# 城市公共设施智能报修与派单系统 - ES索引同步脚本
# 作用：将 MySQL 工单数据同步至 Elasticsearch；
#       支持全量同步（--mode full）和增量同步（--mode incremental --since 2026-06-22）；
#       也可作为定时任务（cron 每5分钟）补漏
# 运行：cd backend && python scripts/sync_es.py --mode full
#       cd backend && python scripts/sync_es.py --mode incremental --since 2026-06-22
# ============================================================

import argparse
import asyncio
import io
import sys

# Windows GBK 终端兼容
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from datetime import datetime, timezone

# 确保 backend 目录在 sys.path 中
from pathlib import Path
_backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_dir))

from app.config.mysql import async_session_factory
from app.config.elasticsearch_client import get_es_client, init_es
from app.config.settings import settings
from app.models.mysql.ticket import Ticket
from sqlalchemy import select

BATCH_SIZE = 200  # 批量索引大小


async def sync_full():
    """全量同步：MySQL tickets → ES tickets_index"""
    await init_es()
    es = get_es_client()
    index_name = f"{settings.ES_INDEX_PREFIX}_tickets"
    print(f"开始全量同步 MySQL tickets → ES {index_name}...")

    async with async_session_factory() as db:
        result = await db.execute(select(Ticket))
        tickets = result.scalars().all()

        synced = 0
        for ticket in tickets:
            doc = _build_doc(ticket)
            await es.index(index=index_name, id=ticket.ticket_id, body=doc)
            synced += 1
            if synced % BATCH_SIZE == 0:
                print(f"  已同步 {synced}/{len(tickets)}...")

    print(f"[OK] 全量同步完成: {synced} 条工单数据")


async def sync_incremental(since: datetime):
    """增量同步：同步 since 之后创建/更新的工单"""
    await init_es()
    es = get_es_client()
    index_name = f"{settings.ES_INDEX_PREFIX}_tickets"
    print(f"开始增量同步 MySQL tickets → ES {index_name}（since {since.isoformat()}）...")

    async with async_session_factory() as db:
        result = await db.execute(
            select(Ticket).where(Ticket.created_at >= since)
        )
        tickets = result.scalars().all()

        synced = 0
        for ticket in tickets:
            doc = _build_doc(ticket)
            await es.index(index=index_name, id=ticket.ticket_id, body=doc)
            synced += 1
            if synced % BATCH_SIZE == 0:
                print(f"  已同步 {synced}/{len(tickets)}...")

    print(f"[OK] 增量同步完成: {synced} 条工单数据")


def _build_doc(ticket: Ticket) -> dict:
    """构建完整 ES 文档（与 ES Sync 消费者保持一致）"""
    return {
        "ticket_id": ticket.ticket_id,
        "user_id": ticket.user_id,
        "facility_type": ticket.facility_type,
        "status": ticket.status,
        "description": ticket.description or "",
        "address": ticket.address or "",
        "district": ticket.district or "",
        "emergency_level": ticket.emergency_level or 0,
        "ai_category": ticket.ai_category,
        "assigned_worker_id": ticket.assigned_worker_id,
        "location": {"lat": ticket.location_lat, "lon": ticket.location_lng},
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ES 索引同步脚本")
    parser.add_argument(
        "--mode", choices=["full", "incremental"], default="full",
        help="同步模式：full=全量, incremental=增量（需配合 --since）",
    )
    parser.add_argument(
        "--since", type=str, default=None,
        help="增量同步起始时间（ISO 格式，如 2026-06-22 或 2026-06-22T00:00:00）",
    )
    args = parser.parse_args()

    if args.mode == "incremental":
        if not args.since:
            print("错误：incremental 模式需要 --since 参数", file=sys.stderr)
            sys.exit(1)
        try:
            since_dt = datetime.fromisoformat(args.since)
            # 若无时区信息，假定 UTC
            if since_dt.tzinfo is None:
                since_dt = since_dt.replace(tzinfo=timezone.utc)
        except ValueError as e:
            print(f"错误：--since 时间格式无效: {e}", file=sys.stderr)
            sys.exit(1)
        asyncio.run(sync_incremental(since_dt))
    else:
        asyncio.run(sync_full())
