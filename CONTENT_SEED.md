# Practice Content Seed

탈북민 사투리 교정용 연습 데이터를 중복 없이 추가합니다.

## 실행
```bash
cd /Users/LSY/dev/깃헙/pj_django
python3 manage.py seed_practice_content
```

## 진행도 초기화 포함
```bash
cd /Users/LSY/dev/깃헙/pj_django
python3 manage.py seed_practice_content --reset-progress
```

## Docker 환경(서버)
```bash
cd /opt/protfolio/satoori
sudo docker compose run --rm api python manage.py seed_practice_content
```
