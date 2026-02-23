#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

podman compose -f "$SCRIPT_DIR/podman-compose.yml" exec -T oracle \
  sqlplus accelerator/accelerator@localhost:1521/XEPDB1 @/dev/stdin < "$SCRIPT_DIR/seed_oracle.sql"

echo "Oracle demo schema/data seeded successfully."
