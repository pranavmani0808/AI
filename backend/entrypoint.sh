#!/bin/sh

# Start Celery worker in the background
echo "Starting Celery worker..."
celery -A backend.core.celery_app.celery_app worker --loglevel=info &

# Start FastAPI server
echo "Starting FastAPI server..."
exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
