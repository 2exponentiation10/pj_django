#!/usr/bin/env bash
set -euo pipefail

DEPLOY_ROOT="${DEPLOY_ROOT:-/opt/protfolio/satoori}"
PROJECT_ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
TARGET_DJANGO_DIR="$DEPLOY_ROOT/pj_django"
COMPOSE_FILE="$DEPLOY_ROOT/docker-compose.yml"
DOCKER_SUDO="${DOCKER_SUDO:-false}"
TARGET_NGINX_CONF="$DEPLOY_ROOT/nginx/conf.d/default.conf"
SOURCE_NGINX_CONF="$PROJECT_ROOT/deploy/nginx/https.conf"

run_docker() {
  if [ "$DOCKER_SUDO" = "true" ]; then
    sudo docker "$@"
  else
    docker "$@"
  fi
}

mkdir -p "$TARGET_DJANGO_DIR"
rsync -az --delete \
  --exclude='.git' \
  --exclude='.github' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  "$PROJECT_ROOT/" "$TARGET_DJANGO_DIR/"

cd "$DEPLOY_ROOT"
run_docker compose -f "$COMPOSE_FILE" up -d --build api

run_docker compose -f "$COMPOSE_FILE" run --rm api python manage.py migrate
run_docker compose -f "$COMPOSE_FILE" run --rm api python manage.py collectstatic --noinput

if [ -f "$TARGET_DJANGO_DIR/fixtures/initial_data.json" ]; then
  CHAPTER_COUNT=$(
    run_docker compose -f "$COMPOSE_FILE" run --rm api \
      python manage.py shell -c "from api.models import Chapter; print(Chapter.objects.count())" \
      | tail -n 1 | tr -d '\r'
  )
  if [ "${CHAPTER_COUNT:-0}" = "0" ]; then
    run_docker compose -f "$COMPOSE_FILE" run --rm api python manage.py loaddata fixtures/initial_data.json
  fi
fi

run_docker compose -f "$COMPOSE_FILE" restart api

if [ -f "$SOURCE_NGINX_CONF" ]; then
  mkdir -p "$(dirname "$TARGET_NGINX_CONF")"
  cp "$SOURCE_NGINX_CONF" "$TARGET_NGINX_CONF"
  run_docker compose -f "$COMPOSE_FILE" restart nginx
fi
