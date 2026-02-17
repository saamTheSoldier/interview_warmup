"""
Celery application - async task queue with RabbitMQ (job requirement: queue management).
Challenge: Decouple heavy work from HTTP request; retries, visibility.
Design: Same broker as job description (RabbitMQ); Redis as result backend optional.
"""

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "interview_app",
    broker=settings.celery_broker_url,
    backend=settings.redis_url,
    include=["app.queue.tasks"],
)

# Task settings: retries, time limits, serialization
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=60,
    worker_prefetch_multiplier=1,  # Fair distribution
)
