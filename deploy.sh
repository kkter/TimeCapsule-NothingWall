#!/bin/sh
set -eu

if [ -f .env ]; then
    set -a
    . ./.env
    set +a
fi

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
    echo "TELEGRAM_BOT_TOKEN is required in the environment or .env" >&2
    exit 1
fi

mkdir -p data
chmod 700 data
docker compose up -d --build --remove-orphans
docker compose ps
