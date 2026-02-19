# Satoori Deployment Automation

This project is deployed to a personal Ubuntu server using Docker Compose and GitHub Actions self-hosted runner.

## Domains
- Web: `satoori.protfolio.store`
- API: `satoori-api.protfolio.store`

## Server paths
- Deploy root: `/opt/protfolio/satoori`
- Django code: `/opt/protfolio/satoori/pj_django`
- Flutter web artifacts: `/opt/protfolio/satoori/pj_flutter_web`

## 1) One-time server bootstrap

Run on server:

```bash
sudo mkdir -p /opt/protfolio/satoori/{env,nginx/conf.d,certbot/www,certbot/conf,pj_django,pj_flutter_web}
sudo chown -R $USER:$USER /opt/protfolio
touch /opt/protfolio/satoori/pj_django/db.sqlite3
```

Create env file `/opt/protfolio/satoori/env/api.env`:

```env
DJANGO_SECRET_KEY=change-this-long-random-string
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=satoori-api.protfolio.store
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://satoori.protfolio.store
```

Copy compose file and nginx config from this repository:

```bash
cp deploy/docker-compose.yml /opt/protfolio/satoori/docker-compose.yml
cp deploy/nginx/http-only.conf /opt/protfolio/satoori/nginx/conf.d/default.conf
```

## 2) Setup self-hosted runner (required for WireGuard-only environments)

Do this in **both** repositories (`pj_django`, `pj_flutter`) under GitHub:
- `Settings -> Actions -> Runners -> New self-hosted runner`
- Use Linux x64 install commands on server
- Add labels: `self-hosted`, `linux`, `satoori`

Keep runner service enabled:

```bash
sudo ./svc.sh install
sudo ./svc.sh start
```

## 3) First manual start

```bash
cd /opt/protfolio/satoori
docker compose up -d --build
docker compose run --rm api python manage.py migrate
docker compose run --rm api python manage.py collectstatic --noinput
docker compose restart api nginx
```

## 4) HTTPS certificate

```bash
docker run --rm \
  -v /opt/protfolio/satoori/certbot/www:/var/www/certbot \
  -v /opt/protfolio/satoori/certbot/conf:/etc/letsencrypt \
  certbot/certbot certonly --webroot -w /var/www/certbot \
  -d satoori.protfolio.store -d satoori-api.protfolio.store \
  --email YOUR_EMAIL --agree-tos --no-eff-email
```

Then switch nginx config:

```bash
cp deploy/nginx/https.conf /opt/protfolio/satoori/nginx/conf.d/default.conf
cd /opt/protfolio/satoori
docker compose restart nginx
```

## 5) Automated deploy triggers

- `pj_django` push to `main`/`master` -> deploy API container + migrate + collectstatic
- `pj_flutter` push to `main`/`master` -> build web + sync artifacts + restart nginx

## 6) GitHub Secrets (required)

Set in repository `Settings -> Secrets and variables -> Actions`:

- `DJANGO_SECRET_KEY`: Django secret key used in production
- `GEMINI_API_KEY`: Gemini API key for chat/pronunciation APIs

Workflows:
- `.github/workflows/deploy.yml` in each repository
