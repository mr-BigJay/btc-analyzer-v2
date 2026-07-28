#!/usr/bin/env bash
# Chapter 20 §20.18 — scheduled backup helper (database + config snapshots).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${BACKUP_DIR:-$ROOT/deploy/backups}/$STAMP"
mkdir -p "$OUT_DIR"

echo "[backup] writing to $OUT_DIR"

# PostgreSQL logical dump when DATABASE_URL points at postgres
if [[ "${DATABASE_URL:-}" == postgresql* ]] || [[ "${DATABASE_URL:-}" == postgres* ]]; then
  if command -v pg_dump >/dev/null 2>&1; then
    pg_dump "$DATABASE_URL" --no-owner --format=custom -f "$OUT_DIR/postgres.dump"
    echo "[backup] postgres dump ok"
  else
    echo "[backup] pg_dump not installed — skipping DB dump" >&2
  fi
elif [[ -f "${ROOT}/data/btc_analyzer.db" ]]; then
  cp -a "${ROOT}/data/btc_analyzer.db" "$OUT_DIR/btc_analyzer.db"
  echo "[backup] sqlite copy ok"
fi

# Configuration / feature-store / reports snapshots (non-secret templates only)
mkdir -p "$OUT_DIR/config" "$OUT_DIR/reports"
if [[ -f "$ROOT/.env.example" ]]; then
  cp -a "$ROOT/.env.example" "$OUT_DIR/config/"
fi
cp -a "$ROOT/docker-compose.yml" "$OUT_DIR/config/" 2>/dev/null || true
cp -a "$ROOT/deploy/nginx.conf" "$OUT_DIR/config/" 2>/dev/null || true
if [[ -d "$ROOT/data/reports" ]]; then
  cp -a "$ROOT/data/reports/." "$OUT_DIR/reports/" 2>/dev/null || true
fi

# Integrity fingerprint
(
  cd "$OUT_DIR"
  find . -type f | sort | while read -r f; do
    sha256sum "$f"
  done
) >"$OUT_DIR/SHA256SUMS"

echo "[backup] complete — verify with: sha256sum -c $OUT_DIR/SHA256SUMS"
