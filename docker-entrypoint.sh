#!/bin/bash
# docker-entrypoint.sh
# ---------------------
# Selects between API and Worker mode based on the MODE environment variable.
# Usage: set MODE=api (default) or MODE=worker in docker-compose / K8s.

set -e

MODE="${MODE:-api}"

case "$MODE" in
  api)
    echo "▶  Starting FastAPI (uvicorn)..."
    exec uvicorn backend.main:app \
      --host 0.0.0.0 \
      --port 8000 \
      --workers "${UVICORN_WORKERS:-2}" \
      --log-level "${LOG_LEVEL:-info}"
    ;;

  worker)
    QUEUES="${CELERY_QUEUES:-high,default,low}"
    CONCURRENCY="${CELERY_CONCURRENCY:-4}"
    echo "▶  Starting Celery worker (queues=$QUEUES, concurrency=$CONCURRENCY)..."
    exec celery -A backend.celery_app.celery worker \
      --loglevel="${LOG_LEVEL:-info}" \
      --pool=gevent \
      --concurrency="$CONCURRENCY" \
      --queues="$QUEUES"
    ;;

  flower)
    echo "▶  Starting Flower (Celery monitoring)..."
    exec celery -A backend.celery_app.celery flower \
      --port=5555 \
      --basic_auth="${FLOWER_USER:-admin}:${FLOWER_PASSWORD:-veritas}"
    ;;

  *)
    echo "❌ Unknown MODE: $MODE. Use 'api', 'worker', or 'flower'."
    exit 1
    ;;
esac
