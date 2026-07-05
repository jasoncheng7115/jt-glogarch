#!/bin/bash
# jt-glogarch Install Script
# Author: Jason Cheng (Jason Tools)

set -e

SERVICE_USER="jt-glogarch"
INSTALL_DIR="/opt/jt-glogarch"
ARCHIVE_DIR="/data/graylog-archives"
CONFIG_DIR="/etc/jt-glogarch"
CERT_DIR="$INSTALL_DIR/certs"
DB_PATH="$INSTALL_DIR/jt-glogarch.db"

echo "=== jt-glogarch Installer ==="
echo ""

# Detect whether we are running over an existing, already-running install
# (i.e. install.sh is being used as an upgrade). If the service was active
# before we touched anything, we must restart it afterwards so the new code
# actually takes effect — reinstalling dist-packages does NOT restart the
# running process on its own.
WAS_ACTIVE=no
if command -v systemctl &>/dev/null; then
    systemctl is-active --quiet jt-glogarch 2>/dev/null && WAS_ACTIVE=yes
fi

# Check Python version
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 not found. Please install Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo "Error: Python 3.10+ required (found $PYTHON_VERSION)"
    exit 1
fi
echo "Python $PYTHON_VERSION OK"

# Check pip
if ! command -v pip3 &>/dev/null && ! command -v pip &>/dev/null; then
    echo "Error: pip not found. Please install: apt install python3-pip"
    exit 1
fi
PIP=$(command -v pip3 || command -v pip)
echo "pip OK ($PIP)"

# Detect PEP 668 lockdown (Ubuntu 24.04+ / Debian 12+ / Python 3.11+ ship
# /usr/lib/pythonX.Y/EXTERNALLY-MANAGED, which makes `pip install` refuse to
# write to the system Python without --break-system-packages). jt-glogarch
# is a dedicated service install — writing into the system Python is the
# intended deployment model — so pass the flag through automatically. Older
# distros never get this flag (the marker file isn't present there).
EM_FILE=$(python3 -c 'import sysconfig; print(sysconfig.get_paths()["stdlib"] + "/EXTERNALLY-MANAGED")' 2>/dev/null || true)
PIP_FLAGS=""
if [ -n "$EM_FILE" ] && [ -f "$EM_FILE" ]; then
    PIP_FLAGS="--break-system-packages"
    echo "Detected PEP 668 (EXTERNALLY-MANAGED) — using --break-system-packages"
fi

# --- Create service user ---
echo ""
if id "$SERVICE_USER" &>/dev/null; then
    echo "User '$SERVICE_USER' already exists"
else
    echo "Creating system user '$SERVICE_USER'..."
    useradd --system --no-create-home --home-dir "$INSTALL_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
    echo "User '$SERVICE_USER' created"
fi
# Allow reading journalctl logs (for Web UI System Logs page)
usermod -aG systemd-journal "$SERVICE_USER" 2>/dev/null || true

# Ensure setuptools is new enough to read pyproject.toml metadata
echo ""
echo "Upgrading setuptools and wheel..."
$PIP install $PIP_FLAGS --upgrade "setuptools>=68.0" wheel 2>&1 | tail -1

# Install Python dependencies and package
# Clean any stale build artifacts to ensure latest code is installed
rm -rf "$INSTALL_DIR/build" "$INSTALL_DIR"/*.egg-info 2>/dev/null
echo ""
echo "Installing jt-glogarch and dependencies..."
$PIP install $PIP_FLAGS --no-build-isolation --no-cache-dir --force-reinstall --no-deps "$INSTALL_DIR"
# Install runtime deps + the [report] extra (Playwright) so PDF Reports work
# out of the box. Bracket-extra syntax requires the path quoted.
$PIP install $PIP_FLAGS --no-build-isolation --no-cache-dir "$INSTALL_DIR"[report]
echo ""
echo "Python packages installed OK"

# --- PDF Reports host deps: Chromium browser + CJK font (best-effort) ---
if [ -f "$INSTALL_DIR/deploy/report-deps.sh" ]; then
    source "$INSTALL_DIR/deploy/report-deps.sh"
    install_report_deps "$PIP_FLAGS"
fi

# --- Create directories ---
echo ""
echo "Creating directories..."

# Archive storage
mkdir -p "$ARCHIVE_DIR"
echo "  $ARCHIVE_DIR"

# Config directory
mkdir -p "$CONFIG_DIR"
echo "  $CONFIG_DIR"

# Cert directory
mkdir -p "$CERT_DIR"
echo "  $CERT_DIR"

# --- Write a minimal bootstrap config if none exists ---
# Fresh installs get an EMPTY servers list on purpose: the Web UI detects the
# unconfigured state and launches the first-run setup wizard at /setup, so the
# admin never has to hand-edit YAML. The full annotated reference lives in
# deploy/config.yaml.example (and `glogarch config`).
if [ ! -f "$INSTALL_DIR/config.yaml" ] && [ ! -f "$CONFIG_DIR/config.yaml" ]; then
    echo ""
    echo "Writing minimal bootstrap config (first-run setup wizard will guide you)..."
    cat > "$INSTALL_DIR/config.yaml" <<'BOOTSTRAP'
# jt-glogarch bootstrap config — configure everything from the Web UI.
# Open https://<this-host>:8990/ and the setup wizard will guide you.
# Full reference: deploy/config.yaml.example
servers: []            # populated by the /setup wizard (or Settings page)
default_server: ""
export_mode: api

opensearch:
  hosts: []
  verify_ssl: false

export:
  base_path: /data/graylog-archives

database_path: /opt/jt-glogarch/jt-glogarch.db
log_level: INFO

web:
  host: 0.0.0.0
  port: 8990
  ssl_certfile: /opt/jt-glogarch/certs/server.crt
  ssl_keyfile: /opt/jt-glogarch/certs/server.key
  localadmin_password_hash: ""   # set via the setup wizard (step 1)

op_audit:
  enabled: true
  listen_port: 8991
  retention_days: 180
BOOTSTRAP
    echo "  => $INSTALL_DIR/config.yaml"
    echo "  Finish setup in your browser: https://<this-host>:8990/"
fi

# --- Generate self-signed SSL certificate ---
if [ ! -f "$CERT_DIR/server.crt" ]; then
    echo ""
    echo "Generating self-signed SSL certificate..."
    HOSTNAME=$(hostname -f 2>/dev/null || hostname)
    openssl req -x509 -newkey rsa:2048 -nodes \
        -keyout "$CERT_DIR/server.key" \
        -out "$CERT_DIR/server.crt" \
        -days 3650 \
        -subj "/CN=$HOSTNAME/O=jt-glogarch" \
        -addext "subjectAltName=DNS:$HOSTNAME,DNS:localhost,IP:127.0.0.1" \
        2>/dev/null
    echo "  SSL cert: $CERT_DIR/server.crt"
    echo "  SSL key:  $CERT_DIR/server.key"
    echo "  Valid for 10 years, CN=$HOSTNAME"
else
    echo ""
    echo "SSL certificate already exists at $CERT_DIR/server.crt"
fi

# --- Set ownership and permissions ---
echo ""
echo "Setting ownership and permissions for user '$SERVICE_USER'..."

# Install directory (program + config + db + certs)
chown -R "$SERVICE_USER":"$SERVICE_USER" "$INSTALL_DIR"
chmod 750 "$INSTALL_DIR"

# SSL key needs restricted access
chmod 600 "$CERT_DIR/server.key"
chmod 644 "$CERT_DIR/server.crt"

# Archive storage directory
chown -R "$SERVICE_USER":"$SERVICE_USER" "$ARCHIVE_DIR"
chmod 750 "$ARCHIVE_DIR"

# Config directory
chown -R "$SERVICE_USER":"$SERVICE_USER" "$CONFIG_DIR"
chmod 750 "$CONFIG_DIR"

# DB file (may not exist yet, but set dir permissions)
touch "$DB_PATH"
chown "$SERVICE_USER":"$SERVICE_USER" "$DB_PATH"
chmod 640 "$DB_PATH"

echo "  $INSTALL_DIR => $SERVICE_USER"
echo "  $ARCHIVE_DIR => $SERVICE_USER"
echo "  $CONFIG_DIR  => $SERVICE_USER"

# --- Install systemd service (optional) ---
if [ -d /etc/systemd/system ]; then
    echo ""
    # Only prompt when stdin is an interactive terminal. Under a piped /
    # non-interactive install (ssh 'bash ...', curl | bash, redirected stdin)
    # `read` hits EOF and returns non-zero — which, with `set -e`, would abort
    # the whole script right here and silently skip service install + restart.
    # Default to installing the service in that case.
    REPLY=Y
    if [ -t 0 ]; then
        read -p "Install systemd service? [Y/n] " -n 1 -r || true
        echo
    fi
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        cp "$INSTALL_DIR/deploy/jt-glogarch.service" /etc/systemd/system/
        systemctl daemon-reload
        echo "Service installed."
        if [ "$WAS_ACTIVE" = "yes" ]; then
            # install.sh was used as an upgrade over a running service —
            # restart so the newly installed code actually takes effect.
            echo "Existing service was running — restarting to load the new version..."
            systemctl restart jt-glogarch
            sleep 2
            if systemctl is-active --quiet jt-glogarch; then
                echo "  Service restarted (now running new version)."
            else
                echo "  WARNING: service failed to restart — check: journalctl -u jt-glogarch -n 50"
            fi
        else
            echo "  Enable:  systemctl enable --now jt-glogarch"
        fi
        echo "  Status:  systemctl status jt-glogarch"
        echo "  Logs:    journalctl -u jt-glogarch -f"
    fi
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit $INSTALL_DIR/config.yaml with your Graylog server details"
echo "  2. Run: glogarch status"
echo "  3. Run: glogarch export --days 180"
echo "  4. systemctl enable --now jt-glogarch  (Web UI: https://$(hostname):8990)"
