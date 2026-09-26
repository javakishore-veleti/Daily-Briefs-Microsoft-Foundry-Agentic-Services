#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
COMPOSE_FILE="$ROOT/mongo/docker-compose.yaml"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is not installed"
  exit 1
fi

docker compose -f "$COMPOSE_FILE" ps
running=$(docker compose -f "$COMPOSE_FILE" ps --status running -q | wc -l | tr -d ' ')
expected=$(docker compose -f "$COMPOSE_FILE" config --services | wc -l | tr -d ' ')
if [ "$running" != "$expected" ] || [ "$expected" = "0" ]; then
  echo "local containers are not all running ($running/$expected)"
  exit 1
fi
echo "local containers are running ($running/$expected)"
