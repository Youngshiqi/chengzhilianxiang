# ============================================================
# 城市公共设施智能报修与派单系统 - ai_analysis_logs AI解析日志文档
# 作用：存储 Dify 三大工作流（nlp_parse/dispatch_score/ai_verify）的输入/输出JSON；
#       input/output 字段为任意 JSON Object，充分利用 MongoDB Schema 灵活特性；
#       不同工作流的返回结构差异大，MongoDB 天然适配无需 MySQL ALTER TABLE；
#       按 ticket_id 索引支持快速溯源 AI 决策过程
# 对应 MongoDB Collection：ai_analysis_logs
# ============================================================

from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.utils.timezone import now_beijing


class AIAnalysisLog(BaseModel):
    """AI 解析日志文档结构"""
    ticket_id: str = Field(..., description="关联工单ID")
    workflow: str = Field(
        ..., description="工作流类型: nlp_parse | dispatch_score | ai_verify"
    )
    input: Dict[str, Any] = Field(default_factory=dict, description="工作流输入参数JSON")
    output: Dict[str, Any] = Field(default_factory=dict, description="工作流输出结果JSON")
    confidence: Optional[float] = Field(None, description="AI置信度")
    model_version: Optional[str] = Field(None, description="模型版本号")
    created_at: datetime = Field(default_factory=now_beijing)

    class Config:
        json_schema_extra = {
            "example": {
                "ticket_id": "TK20260621001",
                "workflow": "nlp_parse",
                "input": {"text": "路灯不亮了，在建国路附近", "image_urls": []},
                "output": {
                    "category": "路灯故障",
                    "sub_category": "灯具不亮",
                    "address": "建国路100号",
                    "confidence": 0.95,
                },
                "confidence": 0.95,
                "model_version": "v2.1.0",
            }
        }
