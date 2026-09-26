#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
PID_FILE="$ROOT/.middleware.pid"
LOG_FILE="$ROOT/.middleware.log"
cd "$ROOT"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

PORT=${API_PORT:-8000}
HOST=${API_HOST:-0.0.0.0}

is_running() {
  [ -f "$PID_FILE" ] || return 1
  pid=$(cat "$PID_FILE")
  [ -n "$pid" ] || return 1
  kill -0 "$pid" 2>/dev/null
}

stop_tree() {
  parent=$1
  for child in $(pgrep -P "$parent" 2>/dev/null || true); do
    stop_tree "$child"
  done
  kill "$parent" 2>/dev/null || true
}

start() {
  if is_running; then
    echo "middleware is running (pid $(cat "$PID_FILE")) on ${HOST}:${PORT}"
    exit 0
  fi
  rm -f "$PID_FILE"
  uv run python main.py >"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"
  i=0
  while [ "$i" -lt 20 ]; do
    if is_running && curl -fsS "http://127.0.0.1:${PORT}/openapi.json" >/dev/null 2>&1; then
      echo "middleware started (pid $(cat "$PID_FILE")) on ${HOST}:${PORT}"
      echo "swagger http://127.0.0.1:${PORT}/docs"
      exit 0
    fi
    if ! is_running; then
      echo "middleware failed to start. See ${LOG_FILE}"
      exit 1
    fi
    i=$((i + 1))
    sleep 0.5
  done
  echo "middleware started (pid $(cat "$PID_FILE")) but port ${PORT} is not ready yet. See ${LOG_FILE}"
}

stop() {
  if ! is_running; then
    rm -f "$PID_FILE"
    echo "middleware is not running"
    exit 0
  fi
  pid=$(cat "$PID_FILE")
  stop_tree "$pid"
  rm -f "$PID_FILE"
  echo "middleware stopped (pid ${pid})"
}

status() {
  if is_running; then
    echo "middleware is running (pid $(cat "$PID_FILE")) on ${HOST}:${PORT}"
    echo "swagger http://127.0.0.1:${PORT}/docs"
    exit 0
  fi
  rm -f "$PID_FILE"
  echo "middleware is not running"
  exit 1
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  status) status ;;
  *)
    echo "usage: $0 {start|stop|status}"
    exit 1
    ;;
esac
