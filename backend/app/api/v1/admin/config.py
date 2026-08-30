# ============================================================
# 城市公共设施智能报修与派单系统 - 管理后台系统配置 API
# 作用：GET /admin/config — 读取结算规则配置（支持搜索+分页）；
#       PUT /admin/config — 批量更新结算规则
# ============================================================

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.config.mysql import get_db
from app.models.mysql.audit_rule import AuditRule
from app.schemas.common import APIResponse
from app.core.security import get_current_user
from app.core.exceptions import BadRequestException

router = APIRouter()


class ConfigItem(BaseModel):
    rule_id: str
    facility_type: str
    base_price: float
    overtime_rate: float
    emergency_multiplier: float
    night_subsidy: float


class ConfigUpdateRequest(BaseModel):
    items: List[ConfigItem] = Field(..., min_length=1, description="配置项列表")


class ConfigCreateRequest(BaseModel):
    facility_type: str = Field(..., min_length=1, max_length=32, description="设施品类名称")
    base_price: float = Field(50.0, ge=5, le=500, description="基础单价")
    overtime_rate: float = Field(1.5, ge=1, le=5, description="加班费率")
    emergency_multiplier: float = Field(2.0, ge=1, le=5, description="紧急倍率")
    night_subsidy: float = Field(30.0, ge=0, le=200, description="夜班补贴")


@router.get("/config", response_model=APIResponse)
async def get_config(
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """读取结算规则配置，支持按品类关键词搜索 + 分页"""
    query = select(AuditRule)
    count_query = select(func.count(AuditRule.rule_id))
    if keyword:
        query = query.where(AuditRule.facility_type.like(f"%{keyword}%"))
        count_query = count_query.where(AuditRule.facility_type.like(f"%{keyword}%"))
    query = query.order_by(AuditRule.rule_id).limit(page_size).offset((page - 1) * page_size)

    result = await db.execute(query)
    rules = result.scalars().all()

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    items = [{
        "rule_id": r.rule_id,
        "facility_type": r.facility_type,
        "base_price": float(r.base_price),
        "overtime_rate": float(r.overtime_rate),
        "emergency_multiplier": float(r.emergency_multiplier),
        "night_subsidy": float(r.night_subsidy),
    } for r in rules]

    return APIResponse(data={"items": items, "total": total}).model_dump()


@router.put("/config", response_model=APIResponse)
async def update_config(
    req: ConfigUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量更新结算规则配置"""
    for item in req.items:
        result = await db.execute(
            select(AuditRule).where(AuditRule.rule_id == item.rule_id)
        )
        rule = result.scalar_one_or_none()
        if rule is None:
            continue
        rule.base_price = item.base_price
        rule.overtime_rate = item.overtime_rate
        rule.emergency_multiplier = item.emergency_multiplier
        rule.night_subsidy = item.night_subsidy

    await db.commit()
    return APIResponse(msg="配置已更新").model_dump()


@router.post("/config", response_model=APIResponse, status_code=201)
async def create_config(
    req: ConfigCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """新增设施品类结算规则"""
    # 检查是否已存在
    existing = await db.execute(
        select(AuditRule).where(AuditRule.facility_type == req.facility_type)
    )
    if existing.scalar_one_or_none():
        raise BadRequestException(f"设施品类「{req.facility_type}」的结算规则已存在")

    rule = AuditRule(
        rule_id=f"rule_{uuid.uuid4().hex[:12]}",
        facility_type=req.facility_type,
        base_price=req.base_price,
        overtime_rate=req.overtime_rate,
        emergency_multiplier=req.emergency_multiplier,
        night_subsidy=req.night_subsidy,
    )
    db.add(rule)
    await db.commit()

    return APIResponse(
        msg=f"已添加「{req.facility_type}」结算规则",
        data={"rule_id": rule.rule_id},
    ).model_dump()
