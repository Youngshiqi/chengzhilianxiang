# ============================================================
# 城市公共设施智能报修与派单系统 - 市民端接口测试
# 作用：测试 Citizen API 的登录、报修、工单查询、评价流程；
#       使用 pytest + httpx 进行端到端接口测试
# ============================================================

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client):
    """测试健康检查接口"""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_citizen_login(client):
    """测试市民微信登录"""
    resp = await client.post("/api/v1/citizen/auth/login", json={
        "code": "test_code_001",
        "nickname": "测试市民",
    })
    data = resp.json()
    assert data["code"] == 200
    assert data["data"]["token"] is not None
    assert data["data"]["role"] == "citizen"


@pytest.mark.asyncio
async def test_create_ticket(client):
    """测试市民报修提交"""
    # 先登录
    login_resp = await client.post("/api/v1/citizen/auth/login", json={"code": "test_002"})
    token = login_resp.json()["data"]["token"]

    resp = await client.post(
        "/api/v1/citizen/tickets",
        json={
            "description": "测试故障：路灯不亮，位置在芙蓉区",
            "location_lng": 112.9884,
            "location_lat": 28.1938,
            "address": "长沙市芙蓉区测试路100号",
            "emergency_level": 0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()
    assert data["code"] == 200
    assert data["data"]["ticket_id"].startswith("TK")


@pytest.mark.asyncio
async def test_get_ticket_progress(client):
    """测试工单进度查询"""
    login_resp = await client.post("/api/v1/citizen/auth/login", json={"code": "test_003"})
    token = login_resp.json()["data"]["token"]

    # 先创建工单
    create_resp = await client.post(
        "/api/v1/citizen/tickets",
        json={
            "description": "测试井盖异常",
            "location_lng": 112.9969,
            "location_lat": 28.1125,
            "address": "长沙市天心区",
            "emergency_level": 1,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    ticket_id = create_resp.json()["data"]["ticket_id"]

    # 查询进度
    resp = await client.get(
        f"/api/v1/citizen/tickets/{ticket_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.json()["code"] == 200



class DummyResult:
    def __init__(self, user):
        self._user = user
    def scalar_one_or_none(self):
        return self._user


class DummyUser:
    def __init__(self):
        self.user_id = 'U1001'
        self.role = 'citizen'
        self.nickname = '????'
        self.username = 'testuser'
        self.password_hash = None
        self.is_active = True
        self.phone_normalized = '13800138000'


class DummyRedis:
    def __init__(self):
        self.store = {}
    async def setex(self, key, ttl, value):
        self.store[key] = value
    async def get(self, key):
        return self.store.get(key)
    async def delete(self, key):
        self.store.pop(key, None)
    async def sadd(self, *args, **kwargs):
        return 1
    async def geoadd(self, *args, **kwargs):
        return 1


@pytest.mark.asyncio
async def test_sms_login_with_cached_code(client, monkeypatch):
    from app.api.v1 import auth as auth_module

    redis = DummyRedis()
    await redis.setex(auth_module._sms_code_key('13800138000'), auth_module.SMS_CODE_TTL_SECONDS, '123456')
    monkeypatch.setattr(auth_module, 'get_redis_cache', lambda: redis)
    monkeypatch.setattr(auth_module, 'get_redis_counter', lambda: redis)
    async def fake_generate_id(_redis, _prefix):
        return 'U1002'

    monkeypatch.setattr(auth_module, 'generate_id', fake_generate_id)

    class DummyDB:
        async def execute(self, *_args, **_kwargs):
            return DummyResult(None)
        def add(self, _obj):
            return None
        async def commit(self):
            return None

    async def fake_get_db():
        yield DummyDB()

    from app.config.mysql import get_db
    app.dependency_overrides[get_db] = fake_get_db
    try:
        resp = await client.post('/api/v1/auth/sms-login', json={
            'phone_number': '13800138000',
            'verify_code': '123456',
        })
        data = resp.json()
        assert data['code'] == 200
        assert data['data']['token']
        assert data['data']['role'] == 'citizen'
    finally:
        app.dependency_overrides.clear()
