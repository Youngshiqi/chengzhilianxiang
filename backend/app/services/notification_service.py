# ============================================================
# 城市公共设施智能报修与派单系统 - 通知服务
# 作用：创建和管理系统通知（派单提醒、状态变更等）
# ============================================================

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId

from app.config.mongodb import get_mongo_db
from app.utils.timezone import now_beijing

logger = logging.getLogger(__name__)


async def create_notification(
    user_id: str,
    notification_type: str,
    content: Dict[str, Any],
    ticket_id: Optional[str] = None,
    channel: str = "push",
) -> str:
    """
    创建通知

    Args:
        user_id: 接收用户ID
        notification_type: 通知类型: dispatch/status_change/evaluation/system
        content: 通知内容字典
        ticket_id: 关联工单ID
        channel: 推送渠道

    Returns:
        创建的通知ID
    """
    mongo_db = get_mongo_db()

    notification = {
        "user_id": user_id,
        "type": notification_type,
        "content": content,
        "is_read": False,
        "channel": channel,
        "ticket_id": ticket_id,
        "created_at": now_beijing(),
    }

    result = await mongo_db.notifications.insert_one(notification)
    logger.info(f"通知创建成功: user={user_id}, type={notification_type}")

    return str(result.inserted_id)


async def get_unread_notifications(user_id: str, limit: int = 50) -> List[Dict]:
    """获取用户未读通知"""
    mongo_db = get_mongo_db()

    cursor = mongo_db.notifications.find(
        {"user_id": user_id, "is_read": False}
    ).sort("created_at", -1).limit(limit)

    notifications = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        notifications.append(doc)

    return notifications


async def get_all_notifications(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict]:
    """获取用户所有通知（分页）"""
    mongo_db = get_mongo_db()

    cursor = mongo_db.notifications.find(
        {"user_id": user_id}
    ).sort("created_at", -1).skip(offset).limit(limit)

    notifications = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        notifications.append(doc)

    return notifications


async def count_unread(user_id: str) -> int:
    """统计用户未读通知数量"""
    mongo_db = get_mongo_db()
    return await mongo_db.notifications.count_documents(
        {"user_id": user_id, "is_read": False}
    )


async def mark_as_read(notification_id: str, user_id: str) -> bool:
    """标记通知为已读"""
    mongo_db = get_mongo_db()

    result = await mongo_db.notifications.update_one(
        {"_id": ObjectId(notification_id), "user_id": user_id},
        {"$set": {"is_read": True}}
    )

    return result.modified_count > 0


async def mark_all_as_read(user_id: str) -> int:
    """标记所有通知为已读"""
    mongo_db = get_mongo_db()

    result = await mongo_db.notifications.update_many(
        {"user_id": user_id, "is_read": False},
        {"$set": {"is_read": True}}
    )

    return result.modified_count


async def create_dispatch_notification(
    worker_id: str,
    ticket_id: str,
    facility_type: str,
    address: str,
    description: str,
    emergency_level: int = 0,
    is_auto_dispatch: bool = False,
) -> str:
    """
    创建派单通知（自动派单或管理员指派）

    Args:
        worker_id: 维修员ID
        ticket_id: 工单ID
        facility_type: 设施类型
        address: 地址
        description: 描述
        emergency_level: 紧急程度
        is_auto_dispatch: 是否为自动派单
    """
    title = "新工单已派给您" if is_auto_dispatch else "工单已指派给您"
    dispatch_type = "系统自动派单" if is_auto_dispatch else "管理员指派"

    content = {
        "title": title,
        "body": f"您有一个新的{facility_type}报修工单待处理",
        "ticket_id": ticket_id,
        "facility_type": facility_type,
        "address": address,
        "description": description[:100] if description else "",
        "emergency_level": emergency_level,
        "dispatch_type": dispatch_type,
    }

    return await create_notification(
        user_id=worker_id,
        notification_type="dispatch",
        content=content,
        ticket_id=ticket_id,
    )
