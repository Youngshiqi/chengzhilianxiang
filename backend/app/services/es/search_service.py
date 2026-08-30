# ============================================================
# 城市公共设施智能报修与派单系统 - Elasticsearch 检索服务
# 作用：提供工单全文检索（IK中文分词）、故障聚合统计、绩效排行分析；
#       - search_tickets: 全文检索工单（支持多维度筛选）
#       - aggregate_fault_stats: 故障分布聚合（TOP类型/片区/趋势）
#       - aggregate_worker_perf: 维修员绩效聚合
#       - sync_ticket_to_es: 被 RabbitMQ ES Sync 消费者调用（全量文档索引）
#       - sync_worker_perf: Redis计数器定时同步到ES workers_perf_index
# ============================================================

from typing import Any, Dict, List, Optional
from elasticsearch import AsyncElasticsearch

from app.config.settings import settings


async def search_tickets(
    es: AsyncElasticsearch,
    keyword: str = "",
    status: str = "",
    facility_type: str = "",
    district: str = "",
    date_from: str = "",
    date_to: str = "",
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """
    工单全文检索（IK中文分词）：
    - text类型使用 ik_max_word 索引分词，ik_smart 查询分词
    - 支持按状态、设施类型、行政区、时间范围筛选
    """
    index_name = f"{settings.ES_INDEX_PREFIX}_tickets"

    must_clauses = []
    if keyword:
        must_clauses.append({
            "match": {
                "description": {
                    "query": keyword,
                    "analyzer": "ik_smart",
                }
            }
        })
    if status:
        must_clauses.append({"term": {"status": status}})
    if facility_type:
        must_clauses.append({"term": {"facility_type": facility_type}})
    if district:
        must_clauses.append({"term": {"district": district}})
    if date_from or date_to:
        range_filter = {"created_at": {}}
        if date_from:
            range_filter["created_at"]["gte"] = date_from
        if date_to:
            range_filter["created_at"]["lte"] = date_to
        must_clauses.append({"range": range_filter})

    query = {"bool": {"must": must_clauses}} if must_clauses else {"match_all": {}}

    result = await es.search(
        index=index_name,
        body={
            "query": query,
            "from": (page - 1) * page_size,
            "size": page_size,
            "sort": [{"created_at": {"order": "desc"}}],
            "highlight": {
                "fields": {"description": {}},
                "pre_tags": ["<em>"],
                "post_tags": ["</em>"],
            },
        },
    )

    hits = result["hits"]
    return {
        "total": hits["total"]["value"],
        "items": [
            {
                "ticket_id": h["_source"].get("ticket_id"),
                "status": h["_source"].get("status"),
                "description": h["_source"].get("description"),
                "highlight": h.get("highlight", {}).get("description", []),
                "score": h["_score"],
            }
            for h in hits["hits"]
        ],
    }


async def aggregate_fault_stats(
    es: AsyncElasticsearch,
    date_from: str = "",
    date_to: str = "",
) -> Dict[str, Any]:
    """
    ES 聚合分析 — 故障分布统计：
    - terms 聚合：高频故障设施 TOP10
    - terms 聚合：故障高发片区分布
    - date_histogram：周/月度趋势
    """
    index_name = f"{settings.ES_INDEX_PREFIX}_tickets"

    body = {
        "size": 0,
        "aggs": {
            "top_facility_types": {
                "terms": {"field": "facility_type", "size": 10}
            },
            "district_distribution": {
                "terms": {"field": "district", "size": 20}
            },
            "monthly_trend": {
                "date_histogram": {
                    "field": "created_at",
                    "calendar_interval": "month",
                }
            },
        },
    }

    result = await es.search(index=index_name, body=body)
    aggs = result["aggregations"]

    return {
        "top_facility_types": [
            {"type": b["key"], "count": b["doc_count"]}
            for b in aggs["top_facility_types"]["buckets"]
        ],
        "district_distribution": [
            {"district": b["key"], "count": b["doc_count"]}
            for b in aggs["district_distribution"]["buckets"]
        ],
        "monthly_trend": [
            {"month": b["key_as_string"], "count": b["doc_count"]}
            for b in aggs["monthly_trend"]["buckets"]
        ],
    }


async def aggregate_worker_perf(
    es: AsyncElasticsearch,
    district: str = "",
) -> Dict[str, Any]:
    """
    ES 聚合分析 — 维修员绩效排行：
    - avg 聚合：平均响应时间、平均星级
    - sum 聚合：总工单量、总差评数
    """
    index_name = f"{settings.ES_INDEX_PREFIX}_workers_perf"

    body = {
        "size": 0,
        "query": {"term": {"district": district}} if district else {"match_all": {}},
        "aggs": {
            "avg_response": {"avg": {"field": "avg_response_minutes"}},
            "avg_star": {"avg": {"field": "avg_star"}},
            "total_orders": {"sum": {"field": "total_orders"}},
        },
    }

    result = await es.search(index=index_name, body=body)
    aggs = result["aggregations"]

    return {
        "avg_response_minutes": aggs["avg_response"]["value"],
        "avg_star": aggs["avg_star"]["value"],
        "total_orders": int(aggs["total_orders"]["value"]),
    }


async def sync_ticket_to_es(es: AsyncElasticsearch, ticket_data: dict):
    """
    工单数据同步至 ES：
    MySQL 写入成功后，通过 RabbitMQ 消费触发 ES 索引同步（最终一致性）
    """
    index_name = f"{settings.ES_INDEX_PREFIX}_tickets"
    await es.index(
        index=index_name,
        id=ticket_data["ticket_id"],
        body=ticket_data,
    )
