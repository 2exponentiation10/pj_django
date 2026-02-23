#!/usr/bin/env bash
set -euo pipefail

WEB_URL="${WEB_URL:-https://satoori.protfolio.store}"
API_URL="${API_URL:-https://satoori-api.protfolio.store/api}"

echo "[1/4] web health: $WEB_URL"
curl -fsS -o /dev/null -w "web_status=%{http_code}\n" "$WEB_URL"

echo "[2/4] next chapter"
curl -fsS "$API_URL/next_chapter/" | head -c 300
echo

echo "[3/4] sample sentences"
curl -fsS "$API_URL/chapters/1/sentences/" | head -c 300
echo

echo "[4/4] done"
