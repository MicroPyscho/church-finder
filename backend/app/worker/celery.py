from celery import Celery
from app.core.config import settings if False else None
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "sanctuary",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/London",
    enable_utc=True,
    beat_schedule={
        "crawl-all-sources": {
            "task":     "app.worker.tasks.crawl_all",
            "schedule": 10800,  # every 3 hours
        },
        "match-alerts": {
            "task":     "app.worker.tasks.match_alerts",
            "schedule": 3600,   # every hour
        },
    },
)
