"""Elasticsearch BM25 关键词检索"""
from typing import Any

from elasticsearch import AsyncElasticsearch

SCHEMA_INDEX = "schema_fields"


async def ensure_schema_index(es: AsyncElasticsearch) -> None:
    """确保 Schema 索引存在"""
    exists = await es.indices.exists(index=SCHEMA_INDEX)
    if not exists:
        await es.indices.create(
            index=SCHEMA_INDEX,
            body={
                "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                "mappings": {
                    "properties": {
                        "datasource_id": {"type": "integer"},
                        "table_name": {"type": "keyword"},
                        "column_name": {"type": "keyword"},
                        "description": {"type": "text", "analyzer": "ik_max_word"},
                        "data_type": {"type": "keyword"},
                    }
                },
            },
        )


async def search_es(
    es: AsyncElasticsearch,
    query: str,
    datasource_id: int,
    top_k: int = 20,
) -> list[dict[str, Any]]:
    """ES BM25 关键词检索"""
    filters = [{"term": {"datasource_id": datasource_id}}] if datasource_id else []

    resp = await es.search(
        index=SCHEMA_INDEX,
        body={
            "query": {
                "bool": {
                    "must": {"multi_match": {"query": query, "fields": ["table_name^2", "column_name^2", "description"]}},
                    "filter": filters,
                }
            },
            "size": top_k,
        },
    )

    return [
        {
            "id": hit["_id"],
            "score": hit["_score"],
            **hit["_source"],
        }
        for hit in resp["hits"]["hits"]
    ]


async def index_schema_doc(es: AsyncElasticsearch, doc_id: int, body: dict) -> None:
    """写入 ES 文档"""
    await es.index(index=SCHEMA_INDEX, id=doc_id, body=body, refresh="wait_for")


async def delete_schema_docs(es: AsyncElasticsearch, datasource_id: int) -> None:
    """删除数据源所有 ES 文档"""
    await es.delete_by_query(
        index=SCHEMA_INDEX,
        body={"query": {"term": {"datasource_id": datasource_id}}},
        refresh=True,
    )