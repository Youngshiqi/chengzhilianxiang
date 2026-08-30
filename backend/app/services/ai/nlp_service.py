# ============================================================
# 城市公共设施智能报修与派单系统 - AI报修NLP解析服务
# 作用：通过 LangChain + 百炼 LLM 分析市民报修内容（文字+可选图片）；
#       输入：市民文字描述 + 图片URL列表 + 可选坐标；
#       输出：归一化的分类/紧急度/维修建议 dict（与旧 Dify 输出完全兼容）；
#       结果异步写入 MongoDB ai_analysis_logs（workflow=nlp_parse），不阻塞主流程
# ============================================================

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.config.settings import settings
from app.services.ai.prompts import NLP_SYSTEM_PROMPT
from app.services.ai.provider import get_llm_provider
from app.services.ai.schemas import NLPOutput

logger = logging.getLogger(__name__)


async def analyze_repair_request(
    text: str,
    image_urls: list[str] = None,
    lng: float = None,
    lat: float = None,
) -> dict[str, Any]:
    """通过 LLM 分析市民报修内容，返回归一化的分类/紧急度/维修建议。

    Args:
        text: 市民报修文字描述。
        image_urls: 可选图片 URL 列表（供视觉模型分析）。
        lng: 可选经度（用于辅助地址推断）。
        lat: 可选纬度（用于辅助地址推断）。

    Returns:
        兼容旧 Dify 输出格式的归一化 dict：
        - 旧系统字段：category, sub_category, address, confidence, emergency_level
        - 当前字段：issue_category, subcategory, urgency_level, urgency_reason 等
        - 扩展字段：repair_knowledge, tools_needed, safety_tips, parts_needed 等
    """
    provider = get_llm_provider()
    if not provider.is_available():
        logger.info("LLM_API_KEY not set, using mock NLP result")
        return _mock_nlp_result(text)

    try:
        model = provider.get_model()
        structured_model = model.with_structured_output(NLPOutput)

        messages = _build_nlp_messages(text, image_urls, lng, lat)
        result: NLPOutput = await structured_model.ainvoke(messages)

        logger.info(
            "NLP analysis completed: category=%s sub=%s confidence=%.2f emergency=%d",
            result.category, result.sub_category, result.confidence, result.emergency_level,
        )
        return _normalize_nlp_outputs(result)

    except Exception:
        logger.exception("LLM NLP analysis failed, falling back to mock")
        return _mock_nlp_result(text)


def _build_nlp_messages(
    text: str,
    image_urls: list[str] | None,
    lng: float | None,
    lat: float | None,
) -> list:
    """构造 NLP 分析的 messages，根据模型视觉能力决定是否附加图片。"""
    provider = get_llm_provider()

    # 构造用户消息文本
    user_parts: list[str] = [f"市民报修描述：{text}"]
    if lng is not None and lat is not None:
        user_parts.append(f"用户坐标：经度 {lng:.6f}，纬度 {lat:.6f}")
    user_parts.append("请分析以上报修内容，返回结构化结果。")

    user_text = "\n".join(user_parts)

    # 如果模型支持视觉且有图片 URL，构造多模态消息
    image_urls = image_urls or []
    if provider.supports_vision() and image_urls:
        content: list[dict[str, Any]] = [{"type": "text", "text": user_text}]
        for url in image_urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": url, "detail": "low"},
            })
        user_message = HumanMessage(content=content)
    else:
        user_message = HumanMessage(content=user_text)

    return [SystemMessage(content=NLP_SYSTEM_PROMPT), user_message]


def _normalize_nlp_outputs(outputs: NLPOutput | dict[str, Any]) -> dict[str, Any]:
    """将 Pydantic NLPOutput（或 mock dict）归一化为下游兼容的 dict。

    别名字段自动填充，确保 report_service / ticket_detail_service 读取不变。
    """
    if isinstance(outputs, NLPOutput):
        data = outputs.model_dump()
    elif isinstance(outputs, dict):
        data = outputs
    else:
        data = {}

    # 安全归一化核心字段
    category = _as_text(data.get("category") or data.get("issue_category")) or "其他设施"
    sub_category = _as_text(data.get("sub_category") or data.get("subcategory"))
    emergency_level = _normalize_emergency_level(
        data.get("emergency_level", data.get("urgency_level", 0))
    )
    confidence = _normalize_float(data.get("confidence"), 0.5)
    priority_score = _normalize_float(data.get("priority_score"), 0.0)

    normalized: dict[str, Any] = {
        "category": category,
        "sub_category": sub_category,
        "address": _as_text(data.get("address")),
        "confidence": confidence,
        "emergency_level": emergency_level,

        "issue_category": _as_text(data.get("issue_category")) or category,
        "subcategory": _as_text(data.get("subcategory")) or sub_category,
        "urgency_level": data.get("urgency_level") or emergency_level,
        "urgency_reason": _as_text(data.get("urgency_reason")),
        "key_info": data.get("key_info") or [],
        "suggested_action": _as_text(data.get("suggested_action")),
        "priority_score": priority_score,

        "repair_knowledge": data.get("repair_knowledge") or [],
        "tools_needed": data.get("tools_needed") or [],
        "safety_tips": data.get("safety_tips") or [],
        "parts_needed": data.get("parts_needed") or [],
    }

    # 透传额外字段，避免未来扩展字段丢失
    for key, value in data.items():
        normalized.setdefault(key, value)

    return normalized


def _normalize_emergency_level(value: Any) -> int:
    """统一紧急程度为 0/1，兼容数字和中文/英文紧急程度。"""
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return 1 if value >= 1 else 0
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "urgent", "high", "emergency"}:
            return 1
        if any(word in text for word in ("紧急", "高", "危险", "严重", "立即")):
            return 1
    return 0


def _normalize_float(value: Any, default: float) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


# ── Mock 降级知识库 ─────────────────────────────────────────
# 即使 LLM 不可用，维修工也能看到分类对应的标准维修知识/工具/零件/安全提示
# 这些数据来自《城市公共设施维修作业规范》，确保降级不降质量

_MOCK_KNOWLEDGE_BASE: dict[str, dict[str, Any]] = {
    "路灯故障": {
        "sub": "灯具不亮",
        "emergency_level": 0,
        "priority_score": 75.0,
        "urgency_reason": "",
        "suggested_action": "检查供电线路和灯具本体，优先排查电源是否正常，再检查灯板和驱动器",
        "key_info": ["夜间照明失效", "影响行人及车辆通行安全"],
        "repair_knowledge": [
            "路灯不亮常见原因：电源线断路、LED驱动电源损坏、灯板烧毁、控制器故障",
            "维修前需确认灯杆编号和供电回路，断开电源后用万用表逐级排查",
            "LED路灯标准色温4000K，更换灯板时需匹配原灯具功率和接口规格",
        ],
        "tools_needed": ["绝缘手套", "万用表", "螺丝刀套装", "绝缘胶带", "手电筒"],
        "parts_needed": ["LED灯板24W", "LED驱动电源", "接线端子"],
        "safety_tips": [
            "作业前必须断电并验电，严禁带电操作",
            "夜间作业需穿戴反光背心，设置警示锥和警示灯",
            "登高作业需两人协同，一人操作一人监护",
        ],
    },
    "道路破损": {
        "sub": "路面坑洞",
        "emergency_level": 0,
        "priority_score": 65.0,
        "urgency_reason": "",
        "suggested_action": "评估坑洞面积和深度，小面积用冷补沥青临时修复，大面积需切割规整后分层回填",
        "key_info": ["路面坑洞", "影响行车安全", "雨天积水加重破损"],
        "repair_knowledge": [
            "小坑洞（<0.5㎡）：清理碎渣后填入冷补沥青，夯实即可",
            "大坑洞（>0.5㎡）：切割成规则矩形，分层回填热拌沥青混凝土并压实",
            "雨天应急：先用钢板覆盖保证通行，天晴后再永久修复",
        ],
        "tools_needed": ["冷补沥青", "夯实机", "切割机", "吹风机", "钢尺"],
        "parts_needed": ["冷补沥青料", "乳化沥青粘层油", "热拌沥青混凝土"],
        "safety_tips": [
            "作业区域前后50米设置施工警示牌和锥形桶",
            "施工人员必须穿反光背心，夜间加配爆闪灯",
            "开放通行前确认沥青已冷却至50℃以下",
        ],
    },
    "井盖异常": {
        "sub": "井盖缺失",
        "emergency_level": 1,
        "priority_score": 95.0,
        "urgency_reason": "井盖缺失有行人坠落和车辆陷落风险，属于严重安全隐患",
        "suggested_action": "立即用临时围挡封闭井口，测量井口尺寸后更换匹配井盖并固定",
        "key_info": ["井盖缺失或破损", "行人坠落风险", "需立即处置"],
        "repair_knowledge": [
            "井盖规格需匹配井口直径（常用φ700/φ800），材质分铸铁和复合材料",
            "安装时井座需坐浆找平，井盖与路面高差不超过5mm",
            "防盗井盖需加装防坠网，承载等级需匹配道路荷载（D400/C250）",
        ],
        "tools_needed": ["临时围挡", "撬棍", "水平尺", "抹子", "卷尺"],
        "parts_needed": ["铸铁/复合材料井盖", "井座", "防坠网", "水泥砂浆"],
        "safety_tips": [
            "发现缺失井盖必须立即设置临时围挡，严禁离开现场直到围挡到位",
            "搬运铸铁井盖需两人配合，单块重量可达50kg以上",
            "施工时注意井下气体安全，必要时先通风后作业",
        ],
    },
    "护栏损坏": {
        "sub": "护栏断裂",
        "emergency_level": 0,
        "priority_score": 60.0,
        "urgency_reason": "",
        "suggested_action": "拆除损坏段护栏，按原规格更换新护栏并焊接/螺栓固定",
        "key_info": ["护栏断裂或变形", "失去防护功能"],
        "repair_knowledge": [
            "护栏材质分镀锌钢管和不锈钢，更换时需匹配原规格（管径、壁厚、高度）",
            "焊接处需做防锈处理（刷防锈漆两遍），螺栓连接需加弹簧垫圈防松",
            "护栏立柱基础松动时需重新浇筑混凝土底座",
        ],
        "tools_needed": ["电焊机", "角磨机", "扳手套装", "水平尺", "卷尺"],
        "parts_needed": ["镀锌钢管", "法兰底座", "防锈漆", "膨胀螺栓"],
        "safety_tips": [
            "焊接作业需佩戴防护面罩和焊接手套",
            "施工区域设置警示带，防止行人靠近",
            "拆除旧护栏时注意断口锋利，戴防割手套",
        ],
    },
    "环卫设施": {
        "sub": "垃圾桶损坏",
        "emergency_level": 0,
        "priority_score": 45.0,
        "urgency_reason": "",
        "suggested_action": "更换损坏的垃圾桶，清理周边散落垃圾并进行消杀",
        "key_info": ["垃圾桶破损或缺失", "影响市容环境卫生"],
        "repair_knowledge": [
            "垃圾桶常用规格：240L/660L塑料桶或分类不锈钢桶",
            "更换垃圾桶后需重新喷涂分类标识（可回收/其他/厨余/有害）",
            "底座松动时需用膨胀螺栓重新固定",
        ],
        "tools_needed": ["扳手", "膨胀螺栓", "电钻", "扫帚", "消毒喷壶"],
        "parts_needed": ["分类垃圾桶", "分类标识贴", "膨胀螺栓"],
        "safety_tips": [
            "清理垃圾桶时佩戴手套和口罩，注意玻璃碎片等尖锐物",
            "更换完毕后用消毒液对桶体及周边进行消杀",
        ],
    },
    "交通信号设施": {
        "sub": "信号灯故障",
        "emergency_level": 1,
        "priority_score": 90.0,
        "urgency_reason": "信号灯故障可能导致交通混乱和事故，属于紧急情况",
        "suggested_action": "立即上报交警部门，检查信号机控制器和灯组，更换故障模块",
        "key_info": ["信号灯不亮或显示异常", "影响交通秩序", "事故风险"],
        "repair_knowledge": [
            "信号灯故障分：全灭（供电问题）、单灯不亮（灯组损坏）、黄闪（控制器异常）",
            "检修前需联系交警指挥中心切换到黄闪或手动指挥模式",
            "LED信号灯模组寿命约50000小时，老化后光衰超过30%需更换",
        ],
        "tools_needed": ["绝缘手套", "万用表", "信号机调试工具", "安全帽"],
        "parts_needed": ["LED信号灯模组", "保险丝", "接线端子"],
        "safety_tips": [
            "必须配合交警现场指挥方可作业，严禁独自操作",
            "登高作业时注意避让来往车辆",
            "带电检测需两人配合，一人操作一人监护",
        ],
    },
    "公共绿化": {
        "sub": "树木倒伏",
        "emergency_level": 1,
        "priority_score": 85.0,
        "urgency_reason": "倒伏树木可能阻塞道路或压坏设施，大风天气风险更高",
        "suggested_action": "先清理倒伏树木保障通行，再补种或加固周边树木",
        "key_info": ["树木倒伏或断枝", "阻碍交通", "可能损坏设施"],
        "repair_knowledge": [
            "倒伏树木处理：先锯断枝干分段清运，再挖出根系或原地扶正加固",
            "扶正后需用支撑架三角加固，浇透定根水，涂伤口愈合剂",
            "汛期前应对行道树进行疏枝修剪，减少风阻",
        ],
        "tools_needed": ["油锯", "绳索", "支撑木杆", "铁锹", "手锯"],
        "parts_needed": ["支撑木杆", "草绳", "伤口愈合剂", "营养液"],
        "safety_tips": [
            "油锯操作需持证上岗，佩戴防护面罩和防割裤",
            "清理倒伏树木时注意上方电线，保持安全距离",
            "大风天气禁止登高修剪作业",
        ],
    },
}

# 未知故障的默认降级数据
_MOCK_DEFAULT: dict[str, Any] = {
    "category": "其他设施",
    "sub_category": "未知故障",
    "address": "GPS反查地址（模拟）",
    "confidence": 0.50,
    "emergency_level": 0,
    "priority_score": 40.0,
    "urgency_reason": "",
    "suggested_action": "建议现场勘查后根据实际情况确定维修方案",
    "key_info": ["故障类型待现场确认"],
    "repair_knowledge": ["到达现场后先评估故障范围和严重程度", "拍照记录现场情况，必要时请求技术支持"],
    "tools_needed": ["基础工具套装", "手电筒", "卷尺", "相机/手机"],
    "parts_needed": ["待现场勘查后确定"],
    "safety_tips": ["到达现场后先评估安全风险", "必要时设置警示标识"],
}


def _mock_nlp_result(text: str) -> dict[str, Any]:
    """模拟 NLP 结果（LLM 不可用时的降级方案）。

    关键词匹配到设施类别后，返回该类别对应的标准维修知识库数据，
    包括维修知识、工具、零件、安全提示等，确保即使 LLM 不可用，
    维修工也能在 H5 端看到有用的指导信息。
    """
    # 按匹配优先级排序：长词优先，避免"信号灯"被"灯"误匹配
    keyword_map = [
        ("信号灯", "交通信号设施"),
        ("红绿灯", "交通信号设施"),
        ("绿化", "公共绿化"),
        ("树木", "公共绿化"),
        ("垃圾桶", "环卫设施"),
        ("垃圾", "环卫设施"),
        ("井盖", "井盖异常"),
        ("护栏", "护栏损坏"),
        ("路灯", "路灯故障"),
        ("路面", "道路破损"),
        ("道路", "道路破损"),
        ("树", "公共绿化"),
        ("花", "公共绿化"),
        ("草", "公共绿化"),
        ("灯", "路灯故障"),
        ("路", "道路破损"),
        ("井", "井盖异常"),
        ("栏", "护栏损坏"),
        ("桶", "环卫设施"),
    ]
    for keyword, category in keyword_map:
        if keyword in text:
            if category in _MOCK_KNOWLEDGE_BASE:
                info = _MOCK_KNOWLEDGE_BASE[category]
                return _normalize_nlp_outputs({
                    "category": category,
                    "sub_category": info["sub"],
                    "address": "GPS反查地址（模拟）",
                    "confidence": 0.85,
                    "emergency_level": info["emergency_level"],
                    "priority_score": info["priority_score"],
                    "urgency_reason": info["urgency_reason"],
                    "suggested_action": info["suggested_action"],
                    "key_info": info["key_info"],
                    "repair_knowledge": info["repair_knowledge"],
                    "tools_needed": info["tools_needed"],
                    "parts_needed": info["parts_needed"],
                    "safety_tips": info["safety_tips"],
                })
            return _normalize_nlp_outputs({
                "category": category,
                "sub_category": _MOCK_KNOWLEDGE_BASE.get(category, {}).get("sub", ""),
                "address": "GPS反查地址（模拟）",
                "confidence": 0.85,
                "emergency_level": 0,
            })
    return _normalize_nlp_outputs(_MOCK_DEFAULT)
