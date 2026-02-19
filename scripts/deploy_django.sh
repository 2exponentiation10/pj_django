#!/usr/bin/env bash
set -euo pipefail

DEPLOY_ROOT="${DEPLOY_ROOT:-/opt/protfolio/satoori}"
PROJECT_ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
TARGET_DJANGO_DIR="$DEPLOY_ROOT/pj_django"
COMPOSE_FILE="$DEPLOY_ROOT/docker-compose.yml"
DOCKER_SUDO="${DOCKER_SUDO:-false}"

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

run_docker compose -f "$COMPOSE_FILE" restart api
