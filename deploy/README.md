# Deployment runbook (Chapter 20)

## Topology

Nginx (edge) → FastAPI (`api`, scalable) → Redis / PostgreSQL  
Background: `scheduler` (single active preferred), `collectors` (loop), optional `ai` profile.

Service discovery uses Compose DNS names: `postgres`, `redis`, `api`, `scheduler`.

## Environments

| Env | `APP_ENV` |
|-----|-----------|
| Development | `development` |
| Testing | `testing` |
| Staging | `staging` |
| Production | `production` |

Credentials are never baked into images — pass via Compose/`env` files.

## Probes

| Path | Meaning |
|------|---------|
| `/live` | Process up |
| `/ready` | DB (required) + Redis if configured |
| `/health` | Combined readiness detail |

## Release strategies

### Rolling update

```bash
docker compose up -d --build --no-deps api
# verify /ready then continue other services
```

### Blue-Green

1. Bring up green stack (`COMPOSE_PROJECT_NAME=btc-green`).
2. Validate `/ready`, checklist, smoke tests.
3. Point nginx upstream (or edge LB) from blue → green.
4. Keep blue warm for automated rollback.

### Rollback triggers

Health check failure · elevated errors · latency regression · migration issues · critical security.

```bash
# Compose: redeploy previous image tag
docker compose pull api && docker compose up -d api
```

## Backup / DR

- RTO ≤ 30 min · RPO ≤ 5 min
- `make backup` → `deploy/scripts/backup.sh`
- Periodic restore drills required before production cutover

## Persian UI + Domain / TLS

Static RTL portal is served by Nginx from `frontend/`:

| Path | Page |
|------|------|
| `/` | خانه |
| `/dashboard.html` | داشبورد |
| `/guide.html` | نحوه استفاده |
| `/setup.html` | راه‌اندازی Ubuntu |
| `/ssl.html` | دامنه و SSL |
| `/status.html` | وضعیت سیستم |

```bash
# HTTP first
docker compose up -d --build

# Then TLS (Ubuntu host)
export DOMAIN=example.com
export CERTBOT_EMAIL=admin@example.com
sudo -E bash deploy/scripts/setup-ssl.sh
```

TLS terminates at Nginx. Certificates live in `/etc/letsencrypt` on the host and are mounted read-only into the nginx container.
