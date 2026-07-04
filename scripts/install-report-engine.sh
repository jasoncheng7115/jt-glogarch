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

echo "==> Installing Playwright (Python)"
pip install --no-cache-dir "playwright>=1.40"

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

echo ""
echo "Done. Open the Web UI → Reports (beta). The 'render engine' notice should"
echo "be gone; create a report and click Generate."
