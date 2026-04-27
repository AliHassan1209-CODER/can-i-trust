#!/bin/bash
# ── PostgreSQL backup script ────────────────────────────────────
# Run this from cron or manually:
#   chmod +x scripts/backup_db.sh
#   ./scripts/backup_db.sh

set -e

BACKUP_DIR="./backups/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/can_i_trust_$TIMESTAMP.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "Backing up database to $BACKUP_FILE..."

docker exec cit_postgres pg_dump \
  -U "${POSTGRES_USER:-postgres}" \
  -d "${POSTGRES_DB:-can_i_trust}" \
  | gzip > "$BACKUP_FILE"

echo "Backup complete: $BACKUP_FILE ($(du -sh $BACKUP_FILE | cut -f1))"

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -delete
echo "Old backups cleaned."
