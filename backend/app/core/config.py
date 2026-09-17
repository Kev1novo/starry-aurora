"""
全局配置模块
从 .env 文件加载所有配置项，提供统一的配置入口。
"""

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置"""

    # ---------- 应用基础 ----------
    APP_NAME: str = "Starry Aurora NL2SQL Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    SECRET_KEY: str = "please-change-me-in-production"

    # ---------- 数据库 ----------
    DATABASE_URL: str = "mysql+aiomysql://root:password@localhost:3306/starry_aurora"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ---------- Redis ----------
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_DB: int = 0
    REDIS_QUEUE_DB: int = 1

    # ---------- Qdrant ----------
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_SCHEMA: str = ""  # JSON 字符串，预留

    # ---------- Elasticsearch ----------
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_INDEX_SCHEMA: str = ""  # JSON 字符串，预留

    # ---------- LLM ----------
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o"
    LLM_API_KEY: str = ""
    LLM_API_BASE: str = ""
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096

    # ---------- Embedding ----------
    EMBEDDING_MODEL: str = "C:/Users/EDY/.cache/modelscope/models/BAAI--bge-small-zh-v1.5/snapshots/master"
    EMBEDDING_DIM: int = 512
    EMBEDDING_USE_LOCAL: bool = True  # True=用本地 sentence-transformers, False=用 API

    # ---------- JWT ----------
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    # ---------- Celery ----------
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # ---------- CORS ----------
    CORS_ORIGINS: List[str] = ["*"]

    # ---------- 日志 ----------
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()