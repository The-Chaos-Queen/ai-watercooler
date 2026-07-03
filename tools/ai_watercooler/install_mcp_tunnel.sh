#!/bin/bash
# install_mcp_tunnel.sh — Set up SSH reverse tunnel from NUC to Hetzner
#
# Run this script in TWO phases:
#   Phase 1: On Hetzner (as root) — creates the locked-down tunnel user
#   Phase 2: On NUC (as root) — installs autossh + systemd service
#
# Usage:
#   # On Hetzner:
#   bash install_mcp_tunnel.sh --hetzner --nuc-pubkey "ssh-ed25519 AAAA..."
#
#   # On NUC:
#   bash install_mcp_tunnel.sh --nuc --hetzner-host hurtig.ai --key-path /root/.ssh/mcp_tunnel_ed25519

set -euo pipefail

HETZNER_USER="mcp-tunnel"
TUNNEL_PORT=8787

case "${1:-}" in
  --hetzner)
    NUC_PUBKEY="${3:-}"
    if [ -z "$NUC_PUBKEY" ]; then
      echo "Usage: $0 --hetzner --nuc-pubkey 'ssh-ed25519 AAAA...'"
      exit 1
    fi

    echo "Creating tunnel user '$HETZNER_USER' on Hetzner..."
    useradd -m -s /usr/sbin/nologin "$HETZNER_USER" 2>/dev/null || echo "User exists"
    mkdir -p "/home/$HETZNER_USER/.ssh"
    chmod 700 "/home/$HETZNER_USER/.ssh"

    # Restrict key to port forwarding only (no command="" — it terminates the session and breaks the tunnel)
    AUTH_LINE="no-agent-forwarding,no-X11-forwarding,no-pty,permitopen=\"127.0.0.1:$TUNNEL_PORT\" $NUC_PUBKEY"
    echo "$AUTH_LINE" > "/home/$HETZNER_USER/.ssh/authorized_keys"
    chmod 600 "/home/$HETZNER_USER/.ssh/authorized_keys"
    chown -R "$HETZNER_USER:$HETZNER_USER" "/home/$HETZNER_USER/.ssh"

    # Allow reverse port forwarding in sshd
    echo "GatewayPorts clientspecified" >> /etc/ssh/sshd_config.d/mcp-tunnel.conf 2>/dev/null || true

    echo "Done. Tunnel user created. Restart sshd if needed: systemctl reload sshd"
    ;;

  --nuc)
    HETZNER_HOST="${3:-hurtig.ai}"
    KEY_PATH="${5:-/root/.ssh/mcp_tunnel_ed25519}"

    # Generate key if it doesn't exist
    if [ ! -f "$KEY_PATH" ]; then
      echo "Generating SSH key at $KEY_PATH..."
      ssh-keygen -t ed25519 -f "$KEY_PATH" -N "" -C "mcp-tunnel@nuc"
      echo ""
      echo "Add this public key to Hetzner:"
      cat "${KEY_PATH}.pub"
      echo ""
      echo "Run on Hetzner: bash install_mcp_tunnel.sh --hetzner --nuc-pubkey '$(cat ${KEY_PATH}.pub)'"
      exit 0
    fi

    # Install autossh
    apt-get update -qq && apt-get install -y -qq autossh

    # Create systemd service
    cat > /etc/systemd/system/mcp-tunnel.service << EOF
[Unit]
Description=MCP SSH reverse tunnel to Hetzner
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/autossh -M 0 -N \
  -R $TUNNEL_PORT:localhost:$TUNNEL_PORT \
  $HETZNER_USER@$HETZNER_HOST \
  -i $KEY_PATH \
  -o StrictHostKeyChecking=accept-new \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -o ExitOnForwardFailure=yes
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable mcp-tunnel
    echo "Done. Start with: systemctl start mcp-tunnel"
    echo "Check with: systemctl status mcp-tunnel"
    ;;

  *)
    echo "Usage:"
    echo "  $0 --hetzner --nuc-pubkey 'ssh-ed25519 AAAA...'"
    echo "  $0 --nuc --hetzner-host hurtig.ai --key-path /root/.ssh/mcp_tunnel_ed25519"
    exit 1
    ;;
esac
