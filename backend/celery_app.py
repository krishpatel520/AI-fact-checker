import os
from dotenv import load_dotenv
from celery import Celery

# Load variables from the .env file
load_dotenv()

# --- Read the Redis URL from the environment, with a default fallback ---
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery = Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["backend.worker"],   # ← tells the worker to load our tasks
)

celery.conf.update(
    task_track_started=True,
)