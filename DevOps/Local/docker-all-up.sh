#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")" && pwd)

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is not installed"
  exit 1
fi

docker compose -f "$ROOT/mongo/docker-compose.yaml" up -d --wait
echo "local containers are up"
echo "mongodb mongodb://127.0.0.1:27017 database daily_briefs"
