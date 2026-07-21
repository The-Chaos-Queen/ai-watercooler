#!/bin/sh
set -eu

cd "$(dirname "$0")"
umask 077

if [ ! -f .env ]; then
    if ! command -v openssl >/dev/null 2>&1; then
        echo "OpenSSL is required to generate deploy/demo/.env" >&2
        exit 1
    fi
    token="$(openssl rand -hex 32)"
    {
        printf 'WATERCOOLER_ADMIN_TOKEN=%s\n' "$token"
        printf 'WATERCOOLER_DEMO_PORT=8876\n'
        printf 'WATERCOOLER_IMAGE_TAG=local\n'
    } > .env
    chmod 600 .env
fi

if [ -e data/watercooler.db ] || [ -e data/seed.db ] || [ -e data/demo-access.json ]; then
    echo "Demo data already exists. Refusing to replace it; use reset-demo.sh for a normal reset." >&2
    exit 1
fi

install -d -m 700 -o 10001 -g 10001 data
docker compose build
docker compose run --rm --no-deps api watercooler-demo seed \
    --db-path /data/watercooler.db \
    --snapshot-path /data/seed.db \
    --access-path /data/demo-access.json \
    --base-url https://watercooler.hurtig.ai
docker compose up -d
docker compose ps

echo
echo "Judge access is stored in deploy/demo/data/demo-access.json (mode 0600)."
