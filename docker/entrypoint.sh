#!/usr/bin/env bash
set -e

: "${UVICORN_HOST:=0.0.0.0}"
: "${PORT:=8000}"
: "${UVICORN_WORKERS:=2}"
: "${APP_MODULE:=app.main:app}"

echo "Starting Uvicorn: ${APP_MODULE} on ${UVICORN_HOST}:${PORT} with ${UVICORN_WORKERS} workers"
exec python -m uvicorn "${APP_MODULE}" --host "${UVICORN_HOST}" --port "${PORT}" --workers "${UVICORN_WORKERS}"
