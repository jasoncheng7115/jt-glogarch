#!/usr/bin/env bash
#
# OWASP ZAP DAST baseline scan for the jt-glogarch Web UI.
#
# Gate: the release requires ZERO High and ZERO Medium risk alerts. This script
# runs the ZAP baseline (passive) scan against a LIVE instance, writes HTML +
# JSON reports, then parses the JSON and FAILS the build if any alert has
# riskcode >= 2 (Medium=2, High=3).
#
# Requirements:
#   - docker (pulls ghcr.io/zaproxy/zaproxy:stable)
#   - a running jt-glogarch instance (self-signed HTTPS is fine)
#   - jq (for parsing the JSON report)
#
# Usage:
#   scripts/zap-scan.sh [TARGET_URL]
#   TARGET_URL defaults to https://localhost:8990
#
# The baseline scan covers the UNAUTHENTICATED attack surface an anonymous
# client can reach: /login, /setup, /static/*, /api/health, /api/setup/*.
# Rules tuned/justified in .zap/rules.tsv (kept next to this script's repo root).

set -euo pipefail

TARGET="${1:-https://localhost:8990}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${REPO_ROOT}/zap-report"
RULES="${REPO_ROOT}/.zap/rules.tsv"
ZAP_IMAGE="ghcr.io/zaproxy/zaproxy:stable"

command -v docker >/dev/null 2>&1 || { echo "ERROR: docker is required"; exit 3; }
command -v jq >/dev/null 2>&1 || { echo "ERROR: jq is required"; exit 3; }

mkdir -p "${OUT_DIR}"
# The ZAP container runs as uid 1000 ("zap"); make the mounted report dir
# writable by it so the HTML/JSON reports can be produced.
chmod 0777 "${OUT_DIR}"

echo "==> ZAP baseline scan target: ${TARGET}"
echo "==> Reports: ${OUT_DIR}/zap-report.{html,json}"

# -I : do not use the ZAP exit code for warnings (we gate on parsed risk instead)
# -j : use the ajax spider too (SPA-ish pages)
# -c : rule config (IGNORE/WARN/FAIL per rule, with written justifications)
# -r/-J : HTML / JSON report filenames (written into the mounted /zap/wrk)
DOCKER_ARGS=(--rm -t -v "${OUT_DIR}:/zap/wrk/:rw")
[ -f "${RULES}" ] && DOCKER_ARGS+=(-v "${RULES}:/zap/wrk/rules.tsv:ro")

set +e
docker run "${DOCKER_ARGS[@]}" "${ZAP_IMAGE}" zap-baseline.py \
    -t "${TARGET}" \
    -I -j \
    $( [ -f "${RULES}" ] && echo "-c rules.tsv" ) \
    -r zap-report.html \
    -J zap-report.json
ZAP_RC=$?
set -e
echo "==> ZAP finished (raw exit ${ZAP_RC})"

REPORT_JSON="${OUT_DIR}/zap-report.json"
if [ ! -f "${REPORT_JSON}" ]; then
    echo "ERROR: no JSON report produced at ${REPORT_JSON}"
    exit 3
fi

# Count Medium(2) + High(3) risk alerts across all sites.
HIGH=$(jq '[.site[].alerts[]? | select((.riskcode|tonumber) == 3)] | length' "${REPORT_JSON}")
MEDIUM=$(jq '[.site[].alerts[]? | select((.riskcode|tonumber) == 2)] | length' "${REPORT_JSON}")
LOW=$(jq '[.site[].alerts[]? | select((.riskcode|tonumber) == 1)] | length' "${REPORT_JSON}")

echo "==> Alerts — High: ${HIGH}  Medium: ${MEDIUM}  Low: ${LOW}"

if [ "${HIGH}" -gt 0 ] || [ "${MEDIUM}" -gt 0 ]; then
    echo ""
    echo "FAIL: found High/Medium risk alerts (gate requires 0/0):"
    jq -r '.site[].alerts[]? | select((.riskcode|tonumber) >= 2)
           | "  [\(.riskdesc)] \(.alert)  (rule \(.pluginid))"' "${REPORT_JSON}"
    echo ""
    echo "Review ${OUT_DIR}/zap-report.html. If an alert is a justified false"
    echo "positive, document it in .zap/rules.tsv (IGNORE + reason)."
    exit 1
fi

echo "PASS: 0 High, 0 Medium risk alerts."
