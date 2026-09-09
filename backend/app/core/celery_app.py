"""
Celery 应用配置
基于配置中心读取的 broker/backend URL 初始化 Celery 应用。
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "starry_aurora",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# ---------- 序列化 ----------
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_soft_time_limit=300,    # 单任务软超时 5 分钟
    task_time_limit=600,         # 单任务硬超时 10 分钟
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=1,
)


# ---------- 定期任务占位 ----
celery_app.conf.beat_schedule = {
    # "clean_expired_tokens": {
    #     "task": "app.tasks.cleaning.clean_expired_tokens",
    #     "schedule": crontab(hour=3, minute=0),
    # },
}