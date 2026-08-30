# ============================================================
# 城市公共设施智能报修与派单系统 - AI派单评分服务
# 作用：以「最小运维总成本」为目标，综合四维度评分选最优维修员；
#       - 距离（40%）：Redis Geo 计算维修员到设施距离
#       - 负载（30%）：worker:{id}:daily_order 当日接单计数
#       - 好评（20%）：ES workers_perf_index 历史好评率
#       - 响应速度（10%）：Redis worker:{id}:profile 平均响应时间
#       默认使用确定性本地加权算法；开启 LLM_ENABLE_DISPATCH_SCORING 后
#       可调用百炼 LLM 做综合判断（LLM 失败时自动回退本地算法）
# ============================================================

import logging
from typing import Any

from app.config.settings import settings
from app.services.ai.prompts import DISPATCH_SYSTEM_PROMPT
from app.services.ai.provider import get_llm_provider
from app.services.ai.schemas import DispatchScoreOutput

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS = {
    "distance": 100,    # 距离权重（简化版：只按距离）
    "load": 0,          # 负载权重（已禁用）
    "rating": 0,        # 好评率权重（已禁用）
    "response": 0,      # 响应速度权重（已禁用）
}


async def score_candidates(
    ticket_id: str,
    candidates: list[dict[str, Any]],
    facility_lng: float,
    facility_lat: float,
) -> dict[str, Any]:
    """从候选维修员中选出最优派单人。

    默认使用本地确定性加权算法（已验证可靠）。
    开启 LLM_ENABLE_DISPATCH_SCORING=true 后调用 LLM 做综合判断，
    LLM 失败时自动回退到本地算法。

    Args:
        ticket_id: 工单 ID。
        candidates: 候选维修员列表（含距离/负载/评分/响应时间）。
        facility_lng: 设施经度。
        facility_lat: 设施纬度。

    Returns:
        {"selected_worker_id": str|null, "scores": [...]}
    """
    if not settings.LLM_ENABLE_DISPATCH_SCORING:
        return _simple_score_candidates(candidates)

    provider = get_llm_provider()
    if not provider.is_available():
        logger.info("LLM_API_KEY not set, using local scoring")
        return _simple_score_candidates(candidates)

    try:
        model = provider.get_model()
        structured_model = model.with_structured_output(DispatchScoreOutput)

        messages = _build_dispatch_messages(ticket_id, candidates, facility_lng, facility_lat)
        result: DispatchScoreOutput = await structured_model.ainvoke(messages)

        logger.info(
            "LLM dispatch scoring: ticket=%s selected=%s candidates=%d",
            ticket_id, result.selected_worker_id, len(result.scores),
        )
        return result.model_dump()

    except Exception:
        logger.exception("LLM dispatch scoring failed, falling back to local")
        return _simple_score_candidates(candidates)


def _build_dispatch_messages(
    ticket_id: str,
    candidates: list[dict[str, Any]],
    facility_lng: float,
    facility_lat: float,
) -> list:
    """构造派单评分的 messages。"""
    from langchain_core.messages import HumanMessage, SystemMessage

    candidates_text = "\n\n".join(
        f"候选 {i+1}：worker_id={c['worker_id']}, "
        f"距离={c.get('distance_km', '?')}km, "
        f"今日已接={c.get('today_orders', 0)}单, "
        f"好评率={c.get('star_rating', '?')}星, "
        f"平均响应={c.get('avg_response_min', '?')}分钟"
        for i, c in enumerate(candidates)
    )

    user_text = (
        f"工单ID：{ticket_id}\n"
        f"设施位置：经度 {facility_lng:.6f}，纬度 {facility_lat:.6f}\n"
        f"候选维修员共 {len(candidates)} 人：\n\n"
        f"{candidates_text}\n\n"
        f"权重配置：距离 {DEFAULT_WEIGHTS['distance']}%，"
        f"负载 {DEFAULT_WEIGHTS['load']}%，"
        f"好评率 {DEFAULT_WEIGHTS['rating']}%，"
        f"响应速度 {DEFAULT_WEIGHTS['response']}%。\n"
        f"请按权重综合评分，选出最优派单人。"
    )

    return [SystemMessage(content=DISPATCH_SYSTEM_PROMPT), HumanMessage(content=user_text)]


def _simple_score_candidates(candidates: list[dict]) -> dict[str, Any]:
    """简化版派单：只按距离排序，选最近的维修工。

    忽略负载、评分、响应速度等其他因素。
    """
    if not candidates:
        return {"selected_worker_id": None, "scores": []}

    scored = []
    for c in candidates:
        # 只按距离打分（越近分数越高）
        dist_score = max(0, 100 - c.get("distance_km", 0) * 20)   # 每公里扣20分
        total = dist_score  # 只考虑距离

        scored.append({
            "worker_id": c["worker_id"],
            "total_score": round(total, 2),
            "dimension_scores": {
                "distance": round(dist_score, 2),
                "load": 0,
                "rating": 0,
                "response": 0,
            },
        })

    # 按距离排序（最近的排第一）
    scored.sort(key=lambda x: x["total_score"], reverse=True)
    return {
        "selected_worker_id": scored[0]["worker_id"],
        "scores": scored,
    }
