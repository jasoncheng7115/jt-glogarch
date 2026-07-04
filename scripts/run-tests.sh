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
