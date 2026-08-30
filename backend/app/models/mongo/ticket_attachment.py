# ============================================================
# 城市公共设施智能报修与派单系统 - ticket_attachments 工单附件文档
# 作用：存储报修照片（type=report_photo）和完工照片（type=completion_photo）的元数据；
#       image_url 指向 OSS，watermark_hash 防篡改，gps 存坐标；
#       ai_result 嵌入文档（故障类型、置信度、核验结果），无需 JOIN
# 对应 MongoDB Collection：ticket_attachments
# ============================================================

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.utils.timezone import now_beijing


class GPS(BaseModel):
    """GPS 坐标"""
    lng: float
    lat: float


class AIResult(BaseModel):
    """AI 视觉核验结果（嵌入文档）"""
    fault_type: Optional[str] = None
    confidence: Optional[float] = None
    verified: Optional[bool] = None


class TicketAttachment(BaseModel):
    """工单附件文档结构

    字段说明：
      - stage: 当前标准格式，取值 "report" | "completion"
      - image_urls: 当前标准格式，图片 URL 列表
      - type: 旧格式兼容，取值 "report_photo" | "completion_photo"
      - image_url: 旧格式兼容，单张图片 URL
    """
    ticket_id: str = Field(..., description="关联工单ID")
    # 当前标准字段
    stage: Optional[str] = Field(None, description="附件阶段: report | completion")
    image_urls: Optional[list[str]] = Field(None, description="OSS 图片 URL 列表")
    # 旧格式兼容字段
    type: Optional[str] = Field(None, description="[旧格式] 附件类型: report_photo | completion_photo")
    image_url: Optional[str] = Field(None, description="[旧格式] OSS 图片 URL（单张）")
    # 通用字段
    uploader_id: Optional[str] = Field(None, description="上传者ID")
    uploaded_by: Optional[str] = Field(None, description="上传者ID（新字段名）")
    gps: Optional[GPS] = Field(None, description="拍摄GPS坐标")
    timestamp: Optional[datetime] = Field(None, description="拍摄时间戳")
    watermark_hash: Optional[str] = Field(None, description="水印Hash防篡改")
    ai_result: Optional[AIResult] = Field(None, description="AI核验结果")
    ai_ocr_result: Optional[dict] = Field(None, description="AI OCR结果")
    created_at: datetime = Field(default_factory=now_beijing)

    class Config:
        json_schema_extra = {
            "example": {
                "ticket_id": "TK20260621001",
                "stage": "report",
                "image_urls": ["https://oss.example.com/photos/xxx.jpg"],
                "uploaded_by": "U001",
                "gps": {"lng": 112.9388, "lat": 28.2282},
                "timestamp": "2026-06-21T10:30:00",
                "watermark_hash": "e3b0c44298fc1c14...",
                "ai_result": {"fault_type": "灯杆倾斜", "confidence": 0.92, "verified": True},
            }
        }
