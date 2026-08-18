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


if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <target-database-url> <backup-file>"
    exit 2
fi

DATABASE_URL="$1"
BACKUP_FILE="$2"

if [[ "$DATABASE_URL" != postgresql://* ]] && \
   [[ "$DATABASE_URL" != postgres://* ]]; then
    echo "STOP: Restore requires a PostgreSQL database URL."
    exit 2
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "STOP: Backup file not found: $BACKUP_FILE"
    exit 2
fi

if [ "${PTM_ALLOW_RESTORE:-}" != "YES" ]; then
    echo
    echo "WARNING:"
    echo "This operation restores a PostgreSQL backup."
    echo
    echo "STOP: Set PTM_ALLOW_RESTORE=YES to authorize this restore."
    exit 2
fi

PG_RESTORE="$(find_postgres_tool pg_restore || true)"

if [ -z "$PG_RESTORE" ]; then
    echo "STOP: pg_restore is not installed or could not be located."
    exit 2
fi

echo
echo "Restore authorized."
echo "Target PostgreSQL database:"
echo "$DATABASE_URL"
echo

"$PG_RESTORE" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    --exit-on-error \
    --dbname="$DATABASE_URL" \
    "$BACKUP_FILE"

echo "PASS: Restore completed."
