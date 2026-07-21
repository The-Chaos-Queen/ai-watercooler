#!/bin/sh
set -eu

cd "$(dirname "$0")"

if [ ! -f data/seed.db ]; then
    echo "Missing data/seed.db; run initialize.sh first." >&2
    exit 1
fi

docker compose stop api
docker compose run --rm --no-deps api watercooler-demo restore \
    --db-path /data/watercooler.db \
    --snapshot-path /data/seed.db
docker compose up -d api web
docker compose ps
