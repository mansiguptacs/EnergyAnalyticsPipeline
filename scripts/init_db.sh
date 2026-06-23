#!/usr/bin/env bash
# ==============================================================================
# Initialize the Energy Analytics Database
# ==============================================================================
# Runs all SQL schema files in order against the energy PostgreSQL instance.
#
# Usage:
#   ./scripts/init_db.sh                  # Uses default connection
#   ./scripts/init_db.sh --host localhost  # Override host
# ==============================================================================

set -euo pipefail

# Defaults (override via environment or arguments)
DB_HOST="${ENERGY_DB_HOST:-localhost}"
DB_PORT="${ENERGY_DB_PORT:-5432}"
DB_NAME="${ENERGY_DB_NAME:-energy_db}"
DB_USER="${ENERGY_DB_USER:-energy_user}"

SCHEMA_DIR="$(dirname "$0")/../sql/schema"

echo "=============================================="
echo "  Energy Analytics — Database Initialization"
echo "=============================================="
echo "  Host: ${DB_HOST}:${DB_PORT}"
echo "  DB:   ${DB_NAME}"
echo "  User: ${DB_USER}"
echo ""

# Run each SQL file in order
for sql_file in $(ls "${SCHEMA_DIR}"/*.sql | sort); do
    filename=$(basename "$sql_file")
    echo "  ▶ Running ${filename}..."
    PGPASSWORD="${ENERGY_DB_PASSWORD:-energy_pass}" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -f "$sql_file" \
        --quiet \
        --no-psqlrc
    echo "    ✅ ${filename} done"
done

echo ""
echo "=============================================="
echo "  ✅ Database initialization complete!"
echo "=============================================="
