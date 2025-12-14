from celery import Celery
import os
from worker.beat_schedule import beat_schedule
from dotenv import load_dotenv
load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery = Celery(
    "pantry_app",
    broker=REDIS_URL,
    include=["worker.tasks"],
)

celery.conf.timezone = "UTC"
celery.conf.enable_utc = True
celery.conf.beat_schedule = beat_schedule