#!/usr/bin/env bash
# ONE command before every release. ALL PASS = ok to ship; anything else = not ready.
#
#   UI_URL=https://<staging>:8990 UI_USER=localadmin UI_PASS=... \
#   GL_HOST=<graylog-ip> GL_USER=admin GL_PASS=... \
#   [GL_SSH=root@<graylog-ip>]  [REPO=<git-clone-for-upgrade-test>] \
#   bash scripts/release-check.sh
#
# Each layer exists because its class shipped a real bug (see TESTING.md).
set -u
cd "$(dirname "$0")/.."
FAILED=()
step() {
  local id="$1" desc="$2"; shift 2
  echo; echo "=== [$id] $desc ==="
  if "$@"; then echo "--- [$id OK] ---"; else FAILED+=("$id"); echo "--- [$id FAILED] ---"; fi
}

step gate      "syntax + undefined-JS + UI smoke + bandit + pytest(+sweeps/perf) + version" ./scripts/run-tests.sh
step ui-sim    "browser simulation of the main user flows" python3 scripts/ui-sim-test.py
step ui-cancel "real click: Cancel over a running import"  python3 scripts/ui-cancel-test.py
if [ -n "${GL_HOST:-}" ] && [ -n "${GL_PASS:-}" ]; then
  step bigrange "wide-window reports against live Graylog" \
    python3 scripts/report-bigrange-test.py "http://${GL_HOST}:9000"
else
  FAILED+=("bigrange(GL_HOST/GL_PASS not set)")
fi
if [ -n "${GL_SSH:-}" ]; then
  step e2e "archive round-trip [7 steps] ON the Graylog host" \
    ssh -o StrictHostKeyChecking=no "$GL_SSH" \
      "GL_PASS='${GL_PASS:-}' bash /opt/jt-glogarch/scripts/e2e-archive-test.sh"
else
  FAILED+=("e2e(GL_SSH not set — must run ON the Graylog host)")
fi
if [ -n "${REPO:-}" ]; then
  step upgrade "upgrade compatibility (1.7.9+ -> current)" \
    env REPO="$REPO" bash scripts/upgrade-compat-test.sh
else
  echo; echo "NOTE: upgrade-compat SKIPPED (REPO not set) — MANDATORY for any schema/config-default/scheduler change."
fi

echo
if [ ${#FAILED[@]} -eq 0 ]; then
  echo "=== RELEASE CHECK: ALL PASS — ok to ship ==="
else
  echo "=== RELEASE CHECK: NOT READY — ${FAILED[*]} ==="; exit 1
fi
