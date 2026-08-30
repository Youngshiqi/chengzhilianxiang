# ============================================================
# 城市公共设施智能报修与派单系统 - LLM Provider 抽象层
# 作用：封装 ChatOpenAI（兼容阿里云百炼 DashScope），提供懒加载、
#       视觉能力检测、全局单例；各 AI 服务通过 get_llm_provider() 获取
# ============================================================

import logging

from langchain_openai import ChatOpenAI

from app.config.settings import settings

logger = logging.getLogger(__name__)

# 视觉模型名前缀列表（用于 supports_vision 判断）
_VISION_MODEL_PREFIXES = ("qwen-vl", "qwen3-vl", "gpt-4o", "gpt-4-turbo", "gpt-4.1", "claude-3")


class LLMProvider:
    """LLM 提供者，封装 ChatOpenAI 实例的懒加载和配置。

    通过阿里云百炼 DashScope 的 OpenAI 兼容接口调用：
        base_url = https://dashscope.aliyuncs.com/compatible-mode/v1
        默认模型 = qwen-vl-max-latest（支持图片理解）

    Usage:
        provider = get_llm_provider()
        if provider.is_available():
            model = provider.get_model()
            result = await model.with_structured_output(MySchema).ainvoke(messages)
    """

    def __init__(self) -> None:
        self._model: ChatOpenAI | None = None

    def is_available(self) -> bool:
        """LLM 是否可用：API Key 已配置。"""
        return bool(settings.LLM_API_KEY)

    def supports_vision(self) -> bool:
        """当前模型是否支持图片输入。"""
        model_name = settings.LLM_MODEL_NAME.lower()
        return any(model_name.startswith(prefix) for prefix in _VISION_MODEL_PREFIXES)

    def get_model(self) -> ChatOpenAI:
        """获取 ChatOpenAI 实例（懒加载，首次调用时创建）。

        Returns:
            ChatOpenAI: 已配置的 LLM 客户端实例。

        Raises:
            RuntimeError: LLM_API_KEY 未配置时调用。
        """
        if not self.is_available():
            raise RuntimeError(
                "LLM_API_KEY is not configured. "
                "Set LLM_API_KEY in .env to enable AI features."
            )

        if self._model is None:
            self._model = ChatOpenAI(
                model=settings.LLM_MODEL_NAME,
                temperature=settings.LLM_TEMPERATURE,
                openai_api_key=settings.LLM_API_KEY,
                openai_api_base=settings.LLM_BASE_URL,
            )
            logger.info(
                "LLM provider initialized: model=%s base_url=%s",
                settings.LLM_MODEL_NAME,
                settings.LLM_BASE_URL,
            )

        return self._model

    def reset(self) -> None:
        """重置模型实例（配置变更后需要重建时调用）。"""
        self._model = None
        logger.info("LLM provider reset")


# 模块级单例
_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    """获取全局 LLMProvider 单例。"""
    global _provider
    if _provider is None:
        _provider = LLMProvider()
    return _provider
