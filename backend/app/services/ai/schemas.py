# ============================================================
# 城市公共设施智能报修与派单系统 - AI 服务 Pydantic 输出模型
# 作用：定义 NLP 解析 / 派单评分 / AI 验收三个服务的结构化输出 schema；
#       配合 LangChain with_structured_output() 使用，LLM 直接返回验证后的对象；
#       每个模型 1:1 对应现有下游消费者期望的 dict 结构，零破坏性变更
# ============================================================

from pydantic import BaseModel, Field


class NLPOutput(BaseModel):
    """NLP 报修解析结构化输出 — 与 _normalize_nlp_outputs 返回的 dict 完全对应。"""

    # —— 核心分类字段 ——
    category: str = Field(
        default="其他设施",
        description="主要设施类别：路灯故障/道路破损/井盖异常/护栏损坏/环卫设施/交通信号设施/公共绿化/其他设施",
    )
    sub_category: str = Field(default="", description="具体子类别，如灯具不亮/路面坑洞/井盖缺失")
    address: str = Field(default="", description="报修描述中提及或推断的地址")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="分类置信度")
    emergency_level: int = Field(default=0, ge=0, le=1, description="紧急程度：0=普通，1=紧急")

    # —— 旧 Dify 字段别名（保留向后兼容） ——
    issue_category: str = Field(default="", description="category 的别名，设为相同值")
    subcategory: str = Field(default="", description="sub_category 的别名，设为相同值")
    urgency_level: int = Field(default=0, description="emergency_level 的别名，设为相同值")
    urgency_reason: str = Field(default="", description="标记为紧急的原因简述")
    key_info: list[str] = Field(default_factory=list, description="从描述中提取的关键信息（最多5条）")
    suggested_action: str = Field(default="", description="建议维修操作")
    priority_score: float = Field(default=0.0, ge=0.0, le=100.0, description="优先级分数 0-100")

    # —— 扩展字段 ——
    repair_knowledge: list[str] = Field(default_factory=list, description="相关维修知识（最多3条）")
    tools_needed: list[str] = Field(default_factory=list, description="所需工具（最多5项）")
    safety_tips: list[str] = Field(default_factory=list, description="安全注意事项（最多3条）")
    parts_needed: list[str] = Field(default_factory=list, description="所需零件/耗材（最多5项）")


class DimensionScores(BaseModel):
    """单个候选维修员的各维度评分。"""
    distance: float = Field(description="距离得分")
    load: float = Field(description="负载得分")
    rating: float = Field(description="好评率得分")
    response: float = Field(description="响应速度得分")


class CandidateScore(BaseModel):
    """单个候选维修员的综合评分。"""
    worker_id: str = Field(description="维修员ID")
    total_score: float = Field(description="加权总分")
    dimension_scores: DimensionScores


class DispatchScoreOutput(BaseModel):
    """派单评分结构化输出。"""
    selected_worker_id: str | None = Field(default=None, description="最优维修员ID，无合适人选时为null")
    scores: list[CandidateScore] = Field(default_factory=list, description="所有候选维修员评分列表")


class VerifyOutput(BaseModel):
    """AI 验收结构化输出。"""
    verified: bool = Field(description="维修是否通过验收")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="验收置信度")
    diff_summary: str = Field(default="", description="修前/修后对比摘要")
