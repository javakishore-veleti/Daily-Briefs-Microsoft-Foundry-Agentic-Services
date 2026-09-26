#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
sh "$ROOT/scripts/local-portals.sh" stop
sh "$ROOT/scripts/local-middleware.sh" stop
