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
$PIP install --upgrade "setuptools>=68.0" wheel 2>&1 | tail -1

# Install Python dependencies and package
# Clean any stale build artifacts to ensure latest code is installed
rm -rf "$INSTALL_DIR/build" "$INSTALL_DIR"/*.egg-info 2>/dev/null
echo ""
echo "Installing jt-glogarch and dependencies..."
$PIP install --no-build-isolation --no-cache-dir --force-reinstall --no-deps "$INSTALL_DIR"
$PIP install --no-build-isolation --no-cache-dir "$INSTALL_DIR"
echo ""
echo "Python packages installed OK"

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

# --- Copy example config if needed ---
if [ ! -f "$INSTALL_DIR/config.yaml" ] && [ ! -f "$CONFIG_DIR/config.yaml" ]; then
    echo ""
    echo "Copying example config..."
    cp "$INSTALL_DIR/deploy/config.yaml.example" "$INSTALL_DIR/config.yaml"
    echo "  => $INSTALL_DIR/config.yaml"
    echo "  Please edit this file with your Graylog server details and API token"
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
    read -p "Install systemd service? [Y/n] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        cp "$INSTALL_DIR/deploy/jt-glogarch.service" /etc/systemd/system/
        systemctl daemon-reload
        echo "Service installed."
        echo "  Enable:  systemctl enable --now jt-glogarch"
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
