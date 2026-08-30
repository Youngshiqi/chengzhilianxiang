# ============================================================
# 城市公共设施智能报修与派单系统 - 维修员通知 API
# 作用：获取通知列表、标记已读等
# ============================================================

import logging
from fastapi import APIRouter, Depends, Query

from app.config.mysql import get_db
from app.schemas.common import APIResponse
from app.core.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/unread", response_model=APIResponse)
async def get_unread_notifications(
    current_user: dict = Depends(get_current_user),
):
    """获取维修员未读通知列表"""
    from app.services.notification_service import get_unread_notifications, count_unread

    worker_id = current_user["user_id"]
    notifications = await get_unread_notifications(worker_id)
    unread_count = await count_unread(worker_id)

    return APIResponse(data={
        "notifications": notifications,
        "unread_count": unread_count,
    }).model_dump()


@router.get("", response_model=APIResponse)
async def get_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """获取维修员所有通知列表（分页）"""
    from app.services.notification_service import get_all_notifications, count_unread

    worker_id = current_user["user_id"]
    offset = (page - 1) * page_size

    notifications = await get_all_notifications(worker_id, limit=page_size, offset=offset)
    unread_count = await count_unread(worker_id)

    return APIResponse(data={
        "notifications": notifications,
        "unread_count": unread_count,
        "page": page,
        "page_size": page_size,
    }).model_dump()


@router.put("/{notification_id}/read", response_model=APIResponse)
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
):
    """标记通知为已读"""
    from app.services.notification_service import mark_as_read

    worker_id = current_user["user_id"]
    success = await mark_as_read(notification_id, worker_id)

    return APIResponse(
        msg="标记成功" if success else "标记失败",
        data={"success": success},
    ).model_dump()


@router.put("/read-all", response_model=APIResponse)
async def mark_all_notifications_read(
    current_user: dict = Depends(get_current_user),
):
    """标记所有通知为已读"""
    from app.services.notification_service import mark_all_as_read

    worker_id = current_user["user_id"]
    count = await mark_all_as_read(worker_id)

    return APIResponse(
        msg=f"已标记 {count} 条通知为已读",
        data={"marked_count": count},
    ).model_dump()
