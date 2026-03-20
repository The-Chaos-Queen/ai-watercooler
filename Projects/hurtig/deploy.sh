#!/bin/bash
# Deploy hurtig.ai to Hetzner
# Usage: bash deploy.sh
#
# Syncs site/ contents to /var/www/hurtig/ on the Hetzner box.
# Uses rsync for incremental transfer (only changed files).
# Falls back to scp if rsync is not available.

SITE_DIR="$(dirname "$0")/site"
TARGET="root@178.104.75.161:/var/www/hurtig/"

echo "🚀 Deploying hurtig.ai..."

if command -v rsync &> /dev/null; then
    rsync -avz --delete "$SITE_DIR/" "$TARGET"
else
    # Trailing /. ensures contents are copied, not the directory itself
    scp -r "$SITE_DIR/." "$TARGET"
fi

echo "✅ Done. Live at https://hurtig.ai"
