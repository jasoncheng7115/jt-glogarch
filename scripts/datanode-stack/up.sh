#!/usr/bin/env bash
# Bring up Graylog + Data Node + MongoDB for the Data Node e2e test and finish
# Graylog's first-start ("preflight") setup without a browser: create the CA,
# let Graylog provision the Data Node, finish. Prints the env the e2e needs.
#   GL_VERSION=7.2.2 bash scripts/datanode-stack/up.sh   (tested: 7.2.2, 7.1.11, 6.3.x)
set -euo pipefail
cd "$(dirname "$0")"
export GL_VERSION="${GL_VERSION:-7.2.2}"
# Graylog 6.x wants MongoDB 6 (measured with 6.3.15); 7.x runs on 7.
case "$GL_VERSION" in 6.*) MONGO_IMAGE="${MONGO_IMAGE:-mongo:6.0}" ;; *) MONGO_IMAGE="${MONGO_IMAGE:-mongo:7.0}" ;; esac
sed -i "s|graylog/graylog-datanode:[0-9.]*|graylog/graylog-datanode:${GL_VERSION}|; s|graylog/graylog:[0-9.]*|graylog/graylog:${GL_VERSION}|; s|image: mongo:[0-9.]*|image: ${MONGO_IMAGE}|" docker-compose.yml
if [ ! -f .env ]; then
  ADMIN_PW="${GL_PASS:-$(openssl rand -hex 12)}"
  umask 077
  {
    echo "GRAYLOG_PASSWORD_SECRET=$(openssl rand -hex 48)"
    echo "GRAYLOG_ROOT_PASSWORD_SHA2=$(printf '%s' "$ADMIN_PW" | sha256sum | cut -d' ' -f1)"
    echo "# admin password: $ADMIN_PW"
  } > .env
fi
ADMIN_PW=$(sed -n 's/^# admin password: //p' .env)
docker compose up -d
B=http://127.0.0.1:19000
echo "waiting for Graylog's first-start setup..."
for _ in $(seq 1 90); do
  P=$(docker logs dn-graylog 2>&1 | grep -o "password '[^']*'" | tail -1 | cut -d"'" -f2 || true)
  [ -n "$P" ] && break
  if curl -s -o /dev/null -w '%{http_code}' -u "admin:$ADMIN_PW" $B/api/system | grep -q 200; then P=""; break; fi
  sleep 3
done
if [ -n "${P:-}" ]; then
  H=(-H 'X-Requested-By: jt' -H 'Content-Type: application/json' -u "admin:$P")
  curl -s "${H[@]}" -X POST $B/api/ca/create -d '{"organization":"jt-e2e"}' -o /dev/null
  curl -s "${H[@]}" -X POST $B/api/renewal_policy -d '{"mode":"AUTOMATIC","certificate_lifetime":"P30D"}' -o /dev/null
  curl -s "${H[@]}" -X POST $B/api/generate -o /dev/null
  for _ in $(seq 1 60); do
    curl -s "${H[@]}" $B/api/data_nodes | grep -q CONNECTED && break; sleep 5
  done
  curl -s "${H[@]}" -X POST $B/api/status/finish-config -o /dev/null
fi
for _ in $(seq 1 60); do
  curl -s -o /dev/null -w '%{http_code}' -u "admin:$ADMIN_PW" $B/api/system | grep -q 200 && break; sleep 5
done
echo "Graylog up:  GL_URL=$B GL_USER=admin GL_PASS=$ADMIN_PW DN_OS_URL=https://127.0.0.1:19200 GELF_PORT=32212"
