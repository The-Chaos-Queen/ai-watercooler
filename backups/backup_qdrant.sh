#!/bin/bash
# Qdrant Backup Script — snapshots exocortex collection and pushes to Google Drive
set -euo pipefail

TIMESTAMP=$(date +%Y-%m-%d_%H%M)
BACKUP_DIR=/root/backups
GDRIVE_PATH=gdrive:backups/qdrant
COLLECTION=exocortex
LOG=/root/backup_qdrant.log

echo "[$TIMESTAMP] Starting Qdrant backup..." >> $LOG

# Create local backup dir
mkdir -p $BACKUP_DIR

# 1. Create Qdrant snapshot
SNAP_RESPONSE=$(curl -s -X POST "http://localhost:6333/collections/$COLLECTION/snapshots")
SNAP_NAME=$(echo "$SNAP_RESPONSE" | sed -n 's/.*"name":"\([^"]*\)".*/\1/p')

if [ -z "$SNAP_NAME" ]; then
    echo "[$TIMESTAMP] ERROR: Snapshot creation failed: $SNAP_RESPONSE" >> $LOG
    exit 1
fi

echo "[$TIMESTAMP] Snapshot created: $SNAP_NAME" >> $LOG

# 2. Download snapshot locally
curl -s -o "$BACKUP_DIR/$SNAP_NAME" "http://localhost:6333/collections/$COLLECTION/snapshots/$SNAP_NAME"
echo "[$TIMESTAMP] Downloaded to $BACKUP_DIR/$SNAP_NAME" >> $LOG

# 3. Push to Google Drive
rclone copy "$BACKUP_DIR/$SNAP_NAME" "$GDRIVE_PATH/" --log-level ERROR 2>> $LOG
echo "[$TIMESTAMP] Pushed to Google Drive: $GDRIVE_PATH/$SNAP_NAME" >> $LOG

# 4. Clean up local snapshots older than 7 days
find "$BACKUP_DIR" -name "*.snapshot" -mtime +7 -delete 2>/dev/null || true

# 5. Clean up Qdrant server-side snapshots (keep latest 3)
SNAPS=$(curl -s "http://localhost:6333/collections/$COLLECTION/snapshots" | sed 's/},/}\n/g' | sed -n 's/.*"name":"\([^"]*\)".*/\1/p' | sort -r)
COUNT=0
for SNAP in $SNAPS; do
    COUNT=$((COUNT + 1))
    if [ $COUNT -gt 3 ]; then
        curl -s -X DELETE "http://localhost:6333/collections/$COLLECTION/snapshots/$SNAP" > /dev/null
        echo "[$TIMESTAMP] Deleted old server snapshot: $SNAP" >> $LOG
    fi
done

echo "[$TIMESTAMP] Backup complete." >> $LOG
