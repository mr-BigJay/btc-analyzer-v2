#!/usr/bin/env bash
# Issue Let's Encrypt cert and switch Nginx to TLS for BTC Analyzer (Ubuntu 24).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

DOMAIN="${DOMAIN:-}"
EMAIL="${CERTBOT_EMAIL:-${EMAIL:-}}"

if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  set -a
  # Only pull DOMAIN/EMAIL-ish keys safely
  while IFS= read -r line; do
    case "$line" in
      DOMAIN=*|CERTBOT_EMAIL=*|EMAIL=*) export "$line" ;;
    esac
  done < <(grep -E '^(DOMAIN|CERTBOT_EMAIL|EMAIL)=' .env || true)
  set +a
fi

DOMAIN="${DOMAIN:-}"
EMAIL="${CERTBOT_EMAIL:-${EMAIL:-admin@${DOMAIN}}}"

if [[ -z "$DOMAIN" || "$DOMAIN" == "example.com" ]]; then
  echo "Usage: DOMAIN=your.domain.com CERTBOT_EMAIL=you@domain.com sudo -E bash deploy/scripts/setup-ssl.sh"
  exit 1
fi

echo "[ssl] domain=$DOMAIN email=$EMAIL"

mkdir -p deploy/certbot/www deploy/certbot/conf

# Ensure HTTP nginx is up for webroot challenges (or stop briefly for standalone)
if ! command -v certbot >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y certbot
fi

# Prefer webroot while compose nginx serves /.well-known
if docker compose ps nginx 2>/dev/null | grep -q Up; then
  echo "[ssl] using webroot via running nginx"
  # Mount paths expected by compose override — write challenge dir on host
  docker compose stop nginx || true
fi

# Standalone on :80 (simplest on fresh Ubuntu)
echo "[ssl] requesting certificate (standalone)"
certbot certonly --standalone \
  -d "$DOMAIN" -d "www.$DOMAIN" \
  --email "$EMAIL" \
  --agree-tos --non-interactive --keep-until-expiring \
  --rsa-key-size 2048

# Render SSL nginx config
sed "s/__DOMAIN__/${DOMAIN}/g" deploy/nginx-ssl.conf.template > deploy/nginx.conf
echo "[ssl] wrote deploy/nginx.conf for $DOMAIN"

# Ensure compose publishes 80/443 and mounts certs — patch via env file hint
if ! grep -q "443:443" docker-compose.yml; then
  echo "[ssl] NOTE: ensure docker-compose nginx ports include 80:80 and 443:443"
fi

docker compose up -d nginx
echo "[ssl] done — open https://${DOMAIN}/"
