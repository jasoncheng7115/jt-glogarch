#!/bin/bash
# Run full test suite and write results to github/TEST-RESULTS.md
# This script must be run before every GitHub push.

set -e
cd "$(dirname "$0")/.."

RESULT_FILE="github/TEST-RESULTS.md"
VERSION=$(python3 -c 'import glogarch; print(glogarch.__version__)')
TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M:%S UTC')
PLATFORM=$(python3 --version 2>&1)
OS=$(uname -srm)

echo "Running tests for v${VERSION}..."

# --- JS syntax gate ---------------------------------------------------------
# The Python suite never loads the browser JS, so a syntax error there (e.g. an
# apostrophe inside a single-quoted i18n string) shipped undetected and broke the
# whole UI (fell back to English, settings page failed to render). Hard-fail the
# release if any static JS file doesn't parse. Requires node.
JS_ERR=""
if command -v node >/dev/null 2>&1; then
    for jsf in glogarch/web/static/js/*.js; do
        if ! node --check "$jsf" 2>/tmp/jscheck.err; then
            JS_ERR="${JS_ERR}\n$jsf:\n$(cat /tmp/jscheck.err)"
        fi
    done
    if [ -n "$JS_ERR" ]; then
        echo "❌ JS SYNTAX ERROR — refusing to release:"
        printf "%b\n" "$JS_ERR"
        exit 1
    fi
    echo "JS syntax check: OK ($(ls glogarch/web/static/js/*.js | wc -l) files)"
else
    echo "⚠ node not found — SKIPPING JS syntax check (install node to gate JS)."
fi

# --- JS undefined-identifier check ---------------------------------------
# `node --check` validates SYNTAX only. `customConfirm(...)` was valid syntax and
# defined nowhere, so Cancel in the import dialog threw ReferenceError on its
# first line and silently did nothing (v1.13.70). This catches that class.
if command -v node >/dev/null 2>&1; then
    if ! node scripts/js-undefined-check.js glogarch/web/static/js; then
        echo "❌ JS UNDEFINED-CALL CHECK FAILED — refusing to release."
        exit 1
    fi
fi

# --- Bandit: source-level Python security ---------------------------------
# ZAP is a DYNAMIC scan of the running web surface and structurally cannot see
# `verify=False`, a hardcoded credential, or a concatenated SQL string. Bandit
# reads the source. Policy and the LOW ratchet live in the script itself.
# Exit 2 = not installed: report loudly, never pass silently (a security gate
# that quietly does not run is worse than none).
# `|| RC=$?`: under `set -e` a bare `X=$(failing)` exits the script right here,
# silently, before the failure is printed (it hid a Bandit finding in 1.17.0).
BANDIT_RC=0
BANDIT_OUT=$(bash scripts/bandit-scan.sh 2>&1) || BANDIT_RC=$?
echo "$BANDIT_OUT"
if [ $BANDIT_RC -eq 1 ]; then
    echo "❌ BANDIT GATE FAILED — refusing to release."
    exit 1
fi

# --- Headless UI smoke ------------------------------------------------------
# node --check catches JS *syntax* errors; this drives a REAL headless browser
# against a running instance to catch RUNTIME/render breakage (i18n not
# applying, Settings blank, uncaught pageerror). Needs a live URL: UI_SMOKE_URL
# env, else localhost:8990. Hard-fails if reachable and broken; loud reminder if
# no instance is reachable (can't fail the build on infra absence).
UI_URL="${UI_SMOKE_URL:-https://localhost:8990}"
UI_RC=0
UI_OUT=$(timeout 150 python3 scripts/ui-smoke.py "$UI_URL" ${UI_SMOKE_USER:+"$UI_SMOKE_USER" "$UI_SMOKE_PASS"} 2>&1) || UI_RC=$?
if echo "$UI_OUT" | grep -q "RESULT: OK"; then
    echo "UI smoke ($UI_URL): OK"
    # A skipped layer must never read as a passed one.
    echo "$UI_OUT" | grep "⚠" || true
elif echo "$UI_OUT" | grep -q "RESULT: FAIL"; then
    echo "❌ UI SMOKE FAILED — refusing to release:"
    echo "$UI_OUT"
    exit 1
else
    echo "⚠ UI smoke could NOT run against $UI_URL (instance unreachable)."
    echo "  MANDATORY before release: point it at your deploy target, e.g."
    echo "    python3 scripts/ui-smoke.py https://192.0.2.36:8990"
fi

# --- SBOM (every release, owner 2026-11-16) ---------------------------------
# github/sbom.cdx.json = CycloneDX 1.5 of the versions this release was built and
# tested with: read from the INSTALLED distributions, so pip must have installed
# this very version first (--force-reinstall). A stale install would describe
# the previous release, so a version mismatch stops the release here.
SBOM_FILE="github/sbom.cdx.json"
SBOM_RC=0
# Run from /tmp WITHOUT the source tree on sys.path: the INSTALLED code describes
# the installed packages (the checkout's stale *.egg-info must not answer).
SBOM_OUT=$(cd /tmp && python3 -m glogarch.sbom -o "$OLDPWD/$SBOM_FILE.new" 2>&1) || SBOM_RC=$?
if [ $SBOM_RC -ne 0 ]; then
    echo "❌ SBOM GENERATION FAILED — refusing to release:"; echo "$SBOM_OUT"; rm -f "$SBOM_FILE.new"; exit 1
fi
SBOM_VER=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["metadata"]["component"]["version"])' "$SBOM_FILE.new")
if [ "$SBOM_VER" != "$VERSION" ]; then
    echo "❌ SBOM describes installed jt-glogarch $SBOM_VER, source is $VERSION — refusing to release."
    echo "   Install this version first: pip install --no-build-isolation --no-cache-dir --force-reinstall --no-deps ."
    rm -f "$SBOM_FILE.new"; exit 1
fi
mv "$SBOM_FILE.new" "$SBOM_FILE"
SBOM_SUMMARY="✅ $(python3 -c 'import json,sys;print(len(json.load(open(sys.argv[1]))["components"]))' "$SBOM_FILE") components (CycloneDX 1.5, ${SBOM_FILE#github/})"
echo "SBOM: $SBOM_SUMMARY"

# Run pytest and capture output (NO_COLOR disables ANSI escape codes).
# IMPORTANT: pytest's exit code is captured BEFORE the ANSI strip pipe.
# Previous "pytest | sed" form put $? on sed (always 0) so failures were
# silently masked as "ALL PASSED".
set +e
TEST_OUTPUT_RAW=$(NO_COLOR=1 TERM=dumb python3 -m pytest tests/ -v --tb=short --no-header -p no:cacheprovider 2>&1)
EXIT_CODE=$?
set -e
TEST_OUTPUT=$(printf '%s' "$TEST_OUTPUT_RAW" | sed 's/\x1b\[[0-9;]*m//g')

# Extract summary line
SUMMARY=$(echo "$TEST_OUTPUT" | grep -E "^=+ .+ =+$" | tail -1)

# Count pass/fail/skip
PASSED=$(echo "$SUMMARY" | grep -oP '\d+ passed' || echo "0 passed")
FAILED=$(echo "$SUMMARY" | grep -oP '\d+ failed' || echo "")
SKIPPED=$(echo "$SUMMARY" | grep -oP '\d+ skipped' || echo "")
DURATION=$(echo "$SUMMARY" | grep -oP 'in [\d.]+s' || echo "")

# Run version check. A hardcoded version is a release blocker, so it fails the
# run like a failing test (it used to be written to TEST-RESULTS.md as FAIL while
# the run still said ALL PASSED and exited 0).
VERSION_OK=0
VERSION_CHECK=$(./scripts/check-version.sh 2>&1) || VERSION_OK=$?
if [ $VERSION_OK -ne 0 ] && [ $EXIT_CODE -eq 0 ]; then
    EXIT_CODE=1
    echo ""
    echo "Version check FAILED:"
    echo "$VERSION_CHECK" | head -20
fi

if [ $EXIT_CODE -eq 0 ]; then
    STATUS="✅ ALL PASSED"
else
    STATUS="❌ FAILED"
fi

# Write results
cat > "$RESULT_FILE" << EOF
# Test Results

| Item | Value |
|---|---|
| **Status** | ${STATUS} |
| **Version** | v${VERSION} |
| **Date** | ${TIMESTAMP} |
| **Platform** | ${PLATFORM} / ${OS} |
| **Results** | ${PASSED} ${FAILED:+/ $FAILED} ${SKIPPED:+/ $SKIPPED} ${DURATION} |
| **Version Check** | $([ $VERSION_OK -eq 0 ] && echo "✅ OK" || echo "❌ FAIL") |
| **Bandit (source security)** | $(echo "$BANDIT_OUT" | tail -1) |
| **SBOM** | ${SBOM_SUMMARY} |

## Test Output

\`\`\`
${TEST_OUTPUT}
\`\`\`

## Version Check

\`\`\`
${VERSION_CHECK}
\`\`\`
EOF

echo ""
echo "${STATUS}: ${PASSED} ${FAILED:+/ $FAILED} ${SKIPPED:+/ $SKIPPED} ${DURATION}"
echo "Results written to ${RESULT_FILE}"

exit $EXIT_CODE
