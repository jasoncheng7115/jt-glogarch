#!/usr/bin/env bash
# Bandit — source-level Python security scan.
#
# Complements the OWASP ZAP baseline, which is a DYNAMIC scan of the running
# web surface and by construction cannot see `verify=False`, a hardcoded
# credential, or a SQL string built by concatenation. Bandit reads the source.
# It was added after a scan found 7 sites that hardcoded `verify=False` and so
# silently ignored an operator who had turned `verify_ssl` ON — several of them
# transmitting Graylog / OpenSearch credentials.
#
# Policy
#   HIGH + MEDIUM  -> must be ZERO. Fix it, or annotate the line with
#                     `# nosec <IDs> - <reason>` stating WHY it is safe.
#                     Never disable a whole rule: the next real one would then
#                     be invisible.
#   LOW            -> ratcheted (budget below, only ever goes DOWN), EXCLUDING
#                     B110/B112 (try/except/pass|continue). Those are already
#                     owned by tests/test_static_sweeps.py, which has its own
#                     budget and richer per-site classification. Two rules for
#                     one decision is how gates end up contradicting each other.
#
# Usage: bash scripts/bandit-scan.sh [path]
set -uo pipefail

TARGET="${1:-glogarch}"
cd "$(dirname "$0")/.." || exit 1

# Only ever lower this. Raising it needs a stated reason in the commit message.
LOW_BUDGET=8
SKIP_LOW="B110 B112"     # owned by tests/test_static_sweeps.py

if ! python3 -m bandit --version >/dev/null 2>&1; then
    echo "⚠ Bandit NOT INSTALLED — the source-level security gate did NOT run."
    echo "  Install it before release:  pip install bandit"
    exit 2
fi

OUT=$(mktemp); trap 'rm -f "$OUT"' EXIT
python3 -m bandit -r "$TARGET" -f json -o "$OUT" -q >/dev/null 2>&1

python3 - "$OUT" "$LOW_BUDGET" "$SKIP_LOW" <<'PY'
import json, sys, collections
path, budget, skip = sys.argv[1], int(sys.argv[2]), set(sys.argv[3].split())
try:
    results = json.load(open(path))["results"]
except Exception as e:
    print(f"❌ BANDIT: could not read results ({e})")
    sys.exit(1)

sev = collections.Counter(r["issue_severity"] for r in results)
blocking = [r for r in results if r["issue_severity"] in ("HIGH", "MEDIUM")]
low_gated = [r for r in results
             if r["issue_severity"] == "LOW" and r["test_id"] not in skip]

if blocking:
    print(f"❌ BANDIT FAILED — {len(blocking)} HIGH/MEDIUM finding(s):")
    for r in blocking:
        print(f"   {r['issue_severity']:6} {r['test_id']:6} "
              f"{r['filename']}:{r['line_number']}  {r['issue_text'][:70]}")
    print("   Fix, or annotate the line: # nosec <IDs> - <why this is safe>")
    sys.exit(1)

if len(low_gated) > budget:
    extra = collections.Counter(r["test_id"] for r in low_gated)
    print(f"❌ BANDIT LOW RATCHET EXCEEDED — {len(low_gated)} > budget {budget}")
    print(f"   by test: {dict(extra)}")
    for r in low_gated[-10:]:
        print(f"   {r['test_id']:6} {r['filename']}:{r['line_number']}  "
              f"{r['issue_text'][:70]}")
    print("   The budget only goes DOWN. Fix the new finding or justify raising it.")
    sys.exit(1)

print(f"Bandit: OK (HIGH 0, MEDIUM 0, gated LOW {len(low_gated)}/{budget}; "
      f"{sev.get('LOW', 0)} LOW total, {sev.get('LOW', 0) - len(low_gated)} "
      f"owned by the except-ratchet sweep)")
PY
