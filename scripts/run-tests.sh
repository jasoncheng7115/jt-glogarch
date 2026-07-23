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

# --- Headless UI smoke ------------------------------------------------------
# node --check catches JS *syntax* errors; this drives a REAL headless browser
# against a running instance to catch RUNTIME/render breakage (i18n not
# applying, Settings blank, uncaught pageerror). Needs a live URL: UI_SMOKE_URL
# env, else localhost:8990. Hard-fails if reachable and broken; loud reminder if
# no instance is reachable (can't fail the build on infra absence).
UI_URL="${UI_SMOKE_URL:-https://localhost:8990}"
UI_OUT=$(timeout 150 python3 scripts/ui-smoke.py "$UI_URL" ${UI_SMOKE_USER:+"$UI_SMOKE_USER" "$UI_SMOKE_PASS"} 2>&1)
UI_RC=$?
if echo "$UI_OUT" | grep -q "RESULT: OK"; then
    echo "UI smoke ($UI_URL): OK"
elif echo "$UI_OUT" | grep -q "RESULT: FAIL"; then
    echo "❌ UI SMOKE FAILED — refusing to release:"
    echo "$UI_OUT"
    exit 1
else
    echo "⚠ UI smoke could NOT run against $UI_URL (instance unreachable)."
    echo "  MANDATORY before release: point it at your deploy target, e.g."
    echo "    python3 scripts/ui-smoke.py https://192.0.2.36:8990"
fi

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

if [ $EXIT_CODE -eq 0 ]; then
    STATUS="✅ ALL PASSED"
else
    STATUS="❌ FAILED"
fi

# Run version check
VERSION_CHECK=$(./scripts/check-version.sh 2>&1)
VERSION_OK=$?

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
