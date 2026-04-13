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

# 1. Backup DB
echo ""
echo "[1/5] Backing up database..."
sudo -u jt-glogarch python3 -m glogarch db-backup 2>/dev/null || echo "  (skip: db-backup not available in current version)"

# 2. Pull latest
echo ""
echo "[2/5] Pulling latest version..."
cd "$INSTALL_DIR"
git pull

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
