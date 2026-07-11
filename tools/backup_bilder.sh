#!/bin/bash
# backup_bilder.sh — Sync Bilder folder to Google Drive
# Usage:
#   ./backup_bilder.sh
#
# Syncs C:\Users\cerub\OneDrive\Bilder to gdrive:Privat/Photos/
# Incremental sync only (photos don't need zipping or special handling)
#
# Author: Pinky (Claude Sonnet 4.5)
# Date: 2026-07-11

set -euo pipefail

SOURCE="/c/Users/cerub/OneDrive/Bilder"
REMOTE="gdrive:Privat/Photos"
DATE=$(date +%Y-%m-%d)
LOG_DIR="/c/Users/cerub/OneDrive/Dokumente/LLM/tools/backup_logs"
mkdir -p "$LOG_DIR"

echo "=== BILDER SYNC: $DATE ==="
echo "Syncing Bilder to Google Drive..."

rclone sync "$SOURCE" "$REMOTE" \
    --progress \
    --log-file="${LOG_DIR}/bilder_${DATE}.log" \
    --log-level INFO \
    --transfers 8 \
    --checkers 16

echo "=== SYNC COMPLETE ==="
