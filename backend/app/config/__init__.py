from pathlib import Path

from pydantic_settings import BaseSettings


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Global application settings loaded from backend/.env and environment variables."""

    # Application
    APP_NAME: str = "CityRepairSystem"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me"

    # MySQL
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "city_repair"
    MYSQL_PASSWORD: str = "city_repair_2026"
    MYSQL_DATABASE: str = "city_repair"
    MYSQL_POOL_SIZE: int = 20

    # Redis
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB_CACHE: int = 0
    REDIS_DB_GEO: int = 1
    REDIS_DB_LOCK: int = 2
    REDIS_DB_COUNTER: int = 3

    # MongoDB
    MONGO_HOST: str = "127.0.0.1"
    MONGO_PORT: int = 27017
    MONGO_USER: str = "city_repair"
    MONGO_PASSWORD: str = "city_repair_2026"
    MONGO_DATABASE: str = "city_repair"

    # Elasticsearch
    ES_HOST: str = "127.0.0.1"
    ES_PORT: int = 9200
    ES_INDEX_PREFIX: str = "city_repair"

    # RabbitMQ
    RABBITMQ_HOST: str = "127.0.0.1"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"

    # Dify AI
    DIFY_API_BASE_URL: str = "http://127.0.0.1:5001/v1"
    DIFY_API_KEY_NLP: str = ""
    DIFY_API_KEY_DISPATCH: str = ""
    DIFY_API_KEY_VERIFY: str = ""

    # LLM
    LLM_API_KEY: str = ""
    LLM_MODEL_NAME: str = "qwen-vl-max"
    LLM_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    LLM_TEMPERATURE: float = 0.3
    LLM_ENABLE_DISPATCH_SCORING: bool = False

    # JWT
    JWT_SECRET_KEY: str = "change-me-jwt"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # OSS
    OSS_REGION: str = "cn-beijing"
    OSS_ENDPOINT: str = "oss-cn-beijing.aliyuncs.com"
    OSS_INTERNAL_ENDPOINT: str = "oss-cn-beijing-internal.aliyuncs.com"
    OSS_BUCKET: str = "city-repair-system-images"
    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""
    OSS_MAX_FILE_SIZE_MB: int = 10
    OSS_ALLOWED_EXTENSIONS: str = "jpg,jpeg,png,gif,webp,bmp"
    OSS_PUBLIC_BASE_URL: str = ""

    # Aliyun phone auth
    DYPNS_ACCESS_KEY_ID: str = ""
    DYPNS_ACCESS_KEY_SECRET: str = ""
    DYPNS_REGION: str = "cn-hangzhou"
    DYPNS_SMS_SIGN_NAME: str = ""
    DYPNS_SMS_TEMPLATE_CODE: str = ""
    DYPNS_SCHEME_NAME: str = ""

    # AMap
    AMAP_API_KEY: str = ""
    AMAP_SECURITY_KEY: str = ""

    # ES sync reliability
    ES_SYNC_MAX_RETRIES: int = 5
    ES_SYNC_BASE_DELAY_SEC: int = 2
    ES_SYNC_MAX_DELAY_SEC: int = 120

    # Business rules
    DISPATCH_LOCK_TTL: int = 300
    DISPATCH_TIMEOUT_MINUTES: int = 10
    CACHE_DELETE_DELAY_MS: int = 500
    AUTO_CLOSE_DAYS: int = 7
    TIMEZONE: str = "Asia/Shanghai"

    class Config:
        env_file = ENV_FILE
        env_file_encoding = "utf-8"


settings = Settings()
