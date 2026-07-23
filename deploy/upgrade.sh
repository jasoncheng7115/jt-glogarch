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

# --- TLS / proxy options (for corporate MITM proxies or a broken CA store) ---
#   --ca-bundle <file>   verify against a custom CA (e.g. the proxy root CA)
#   --insecure           skip TLS verification for this run (like 'curl -k')
# Both also readable from the environment (JT_CA_BUNDLE / JT_INSECURE).
while [ $# -gt 0 ]; do
    case "$1" in
        --ca-bundle) JT_CA_BUNDLE="$2"; shift 2 ;;
        --ca-bundle=*) JT_CA_BUNDLE="${1#*=}"; shift ;;
        --insecure) JT_INSECURE=1; shift ;;
        -h|--help)
            echo "Usage: sudo bash deploy/upgrade.sh [--ca-bundle <file>] [--insecure]"
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done
if [ -f "$INSTALL_DIR/deploy/tls-env.sh" ]; then
    source "$INSTALL_DIR/deploy/tls-env.sh"
else
    export GIT_TERMINAL_PROMPT=0; GIT_TLS_OPTS=""; PIP_TLS_OPTS=""
fi

# Show current version
CURRENT=$(python3 -c "import glogarch; print(glogarch.__version__)" 2>/dev/null || echo "unknown")
echo "Current version: $CURRENT"

# Detect PEP 668 lockdown (Ubuntu 24.04+ / Debian 12+ / Python 3.11+ ship
# /usr/lib/pythonX.Y/EXTERNALLY-MANAGED). Pass --break-system-packages when
# present so the upgrade pip call works the same way install.sh does.
EM_FILE=$(python3 -c 'import sysconfig; print(sysconfig.get_paths()["stdlib"] + "/EXTERNALLY-MANAGED")' 2>/dev/null || true)
PIP_FLAGS=""
if [ -n "$EM_FILE" ] && [ -f "$EM_FILE" ]; then
    PIP_FLAGS="--break-system-packages"
    echo "Detected PEP 668 (EXTERNALLY-MANAGED) — using --break-system-packages"
fi

# 0. Fix permissions and environment (for upgrades from older versions)
usermod -aG systemd-journal jt-glogarch 2>/dev/null || true

# Ensure git trusts the install directory (owned by jt-glogarch, not root)
git config --global --add safe.directory "$INSTALL_DIR" 2>/dev/null || true

# 1. Backup DB
echo ""
echo "[1/5] Backing up database..."
mkdir -p /var/backups/jt-glogarch
chown jt-glogarch:jt-glogarch /var/backups/jt-glogarch
# Keep stderr visible: a genuine backup failure (disk full, permissions) must
# NOT be silently swallowed — that backup is the safety net for this upgrade.
# Only the "command not present in the old version" case is an acceptable skip.
if sudo -u jt-glogarch python3 -m glogarch db-backup --help >/dev/null 2>&1; then
    # Run from INSTALL_DIR so db-backup finds ./config.yaml (and thus the DB).
    if ! ( cd "$INSTALL_DIR" && sudo -u jt-glogarch python3 -m glogarch db-backup ); then
        echo "  ⚠ WARNING: database backup FAILED (see error above)."
        if read -r -p "  Continue upgrade without a fresh backup? [y/N] " _ans </dev/tty 2>/dev/null; then
            case "$_ans" in
                y|Y) echo "  Continuing without fresh backup." ;;
                *)   echo "  Aborting upgrade."; exit 1 ;;
            esac
        else
            echo "  (non-interactive) Continuing WITHOUT a fresh backup — verify the backup manually."
        fi
    fi
else
    echo "  (skip: db-backup not available in current version)"
fi

# 2. Pull latest
echo ""
echo "[2/5] Pulling latest version..."
cd "$INSTALL_DIR"
# CRITICAL: guarantee user data is git-IGNORED *before* any git stash/clean/pull.
# Installs from before v1.10.3 shipped no .gitignore, so config.yaml, certs/,
# .session_secret and the DB were untracked — and `git stash -u` below would
# sweep them away and never restore them (real data loss). Writing these rules
# first makes stash/clean skip them. Idempotent; the pull later brings the
# committed .gitignore too.
for _pat in "config.yaml" "config.yaml.bak*" "*.db" "*.db-wal" "*.db-shm" \
            ".session_secret" "certs/" ".playwright/" "reports/" "backups/"; do
    grep -qxF "$_pat" "$INSTALL_DIR/.gitignore" 2>/dev/null || echo "$_pat" >> "$INSTALL_DIR/.gitignore"
done
# `set -e` would abort on a bare `git pull` failure (local edits to tracked
# files, e.g. a hotfix, make pull refuse) leaving a half-upgraded box. Try a
# clean pull; if it fails, auto-stash the local changes and retry so the
# upgrade proceeds. User data (config.yaml/certs/DB) is now gitignored above,
# so `git stash -u` never touches it.
# Capture stderr so we can tell a TLS/CA failure (which auto-stash can't fix)
# apart from a local-changes conflict (which it can).
# `timeout` guards against a proxy that black-holes the connection (never hang);
# $GIT_TLS_OPTS carries any --ca-bundle / --insecure choice.
_git_pull() { timeout 180 git $GIT_TLS_OPTS pull --ff-only "$@"; }
_pull_log="$(mktemp 2>/dev/null || echo "/tmp/jt-glogarch-pull.$$")"
if _git_pull 2>"$_pull_log"; then
    [ -s "$_pull_log" ] && cat "$_pull_log"      # show 'From github…' progress
    rm -f "$_pull_log"
else
    _pull_err="$(cat "$_pull_log" 2>/dev/null)"
    rm -f "$_pull_log"
    # A TLS/CA verification failure is NOT a local-changes problem — stashing
    # won't help. Detect it and print an actionable fix instead of a raw git
    # error (real field case: 'server certificate verification failed.
    # CAfile: none' = the host's system CA bundle is missing/broken, or a
    # corporate TLS-interception proxy whose root CA isn't trusted here).
    if printf '%s' "$_pull_err" | grep -qiE 'certificate verification failed|SSL certificate problem|unable to get local issuer|self.signed certificate'; then
        echo "  ⚠ ERROR: git could not verify GitHub's TLS certificate:"
        printf '      %s\n' "$_pull_err" | head -3
        echo ""
        echo "  This host cannot verify HTTPS. Pick ONE fix:"
        echo ""
        echo "  1) Broken/empty CA store ('CAfile: none') — repair it (RECOMMENDED):"
        echo "        sudo apt-get install --reinstall -y ca-certificates && sudo update-ca-certificates"
        echo ""
        echo "  2) Behind a corporate TLS proxy — trust its root CA once (SECURE):"
        echo "        sudo cp <proxy-root-ca>.crt /usr/local/share/ca-certificates/ && sudo update-ca-certificates"
        echo "     …or, without touching the system store, point this upgrade at it:"
        echo "        sudo bash deploy/upgrade.sh --ca-bundle /path/to/proxy-root-ca.crt"
        echo ""
        echo "  3) Accept the risk for this run only (like 'curl -k'):"
        echo "        sudo bash deploy/upgrade.sh --insecure"
        echo ""
        echo "  Fully offline host? Use the offline bundle (no network/TLS):"
        echo "        deploy/upgrade-offline.sh"
        exit 1
    fi
    echo "$_pull_err"
    echo "  Local changes detected — stashing before pull..."
    git stash push -u -m "jt-glogarch upgrade auto-stash" >/dev/null 2>&1 || true
    if ! _git_pull; then
        echo "  ⚠ ERROR: 'git pull' failed even after stashing local changes."
        echo "     Resolve manually (e.g. 'git status' in $INSTALL_DIR) and re-run."
        exit 1
    fi
    echo "  (local changes saved in 'git stash' — run 'git stash list' to review)"
fi

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
pip install $PIP_TLS_OPTS $PIP_FLAGS --no-build-isolation --no-cache-dir --force-reinstall --no-deps "$INSTALL_DIR" 2>&1 | tail -1
# Pull in the [report] extra (Playwright) — an existing install predating PDF
# Reports won't have it; upgrades must. Deps-only, cheap when already satisfied.
# On Ubuntu 24.04 / after an OS-Python major upgrade, pip can ABORT with "Cannot
# uninstall <pkg>, RECORD file not found …installed by debian" when a dependency
# is distro-managed. Retry with --ignore-installed (installs fresh, leaves the
# Debian copies alone). This is also the recovery path after 22.04→24.04, where
# the old deps live under the previous Python and must be reinstalled.
if pip install $PIP_TLS_OPTS $PIP_FLAGS --no-build-isolation --no-cache-dir "$INSTALL_DIR"[report] > /tmp/jt-report-pip.log 2>&1; then
    tail -1 /tmp/jt-report-pip.log
else
    echo "  (deps install hit a distro-managed package — retrying with --ignore-installed)"
    pip install $PIP_TLS_OPTS $PIP_FLAGS --ignore-installed --no-build-isolation --no-cache-dir "$INSTALL_DIR"[report] 2>&1 | tail -1
fi
# Chromium browser + CJK font (best-effort; re-runnable — skips if present).
if [ -f "$INSTALL_DIR/deploy/report-deps.sh" ]; then
    source "$INSTALL_DIR/deploy/report-deps.sh"
    install_report_deps "$PIP_FLAGS"
fi

# 3b. Memory safety cap (drop-in — doesn't touch a customer-edited main unit).
# jt-glogarch usually shares the VM with Graylog + OpenSearch; this cgroup cap
# guarantees a runaway jt-glogarch is OOM-killed within its OWN cgroup instead of
# taking down OpenSearch or the whole box. Only created if absent (respects overrides).
DROPIN=/etc/systemd/system/${SERVICE}.service.d/memory.conf
if [ ! -f "$DROPIN" ]; then
    mkdir -p "$(dirname "$DROPIN")"
    cat > "$DROPIN" <<'EOF'
[Service]
# Adjust for large boxes / heavy PDF-report use; lower on very small VMs.
MemoryAccounting=yes
MemoryHigh=3G
MemoryMax=4G
EOF
    echo "  Installed memory-cap drop-in ($DROPIN): MemoryHigh=3G, MemoryMax=4G"
    systemctl daemon-reload
fi

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
