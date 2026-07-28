#!/bin/bash
# End-to-end archive round-trip test (part of the release test plan).
#
# Exercises the real pipeline against a live Graylog + OpenSearch:
#   [1] Graylog API-mode archive (export)
#   [2] OpenSearch-direct archive (export)
#   [3] GELF import of an archive back into a Graylog GELF TCP input
#   [4] OpenSearch Bulk import (writes straight to OpenSearch — NOT covered by [3])
#   [5] Re-export dedup: already-archived time is skipped in the QUERY (guards the
#       "export stuck at 0%" bug) while a punched GAP is still re-exported exactly
#   [6] A deleted archive FILE is detected by verify and self-healed on re-export
#
# Uses throwaway configs + DBs + archive dirs under /tmp, so it never touches
# the live service's database. A GELF TCP input must be listening on GELF_PORT.
# Run as root on the target host.
#
# Required: GL_PASS (Graylog admin password).
# Optional: GL_URL (http://localhost:9000), OS_URL (http://localhost:9200),
#           GL_USER (admin), GELF_PORT (32202), SEED (300).
set -u

GL_URL="${GL_URL:-http://localhost:9000}"
OS_URL="${OS_URL:-http://localhost:9200}"
GL_USER="${GL_USER:-admin}"
GL_PASS="${GL_PASS:?set GL_PASS to the Graylog admin password}"
GELF_PORT="${GELF_PORT:-32202}"
SEED="${SEED:-300}"
W=/tmp/e2e-archive
FAIL=0

echo "=== jt-glogarch e2e archive round-trip test ==="
rm -rf "$W"; mkdir -p "$W/arch_api" "$W/arch_os"

# Graylog relative-search count over the last 24h (URL-encoded query). 24h so a
# re-import that lands 8h earlier — the naive-Taipei-vs-UTC timestamp offset, see
# CLAUDE.md "Restore / Re-import" — is still inside the window.
count() {
    curl -s -u "$GL_USER:$GL_PASS" -H "Accept: application/json" -H "X-Requested-By: cli" \
        "$GL_URL/api/search/universal/relative?query=$1&range=86400&limit=0" \
        | python3 -c 'import sys,json;print(json.load(sys.stdin).get("total_results",-1))' 2>/dev/null || echo -1
}

# Detect OpenSearch auth (none / admin).
if [ "$(curl -s -m5 -o /dev/null -w '%{http_code}' "$OS_URL/_cluster/health")" = "200" ]; then
    OS_USER=""; OS_PASS=""
else
    OS_USER="$GL_USER"; OS_PASS="$GL_PASS"
fi

mkcfg() {   # $1=name  $2=archdir  $3=export_mode
    cat > "$W/cfg_$1.yaml" <<YAML
servers:
  - {name: local, url: $GL_URL, username: $GL_USER, password: $GL_PASS, verify_ssl: false}
default_server: local
export_mode: $3
export: {base_path: $2}
opensearch: {hosts: ["$OS_URL"], username: "$OS_USER", password: "$OS_PASS", verify_ssl: false}
import: {gelf_host: localhost, gelf_port: $GELF_PORT, gelf_protocol: tcp}
database_path: $W/db_$1.db
log_level: WARNING
YAML
}
mkcfg api "$W/arch_api" api          # separate DBs so cross-mode dedup can't
mkcfg os  "$W/arch_os"  opensearch   # hide one mode's data from the other
chown -R jt-glogarch:jt-glogarch "$W"
PYA="sudo -u jt-glogarch python3 -m glogarch --config $W/cfg_api.yaml"
PYO="sudo -u jt-glogarch python3 -m glogarch --config $W/cfg_os.yaml"

# --- Seed data via GELF TCP so there is something to archive ---
python3 - "$GELF_PORT" "$SEED" <<'PYEOF'
import socket, json, sys, time
port, n = int(sys.argv[1]), int(sys.argv[2])
s = socket.create_connection(("127.0.0.1", port), timeout=10)
for i in range(n):
    s.sendall((json.dumps({"version": "1.1", "host": "e2e-test",
                           "short_message": f"e2e archive test msg {i}",
                           "level": 6, "_e2e": "1"}) + "\0").encode())
    time.sleep(0.002)
s.close(); print(f"  seeded {n} GELF messages")
PYEOF
echo "  waiting 20s for Graylog to index..."; sleep 20
seeded="$(count '%2A')"
echo "  1h message count after seed: $seeded"
[ "${seeded:-0}" -ge 1 ] 2>/dev/null || { echo "FAIL: seed not indexed"; FAIL=1; }

# Cycle the deflector so the active write index seals → becomes OS-exportable
# (OpenSearch-direct export always skips the current active write index).
echo "  cycling deflector so the seed index seals..."
curl -s -u "$GL_USER:$GL_PASS" -H "X-Requested-By: cli" -X POST \
    "$GL_URL/api/cluster/deflector/cycle" -o /dev/null -w '  cycle -> http %{http_code}\n'
echo "  waiting 15s for index ranges to recompute..."; sleep 15

echo "=== [1] Graylog API-mode archive ==="
$PYA export --mode api --days 1 --no-resume 2>&1 | tail -3
na="$(find "$W/arch_api" -name '*.json.gz' | wc -l)"
echo "  API archives produced: $na"
[ "$na" -ge 1 ] || { echo "FAIL: API export produced no archive"; FAIL=1; }

echo "=== [2] OpenSearch-direct archive ==="
$PYO export --mode opensearch --days 1 --no-resume 2>&1 | tail -3
no="$(find "$W/arch_os" -name '*.json.gz' | wc -l)"
echo "  OS archives produced: $no"
[ "$no" -ge 1 ] || { echo "FAIL: OpenSearch export produced no archive"; FAIL=1; }

echo "=== [3] GELF import back into :$GELF_PORT ==="
yest="$(date -d 'yesterday' +%Y-%m-%d)"
imp_out="$($PYA import --mode gelf --from "$yest" \
    --target-api-url "$GL_URL" --target-api-username "$GL_USER" --target-api-password "$GL_PASS" 2>&1)"
echo "$imp_out" | grep -E 'Messages sent|indexer failures|Reconciliation|Import completed|Archives:' | tail -6
# Authoritative success = the importer's own compliance reconciliation:
# messages actually sent (>0) AND zero indexer failures.
sent="$(echo "$imp_out" | grep -oE 'Messages sent: [0-9,]+' | grep -oE '[0-9,]+' | tr -d ',' | tail -1)"
if [ "${sent:-0}" -gt 0 ] 2>/dev/null && echo "$imp_out" | grep -q '0 indexer failures'; then
    echo "  PASS: imported $sent messages with 0 indexer failures (compliance OK)"
else
    echo "FAIL: import did not complete cleanly"; FAIL=1
fi
echo "  waiting 20s for re-indexing..."; sleep 20
echo "  (24h Graylog count now: $(count '%2A') — re-imported messages land 8h earlier per the Taipei/UTC offset)"

echo "=== [4] OpenSearch Bulk import ==="
# Bulk writes STRAIGHT to OpenSearch (no Graylog), so step [3] does not cover it.
# This gap is how a "json.load the whole archive" OOM risk survived in the bulk
# path long after the GELF path was converted to streaming. Verify docs land.
osc() {   # curl against OpenSearch, with auth only if the cluster needs it
    if [ -n "$OS_USER" ]; then curl -s -u "$OS_USER:$OS_PASS" "$@"; else curl -s "$@"; fi
}
BIDX="jt_e2e_bulk"
osc -X DELETE "$OS_URL/${BIDX}*" >/dev/null 2>&1
# Do NOT pre-create the index/alias. Preflight must provision the Graylog index
# set AND cycle it so Graylog creates the first write index — that is the real
# first-import path, and it was broken (every first bulk import to a new pattern
# failed with "deflector alias does not exist"). Pre-creating it here both hid
# that bug and raced with Graylog's own provisioning, which silently replaced
# the index we had just written into.
bulk_out="$($PYO import --mode bulk --from "$yest" \
    --target-index-pattern "$BIDX" \
    --target-api-url "$GL_URL" --target-api-username "$GL_USER" \
    --target-api-password "$GL_PASS" 2>&1)"
echo "$bulk_out" | grep -iE 'indexed|failed|messages sent|import completed|archives:' | tail -5
sleep 5
# Count across the WHOLE index pattern, not a hardcoded _0: bulk writes through
# the deflector alias, and preflight may cycle it onto a new index (${BIDX}_1…),
# so checking only _0 can report 0 while the data is really there.
bcount="$(osc "$OS_URL/${BIDX}*/_count" \
    | python3 -c 'import sys,json;print(json.load(sys.stdin).get("count",-1))' 2>/dev/null || echo -1)"
echo "  docs actually in OpenSearch (${BIDX}*): $bcount"
if [ "${bcount:-0}" -gt 0 ] 2>/dev/null && ! echo "$bulk_out" | grep -qiE 'Traceback|MemoryError'; then
    echo "  PASS: bulk import wrote $bcount docs to OpenSearch"
else
    echo "FAIL: bulk import wrote no docs (or crashed)"
    echo "$bulk_out" | tail -15
    FAIL=1
fi
# Clean up after ourselves. Bulk import creates a Graylog Stream + Index Set per
# target pattern, so without this every run leaves one behind for good. Use the
# product's own command (it deletes the stream first, then the index set —
# Graylog refuses to drop an index set a stream still writes to).
$PYO streams-cleanup --prefix "$BIDX" --yes 2>&1 | grep -iE 'deleted|failed' | sed 's/^/  /'
osc -X DELETE "$OS_URL/${BIDX}*" >/dev/null 2>&1   # any index the cleanup missed

echo "=== [5] Re-export dedup: skip archived time, still refill gaps ==="
# Guards the "export stuck at 0% for 14h" class of bug: de-dup must happen in the
# QUERY (so an already-archived index is skipped instantly instead of dragging
# hundreds of millions of documents across the network), while a GAP must still
# be re-exported — getting that wrong loses data silently.
W5="$W/dedup"; mkdir -p "$W5/arch"
cat > "$W5/cfg.yaml" <<YAML
servers:
  - {name: local, url: $GL_URL, username: $GL_USER, password: $GL_PASS, verify_ssl: false}
default_server: local
export_mode: opensearch
export: {base_path: $W5/arch}
opensearch: {hosts: ["$OS_URL"], username: "$OS_USER", password: "$OS_PASS", verify_ssl: false}
database_path: $W5/db.db
log_level: WARNING
YAML
chown -R jt-glogarch:jt-glogarch "$W5"
P5="sudo -u jt-glogarch python3 -m glogarch --config $W5/cfg.yaml"
$P5 export --mode opensearch --days 3 --no-resume >/dev/null 2>&1
sum5() { sudo -u jt-glogarch python3 -c "import sqlite3;c=sqlite3.connect('$W5/db.db');print(c.execute('SELECT COALESCE(SUM(message_count),0) FROM archives WHERE status=\"completed\"').fetchone()[0])"; }
base="$(sum5)"
echo "  first export archived: $base records"
if [ "${base:-0}" -le 0 ] 2>/dev/null; then
    echo "FAIL: dedup test could not archive anything to work with"; FAIL=1
else
    # (a) re-run with everything covered -> must add nothing, and be quick
    t0=$(date +%s)
    out5="$($P5 export --mode opensearch --days 3 --no-resume 2>&1)"
    el=$(( $(date +%s) - t0 ))
    again="$(sum5)"
    echo "  re-export added $(( again - base )) records in ${el}s (expect 0)"
    if [ "$again" != "$base" ]; then
        echo "FAIL: re-export duplicated data ($base -> $again)"; FAIL=1
    elif ! echo "$out5" | grep -qiE "Nothing left to export|Excluding already-archived"; then
        echo "FAIL: re-export did not use query-level dedup (would re-scan everything)"; FAIL=1
    else
        echo "  PASS: already-archived time skipped at the query level"
    fi
    # (b) punch a GAP and confirm exactly that gap is re-exported
    gap="$(sudo -u jt-glogarch python3 - <<PY
import sqlite3, os
c = sqlite3.connect("$W5/db.db")
rows = c.execute("SELECT id,message_count,file_path FROM archives "
                 "WHERE status='completed' ORDER BY time_from").fetchall()
mid = rows[len(rows)//2]
try: os.remove(mid[2])
except OSError: pass
c.execute("DELETE FROM archives WHERE id=?", (mid[0],)); c.commit()
print(mid[1])
PY
)"
    $P5 export --mode opensearch --days 3 --no-resume >/dev/null 2>&1
    filled="$(sum5)"
    echo "  gap of $gap records removed; after re-export total=$filled (expect $base)"
    if [ "$filled" = "$base" ]; then
        echo "  PASS: gap re-exported exactly, nothing duplicated"
    else
        echo "FAIL: gap not restored correctly ($base expected, got $filled)"; FAIL=1
    fi
fi

echo "=== [6] Deleted archive FILE: verify detects it, re-export self-heals ==="
# The dedup in [5] trusts the DATABASE. So if an archive FILE disappears while
# its row survives, the export must not keep skipping that time forever. verify
# marks such a row `missing`, and because dedup only counts `completed` rows the
# next export re-archives exactly that range. This is the safety net for the
# whole query-level dedup design — assert the chain end to end.
if [ "${base:-0}" -gt 0 ] 2>/dev/null; then
    victim="$(sudo -u jt-glogarch python3 - <<PY
import sqlite3
c = sqlite3.connect("$W5/db.db")
r = c.execute("SELECT file_path,message_count FROM archives "
              "WHERE status='completed' ORDER BY time_from").fetchall()
m = r[len(r) // 2]
print(f"{m[0]}|{m[1]}")
PY
)"
    vfile="${victim%|*}"; vcount="${victim#*|}"
    rm -f "$vfile"
    echo "  deleted archive file ($vcount records): $(basename "$vfile")"
    vout="$($P5 verify 2>&1)"
    echo "$vout" | grep -iE "Missing files|Valid:" | sed 's/^/    /'
    if echo "$vout" | grep -qiE "Missing files: [1-9]"; then
        echo "  PASS: verify detected the missing archive file"
    else
        echo "FAIL: verify did not detect the deleted archive file"; FAIL=1
    fi
    $P5 export --mode opensearch --days 3 --no-resume >/dev/null 2>&1
    healed="$(sum5)"
    echo "  completed records after re-export: $healed (expect $base)"
    if [ "$healed" = "$base" ]; then
        echo "  PASS: the missing range was re-archived automatically"
    else
        echo "FAIL: deleted archive was not self-healed ($base expected, got $healed)"; FAIL=1
    fi
fi

echo ""
echo "=== [7] Clear target index set, then import into it ==="
# This DELETES data on the target, so it is verified every release on a
# throwaway index set of our own — never on the real one. Three properties:
#   (a) the clear leaves exactly ONE index and it is empty (the fresh write index),
#   (b) the target can still ingest afterwards — the whole point,
#   (c) Graylog-internal event index sets are refused outright.
CIDX="jt_e2e_clear"
gql() { curl -s -u "$GL_USER:$GL_PASS" -H 'X-Requested-By: jt-glogarch' "$@"; }

# Provision the set + data by doing a real bulk import into it.
$PYO import --mode bulk --from "$yest" --target-index-pattern "$CIDX" \
    --target-api-url "$GL_URL" --target-api-username "$GL_USER" \
    --target-api-password "$GL_PASS" >/dev/null 2>&1
sleep 5
before_docs="$(osc "$OS_URL/${CIDX}*/_count" \
    | python3 -c 'import sys,json;print(json.load(sys.stdin).get("count",0))' 2>/dev/null || echo 0)"
echo "  seeded index set $CIDX with $before_docs docs"

clear_out="$(GL_URL="$GL_URL" GL_USER="$GL_USER" GL_PASS="$GL_PASS" CIDX="$CIDX" python3 - <<'PYEOF'
import asyncio, os, json
from glogarch.graylog.maintenance import GraylogIndexCleaner
c = GraylogIndexCleaner(api_url=os.environ["GL_URL"],
                        api_username=os.environ["GL_USER"],
                        api_password=os.environ["GL_PASS"])
async def main():
    sets = await c.list_index_sets()
    mine = next((s for s in sets if s["index_prefix"] == os.environ["CIDX"]), None)
    if not mine:
        print(json.dumps({"error": "test index set not listed"})); return
    # (c) internal event sets must never even be offered
    leaked = [s["index_prefix"] for s in sets if s["index_prefix"].startswith("gl-")]
    r = await c.clear_index_set(mine["id"])
    print(json.dumps({"before_count": mine["index_count"], "before_bytes": mine["size_bytes"],
                      "deleted": r["deleted_count"], "kept": r["write_index_kept"],
                      "leaked_internal": leaked}))
asyncio.run(main())
PYEOF
)"
echo "  clear -> $clear_out"
sleep 3
after_docs="$(osc "$OS_URL/${CIDX}*/_count" \
    | python3 -c 'import sys,json;print(json.load(sys.stdin).get("count",-1))' 2>/dev/null || echo -1)"
after_idx="$(osc "$OS_URL/_cat/indices/${CIDX}*?format=json" \
    | python3 -c 'import sys,json;print(len(json.load(sys.stdin)))' 2>/dev/null || echo -1)"
echo "  after clear: $after_idx index(es), $after_docs docs (expect 1 index, 0 docs)"

if echo "$clear_out" | grep -q '"leaked_internal": \[\]' \
   && [ "${before_docs:-0}" -gt 0 ] 2>/dev/null \
   && [ "$after_docs" = "0" ] && [ "$after_idx" = "1" ]; then
    echo "  PASS: clear emptied the index set and kept one fresh write index"
else
    echo "FAIL: clear did not leave exactly one empty index (or listed an internal set)"
    FAIL=1
fi

# (b) the target must still accept an import — a clear that wedges ingestion
# would be worse than not clearing at all.
$PYO import --mode bulk --from "$yest" --target-index-pattern "$CIDX" \
    --target-api-url "$GL_URL" --target-api-username "$GL_USER" \
    --target-api-password "$GL_PASS" >/dev/null 2>&1
sleep 5
reimp="$(osc "$OS_URL/${CIDX}*/_count" \
    | python3 -c 'import sys,json;print(json.load(sys.stdin).get("count",0))' 2>/dev/null || echo 0)"
echo "  re-import after clear: $reimp docs"
if [ "${reimp:-0}" -gt 0 ] 2>/dev/null; then
    echo "  PASS: import into the cleared index set works"
else
    echo "FAIL: target could not ingest after the clear"; FAIL=1
fi
$PYO streams-cleanup --prefix "$CIDX" --yes >/dev/null 2>&1
osc -X DELETE "$OS_URL/${CIDX}*" >/dev/null 2>&1

echo ""
echo "=== RESULT: $([ $FAIL -eq 0 ] && echo 'ALL PASS' || echo 'FAILURES') ==="
exit $FAIL
