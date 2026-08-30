# ============================================================
# 城市公共设施智能报修与派单系统 - 管理后台结算管理 API
# 作用：GET /api/v1/admin/settlements — 结算单列表；
#       PUT /api/v1/admin/settlements/{id}/audit — 费用审核（通过/驳回）；
#       GET /api/v1/admin/settlements/export — 导出结算报表（PDF/Excel）
# 数据源：MySQL settlements + audit_rules + MongoDB repair_records 耗材成本
# ============================================================

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.config.mysql import get_db
from app.models.mysql.settlement import Settlement
from app.models.mysql.worker import Worker
from app.schemas.admin import SettlementAuditRequest
from app.schemas.common import APIResponse
from app.core.security import get_current_user

router = APIRouter()


@router.get("/settlements", response_model=APIResponse)
async def list_settlements(
    audit_status: str = "",
    ticket_id: str = "",
    worker_id: str = "",
    date_from: str = "",
    date_to: str = "",
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """结算单列表，支持按审核状态/工单号/维修员/日期范围筛选"""
    query = select(Settlement)
    count_query = select(func.count(Settlement.settlement_id))
    if audit_status:
        query = query.where(Settlement.audit_status == audit_status)
        count_query = count_query.where(Settlement.audit_status == audit_status)
    if ticket_id:
        query = query.where(Settlement.ticket_id.like(f"%{ticket_id}%"))
        count_query = count_query.where(Settlement.ticket_id.like(f"%{ticket_id}%"))
    if worker_id:
        query = query.where(Settlement.worker_id == worker_id)
        count_query = count_query.where(Settlement.worker_id == worker_id)
    if date_from:
        query = query.where(Settlement.created_at >= date_from)
        count_query = count_query.where(Settlement.created_at >= date_from)
    if date_to:
        query = query.where(Settlement.created_at <= f"{date_to} 23:59:59")
        count_query = count_query.where(Settlement.created_at <= f"{date_to} 23:59:59")
    query = query.order_by(Settlement.created_at.desc()).limit(page_size).offset((page - 1) * page_size)

    result = await db.execute(query)
    settlements = result.scalars().all()

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # 补充 worker_name
    worker_ids = list(set(s.worker_id for s in settlements if s.worker_id))
    id_to_name = {}
    if worker_ids:
        wr = await db.execute(select(Worker.worker_id, Worker.name).where(Worker.worker_id.in_(worker_ids)))
        id_to_name = {row.worker_id: row.name for row in wr.all()}

    return APIResponse(data={
        "items": [{
            "settlement_id": s.settlement_id,
            "ticket_id": s.ticket_id,
            "worker_id": s.worker_id,
            "worker_name": id_to_name.get(s.worker_id, ""),
            "labor_cost": s.labor_cost,
            "material_cost": s.material_cost,
            "total": s.total,
            "audit_status": s.audit_status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        } for s in settlements],
        "total": total,
    }).model_dump()


@router.put("/settlements/{settlement_id}/audit", response_model=APIResponse)
async def audit_settlement(
    settlement_id: str,
    req: SettlementAuditRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    结算审核：
    - 审核通过/驳回
    - 记录审核人
    """
    result = await db.execute(
        select(Settlement).where(Settlement.settlement_id == settlement_id)
    )
    settlement = result.scalar_one_or_none()
    if not settlement:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("结算单不存在")

    settlement.audit_status = req.action
    settlement.auditor_id = current_user["user_id"]
    await db.commit()

    return APIResponse(msg=f"审核{req.action}").model_dump()
