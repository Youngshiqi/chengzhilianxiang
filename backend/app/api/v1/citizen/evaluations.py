# ============================================================
# 城市公共设施智能报修与派单系统 - 市民端评价 API
# 作用：POST /api/v1/citizen/evaluations — 市民提交服务评价（星级+标签+文字）；
#       委托 evaluation_service 处理：MySQL写入 / 差评复核 / ES绩效同步 / MongoDB通知
# ============================================================

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.mysql import get_db
from app.schemas.citizen import EvaluationCreateRequest
from app.schemas.common import APIResponse
from app.core.security import get_current_user
from app.core.exceptions import ConflictException
from app.services.citizen.evaluation_service import submit_evaluation

router = APIRouter()


@router.post("/evaluations", response_model=APIResponse)
async def create_evaluation(
    req: EvaluationCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    市民提交服务评价：
    - 委托 evaluation_service 编排全部业务逻辑
    """
    try:
        result = await submit_evaluation(
            db=db,
            ticket_id=req.ticket_id,
            user_id=current_user["user_id"],
            star=req.star,
            tags=req.tags or "",
            comment=req.comment or "",
        )
    except Exception:
        raise ConflictException("该工单已评价，请勿重复提交")

    return APIResponse(msg="评价提交成功", data={"eval_id": result["eval_id"]}).model_dump()
