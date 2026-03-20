#!/bin/bash
# setup_nuc_crons.sh — Install NUC automation scripts and cron jobs
# Run this ON the NUC as root after SCP-ing the scripts.
#
# Usage:
#   scp tools/agent_dispatch.sh tools/morning_brief.sh tools/setup_nuc_crons.sh root@192.168.2.55:/root/
#   ssh root@192.168.2.55 "bash /root/setup_nuc_crons.sh"
#
# Note: safe_rent.sh is for Laura's laptop, not the NUC — not installed here.

set -euo pipefail

SCRIPT_DIR="/root"
LOG_DIR="/var/log"
SCRIPTS=(agent_dispatch.sh morning_brief.sh)

# --- Verify running as root ---
if [[ $EUID -ne 0 ]]; then
    echo "ERROR: This script must be run as root on the NUC."
    echo "  ssh root@192.168.2.55 'bash /root/setup_nuc_crons.sh'"
    exit 1
fi

echo "=== NUC Automation Setup ==="
echo "Host: $(hostname)"
echo "Date: $(date)"
echo ""

# --- Dependency checks ---
echo "Checking required dependencies..."
for dep in curl python3; do
    if command -v "$dep" &>/dev/null; then
        echo "  ${dep}: OK ($(command -v "$dep"))"
    else
        echo "  ERROR: '${dep}' not found. Install it before the automation scripts will work."
        echo "    apt-get install -y ${dep}   # Debian/Ubuntu"
        echo "    yum install -y ${dep}       # RHEL/CentOS"
        exit 1
    fi
done
echo ""

# --- Fix CRLF line endings on installed scripts ---
# Scripts edited on Windows may have CRLF line endings which cause bash to fail
# with cryptic "command not found" errors. Strip them before setting permissions.
echo "Stripping CRLF line endings..."
for script in "${SCRIPTS[@]}"; do
    target="${SCRIPT_DIR}/${script}"
    if [[ -f "$target" ]]; then
        sed -i 's/\r$//' "$target"
        echo "  dos2unix: ${target}"
    fi
done
echo ""

# --- Make scripts executable ---
echo "Setting permissions..."
for script in "${SCRIPTS[@]}"; do
    target="${SCRIPT_DIR}/${script}"
    if [[ -f "$target" ]]; then
        chmod 750 "$target"
        echo "  chmod 750 ${target}"
    else
        echo "  WARNING: ${target} not found — copy it to /root/ first."
    fi
done

# --- Ensure log directory is writable ---
echo ""
echo "Checking log directory..."
if [[ -d "$LOG_DIR" && -w "$LOG_DIR" ]]; then
    echo "  ${LOG_DIR} OK"
    # Pre-create log files so they exist before first cron run
    touch "${LOG_DIR}/agent_dispatch.log"
    touch "${LOG_DIR}/morning_brief.log"
    chmod 640 "${LOG_DIR}/agent_dispatch.log" "${LOG_DIR}/morning_brief.log"
    echo "  Log files created/verified."
else
    echo "  WARNING: ${LOG_DIR} not writable — logs will go to cron's default output."
fi

# --- Set up logrotate ---
echo ""
echo "Installing logrotate config..."
LOGROTATE_CONF="/etc/logrotate.d/nuc_automation"
cat > "$LOGROTATE_CONF" <<'LOGROTATE_EOF'
/var/log/agent_dispatch.log /var/log/morning_brief.log {
    weekly
    rotate 8
    compress
    delaycompress
    missingok
    notifempty
    create 640 root root
}
LOGROTATE_EOF
echo "  Logrotate config written to ${LOGROTATE_CONF}"

# --- Install cron jobs ---
echo ""
echo "Installing cron jobs..."

# Cron entries to install
CRON_DISPATCH="*/30 * * * * ${SCRIPT_DIR}/agent_dispatch.sh >> ${LOG_DIR}/agent_dispatch.log 2>&1"
CRON_BRIEF="30 7 * * * ${SCRIPT_DIR}/morning_brief.sh >> ${LOG_DIR}/morning_brief.log 2>&1"

# Get existing crontab, stripping any previous versions of these entries.
# Also strip comment lines added by previous runs of this script so they don't
# accumulate on repeated installs.
EXISTING_CRON=$(crontab -l 2>/dev/null || true)

CLEANED_CRON=$(echo "$EXISTING_CRON" \
    | grep -v "agent_dispatch.sh" \
    | grep -v "morning_brief.sh" \
    | grep -v "Laura's NUC Automation" \
    | grep -v "Agent task dispatcher" \
    | grep -v "Morning brief generator" \
    || true)

# Compose new crontab
NEW_CRON="${CLEANED_CRON}
# === Laura's NUC Automation (installed by setup_nuc_crons.sh) ===
# Agent task dispatcher — runs every 30 minutes
${CRON_DISPATCH}
# Morning brief generator — runs at 7:30 AM daily
${CRON_BRIEF}
"

# Install
echo "$NEW_CRON" | crontab -
echo "  Crontab updated. Current crontab:"
echo ""
crontab -l | grep -v "^$" | sed 's/^/    /'

# --- Verify OpenCLAW reachability (advisory) ---
echo ""
echo "Checking OpenCLAW at http://localhost:8765 ..."
if curl -s --max-time 5 --head "http://localhost:8765/" >/dev/null 2>&1; then
    echo "  OpenCLAW: REACHABLE"
else
    echo "  OpenCLAW: NOT REACHABLE (scripts will fail silently until it's running)"
fi

# --- Auth token advisory ---
echo ""
if [[ -f "/root/.openclaw_token" ]]; then
    TOKEN_PERMS=$(stat -c '%a' "/root/.openclaw_token" 2>/dev/null || echo "unknown")
    echo "Auth token: /root/.openclaw_token found (permissions: ${TOKEN_PERMS})."
    if [[ "$TOKEN_PERMS" != "600" && "$TOKEN_PERMS" != "unknown" ]]; then
        echo "  WARNING: Token file should be mode 600. Fix with: chmod 600 /root/.openclaw_token"
    fi
else
    echo "Auth token: /root/.openclaw_token NOT found."
    echo "  If OpenCLAW requires auth, create it:"
    echo "    echo 'your_token_here' > /root/.openclaw_token && chmod 600 /root/.openclaw_token"
fi

# --- Repo path advisory ---
echo ""
echo "Repo path for morning_brief.sh:"
REPO_CANDIDATES=("/root/llm" "/home/laura/llm" "/mnt/llm" "/opt/llm")
FOUND=0
for candidate in "${REPO_CANDIDATES[@]}"; do
    if [[ -f "${candidate}/CHEESE_Memory/00_HANDOFF.md" ]]; then
        echo "  FOUND: ${candidate}"
        FOUND=1
        break
    fi
done
if [[ $FOUND -eq 0 ]]; then
    echo "  NOT FOUND in any of: ${REPO_CANDIDATES[*]}"
    echo "  Options:"
    echo "    1. Clone repo: git clone <url> /root/llm"
    echo "    2. Mount share: mount -t cifs //laptop/llm /mnt/llm -o ..."
    echo "    3. Set REPO_PATH in morning_brief.sh, or export REPO_PATH=<path> before running"
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Quick test commands:"
echo "  ${SCRIPT_DIR}/agent_dispatch.sh   # Test dispatch (check /var/log/agent_dispatch.log)"
echo "  ${SCRIPT_DIR}/morning_brief.sh    # Test brief (check /root/morning_brief.txt)"
echo ""
echo "To deploy safe_rent.sh on Laura's laptop instead:"
echo "  chmod 750 ~/tools/safe_rent.sh    # or wherever it lives"
echo "  # Requires: pip install vastai && vastai set api-key YOUR_KEY"
