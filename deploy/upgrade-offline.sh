#!/bin/bash
# jt-glogarch OFFLINE (air-gapped) Upgrade Script
#
# For customer sites that CANNOT reach the internet. On an internet-connected
# machine, build the bundle with scripts/build-offline-bundle.sh, copy the
# resulting jt-glogarch-<ver>-offline.tar.gz to the target host, extract it,
# then run this script FROM the extracted directory:
#
#     tar xzf jt-glogarch-<ver>-offline.tar.gz
#     cd jt-glogarch-<ver>-offline
#     sudo bash upgrade-offline.sh
#
# The bundle contains the jt-glogarch wheel AND every runtime dependency wheel,
# so pip never touches the network (--no-index). Nothing else is required on
# the target host except Python 3.10+ and the existing jt-glogarch install.

set -e
INSTALL_DIR="/opt/jt-glogarch"
SERVICE="jt-glogarch"
# Directory this script lives in = the extracted bundle (holds all the wheels).
BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== jt-glogarch OFFLINE Upgrade ==="
echo ""

# Must be root
if [ "$(id -u)" -ne 0 ]; then
    echo "Error: must run as root (sudo)"
    exit 1
fi

# Existing install present?
if [ ! -d "$INSTALL_DIR/glogarch" ]; then
    echo "Error: $INSTALL_DIR not found. Is jt-glogarch installed? (offline upgrade only)"
    exit 1
fi

# Locate the jt-glogarch wheel inside the bundle
WHEEL=$(ls "$BUNDLE_DIR"/jt_glogarch-*.whl 2>/dev/null | head -1)
if [ -z "$WHEEL" ]; then
    echo "Error: no jt_glogarch-*.whl found in $BUNDLE_DIR."
    echo "       Run this script from inside the extracted offline bundle."
    exit 1
fi
echo "Bundle:  $BUNDLE_DIR"
echo "Wheel:   $(basename "$WHEEL")"

CURRENT=$(python3 -c "import glogarch; print(glogarch.__version__)" 2>/dev/null || echo "unknown")
echo "Current: $CURRENT"
echo ""

# PEP 668 (Ubuntu 24.04+/Debian 12+/Python 3.11+) — add --break-system-packages
EM_FILE=$(python3 -c 'import sysconfig; print(sysconfig.get_paths()["stdlib"] + "/EXTERNALLY-MANAGED")' 2>/dev/null || true)
PIP_FLAGS=""
if [ -n "$EM_FILE" ] && [ -f "$EM_FILE" ]; then
    PIP_FLAGS="--break-system-packages"
    echo "Detected PEP 668 (EXTERNALLY-MANAGED) — using --break-system-packages"
fi

# 0. Environment fixes (parity with online upgrade.sh)
usermod -aG systemd-journal jt-glogarch 2>/dev/null || true

# 1. Backup DB — a genuine backup failure must NOT be silently swallowed.
#    Run from INSTALL_DIR so `db-backup` finds ./config.yaml (and thus the DB).
echo "[1/5] Backing up database..."
mkdir -p /var/backups/jt-glogarch
chown jt-glogarch:jt-glogarch /var/backups/jt-glogarch
if sudo -u jt-glogarch python3 -m glogarch db-backup --help >/dev/null 2>&1; then
    if ! ( cd "$INSTALL_DIR" && sudo -u jt-glogarch python3 -m glogarch db-backup ); then
        echo "  WARNING: database backup FAILED (see error above)."
        # Prompt only if a real terminal is attached; otherwise (scripted SOP)
        # continue with a loud warning rather than hanging on a missing tty.
        if read -r -p "  Continue upgrade without a fresh backup? [y/N] " _ans </dev/tty 2>/dev/null; then
            case "$_ans" in y|Y) echo "  Continuing." ;; *) echo "  Aborting."; exit 1 ;; esac
        else
            echo "  (non-interactive) Continuing WITHOUT a fresh backup — verify the backup manually."
        fi
    fi
else
    echo "  (skip: db-backup not available in current version)"
fi

# 2. Ensure op_audit config exists (new in v1.7+) — never overwrite existing config
CONFIG_FILE="$INSTALL_DIR/config.yaml"
if [ -f "$CONFIG_FILE" ] && ! grep -q "op_audit:" "$CONFIG_FILE" 2>/dev/null; then
    echo "[2/5] Adding op_audit config block..."
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
    echo "[2/5] Config present — not modified."
fi

# 2b. Refresh the /opt source tree so `python -m glogarch` run FROM /opt (the
#     CLI, which Python imports from the CWD) uses the new code too. The wheel
#     install below only updates dist-packages, which the systemd service uses.
#     The online git-pull updates /opt in place; mirror that here. Atomic swap.
if [ -d "$BUNDLE_DIR/src/glogarch" ]; then
    echo "      refreshing $INSTALL_DIR source tree..."
    rm -rf "$INSTALL_DIR/glogarch.new"
    cp -r "$BUNDLE_DIR/src/glogarch" "$INSTALL_DIR/glogarch.new"
    rm -rf "$INSTALL_DIR/glogarch"
    mv "$INSTALL_DIR/glogarch.new" "$INSTALL_DIR/glogarch"
    [ -f "$BUNDLE_DIR/src/pyproject.toml" ] && cp "$BUNDLE_DIR/src/pyproject.toml" "$INSTALL_DIR/pyproject.toml"
    chown -R jt-glogarch:jt-glogarch "$INSTALL_DIR/glogarch" 2>/dev/null || true
fi

# 3. Install from the local bundle ONLY (no network).
#    Step A: resolve + install any MISSING dependency from the bundled wheels.
#    Step B: force-reinstall the package itself so the static files (served from
#            dist-packages) are refreshed — same reason the online upgrade uses
#            --force-reinstall.
echo "[3/5] Installing from offline bundle (no network)..."
pip install $PIP_FLAGS --no-index --find-links="$BUNDLE_DIR" --no-build-isolation "$WHEEL" 2>&1 | tail -2
pip install $PIP_FLAGS --no-index --no-build-isolation --force-reinstall --no-deps "$WHEEL" 2>&1 | tail -1
# PDF Reports: the [report] extra (Playwright) isn't pulled by a bare wheel
# install — install it by name from the bundled wheels (skips silently if the
# bundle predates PDF Reports and has no playwright wheel).
pip install $PIP_FLAGS --no-index --find-links="$BUNDLE_DIR" --no-build-isolation playwright pymupdf pillow 2>&1 | tail -1 \
    || echo "  (no bundled report wheels — PDF Reports unavailable on this bundle)"
# Chromium browser + CJK font come from the bundle (offline mode).
if [ -f "$BUNDLE_DIR/report-deps.sh" ]; then
    source "$BUNDLE_DIR/report-deps.sh"
    install_report_deps "$PIP_FLAGS" "$BUNDLE_DIR"
fi

# 4. Restart
echo "[4/5] Restarting service..."
chown -R jt-glogarch:jt-glogarch "$INSTALL_DIR" 2>/dev/null || true
systemctl restart "$SERVICE"
sleep 2

# 5. Verify
echo "[5/5] Verifying..."
NEW=$(python3 -c "import glogarch; print(glogarch.__version__)" 2>/dev/null || echo "unknown")
HEALTH=$(curl -sk https://localhost:8990/api/health 2>/dev/null || echo '{"status":"unreachable"}')
STATUS=$(echo "$HEALTH" | python3 -c "import sys,json;print(json.load(sys.stdin).get('status','?'))" 2>/dev/null || echo "?")

echo ""
echo "=== Offline Upgrade Complete ==="
echo "  $CURRENT -> $NEW"
echo "  Health: $STATUS"

if [ "$STATUS" != "healthy" ]; then
    echo ""
    echo "WARNING: service may not be healthy. Check: journalctl -u $SERVICE -f"
    exit 1
fi
