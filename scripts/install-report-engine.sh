#!/usr/bin/env bash
#
# Enable the jt-glogarch PDF Reports engine (beta).
#
# Reports render via a headless Chromium (same approach as Graylog Enterprise
# reporting). This installs, for the jt-glogarch service:
#   - the Playwright Python package
#   - a Chromium build into a SHARED path the service user can read
#     (/opt/jt-glogarch/.playwright — root's ~/.cache is not readable by it)
#   - Chromium's system libraries
#   - CJK fonts (so Traditional Chinese reports don't render as tofu)
#
# Run as root:  sudo bash /opt/jt-glogarch/scripts/install-report-engine.sh
#
# The hardened systemd unit (ProtectSystem=strict) keeps /tmp read-only; the
# renderer points Chromium's TMPDIR at /opt/jt-glogarch/.playwright/tmp, which
# is writable — no unit change needed.

set -e
BROWSERS_PATH=/opt/jt-glogarch/.playwright
SVC_USER=jt-glogarch

# PEP 668 (Ubuntu 24.04 / Debian 12+ ship EXTERNALLY-MANAGED): pip refuses a
# system install without --break-system-packages. jt-glogarch is a dedicated,
# single-purpose install so writing into the system Python is intended — pass
# the flag automatically when the marker is present (older distros are unaffected).
PIP_FLAGS=""
EM_FILE=$(python3 -c 'import sysconfig; print(sysconfig.get_paths()["stdlib"] + "/EXTERNALLY-MANAGED")' 2>/dev/null || true)
if [ -n "$EM_FILE" ] && [ -f "$EM_FILE" ]; then
    PIP_FLAGS="--break-system-packages"
    echo "==> Detected PEP 668 (EXTERNALLY-MANAGED) — using --break-system-packages"
fi

# The report engine needs Playwright (render) + PyMuPDF (post-process) + Pillow
# (image slicing) — the whole [report] extra, not just Playwright.
echo "==> Installing report engine packages (Playwright + PyMuPDF + Pillow)"
if ! python3 -m pip install $PIP_FLAGS --no-cache-dir "playwright>=1.40" "pymupdf>=1.24" "pillow>=10.0"; then
    echo "  (a dependency is distro-managed — retrying with --ignore-installed)"
    python3 -m pip install $PIP_FLAGS --ignore-installed --no-cache-dir "playwright>=1.40" "pymupdf>=1.24" "pillow>=10.0"
fi

echo "==> Installing Chromium into ${BROWSERS_PATH}"
mkdir -p "${BROWSERS_PATH}"
PLAYWRIGHT_BROWSERS_PATH="${BROWSERS_PATH}" python3 -m playwright install chromium

echo "==> Installing Chromium system dependencies"
PLAYWRIGHT_BROWSERS_PATH="${BROWSERS_PATH}" python3 -m playwright install-deps chromium || true

echo "==> Installing CJK fonts"
export DEBIAN_FRONTEND=noninteractive
apt-get install -y fonts-noto-cjk fonts-wqy-zenhei || \
  echo "  (could not auto-install CJK fonts — install a CJK font manually for Chinese reports)"
fc-cache -f >/dev/null 2>&1 || true

echo "==> Fixing ownership for the service user"
chown -R "${SVC_USER}:${SVC_USER}" "${BROWSERS_PATH}"

echo "==> Restarting jt-glogarch"
systemctl restart jt-glogarch || echo "  (restart jt-glogarch manually)"

# Prove it actually renders rather than asserting it does — this script exists
# precisely because "installed" and "works" are not the same thing here.
for _rd in "/opt/jt-glogarch/deploy/report-deps.sh" "$(dirname "$0")/../deploy/report-deps.sh"; do
    if [ -f "$_rd" ]; then source "$_rd"; verify_report_engine || true; break; fi
done

echo ""
echo "Done. Open the Web UI → Reports (beta). The 'render engine' notice should"
echo "be gone; create a report and click Generate."
