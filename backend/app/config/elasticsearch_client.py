# ============================================================
# 城市公共设施智能报修与派单系统 - Elasticsearch 客户端管理
# 作用：管理 ES 异步客户端，负责四个 Index 的读写；
#       - tickets_index: 工单全文检索（IK中文分词）+ 故障聚合统计
#       - facilities_index: 设施档案检索 + GeoPoint 空间查询
#       - workers_perf_index: 维修员绩效排行 + 多维度聚合
#       - audit_log_index: 审计日志全文检索（同步自 MongoDB）
# ============================================================

from elasticsearch import AsyncElasticsearch

from app.config.settings import settings

es_client: AsyncElasticsearch = None


async def init_es():
    """应用启动时：连接 Elasticsearch 并创建索引 Mapping（含IK分词配置）"""
    global es_client

    es_client = AsyncElasticsearch(
        f"http://{settings.ES_HOST}:{settings.ES_PORT}",
    )

    # 创建索引（幂等），配置 IK 中文分词器
    await _create_indexes()


async def _create_indexes():
    """创建四个 Index 及其 Mapping，text 类型字段统一使用 ik_max_word 索引分词"""
    prefix = settings.ES_INDEX_PREFIX

    # ---- tickets_index ----
    if not await es_client.indices.exists(index=f"{prefix}_tickets"):
        await es_client.indices.create(
            index=f"{prefix}_tickets",
            body={
                "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                "mappings": {
                    "properties": {
                        "ticket_id": {"type": "keyword"},
                        "status": {"type": "keyword"},
                        "facility_type": {"type": "keyword"},
                        "district": {"type": "keyword"},
                        "address": {
                            "type": "text",
                            "analyzer": "ik_max_word",
                            "search_analyzer": "ik_smart",
                        },
                        "description": {
                            "type": "text",
                            "analyzer": "ik_max_word",
                            "search_analyzer": "ik_smart",
                        },
                        "nlp_confidence": {"type": "float"},
                        "location": {"type": "geo_point"},
                        "created_at": {"type": "date"},
                        "assigned_worker_id": {"type": "keyword"},
                        "closed_at": {"type": "date"},
                    }
                },
            },
        )
    else:
        # 已有索引：补齐缺失的 mapping 字段
        try:
            await es_client.indices.put_mapping(
                index=f"{prefix}_tickets",
                body={
                    "properties": {
                        "address": {
                            "type": "text",
                            "analyzer": "ik_max_word",
                            "search_analyzer": "ik_smart",
                        },
                    }
                },
            )
        except Exception:
            pass  # 字段已存在时忽略

    # ---- facilities_index ----
    if not await es_client.indices.exists(index=f"{prefix}_facilities"):
        await es_client.indices.create(
            index=f"{prefix}_facilities",
            body={
                "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                "mappings": {
                    "properties": {
                        "facility_code": {"type": "keyword"},
                        "type": {"type": "keyword"},
                        "address": {
                            "type": "text",
                            "analyzer": "ik_max_word",
                            "search_analyzer": "ik_smart",
                        },
                        "location": {"type": "geo_point"},
                        "district": {"type": "keyword"},
                        "install_date": {"type": "date"},
                        "fault_count": {"type": "integer"},
                    }
                },
            },
        )

    # ---- workers_perf_index ----
    if not await es_client.indices.exists(index=f"{prefix}_workers_perf"):
        await es_client.indices.create(
            index=f"{prefix}_workers_perf",
            body={
                "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                "mappings": {
                    "properties": {
                        "worker_id": {"type": "keyword"},
                        "name": {"type": "keyword"},
                        "district": {"type": "keyword"},
                        "total_orders": {"type": "integer"},
                        "avg_response_minutes": {"type": "float"},
                        "avg_star": {"type": "float"},
                        "bad_review_count": {"type": "integer"},
                        "settlement_total": {"type": "float"},
                        "date": {"type": "date"},
                    }
                },
            },
        )

    # ---- audit_log_index ----
    if not await es_client.indices.exists(index=f"{prefix}_audit_log"):
        await es_client.indices.create(
            index=f"{prefix}_audit_log",
            body={
                "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                "mappings": {
                    "properties": {
                        "operator_id": {"type": "keyword"},
                        "role": {"type": "keyword"},
                        "action": {"type": "keyword"},
                        "target_type": {"type": "keyword"},
                        "target_id": {"type": "keyword"},
                        "created_at": {"type": "date"},
                        "ip": {"type": "keyword"},
                    }
                },
            },
        )


async def close_es():
    """应用关闭时：释放 ES 连接"""
    if es_client:
        await es_client.close()


def get_es_client() -> AsyncElasticsearch:
    """依赖注入：获取 ES 客户端"""
    return es_client
