import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app.models.mysql.ticket import Ticket
from app.services.worker.repair_service import worker_complete, _get_before_photos


class DummyResult:
    def __init__(self, ticket):
        self._ticket = ticket

    def scalar_one_or_none(self):
        return self._ticket


class DummyDB:
    def __init__(self, ticket):
        self.ticket = ticket
        self.committed = False

    async def execute(self, *_args, **_kwargs):
        return DummyResult(self.ticket)

    async def commit(self):
        self.committed = True


class DummyCollection:
    """模拟 MongoDB Collection，支持 find_one / update_one / insert_one"""

    def __init__(self, find_one_docs=None):
        self.updates = []
        self.inserts = []
        # find_one_docs: dict of filter_key -> document
        # filter_key 使用 JSON 序列化后的字符串作为 key
        self._find_one_docs = find_one_docs or {}

    async def update_one(self, filter_query, update_doc, upsert=False):
        self.updates.append((filter_query, update_doc, upsert))

    async def insert_one(self, doc):
        self.inserts.append(doc)

    async def find_one(self, filter_query, sort=None):
        """根据 filter_query 返回预设的文档"""
        # 将 filter_query 序列化为字符串作为 key
        key_parts = []
        for k in sorted(filter_query.keys()):
            key_parts.append(f"{k}={filter_query[k]}")
        key = "|".join(key_parts)
        return self._find_one_docs.get(key)


class DummyMongo:
    def __init__(self, ticket_attachments_docs=None):
        self.repair_records = DummyCollection()
        self.ticket_attachments = DummyCollection(
            find_one_docs=ticket_attachments_docs or {}
        )
        self.ai_analysis_logs = DummyCollection()
        self.notifications = DummyCollection()


class DummyRedis:
    def __init__(self):
        self.calls = []
        self._store = {}

    async def hset(self, key, mapping=None):
        self.calls.append(("hset", key, mapping))

    async def expire(self, key, ttl):
        self.calls.append(("expire", key, ttl))

    async def delete(self, key):
        self.calls.append(("delete", key))


# ============================================================
# 测试1：AI 验收拒绝后返工标记和通知
# ============================================================
@pytest.mark.asyncio
async def test_worker_complete_ai_rejects_and_records_follow_up(monkeypatch):
    ticket = Ticket(
        ticket_id='TKTEST001',
        user_id='U1',
        facility_code='',
        facility_type='lamp',
        district='',
        status='repairing',
        description='路灯不亮',
        address='测试地址',
        location_lng=112.0,
        location_lat=28.0,
        emergency_level=0,
        assigned_worker_id='W1',
    )
    db = DummyDB(ticket)
    mongo = DummyMongo(ticket_attachments_docs={
        "stage=report|ticket_id=TKTEST001": {
            "ticket_id": "TKTEST001",
            "stage": "report",
            "image_urls": ["https://example.com/before1.jpg"],
        }
    })
    redis = DummyRedis()

    async def fake_verify_repair(**_kwargs):
        return {'verified': False, 'confidence': 0.34, 'diff_summary': '照片对比异常，疑似未修复'}

    async def fake_publish_es_sync(_ticket_id):
        return None

    monkeypatch.setattr('app.services.worker.repair_service.get_mongo_db', lambda: mongo)
    monkeypatch.setattr('app.services.worker.repair_service.get_redis_cache', lambda: redis)
    monkeypatch.setattr('app.services.worker.repair_service.verify_repair', fake_verify_repair)
    monkeypatch.setattr('app.services.mq.rabbitmq_service.publish_es_sync', fake_publish_es_sync)

    result = await worker_complete(
        ticket_id='TKTEST001',
        worker_id='W1',
        materials=[{'name': '灯泡', 'qty': 1, 'unit_cost': 10}],
        labor_hours=1.5,
        work_notes='已更换但效果不佳',
        completion_photo_urls=['https://example.com/after.jpg'],
        db=db,
    )

    assert result['success'] is True
    assert result['ai_verified'] is False
    assert result['ai_confidence'] == 0.34
    assert ticket.status == 'repairing'
    assert db.committed is True
    assert mongo.notifications.inserts, 'should create a follow-up notification'
    assert mongo.repair_records.updates[-1][1]['$set']['ai_rework_required'] is True
    assert redis.calls, 'should sync repairing status back to cache'


# ============================================================
# 测试2：完整返工流程 - 报修→第一次完工→AI拒绝→第二次完工→仍能拿到报修图片
# ============================================================
@pytest.mark.asyncio
async def test_rework_flow_before_photos_preserved(monkeypatch):
    """
    回归测试：验证返工后二次 AI 验收仍能拿到原始报修图片。

    流程：
      1. 市民提交带图片的报修工单（模拟 ticket_attachments 中已有 stage=report 文档）
      2. 维修工第一次提交完工图片 → AI 验收失败 → 工单保持 repairing
      3. 维修工第二次提交完工图片 → AI 验收仍能拿到原始报修图片
    """
    ticket_id = 'TKTEST_REWORK'
    before_photo_urls = [
        'https://example.com/report_photo_1.jpg',
        'https://example.com/report_photo_2.jpg',
    ]

    # --- 准备：模拟报修阶段已写入的 stage=report 文档 ---
    ticket_attachments_docs = {
        "stage=report|ticket_id=" + ticket_id: {
            "ticket_id": ticket_id,
            "stage": "report",
            "image_urls": before_photo_urls,
            "ai_ocr_result": None,
            "created_at": "2026-07-01T10:00:00",
        }
    }

    mongo = DummyMongo(ticket_attachments_docs=ticket_attachments_docs)

    # --- 第一次完工提交（AI 验收失败） ---
    ticket1 = Ticket(
        ticket_id=ticket_id,
        user_id='U_REWORK',
        facility_code='',
        facility_type='lamp',
        district='',
        status='repairing',
        description='路灯闪烁',
        address='测试地址',
        location_lng=112.0,
        location_lat=28.0,
        emergency_level=0,
        assigned_worker_id='W_REWORK',
    )
    db1 = DummyDB(ticket1)
    redis1 = DummyRedis()

    call_count = {'count': 0}
    captured_before_photos = {'first': None, 'second': None}

    async def fake_verify_reject(**kwargs):
        call_count['count'] += 1
        if call_count['count'] == 1:
            captured_before_photos['first'] = kwargs.get('before_photo_urls', [])
        else:
            captured_before_photos['second'] = kwargs.get('before_photo_urls', [])
        return {'verified': False, 'confidence': 0.30, 'diff_summary': '修复不完整'}

    async def fake_publish_es_sync(_ticket_id):
        return None

    monkeypatch.setattr('app.services.worker.repair_service.get_mongo_db', lambda: mongo)
    monkeypatch.setattr('app.services.worker.repair_service.get_redis_cache', lambda: redis1)
    monkeypatch.setattr('app.services.worker.repair_service.verify_repair', fake_verify_reject)
    monkeypatch.setattr('app.services.mq.rabbitmq_service.publish_es_sync', fake_publish_es_sync)

    # 第一次完工
    result1 = await worker_complete(
        ticket_id=ticket_id,
        worker_id='W_REWORK',
        materials=[{'name': '灯管', 'qty': 1, 'unit_cost': 20}],
        labor_hours=0.5,
        work_notes='第一次维修',
        completion_photo_urls=['https://example.com/after_1.jpg'],
        db=db1,
    )

    assert result1['success'] is True, f"第一次完工应成功: {result1}"
    assert result1['ai_verified'] is False, "第一次 AI 验收应失败"
    assert ticket1.status == 'repairing', "AI 拒绝后状态应保持 repairing"
    assert captured_before_photos['first'] == before_photo_urls, \
        f"第一次验收应拿到原始报修图片，实际: {captured_before_photos['first']}"

    # --- 第二次完工提交（返工后再次提交） ---
    ticket2 = Ticket(
        ticket_id=ticket_id,
        user_id='U_REWORK',
        facility_code='',
        facility_type='lamp',
        district='',
        status='repairing',  # 仍为 repairing
        description='路灯闪烁',
        address='测试地址',
        location_lng=112.0,
        location_lat=28.0,
        emergency_level=0,
        assigned_worker_id='W_REWORK',
    )
    db2 = DummyDB(ticket2)
    redis2 = DummyRedis()

    monkeypatch.setattr('app.services.worker.repair_service.get_redis_cache', lambda: redis2)

    result2 = await worker_complete(
        ticket_id=ticket_id,
        worker_id='W_REWORK',
        materials=[{'name': '灯管', 'qty': 1, 'unit_cost': 20}],
        labor_hours=1.0,
        work_notes='第二次维修，彻底更换',
        completion_photo_urls=['https://example.com/after_2.jpg'],
        db=db2,
    )

    assert result2['success'] is True, f"第二次完工应成功: {result2}"
    assert result2['ai_verified'] is False, "第二次 AI 验收仍应失败（mock 设为拒绝）"
    assert captured_before_photos['second'] == before_photo_urls, \
        f"第二次验收仍应拿到原始报修图片，实际: {captured_before_photos['second']}"

    # --- 验证 completion 使用 upsert（不会重复插入） ---
    completion_upserts = [
        u for u in mongo.ticket_attachments.updates
        if u[0].get('stage') == 'completion'
    ]
    assert len(completion_upserts) == 2, \
        f"两次完工应各产生一次 completion upsert，实际: {len(completion_upserts)}"


# ============================================================
# 测试3：缺少维修前照片时返回明确错误
# ============================================================
@pytest.mark.asyncio
async def test_missing_before_photos_returns_error(monkeypatch):
    """当 ticket_attachments 中确实不存在维修前照片时，应返回明确错误。"""
    ticket = Ticket(
        ticket_id='TKTEST_NO_PHOTOS',
        user_id='U1',
        facility_code='',
        facility_type='lamp',
        district='',
        status='repairing',
        description='路灯不亮',
        address='测试地址',
        location_lng=112.0,
        location_lat=28.0,
        emergency_level=0,
        assigned_worker_id='W1',
    )
    db = DummyDB(ticket)
    # ticket_attachments 中没有任何 stage=report 或 type=report_photo 文档
    mongo = DummyMongo(ticket_attachments_docs={})
    redis = DummyRedis()

    async def fake_publish_es_sync(_ticket_id):
        return None

    monkeypatch.setattr('app.services.worker.repair_service.get_mongo_db', lambda: mongo)
    monkeypatch.setattr('app.services.worker.repair_service.get_redis_cache', lambda: redis)
    monkeypatch.setattr('app.services.mq.rabbitmq_service.publish_es_sync', fake_publish_es_sync)

    result = await worker_complete(
        ticket_id='TKTEST_NO_PHOTOS',
        worker_id='W1',
        materials=[{'name': '灯泡', 'qty': 1, 'unit_cost': 10}],
        labor_hours=1.0,
        work_notes='已更换',
        completion_photo_urls=['https://example.com/after.jpg'],
        db=db,
    )

    assert result['success'] is False, "缺少维修前照片应返回失败"
    assert '维修前照片' in result['msg'], f"错误消息应提及缺少维修前照片: {result['msg']}"


# ============================================================
# 测试4：旧数据兼容 - type="report_photo" + image_url 单张格式
# ============================================================
@pytest.mark.asyncio
async def test_old_format_compat_single_image_url(monkeypatch):
    """兼容旧数据结构：type="report_photo"、image_url（单张）。"""
    ticket_id = 'TKTEST_OLD_FORMAT'
    old_doc = {
        "ticket_id": ticket_id,
        "type": "report_photo",
        "image_url": "https://example.com/old_format_photo.jpg",
        "uploader_id": "U_OLD",
    }
    # 注意：DummyCollection.find_one 按字母序排列 key，所以 ticket_id 在前
    mongo = DummyMongo(ticket_attachments_docs={
        "ticket_id=" + ticket_id + "|type=report_photo": old_doc,
    })
    # stage=report 不存在
    monkeypatch.setattr('app.services.worker.repair_service.get_mongo_db', lambda: mongo)

    before_photos = await _get_before_photos(mongo, ticket_id)
    assert before_photos == ["https://example.com/old_format_photo.jpg"], \
        f"应兼容旧格式 image_url 单张，实际: {before_photos}"


# ============================================================
# 测试5：旧数据兼容 - type="report_photo" + image_urls 数组格式
# ============================================================
@pytest.mark.asyncio
async def test_old_format_compat_array_image_urls(monkeypatch):
    """兼容旧数据结构：type="report_photo"、image_urls（数组）。"""
    ticket_id = 'TKTEST_OLD_ARRAY'
    old_doc = {
        "ticket_id": ticket_id,
        "type": "report_photo",
        "image_urls": ["https://example.com/old1.jpg", "https://example.com/old2.jpg"],
        "uploader_id": "U_OLD",
    }
    mongo = DummyMongo(ticket_attachments_docs={
        "ticket_id=" + ticket_id + "|type=report_photo": old_doc,
    })
    monkeypatch.setattr('app.services.worker.repair_service.get_mongo_db', lambda: mongo)

    before_photos = await _get_before_photos(mongo, ticket_id)
    assert before_photos == ["https://example.com/old1.jpg", "https://example.com/old2.jpg"], \
        f"应兼容旧格式 image_urls 数组，实际: {before_photos}"


# ============================================================
# 测试6：优先使用 stage="report" 格式
# ============================================================
@pytest.mark.asyncio
async def test_prefer_stage_report_over_old_format(monkeypatch):
    """当同时存在新旧格式时，优先使用 stage="report" 的数据。"""
    ticket_id = 'TKTEST_PREFER_NEW'
    docs = {
        "stage=report|ticket_id=" + ticket_id: {
            "ticket_id": ticket_id,
            "stage": "report",
            "image_urls": ["https://example.com/new_format.jpg"],
        },
        "ticket_id=" + ticket_id + "|type=report_photo": {
            "ticket_id": ticket_id,
            "type": "report_photo",
            "image_url": "https://example.com/old_format.jpg",
        },
    }
    mongo = DummyMongo(ticket_attachments_docs=docs)
    monkeypatch.setattr('app.services.worker.repair_service.get_mongo_db', lambda: mongo)

    before_photos = await _get_before_photos(mongo, ticket_id)
    assert before_photos == ["https://example.com/new_format.jpg"], \
        f"应优先使用 stage=report 格式，实际: {before_photos}"
