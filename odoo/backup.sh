#!/usr/bin/env bash
# backup.sh — Daily PostgreSQL backup for Odoo database
#
# Intended to run as a daily cron job:
#   0 2 * * * /opt/ai-employee/odoo/backup.sh
#
# Keeps the last 7 daily backups.

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/ai-employee/backups/odoo}"
CONTAINER="${POSTGRES_CONTAINER:-ai-employee-postgres}"
DB_USER="${POSTGRES_USER:-odoo}"
DB_NAME="${POSTGRES_DB:-postgres}"
RETENTION_DAYS=7

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate backup filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/odoo_backup_${TIMESTAMP}.sql.gz"

echo "[$(date)] Starting Odoo database backup..."

# Run pg_dump inside the container and compress
docker exec "$CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
    echo "[$(date)] Backup successful: $BACKUP_FILE ($SIZE)"
else
    echo "[$(date)] ERROR: Backup failed!"
    exit 1
fi

# Clean up old backups
echo "[$(date)] Cleaning backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "odoo_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# List remaining backups
echo "[$(date)] Current backups:"
ls -lh "$BACKUP_DIR"/odoo_backup_*.sql.gz 2>/dev/null || echo "  (none)"

echo "[$(date)] Backup complete."
