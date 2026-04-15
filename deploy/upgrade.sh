#!/bin/bash
# jt-glogarch Upgrade Script
# Usage: sudo bash deploy/upgrade.sh

set -e
INSTALL_DIR="/opt/jt-glogarch"
SERVICE="jt-glogarch"

echo "=== jt-glogarch Upgrade ==="
echo ""

# Check we're root
if [ "$(id -u)" -ne 0 ]; then
    echo "Error: must run as root (sudo)"
    exit 1
fi

# Check install dir
if [ ! -d "$INSTALL_DIR/glogarch" ]; then
    echo "Error: $INSTALL_DIR not found. Is jt-glogarch installed?"
    exit 1
fi

# Show current version
CURRENT=$(python3 -c "import glogarch; print(glogarch.__version__)" 2>/dev/null || echo "unknown")
echo "Current version: $CURRENT"

# 0. Fix permissions (for upgrades from older versions)
usermod -aG systemd-journal jt-glogarch 2>/dev/null || true

# 1. Backup DB
echo ""
echo "[1/5] Backing up database..."
mkdir -p /var/backups/jt-glogarch
chown jt-glogarch:jt-glogarch /var/backups/jt-glogarch
sudo -u jt-glogarch python3 -m glogarch db-backup 2>/dev/null || echo "  (skip: db-backup not available in current version)"

# 2. Pull latest
echo ""
echo "[2/5] Pulling latest version..."
cd "$INSTALL_DIR"
git pull

# 2.5. Ensure op_audit config exists (new in v1.7+)
CONFIG_FILE="$INSTALL_DIR/config.yaml"
if [ -f "$CONFIG_FILE" ]; then
    if ! grep -q "op_audit:" "$CONFIG_FILE" 2>/dev/null; then
        echo ""
        echo "  Adding op_audit config (enabled by default)..."
        cat >> "$CONFIG_FILE" << 'OPAUDIT'

op_audit:
  enabled: true
  listen_port: 8991
  retention_days: 180
  max_body_size: 65536
  alert_sensitive: true
OPAUDIT
        chown jt-glogarch:jt-glogarch "$CONFIG_FILE"
    else
        # op_audit exists — ensure retention_days is present within op_audit block
        if ! sed -n '/^op_audit:/,/^[^ ]/p' "$CONFIG_FILE" | grep -q "retention_days"; then
            echo "  Adding op_audit.retention_days: 180..."
            sed -i '/^op_audit:/,/^[^ ]/{/listen_port/a\  retention_days: 180
}' "$CONFIG_FILE"
            chown jt-glogarch:jt-glogarch "$CONFIG_FILE"
        fi
    fi
fi

# 3. Install
echo ""
echo "[3/5] Installing..."
pip install --no-build-isolation --no-cache-dir --force-reinstall --no-deps "$INSTALL_DIR" 2>&1 | tail -1

# 4. Restart
echo ""
echo "[4/5] Restarting service..."
systemctl restart "$SERVICE"
sleep 2

# 5. Verify
echo ""
echo "[5/5] Verifying..."
NEW=$(python3 -c "import glogarch; print(glogarch.__version__)" 2>/dev/null || echo "unknown")
HEALTH=$(curl -sk https://localhost:8990/api/health 2>/dev/null || echo '{"status":"unreachable"}')
STATUS=$(echo "$HEALTH" | python3 -c "import sys,json;print(json.load(sys.stdin).get('status','?'))" 2>/dev/null || echo "?")

echo ""
echo "=== Upgrade Complete ==="
echo "  $CURRENT → $NEW"
echo "  Health: $STATUS"

if [ "$STATUS" != "healthy" ]; then
    echo ""
    echo "⚠ Service may not be healthy. Check: journalctl -u $SERVICE -f"
    exit 1
fi
