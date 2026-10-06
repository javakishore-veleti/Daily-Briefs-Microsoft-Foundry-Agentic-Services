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
# Azure Foundry bootstrap can take 20s+ when resources are unreachable.
READY_ATTEMPTS=${MIDDLEWARE_READY_ATTEMPTS:-60}
READY_SLEEP=${MIDDLEWARE_READY_SLEEP:-1}

listener_pid() {
  lsof -nP -tiTCP:"${PORT}" -sTCP:LISTEN 2>/dev/null | head -n 1
}

port_ready() {
  curl -fsS "http://127.0.0.1:${PORT}/openapi.json" >/dev/null 2>&1
}

is_running() {
  if [ -f "$PID_FILE" ]; then
    pid=$(cat "$PID_FILE")
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  listener=$(listener_pid)
  [ -n "$listener" ]
}

remember_listener_pid() {
  listener=$(listener_pid)
  if [ -n "$listener" ]; then
    echo "$listener" >"$PID_FILE"
  fi
}

stop_tree() {
  parent=$1
  for child in $(pgrep -P "$parent" 2>/dev/null || true); do
    stop_tree "$child"
  done
  kill "$parent" 2>/dev/null || true
}

start() {
  if port_ready; then
    remember_listener_pid
    echo "middleware is running (pid $(cat "$PID_FILE")) on ${HOST}:${PORT}"
    echo "swagger http://127.0.0.1:${PORT}/docs"
    exit 0
  fi
  rm -f "$PID_FILE"
  uv run python main.py >"$LOG_FILE" 2>&1 &
  starter_pid=$!
  echo "$starter_pid" >"$PID_FILE"
  i=0
  while [ "$i" -lt "$READY_ATTEMPTS" ]; do
    if port_ready; then
      remember_listener_pid
      echo "middleware started (pid $(cat "$PID_FILE")) on ${HOST}:${PORT}"
      echo "swagger http://127.0.0.1:${PORT}/docs"
      exit 0
    fi
    # uv may exit after spawning python; only fail once neither starter nor listener remains.
    if ! kill -0 "$starter_pid" 2>/dev/null; then
      listener=$(listener_pid)
      if [ -z "$listener" ] && [ "$i" -ge 2 ]; then
        echo "middleware failed to start. See ${LOG_FILE}"
        exit 1
      fi
    fi
    i=$((i + 1))
    sleep "$READY_SLEEP"
  done
  if port_ready; then
    remember_listener_pid
    echo "middleware started (pid $(cat "$PID_FILE")) on ${HOST}:${PORT}"
    echo "swagger http://127.0.0.1:${PORT}/docs"
    exit 0
  fi
  echo "middleware started (pid $(cat "$PID_FILE")) but port ${PORT} is not ready yet. See ${LOG_FILE}"
  exit 1
}

stop() {
  if ! is_running; then
    rm -f "$PID_FILE"
    echo "middleware is not running"
    exit 0
  fi
  pid=$(cat "$PID_FILE" 2>/dev/null || true)
  listener=$(listener_pid)
  if [ -n "$pid" ]; then
    stop_tree "$pid"
  fi
  if [ -n "$listener" ] && [ "$listener" != "${pid:-}" ]; then
    stop_tree "$listener"
  fi
  rm -f "$PID_FILE"
  echo "middleware stopped (pid ${pid:-$listener})"
}

status() {
  if port_ready || is_running; then
    remember_listener_pid
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
