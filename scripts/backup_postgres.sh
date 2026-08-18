#!/usr/bin/env bash
set -euo pipefail


find_postgres_tool() {
    local tool="$1"

    if command -v "$tool" >/dev/null 2>&1; then
        command -v "$tool"
        return 0
    fi

    if command -v brew >/dev/null 2>&1; then
        local libpq_bin
        libpq_bin="$(brew --prefix libpq 2>/dev/null)/bin"

        if [ -x "$libpq_bin/$tool" ]; then
            printf '%s\n' "$libpq_bin/$tool"
            return 0
        fi
    fi

    return 1
}


if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <database-url> [output-directory]"
    exit 2
fi

DATABASE_URL="$1"
OUTPUT_DIR="${2:-backups/database}"

if [[ "$DATABASE_URL" != postgresql://* ]] && \
   [[ "$DATABASE_URL" != postgres://* ]]; then
    echo "STOP: Backup requires a PostgreSQL database URL."
    exit 2
fi

PG_DUMP="$(find_postgres_tool pg_dump || true)"

if [ -z "$PG_DUMP" ]; then
    echo "STOP: pg_dump is not installed or could not be located."
    exit 2
fi

mkdir -p "$OUTPUT_DIR"

TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
OUTPUT_FILE="${OUTPUT_DIR}/ptm-postgres-${TIMESTAMP}.dump"

echo "Creating PostgreSQL backup..."
echo "Output: $OUTPUT_FILE"

"$PG_DUMP" \
    --format=custom \
    --no-owner \
    --no-privileges \
    --file="$OUTPUT_FILE" \
    "$DATABASE_URL"

if [ ! -s "$OUTPUT_FILE" ]; then
    echo "STOP: Backup file was not created or is empty."
    exit 1
fi

echo "PASS: Backup created."
echo "$OUTPUT_FILE"
