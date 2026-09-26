#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")" && pwd)

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is not installed"
  exit 1
fi

docker compose -f "$ROOT/mongo/docker-compose.yaml" down --volumes
echo "local containers and volumes are down"
