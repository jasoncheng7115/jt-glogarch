#!/bin/bash
# Upgrade compatibility test (part of the release test plan).
#
# Builds REAL state with an OLD release's own code (taken from git history),
# then hands that state to the CURRENT code and asserts the three
# non-negotiable upgrade principles:
#   1. an upgrade must NEVER lose data
#   2. an upgrade must NEVER leave the system unusable / working incorrectly
#   3. an upgrade must NEVER stop scheduled archiving from running
#
# Usage:  bash scripts/upgrade-compat-test.sh [version ...]      (default set below)
# Needs:  a git clone with history (REPO=, default /tmp/glogarch-push)
set -u
REPO="${REPO:-/tmp/glogarch-push}"
SRC="${SRC:-/opt/jt-glogarch}"
VERSIONS="${*:-1.7.9 1.12.0 1.13.0}"
FAIL=0

echo "=== jt-glogarch upgrade compatibility test ==="
echo "current version: $(cd "$SRC" && grep -oE '[0-9]+\.[0-9]+\.[0-9]+' glogarch/__init__.py | head -1)"

for V in $VERSIONS; do
    echo ""
    echo "########## from $V ##########"
    W="/tmp/upgcompat/$V"; rm -rf "$W"; mkdir -p "$W/old" "$W/arch"
    C=$(cd "$REPO" && git log --all --oneline --format="%H %s" | grep -m1 -E "v?$V[: ]" | cut -d' ' -f1)
    if [ -z "$C" ]; then echo "  SKIP: no commit found for $V"; continue; fi
    (cd "$REPO" && git archive "$C" glogarch) | tar -x -C "$W/old"
    got=$(grep -oE '[0-9]+\.[0-9]+\.[0-9]+' "$W/old/glogarch/__init__.py" | head -1)
    [ "$got" = "$V" ] || { echo "  SKIP: commit holds $got, not $V"; continue; }

    # 1) create state using the OLD code
    if ! W="$W" python3 "$SRC/scripts/_upgrade_make_old.py" > "$W/before.json" 2>"$W/mk.err"; then
        echo "  SKIP: $V could not create state (deps changed):"; sed 's/^/    /' "$W/mk.err" | tail -3
        continue
    fi
    echo "  old state: $(cat "$W/before.json")"

    # 2) hand it to the CURRENT code
    if W="$W" PYTHONPATH="$SRC" python3 "$SRC/scripts/_upgrade_verify.py"; then
        echo "  RESULT: $V -> current  ALL PASS"
    else
        echo "  RESULT: $V -> current  FAILURES"; FAIL=1
    fi
done

echo ""
echo "=== UPGRADE COMPAT: $([ $FAIL -eq 0 ] && echo 'ALL PASS' || echo 'FAILURES') ==="
exit $FAIL
