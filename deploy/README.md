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

## Production gate

`GET /api/v1/deploy/checklist` must show `can_deploy_production=true` with core items passing.
