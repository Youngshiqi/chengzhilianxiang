# ============================================================
# 城市公共设施智能报修与派单系统 - MongoDB 连接管理
# 作用：管理 MongoDB 异步客户端（Motor），负责五个 Collection 的读写；
#       - ticket_attachments: 工单图片元数据 + AI视觉核验结果
#       - ai_analysis_logs: Dify 三大工作流输入/输出 JSON
#       - repair_records: 维修详情（耗材数组、工时、签到坐标）
#       - audit_logs: 后台操作审计日志（append-only，不可篡改）
#       - notifications: 系统消息通知（Schema不固定）
# ============================================================

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config.settings import settings

mongo_client: AsyncIOMotorClient = None
mongo_db: AsyncIOMotorDatabase = None


async def init_mongodb():
    """应用启动时：连接 MongoDB 并获取数据库引用"""
    global mongo_client, mongo_db

    if settings.MONGO_USER and settings.MONGO_PASSWORD:
        uri = (
            f"mongodb://{settings.MONGO_USER}:{settings.MONGO_PASSWORD}"
            f"@{settings.MONGO_HOST}:{settings.MONGO_PORT}"
            f"/?authSource=admin"
        )
    else:
        uri = f"mongodb://{settings.MONGO_HOST}:{settings.MONGO_PORT}"
    # 异步客户端
    mongo_client = AsyncIOMotorClient(uri)
    # 获取数据库实例
    mongo_db = mongo_client[settings.MONGO_DATABASE]

    # 创建索引（幂等操作）
    await _create_indexes()


async def _create_indexes():
    """创建各 Collection 的查询索引"""
    # ticket_id 在各 Collection 中均为高频查询字段
    # 图片 按 ticket_id 索引
    await mongo_db.ticket_attachments.create_index("ticket_id")
    # ai 日志
    await mongo_db.ai_analysis_logs.create_index("ticket_id")
    # 维修记录
    await mongo_db.repair_records.create_index("ticket_id")
    # 审计日志按创建时间降序索引
    await mongo_db.audit_logs.create_index([("created_at", -1)])
    # 审计日志按操作员ID索引
    await mongo_db.audit_logs.create_index("operator_id")
    # 通知按用户ID + 已读状态联合索引
    await mongo_db.notifications.create_index([("user_id", 1), ("is_read", 1)])


async def close_mongodb():
    """应用关闭时：释放 MongoDB 连接"""
    if mongo_client:
        mongo_client.close()


def get_mongo_db() -> AsyncIOMotorDatabase:
    """依赖注入：获取 MongoDB 数据库实例"""
    return mongo_db
