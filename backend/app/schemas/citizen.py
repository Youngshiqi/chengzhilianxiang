# ============================================================
# 城市公共设施智能报修与派单系统 - 市民端 Schema
# 作用：定义市民端 API 的请求体/响应体校验规则；
#       覆盖：微信授权登录、AI报修提交、工单进度查询、服务评价
# ============================================================

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ---------- 登录 ----------
class SendSmsCodeRequest(BaseModel):
    """发送短信验证码请求"""
    phone_number: str = Field(..., min_length=11, max_length=11, description="手机号")
    scene: str = Field("login", description="场景: login=登录 register=注册")


class SmsLoginRequest(BaseModel):
    """短信验证码登录请求"""
    phone_number: str = Field(..., min_length=11, max_length=11, description="手机号")
    verify_code: str = Field(..., min_length=4, max_length=6, description="短信验证码")


class UsernameLoginRequest(BaseModel):
    """用户名+密码登录请求"""
    username: str = Field(..., min_length=2, max_length=64, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    lng: Optional[float] = Field(None, description="前端GPS经度（维修员上报）")
    lat: Optional[float] = Field(None, description="前端GPS纬度（维修员上报）")


class RegisterRequest(BaseModel):
    """用户名+密码注册请求"""
    username: str = Field(..., min_length=2, max_length=64, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    nickname: Optional[str] = Field(None, max_length=64, description="昵称")
    phone: Optional[str] = Field(None, max_length=16, description="手机号")
    verify_code: Optional[str] = Field(None, min_length=4, max_length=6, description="短信验证码")


class LoginResponse(BaseModel):
    """登录响应"""
    token: str = Field(..., description="JWT Token")
    user_id: str = Field(..., description="用户ID")
    role: str = Field(..., description="角色")
    name: str = Field("", description="用户姓名/昵称")


# ---------- 报修 ----------
class TicketCreateRequest(BaseModel):
    """市民报修请求"""
    description: str = Field(..., min_length=5, max_length=500, description="故障文字描述（必填）")
    facility_type: Optional[str] = Field(None, description="AI预填设施品类")
    location_lng: float = Field(..., description="经度")
    location_lat: float = Field(..., description="纬度")
    address: Optional[str] = Field(None, description="GPS反查地址")
    image_urls: List[str] = Field(default_factory=list, max_length=5, description="报修图片OSS URL列表")
    emergency_level: int = Field(0, ge=0, le=1, description="紧急程度 0普通 1紧急")


class TicketCreateResponse(BaseModel):
    """报修提交响应"""
    ticket_id: str = Field(..., description="工单ID")
    status: str = Field(..., description="工单状态")
    ai_category: Optional[str] = Field(None, description="AI识别故障分类")
    message: str = Field("报修已受理", description="受理回执")


# ---------- 工单进度 ----------
class TicketProgressResponse(BaseModel):
    """工单进度响应"""
    ticket_id: str
    status: str
    description: str
    timeline: List[dict] = Field(default_factory=list, description="全流程时间轴节点")
    worker_name: Optional[str] = Field(None, description="维修员（脱敏）")
    worker_location: Optional[dict] = Field(None, description="维修员位置（脱敏偏移）")
    created_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


# ---------- 评价 ----------
class EvaluationCreateRequest(BaseModel):
    """服务评价请求"""
    ticket_id: str = Field(..., description="工单ID")
    star: int = Field(..., ge=1, le=5, description="星级 1-5")
    tags: Optional[str] = Field(None, description="快捷标签（逗号分隔）")
    comment: Optional[str] = Field(None, max_length=500, description="文字评价")
