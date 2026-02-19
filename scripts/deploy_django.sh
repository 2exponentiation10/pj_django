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

run_docker compose -f "$COMPOSE_FILE" exec -T api python manage.py migrate
run_docker compose -f "$COMPOSE_FILE" exec -T api python manage.py collectstatic --noinput

if [ -f "$TARGET_DJANGO_DIR/fixtures/initial_data.json" ]; then
  CHAPTER_COUNT=$(
    run_docker compose -f "$COMPOSE_FILE" exec -T api \
      python manage.py shell -c "from api.models import Chapter; print(Chapter.objects.count())" \
      | tail -n 1 | tr -d '\r'
  )
  if [ "${CHAPTER_COUNT:-0}" = "0" ]; then
    if ! run_docker compose -f "$COMPOSE_FILE" exec -T api python manage.py loaddata fixtures/initial_data.json; then
      run_docker compose -f "$COMPOSE_FILE" exec -T api python manage.py shell <<'PY'
from api.models import Chapter, Sentence, Word

if Chapter.objects.count() == 0:
    ch1 = Chapter.objects.create(title="인사와 일상", accuracy=0.0)
    ch2 = Chapter.objects.create(title="식당과 음식", accuracy=0.0)

    Word.objects.bulk_create([
        Word(chapter=ch1, korean_word="안녕하세요", north_korean_word="안녕하십니까", accuracy=0.0),
        Word(chapter=ch1, korean_word="고마워요", north_korean_word="고맙습니다", accuracy=0.0),
        Word(chapter=ch2, korean_word="라면", north_korean_word="국수", accuracy=0.0),
        Word(chapter=ch2, korean_word="후라이팬", north_korean_word="프라이팬", accuracy=0.0),
    ])

    Sentence.objects.bulk_create([
        Sentence(chapter=ch1, korean_sentence="안녕하세요, 오늘 날씨가 좋네요.", north_korean_sentence="안녕하십니까, 오늘 날씨가 좋습니다.", accuracy=0.0),
        Sentence(chapter=ch1, korean_sentence="내일 또 만나요.", north_korean_sentence="내일 또 봅시다.", accuracy=0.0),
        Sentence(chapter=ch2, korean_sentence="라면을 끓여 주세요.", north_korean_sentence="국수를 끓여 주십시오.", accuracy=0.0),
        Sentence(chapter=ch2, korean_sentence="후라이팬을 달궈요.", north_korean_sentence="프라이팬을 달굽시다.", accuracy=0.0),
    ])
PY
    fi
  fi
fi

run_docker compose -f "$COMPOSE_FILE" restart api

if [ -f "$SOURCE_NGINX_CONF" ]; then
  mkdir -p "$(dirname "$TARGET_NGINX_CONF")"
  cp "$SOURCE_NGINX_CONF" "$TARGET_NGINX_CONF"
  run_docker compose -f "$COMPOSE_FILE" restart nginx
fi
