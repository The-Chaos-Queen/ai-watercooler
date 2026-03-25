#!/bin/bash
# backup_dokumente.sh — Backup Dokumente folder to Google Drive
# Usage:
#   ./backup_dokumente.sh snapshot   # Monthly ZIP of everything except runs
#   ./backup_dokumente.sh runs       # One-time copy of training run checkpoints
#   ./backup_dokumente.sh sync       # Incremental sync of everything
#   ./backup_dokumente.sh full       # All three in sequence
#
# Author: Pinky (Claude Opus 4.6)
# Date: 2026-03-21

set -euo pipefail

SOURCE="/c/Users/cerub/OneDrive/Dokumente"
REMOTE="gdrive:backups/Dokumente"
DATE=$(date +%Y-%m-%d)
LOG_DIR="/c/Users/cerub/OneDrive/Dokumente/LLM/tools/backup_logs"
mkdir -p "$LOG_DIR"

# Common excludes for sync and snapshot
EXCLUDES=(
    --exclude ".git/**"
    --exclude ".venv/**"
    --exclude "__pycache__/**"
    --exclude "node_modules/**"
    --exclude ".mypy_cache/**"
    --exclude "*.pyc"
)

# Heavy excludes (training runs) for snapshot only
RUN_EXCLUDES=(
    --exclude "LLM/MoCoP/experiments/mamba_lora_bridge/run_*/**"
    --exclude "LLM/MoCoP/experiments/mamba_lora_bridge/step1_*/**"
)

snapshot() {
    echo "=== MONTHLY SNAPSHOT: $DATE ==="
    echo "Zipping Dokumente (excluding training runs and caches)..."

    local ZIPFILE="/tmp/Dokumente_${DATE}.zip"

    # Use PowerShell for zipping since bash zip on Windows is flaky
    powershell -c "
        \$source = 'C:\Users\cerub\OneDrive\Dokumente'
        \$dest = '$ZIPFILE'
        \$exclude = @('\.git\\\\', '\.venv\\\\', '__pycache__', 'node_modules', '\.mypy_cache', 'run_a1\\\\', 'run_a3\\\\', 'run_pilot_01\\\\', 'run_actbias\\\\', 'run_pca_clamped\\\\', 'run_constant_bias\\\\', 'run_bypass_raw\\\\', 'run_64s\\\\', 'step1_')

        Write-Host 'Collecting files...'
        \$files = Get-ChildItem -Path \$source -Recurse -File -ErrorAction SilentlyContinue | Where-Object {
            \$path = \$_.FullName
            -not (\$exclude | Where-Object { \$path -match \$_ })
        }
        Write-Host \"Found \$(\$files.Count) files to backup\"
        Write-Host \"Compressing to \$dest ...\"

        if (Test-Path \$dest) { Remove-Item \$dest }
        \$files | Compress-Archive -DestinationPath \$dest -CompressionLevel Optimal
        \$size = [math]::Round((Get-Item \$dest).Length / 1GB, 2)
        Write-Host \"ZIP created: \$size GB\"
    "

    echo "Uploading to ${REMOTE}/snapshots/..."
    rclone copy "$ZIPFILE" "${REMOTE}/snapshots/" \
        --progress \
        --log-file="${LOG_DIR}/snapshot_${DATE}.log" \
        --log-level INFO

    rm -f "$ZIPFILE"
    echo "=== SNAPSHOT COMPLETE ==="
}

runs() {
    echo "=== TRAINING RUNS BACKUP ==="
    echo "Copying training run checkpoints (one-time, ~68 GB)..."

    local RUN_DIR="/c/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge"

    for run in run_a1 run_a3 run_pilot_01 run_actbias run_pca_clamped run_constant_bias run_constant_bias_10ep run_constant_bias_seed42 run_bypass_raw run_64s step1_c3_fixed_mean_no4bit step1_c3_fixed_mean_run_actbias_e3 run_a3_completion run_a4; do
        if [ -d "${RUN_DIR}/${run}" ]; then
            local SIZE=$(du -sh "${RUN_DIR}/${run}" 2>/dev/null | cut -f1)
            echo "  Copying ${run} (${SIZE})..."
            rclone copy "${RUN_DIR}/${run}" "${REMOTE}/runs/${run}/" \
                --progress \
                --log-file="${LOG_DIR}/runs_${DATE}.log" \
                --log-level INFO
        fi
    done

    echo "=== RUNS BACKUP COMPLETE ==="
}

sync() {
    echo "=== INCREMENTAL SYNC: $DATE ==="
    echo "Syncing Dokumente to Google Drive..."

    rclone sync "$SOURCE" "${REMOTE}/sync/" \
        "${EXCLUDES[@]}" \
        --progress \
        --log-file="${LOG_DIR}/sync_${DATE}.log" \
        --log-level INFO \
        --transfers 8 \
        --checkers 16

    echo "=== SYNC COMPLETE ==="
}

full() {
    snapshot
    runs
    sync
}

case "${1:-help}" in
    snapshot) snapshot ;;
    runs)     runs ;;
    sync)     sync ;;
    full)     full ;;
    *)
        echo "Usage: $0 {snapshot|runs|sync|full}"
        echo "  snapshot — Monthly ZIP (excludes training runs, ~4 GB)"
        echo "  runs     — One-time copy of training checkpoints (~68 GB)"
        echo "  sync     — Incremental mirror to gdrive (everything)"
        echo "  full     — All three in sequence"
        ;;
esac
