# 시나브로 (Onsaemiro) - Django API

Flutter 클라이언트를 위한 학습/평가/복습 API 서버입니다.

## 주요 책임

- 챕터/단어/문장 CRUD 및 진행도 집계
- 발음 평가 API(`pronunciation/evaluate`)
- AI 대화 API(`chat`)
- 미디어 자산(이미지) 관리
- 복습 추천 큐 제공

## 기술 스택

- Django + DRF
- SQLite(로컬) / PostgreSQL(운영 가능)
- Docker Compose
- Nginx Reverse Proxy(운영 환경)

## 실행

```bash
cd /Users/LSY/dev/깃헙/pj_django
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## 핵심 엔드포인트

- `GET /api/next_chapter/`
- `GET /api/get_progress/`
- `GET /api/review_queue/?limit=20`
- `POST /api/pronunciation/evaluate/`
- `POST /api/chat/`
- `GET/POST/PATCH/DELETE /api/chapters/`
- `GET/POST/PATCH/DELETE /api/words/`
- `GET/POST/PATCH/DELETE /api/sentences/`
- `GET/POST/PATCH/DELETE /api/media-assets/`

## 배포 자동화

- GitHub Actions + Self-hosted Runner
- 워크플로우: `/Users/LSY/dev/깃헙/pj_django/.github/workflows/deploy.yml`
- smoke check: `/Users/LSY/dev/깃헙/pj_django/scripts/smoke_check.sh`

## 포트폴리오 연결

프론트엔드/제품 설명은 `/Users/LSY/dev/깃헙/pj_flutter/README.md`와  
`/Users/LSY/dev/깃헙/pj_flutter/docs/PORTFOLIO_CASE_STUDY_KR.md`를 참고하세요.
