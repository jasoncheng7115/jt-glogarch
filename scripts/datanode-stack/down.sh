#!/usr/bin/env bash
# Remove the Data Node test stack and its volumes.
set -euo pipefail
cd "$(dirname "$0")"
docker compose down -v
rm -f .env
