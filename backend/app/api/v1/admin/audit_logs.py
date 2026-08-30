# ============================================================
# 城市公共设施智能报修与派单系统 - 管理后台审计日志 API
# 作用：GET /api/v1/admin/audit-logs — 审计日志查询（MongoDB audit_logs Collection）；
#       支持按操作人、操作类型、时间范围筛选；
#       全系统后台操作记录（强制指派、工单冻结、配置修改等）
# ============================================================

from fastapi import APIRouter, Depends

from app.config.mongodb import get_mongo_db
from app.schemas.common import APIResponse
from app.core.security import get_current_user

router = APIRouter()


@router.get("/audit-logs", response_model=APIResponse)
async def query_audit_logs(
    operator_id: str = "",
    action: str = "",
    date_from: str = "",
    date_to: str = "",
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user),
    mongo_db=Depends(get_mongo_db),
):
    """
    审计日志查询（MongoDB audit_logs）：
    - 按操作人、操作类型、时间范围筛选
    - 按时间倒序排列
    - 审计日志 append-only，不可篡改
    """
    filter_query = {}
    if operator_id:
        filter_query["operator_id"] = operator_id
    if action:
        filter_query["action"] = action
    if date_from or date_to:
        created_filter = {}
        if date_from:
            created_filter["$gte"] = date_from
        if date_to:
            created_filter["$lte"] = f"{date_to}T23:59:59"
        filter_query["created_at"] = created_filter

    skip = (page - 1) * page_size
    cursor = mongo_db.audit_logs.find(filter_query).sort("created_at", -1).skip(skip).limit(page_size)
    logs = await cursor.to_list(length=page_size)

    items = []
    for log in logs:
        log["_id"] = str(log["_id"])  # ObjectId 转字符串
        items.append(log)

    total = await mongo_db.audit_logs.count_documents(filter_query)

    return APIResponse(data={"items": items, "total": total}).model_dump()
