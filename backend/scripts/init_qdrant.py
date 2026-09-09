#!/bin/bash
# 初始化 Qdrant 集合
set -e

QDRANT_HOST="${QDRANT_HOST:-localhost}"
QDRANT_PORT="${QDRANT_PORT:-6333}"
SCHEMA_COLLECTION="${QDRANT_COLLECTION_SCHEMA:-schema_embeddings}"
QUERY_CACHE_COLLECTION="${QDRANT_COLLECTION_QUERY_CACHE:-query_cache}"
EMBEDDING_DIM="${EMBEDDING_DIM:-1536}"

# Create schema_embeddings collection
curl -s -X PUT "http://${QDRANT_HOST}:${QDRANT_PORT}/collections/${SCHEMA_COLLECTION}" \
  -H "Content-Type: application/json" \
  -d "{
    \"vectors\": {
      \"size\": ${EMBEDDING_DIM},
      \"distance\": \"Cosine\"
    },
    \"optimizers_config\": {
      \"default_segment_number\": 2
    }
  }"

echo ""
echo "Collection '${SCHEMA_COLLECTION}' created (dim: ${EMBEDDING_DIM})"

# Create query_cache collection
curl -s -X PUT "http://${QDRANT_HOST}:${QDRANT_PORT}/collections/${QUERY_CACHE_COLLECTION}" \
  -H "Content-Type: application/json" \
  -d "{
    \"vectors\": {
      \"size\": ${EMBEDDING_DIM},
      \"distance\": \"Cosine\"
    },
    \"optimizers_config\": {
      \"default_segment_number\": 2
    }
  }"

echo ""
echo "Collection '${QUERY_CACHE_COLLECTION}' created (dim: ${EMBEDDING_DIM})"
echo "Done."