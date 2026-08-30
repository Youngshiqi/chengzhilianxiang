# ============================================================
# 城市公共设施智能报修与派单系统 - 全局配置模块（便捷导入）
# 作用：从 config.__init__ 导出 settings 单例，
#       其他模块统一通过 from app.config.settings import settings 获取配置
# ============================================================
from app.config import settings

__all__ = ["settings"]
