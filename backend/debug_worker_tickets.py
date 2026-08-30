#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ============================================================
# 调试脚本：查看维修员工单数据
# ============================================================

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import select, and_
from app.config.mysql import async_session_factory
from app.models.mysql.ticket import Ticket
from app.models.mysql.worker import Worker
from app.utils.timezone import now_beijing


async def debug_tickets():
    """查看郑晓明的工单数据"""
    print("=" * 80)
    print("调试：查看维修员工单数据")
    print("=" * 80)

    async with async_session_factory() as db:
        # 1. 查找郑晓明
        w_result = await db.execute(select(Worker).where(Worker.name.like("%晓明%")))
        workers = w_result.scalars().all()
        if not workers:
            print("\n未找到姓名包含'晓明'的维修员，尝试查找所有维修员...")
            w_all = await db.execute(select(Worker))
            all_workers = w_all.scalars().all()
            print(f"\n所有维修员:")
            for w in all_workers:
                print(f"  - {w.worker_id}: {w.name}")
            return

        worker = workers[0]
        print(f"\n找到维修员: {worker.worker_id} - {worker.name}")

        # 2. 查询该维修员的所有工单
        t_result = await db.execute(
            select(Ticket)
            .where(Ticket.assigned_worker_id == worker.worker_id)
            .order_by(Ticket.created_at.desc())
        )
        tickets = t_result.scalars().all()
        print(f"\n该维修员共有 {len(tickets)} 个工单")

        now = now_beijing()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        print(f"\n当前时间(北京): {now}")
        print(f"今日 00:00:00: {today_start}")

        print(f"\n工单详情:")
        today_count_by_accepted = 0
        today_count_by_created = 0

        for i, t in enumerate(tickets, 1):
            is_accepted_today = t.accepted_at and t.accepted_at >= today_start
            is_created_today = t.created_at and t.created_at >= today_start

            if is_accepted_today:
                today_count_by_accepted += 1
            if is_created_today:
                today_count_by_created += 1

            print(f"\n  [{i}] {t.ticket_id}")
            print(f"      状态: {t.status}")
            print(f"      设施: {t.facility_type}")
            print(f"      创建时间: {t.created_at} {'<<< 今日创建' if is_created_today else ''}")
            print(f"      接单时间: {t.accepted_at} {'<<< 今日接单' if is_accepted_today else ''}")
            print(f"      完工时间: {t.completed_at}")
            print(f"      结束时间: {t.closed_at}")

        print(f"\n" + "=" * 80)
        print(f"统计结果:")
        print(f"  - 按 accepted_at（今日接单）: {today_count_by_accepted} 单")
        print(f"  - 按 created_at（今日创建）: {today_count_by_created} 单")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(debug_tickets())
