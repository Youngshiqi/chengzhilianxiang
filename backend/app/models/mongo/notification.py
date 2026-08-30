# ============================================================
# 城市公共设施智能报修与派单系统 - notifications 消息通知文档
# 作用：存储系统消息通知（工单进度推送、派单提醒、评价邀请、系统公告）；
#       content 字段因通知类型而异（Schema 不固定），MongoDB 天然适配；
#       按 user_id + is_read 索引支持未读消息快速查询
# 对应 MongoDB Collection：notifications
# ============================================================

from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.utils.timezone import now_beijing


class Notification(BaseModel):
    """消息通知文档结构"""
    user_id: str = Field(..., description="接收用户ID")
    type: str = Field(..., description="通知类型: dispatch/status_change/evaluation/system")
    content: Dict[str, Any] = Field(default_factory=dict, description="通知内容JSON（随类型变化）")
    is_read: bool = Field(default=False, description="是否已读")
    channel: str = Field("push", description="推送渠道: wechat/sms/push")
    ticket_id: Optional[str] = Field(None, description="关联工单ID")
    created_at: datetime = Field(default_factory=now_beijing)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "U001",
                "type": "status_change",
                "content": {
                    "title": "工单进展更新",
                    "body": "您的报修工单已由维修员张三接单，预计30分钟内到达",
                    "ticket_id": "TK20260621001",
                    "new_status": "repairing",
                },
                "is_read": False,
                "channel": "push",
            }
        }
