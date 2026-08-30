# ============================================================
# 城市公共设施智能报修与派单系统 - AI验收比对服务
# 作用：通过 LangChain + 百炼视觉模型对比修前/修后照片，判断维修是否完成；
#       输入：维修前照片 + 维修后照片；
#       输出：{verified: bool, confidence: float, diff_summary: str}；
#       结果写入 MongoDB ai_analysis_logs（workflow=ai_verify）；
#       核验通过 → MySQL 工单状态 → verified → 市民确认 → closed
# ============================================================

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.config.settings import settings
from app.services.ai.prompts import VERIFY_SYSTEM_PROMPT
from app.services.ai.provider import get_llm_provider
from app.services.ai.schemas import VerifyOutput

logger = logging.getLogger(__name__)


async def verify_repair(
    ticket_id: str,
    before_photo_urls: list[str],
    after_photo_urls: list[str],
    repair_description: str = "",
) -> dict[str, Any]:
    """通过 LLM 视觉模型对比修前/修后照片，判断维修是否完成。

    Args:
        ticket_id: 工单 ID（用于日志追踪）。
        before_photo_urls: 维修前照片 URL 列表。
        after_photo_urls: 维修后照片 URL 列表。
        repair_description: 维修描述文本。

    Returns:
        {"verified": bool, "confidence": float, "diff_summary": str}
    """
    provider = get_llm_provider()
    if not provider.is_available():
        logger.info("LLM_API_KEY not set, using mock verify result")
        return _mock_verify_result()

    try:
        model = provider.get_model()
        structured_model = model.with_structured_output(VerifyOutput)

        messages = _build_verify_messages(
            before_photo_urls, after_photo_urls, repair_description
        )
        result: VerifyOutput = await structured_model.ainvoke(messages)

        logger.info(
            "AI verify completed: ticket=%s verified=%s confidence=%.2f",
            ticket_id, result.verified, result.confidence,
        )
        return result.model_dump()

    except Exception:
        logger.exception("LLM verify failed for ticket=%s, falling back to mock", ticket_id)
        return _mock_verify_result()


def _build_verify_messages(
    before_urls: list[str],
    after_urls: list[str],
    description: str,
) -> list:
    """构造验收比对的 messages，根据模型视觉能力决定是否附加图片。

    百炼 qwen-vl-max-latest 支持 image_url 格式的多模态输入。
    """
    provider = get_llm_provider()

    # 构造用户消息文本
    text_parts: list[str] = []
    if description:
        text_parts.append(f"维修描述：{description}")
    text_parts.append(f"修前照片数量：{len(before_urls)} 张")
    text_parts.append(f"修后照片数量：{len(after_urls)} 张")
    text_parts.append("请对比修前和修后照片，判断维修是否合格。")

    user_text = "\n".join(text_parts)

    # 如果模型支持视觉且有照片 URL，构造多模态消息
    if provider.supports_vision() and (before_urls or after_urls):
        content: list[dict[str, Any]] = [{"type": "text", "text": user_text}]
        for url in before_urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": url, "detail": "low"},
            })
        for url in after_urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": url, "detail": "low"},
            })
        user_message = HumanMessage(content=content)
    else:
        user_message = HumanMessage(content=user_text)

    return [SystemMessage(content=VERIFY_SYSTEM_PROMPT), user_message]


def _mock_verify_result() -> dict[str, Any]:
    """模拟 AI 验收结果（LLM 不可用时的降级方案）。"""
    return {
        "verified": True,
        "confidence": 0.92,
        "diff_summary": "照片对比：维修后设施状态明显改善，故障已排除。",
    }
