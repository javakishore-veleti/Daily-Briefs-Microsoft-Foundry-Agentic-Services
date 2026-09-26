#!/bin/sh

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
sh "$ROOT/scripts/local-middleware.sh" status
middleware_status=$?
sh "$ROOT/scripts/local-portals.sh" status
portals_status=$?
if [ "$middleware_status" -ne 0 ] || [ "$portals_status" -ne 0 ]; then
  exit 1
fi
