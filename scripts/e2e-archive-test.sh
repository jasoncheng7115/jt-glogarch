#!/bin/bash
# End-to-end archive round-trip test (part of the release test plan).
#
# Exercises the real pipeline against a live Graylog + OpenSearch:
#   [1] Graylog API-mode archive (export)
#   [2] OpenSearch-direct archive (export)
#   [3] GELF import of an archive back into a Graylog GELF TCP input
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

echo ""
echo "=== RESULT: $([ $FAIL -eq 0 ] && echo 'ALL PASS' || echo 'FAILURES') ==="
exit $FAIL
