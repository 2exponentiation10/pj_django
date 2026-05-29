#!/usr/bin/env bash
set -euo pipefail

DEPLOY_ROOT="${DEPLOY_ROOT:-/opt/protfolio/satoori}"
COMPOSE_FILE="$DEPLOY_ROOT/docker-compose.yml"
CERTBOT_CONF="$DEPLOY_ROOT/certbot/conf"
CERTBOT_WWW="$DEPLOY_ROOT/certbot/www"
CERT_DOMAINS=("satoori.protfolio.store" "satoori-api.protfolio.store")
CERT_EMAIL="${CERTBOT_EMAIL:-tmdduf54@gachon.ac.kr}"
DOCKER_SUDO="${DOCKER_SUDO:-false}"
CHECK_WINDOW_SECONDS="${CHECK_WINDOW_SECONDS:-1209600}" # 14 days

run_docker() {
  if [ "$DOCKER_SUDO" = "true" ]; then
    sudo docker "$@"
  else
    docker "$@"
  fi
}

needs_renewal="false"
for domain in "${CERT_DOMAINS[@]}"; do
  cert_path="$CERTBOT_CONF/live/$domain/fullchain.pem"
  if [ ! -f "$cert_path" ]; then
    needs_renewal="true"
    break
  fi
  if ! openssl x509 -checkend "$CHECK_WINDOW_SECONDS" -noout -in "$cert_path" >/dev/null 2>&1; then
    needs_renewal="true"
    break
  fi
done

if [ "$needs_renewal" != "true" ]; then
  echo "TLS certificates are still valid beyond the renewal window. Skipping renewal."
  exit 0
fi

echo "TLS certificates need renewal. Stopping nginx for standalone challenge."
run_docker compose -f "$COMPOSE_FILE" stop nginx
trap 'run_docker compose -f "$COMPOSE_FILE" up -d nginx >/dev/null 2>&1 || true' EXIT

domain_args=()
for domain in "${CERT_DOMAINS[@]}"; do
  domain_args+=(-d "$domain")
done

run_docker run --rm -p 80:80 \
  -v "$CERTBOT_CONF:/etc/letsencrypt" \
  -v "$CERTBOT_WWW:/var/www/certbot" \
  certbot/certbot certonly --standalone \
  "${domain_args[@]}" \
  --email "$CERT_EMAIL" \
  --agree-tos \
  --no-eff-email

echo "Starting nginx after certificate renewal."
run_docker compose -f "$COMPOSE_FILE" up -d nginx
trap - EXIT
