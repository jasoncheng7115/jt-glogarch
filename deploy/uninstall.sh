#!/bin/bash
# jt-glogarch Uninstall Script
# Author: Jason Cheng (Jason Tools)
#
# Usage:
#   sudo bash /opt/jt-glogarch/deploy/uninstall.sh
#   sudo bash /opt/jt-glogarch/deploy/uninstall.sh --dry-run
#
# Stops the service, removes the systemd unit and the pip package by default.
# Archive data, config, the install directory, and the system user are kept
# unless you opt in — each is a separate prompt because losing them is
# typically irreversible.
#
# --dry-run: print every action without executing or prompting; safe to run
#            on a live system to preview exactly what would be touched.

set -e

DRY_RUN=0
if [ "$1" = "--dry-run" ] || [ "$1" = "-n" ]; then
    DRY_RUN=1
fi

SERVICE_USER="jt-glogarch"
SERVICE="jt-glogarch"
INSTALL_DIR="/opt/jt-glogarch"
ARCHIVE_DIR="/data/graylog-archives"
CONFIG_DIR="/etc/jt-glogarch"
UNIT_FILE="/etc/systemd/system/${SERVICE}.service"

echo "=== jt-glogarch Uninstaller ==="
[ $DRY_RUN -eq 1 ] && echo "(dry-run — nothing will actually be changed)"
echo ""

if [ "$(id -u)" -ne 0 ]; then
    echo "Error: must run as root (sudo)"
    exit 1
fi

# Helper: do `cmd` for real, or just print it in dry-run mode.
run() {
    if [ $DRY_RUN -eq 1 ]; then
        echo "    [dry-run] $*"
    else
        eval "$@"
    fi
}

# Helper: yes/no prompt; in dry-run mode answers "no" by default
# (so we still print what WOULD be deleted via the run() messages).
ask_yes() {
    if [ $DRY_RUN -eq 1 ]; then
        echo "    [dry-run] would prompt: $1 [y/N]  → assuming 'yes' for preview"
        return 0
    fi
    read -p "$1 [y/N] " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# --- 1. Stop + disable + remove systemd unit ---
if systemctl list-unit-files 2>/dev/null | grep -q "^${SERVICE}.service"; then
    echo "Stopping ${SERVICE}..."
    run "systemctl stop $SERVICE 2>/dev/null || true"
    run "systemctl disable $SERVICE 2>/dev/null || true"
    if [ -f "$UNIT_FILE" ]; then
        echo "Removing systemd unit file..."
        run "rm -f $UNIT_FILE"
        run "systemctl daemon-reload"
        run "systemctl reset-failed 2>/dev/null || true"
    fi
    echo "Service removed."
else
    echo "Service ${SERVICE} not registered — skipping."
fi
echo ""

# --- 2. pip uninstall ---
PIP=$(command -v pip3 || command -v pip || true)
if [ -n "$PIP" ] && $PIP show jt-glogarch &>/dev/null; then
    echo "Uninstalling Python package..."
    run "$PIP uninstall -y jt-glogarch 2>&1 | tail -1"
fi
echo ""

# --- 3. Optional: archives ---
if [ -d "$ARCHIVE_DIR" ]; then
    SIZE=$(du -sh "$ARCHIVE_DIR" 2>/dev/null | awk '{print $1}')
    COUNT=$(find "$ARCHIVE_DIR" -type f 2>/dev/null | wc -l)
    echo "Archive directory: $ARCHIVE_DIR ($SIZE, $COUNT files)"
    echo "WARNING: deleting archives is irreversible. Re-exporting from Graylog"
    echo "         will only get whatever is still in OpenSearch's hot tier."
    if ask_yes "Delete $ARCHIVE_DIR ?"; then
        run "rm -rf $ARCHIVE_DIR"
        echo "  Deleted $ARCHIVE_DIR"
    else
        echo "  Kept $ARCHIVE_DIR"
    fi
    echo ""
fi

# --- 4. Optional: config dir ---
if [ -d "$CONFIG_DIR" ]; then
    echo "Config directory: $CONFIG_DIR"
    if ask_yes "Delete $CONFIG_DIR ?"; then
        run "rm -rf $CONFIG_DIR"
        echo "  Deleted $CONFIG_DIR"
    fi
    echo ""
fi

# --- 5. Optional: install dir (sources, DB, certs) ---
if [ -d "$INSTALL_DIR" ]; then
    echo "Install directory: $INSTALL_DIR"
    echo "  Contains source code, config.yaml, jt-glogarch.db (job/audit history),"
    echo "  certs/ (SSL keypair). Removing this means you can't recover the"
    echo "  audit log, scheduled jobs config, or operation history."
    if ask_yes "Delete $INSTALL_DIR ?"; then
        run "rm -rf $INSTALL_DIR"
        echo "  Deleted $INSTALL_DIR"
    else
        echo "  Kept $INSTALL_DIR"
    fi
    echo ""
fi

# --- 6. Optional: system user ---
if id "$SERVICE_USER" &>/dev/null; then
    echo "System user: $SERVICE_USER"
    if [ -d "$INSTALL_DIR" ]; then
        echo "  (still owns $INSTALL_DIR — keep the user if you kept the directory)"
    fi
    if ask_yes "Remove user '$SERVICE_USER' ?"; then
        run "userdel $SERVICE_USER 2>&1 | head -3"
        echo "  User removed"
    fi
    echo ""
fi

echo "=== Uninstall Complete ==="
echo ""
echo "If you also forwarded nginx audit syslog into jt-glogarch (port 8991),"
echo "remember to remove that 'access_log syslog:server=...' line from each"
echo "Graylog node's nginx config and reload nginx."
