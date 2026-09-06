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

# --- TLS / proxy options (for corporate MITM proxies or a broken CA store) ---
#   --ca-bundle <file>   verify against a custom CA (e.g. the proxy root CA)
#   --insecure           skip TLS verification for this run (like 'curl -k')
# Both also readable from the environment (JT_CA_BUNDLE / JT_INSECURE).
#   --offline [<bundle-dir>]  install with ZERO network: every wheel, plus
#                        Chromium and the CJK font, comes from an offline
#                        bundle built by scripts/build-offline-bundle.sh.
#                        Defaults to the directory this script lives in, which
#                        is where install-offline.sh calls it from.
OFFLINE_DIR=""
while [ $# -gt 0 ]; do
    case "$1" in
        --ca-bundle) JT_CA_BUNDLE="$2"; shift 2 ;;
        --ca-bundle=*) JT_CA_BUNDLE="${1#*=}"; shift ;;
        --insecure) JT_INSECURE=1; shift ;;
        --offline)
            if [ -n "$2" ] && [ -d "$2" ]; then OFFLINE_DIR="$2"; shift 2
            else OFFLINE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; shift; fi ;;
        --offline=*) OFFLINE_DIR="${1#*=}"; shift ;;
        -h|--help)
            echo "Usage: sudo bash deploy/install.sh [--ca-bundle <file>] [--insecure] [--offline <bundle-dir>]"
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Offline mode: point pip at the bundle's wheels and never at an index. An
# air-gapped host has no PyPI, and a pip that silently falls back to the
# network would hang for minutes and then fail — so --no-index is explicit.
PIP_SRC=""
if [ -n "$OFFLINE_DIR" ]; then
    if ! ls "$OFFLINE_DIR"/jt_glogarch-*.whl >/dev/null 2>&1; then
        echo "Error: --offline given but no jt_glogarch-*.whl in $OFFLINE_DIR"
        echo "       Point --offline at an extracted offline bundle."
        exit 1
    fi
    PIP_SRC="--no-index --find-links=$OFFLINE_DIR"
    echo "OFFLINE mode: installing from $OFFLINE_DIR (no network will be used)"
fi
if [ -f "$INSTALL_DIR/deploy/tls-env.sh" ]; then
    source "$INSTALL_DIR/deploy/tls-env.sh"
else
    export GIT_TERMINAL_PROMPT=0; GIT_TLS_OPTS=""; PIP_TLS_OPTS=""
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
if [ -n "$OFFLINE_DIR" ]; then
    # Only if the bundle actually carries them; the system copies are normally
    # new enough, and a hard failure here would abort an otherwise fine install.
    $PIP install $PIP_SRC $PIP_FLAGS --upgrade "setuptools>=68.0" wheel 2>&1 | tail -1 \
        || echo "  (not in the bundle — using the system setuptools/wheel)"
else
    $PIP install $PIP_TLS_OPTS $PIP_FLAGS --upgrade "setuptools>=68.0" wheel 2>&1 | tail -1
fi

# Install Python dependencies and package
# Clean any stale build artifacts to ensure latest code is installed
rm -rf "$INSTALL_DIR/build" "$INSTALL_DIR"/*.egg-info 2>/dev/null
echo ""
echo "Installing jt-glogarch and dependencies..."
if [ -n "$OFFLINE_DIR" ]; then
    # Install the prebuilt wheel + every dependency from the bundle. Building
    # from the source tree would need a network for build deps.
    OFFLINE_WHEEL=$(ls "$OFFLINE_DIR"/jt_glogarch-*.whl | head -1)
    $PIP install $PIP_SRC $PIP_FLAGS --no-build-isolation "$OFFLINE_WHEEL" 2>&1 | tail -2
    $PIP install $PIP_SRC $PIP_FLAGS --no-build-isolation --force-reinstall --no-deps "$OFFLINE_WHEEL" 2>&1 | tail -1
    # The [report] extra is not pulled in by a bare wheel install — take it by
    # name from the bundle, and carry on without it if this bundle predates it.
    $PIP install $PIP_SRC $PIP_FLAGS --no-build-isolation playwright pymupdf pillow 2>&1 | tail -1 \
        || echo "  (no report wheels in this bundle — PDF Reports unavailable)"
else
$PIP install $PIP_TLS_OPTS $PIP_FLAGS --no-build-isolation --no-cache-dir --force-reinstall --no-deps "$INSTALL_DIR"
# Install runtime deps + the [report] extra (Playwright) so PDF Reports work
# out of the box. Bracket-extra syntax requires the path quoted.
# On Ubuntu 24.04 (and after an OS/Python major upgrade, e.g. 22.04→24.04), pip
# can ABORT here with "Cannot uninstall <pkg>, RECORD file not found. …installed
# by debian." when a dependency (e.g. PyYAML) is a distro-managed package it wants
# to upgrade. Retry with --ignore-installed, which installs fresh copies without
# touching the Debian ones.
if ! $PIP install $PIP_TLS_OPTS $PIP_FLAGS --no-build-isolation --no-cache-dir "$INSTALL_DIR"[report]; then
    echo "  (deps install hit a distro-managed package — retrying with --ignore-installed)"
    $PIP install $PIP_TLS_OPTS $PIP_FLAGS --ignore-installed --no-build-isolation --no-cache-dir "$INSTALL_DIR"[report]
fi
fi
echo ""
echo "Python packages installed OK"

# --- PDF Reports host deps: Chromium browser + CJK font (best-effort) ---
REPORT_ENGINE_OK=unknown
if [ -f "$INSTALL_DIR/deploy/report-deps.sh" ]; then
    source "$INSTALL_DIR/deploy/report-deps.sh"
    install_report_deps "$PIP_FLAGS" "$OFFLINE_DIR"
    # Installing the browser is not proof that it RUNS — verify by launching it.
    # Offline hosts especially: the OS shared libraries Chromium needs cannot be
    # carried in a tarball, so this is where that shows up, not hours later in a
    # scheduled report.
    if verify_report_engine; then REPORT_ENGINE_OK=yes; else REPORT_ENGINE_OK=no; fi
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
# NOTE: we intentionally do NOT create a config.yaml here. With no config file
# the app loads built-in defaults (unconfigured → servers empty) and launches the
# first-run setup wizard at /setup, which writes /opt/jt-glogarch/config.yaml when
# the operator saves. Shipping a pre-made config just risks it going stale/wrong.
if [ ! -f "$INSTALL_DIR/config.yaml" ] && [ ! -f "$CONFIG_DIR/config.yaml" ]; then
    echo ""
    echo "No config.yaml — the first-run setup wizard will guide you."
    echo "  Open your browser: https://<this-host>:8990/  (redirects to /setup)"
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
# /etc/systemd/system can exist on a host with no systemctl (containers, some
# minimal images). Requiring only the directory made the script die 127 at the
# very last step — after a completely successful install — which reads as a
# failed install.
if [ -d /etc/systemd/system ] && command -v systemctl &>/dev/null; then
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

if [ ! -d /etc/systemd/system ] || ! command -v systemctl &>/dev/null; then
    echo ""
    echo "No systemd on this host — the service unit was NOT installed."
    echo "  Start manually: sudo -u $SERVICE_USER python3 -m glogarch server"
fi

echo ""
echo "=== Installation Complete ==="
if [ "$REPORT_ENGINE_OK" = "no" ]; then
    echo ""
    echo "  NOTE: PDF Reports will NOT render on this host (see the check above)."
    echo "        Archiving, restore, scheduling and the Web UI are unaffected."
fi
echo ""
echo "Next steps:"
echo "  1. Edit $INSTALL_DIR/config.yaml with your Graylog server details"
echo "  2. Run: glogarch status"
echo "  3. Run: glogarch export --days 180"
echo "  4. systemctl enable --now jt-glogarch  (Web UI: https://$(hostname):8990)"
