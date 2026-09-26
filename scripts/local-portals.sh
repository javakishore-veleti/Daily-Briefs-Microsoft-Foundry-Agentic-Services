#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
PID_FILE="$ROOT/.portals.pid"
LOG_FILE="$ROOT/.portals.log"
PORT=${PORTALS_PORT:-4200}
HOST=${PORTALS_HOST:-127.0.0.1}
cd "$ROOT"

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
    echo "portals is running (pid $(cat "$PID_FILE")) on ${HOST}:${PORT}"
    echo "portal http://${HOST}:${PORT}"
    exit 0
  fi
  if [ ! -d "$ROOT/portals/enterprise-briefs/node_modules" ]; then
    echo "enterprise-briefs dependencies are missing. Run npm install in portals/enterprise-briefs first."
    exit 1
  fi
  rm -f "$PID_FILE"
  (
    cd "$ROOT/portals/enterprise-briefs"
    npm start -- --host "$HOST" --port "$PORT"
  ) >"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"
  i=0
  while [ "$i" -lt 60 ]; do
    if is_running && curl -fsS "http://${HOST}:${PORT}" >/dev/null 2>&1; then
      echo "portals started (pid $(cat "$PID_FILE")) on ${HOST}:${PORT}"
      echo "portal http://${HOST}:${PORT}"
      exit 0
    fi
    if ! is_running; then
      echo "portals failed to start. See ${LOG_FILE}"
      exit 1
    fi
    i=$((i + 1))
    sleep 1
  done
  echo "portals started (pid $(cat "$PID_FILE")) but port ${PORT} is not ready yet. See ${LOG_FILE}"
}

stop() {
  if ! is_running; then
    rm -f "$PID_FILE"
    echo "portals is not running"
    exit 0
  fi
  pid=$(cat "$PID_FILE")
  stop_tree "$pid"
  rm -f "$PID_FILE"
  echo "portals stopped (pid ${pid})"
}

status() {
  if is_running; then
    echo "portals is running (pid $(cat "$PID_FILE")) on ${HOST}:${PORT}"
    echo "portal http://${HOST}:${PORT}"
    exit 0
  fi
  rm -f "$PID_FILE"
  echo "portals is not running"
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
