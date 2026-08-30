# ============================================================
# 城市公共设施智能报修与派单系统 - audit_logs 操作审计日志文档
# 作用：全系统后台操作审计记录（强制指派、工单冻结、配置修改等）；
#       old_value/new_value 为任意 JSON 对象，满足政务合规审计溯源需求；
#       append-only 权限，禁止 DELETE/UPDATE 操作，保证审计数据不可篡改；
#       通过 Logstash 管道同步至 ES audit_log_index 支持全文检索
# 对应 MongoDB Collection：audit_logs
# ============================================================

from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.utils.timezone import now_beijing


class ActionTarget(BaseModel):
    """操作目标实体"""
    type: str = Field(..., description="目标类型: ticket/worker/config/settlement")
    id: str = Field(..., description="目标ID")


class AuditLog(BaseModel):
    """操作审计日志文档结构"""
    operator_id: str = Field(..., description="操作人ID")
    role: str = Field(..., description="操作人角色: citizen/worker/admin")
    action: str = Field(..., description="操作类型: force_dispatch/freeze_ticket/update_config")
    target: ActionTarget = Field(..., description="操作目标")
    old_value: Optional[Dict[str, Any]] = Field(None, description="操作前快照")
    new_value: Optional[Dict[str, Any]] = Field(None, description="操作后快照")
    ip: str = Field("0.0.0.0", description="操作IP")
    ua: str = Field("", description="User-Agent")
    created_at: datetime = Field(default_factory=now_beijing)

    class Config:
        json_schema_extra = {
            "example": {
                "operator_id": "A001",
                "role": "admin",
                "action": "force_dispatch",
                "target": {"type": "ticket", "id": "TK20260621001"},
                "old_value": {"assigned_worker_id": None},
                "new_value": {"assigned_worker_id": "W003"},
                "ip": "192.168.1.100",
                "ua": "Mozilla/5.0...",
            }
        }
