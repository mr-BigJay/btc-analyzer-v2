#!/usr/bin/env bash
# BTC Analyzer v2 — نصب و آپدیت کاملاً خودکار (Ubuntu 24)
set -euo pipefail

REPO_URL="${BTC_ANALYZER_REPO:-https://github.com/mr-BigJay/btc-analyzer-v2.git}"
DEFAULT_BRANCH="${BTC_ANALYZER_BRANCH:-main}"
INSTALL_DIR="${BTC_ANALYZER_DIR:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${INSTALL_DIR:-$SCRIPT_DIR}"

SERVICE_NAME="btc-analyzer"
TELEGRAM_SERVICE_NAME="btc-analyzer-telegram"
SYSTEMD_DIR="/etc/systemd/system"
EXPECTED_BUILD="clarity-v1"

USE_DOCKER=0
SKIP_OPTIMIZE=0
NO_START=0
NO_SYSTEMD=0
FORCE_MODE=""
GIT_BRANCH="$DEFAULT_BRANCH"

log()  { echo "[btc-analyzer] $*"; }
warn() { echo "[btc-analyzer] WARNING: $*" >&2; }
die()  { echo "[btc-analyzer] ERROR: $*" >&2; exit 1; }

usage() {
    cat <<'EOF'
BTC Analyzer — نصب/آپدیت کاملاً خودکار

  ./install.sh              نصب اولیه یا آپدیت (همه‌چیز خودکار)
  ./install.sh install      نصب از صفر
  ./install.sh update       آپدیت کامل
  ./install.sh status       وضعیت سرویس

گزینه‌های اختیاری:
  --docker        استفاده از Docker به‌جای systemd
  --no-systemd    بدون نصب سرویس (فقط برای توسعه)
  --no-optimize   رد کردن بهینه‌سازی بک‌تست
  --no-start      بدون راه‌اندازی در پایان
  --branch NAME   شاخه git (پیش‌فرض: main)

روی سرور Ubuntu فقط کافی است:
  git clone https://github.com/mr-BigJay/btc-analyzer-v2.git
  cd btc-analyzer-v2
  chmod +x install.sh
  ./install.sh

اسکریپت خودکار انجام می‌دهد:
  apt packages · git pull · venv · pip · init-db · collect · analyze
  systemd نصب/ری‌استارت · توقف پروسه قدیمی · تأیید نسخه داشبورد
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            install|update|start|stop|status)
                FORCE_MODE="$1"
                shift
                ;;
            --systemd)  shift ;;  # deprecated — systemd is default on Linux
            --docker)   USE_DOCKER=1; shift ;;
            --no-systemd) NO_SYSTEMD=1; shift ;;
            --no-optimize) SKIP_OPTIMIZE=1; shift ;;
            --no-start) NO_START=1; shift ;;
            --branch)   GIT_BRANCH="${2:?--branch needs a value}"; shift 2 ;;
            -h|--help)  usage; exit 0 ;;
            *) die "آرگومان ناشناخته: $1" ;;
        esac
    done
}

run_root() {
    # Use env so VAR=value prefixes work when running as root (not only via sudo).
    if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
        env "$@"
    else
        sudo env "$@"
    fi
}

get_api_port() {
    local port=8000
    if [[ -f "$PROJECT_DIR/.env" ]] && grep -q '^API_PORT=' "$PROJECT_DIR/.env"; then
        port=$(grep '^API_PORT=' "$PROJECT_DIR/.env" | cut -d= -f2 | tr -d ' "')
    fi
    echo "$port"
}

service_user() {
    if [[ "${EUID:-$(id -u)}" -eq 0 ]] && [[ -n "${SUDO_USER:-}" ]]; then
        echo "$SUDO_USER"
    else
        id -un
    fi
}

has_systemd_unit() {
    run_root systemctl list-unit-files 2>/dev/null | grep -q "${SERVICE_NAME}.service"
}

uses_docker() {
    [[ "$USE_DOCKER" -eq 1 ]] && return 0
    [[ -f "$PROJECT_DIR/docker-compose.yml" ]] || return 1
    command -v docker >/dev/null 2>&1 || return 1
    docker compose -f "$PROJECT_DIR/docker-compose.yml" ps -q btc-analyzer 2>/dev/null | grep -q .
}

install_system_packages() {
    if ! command -v apt-get >/dev/null 2>&1; then
        warn "apt-get موجود نیست — نصب پکیج سیستمی رد شد"
        return
    fi

    log "نصب پیش‌نیازهای سیستمی..."
    run_root apt-get update -qq
    run_root DEBIAN_FRONTEND=noninteractive apt-get install -y \
        git curl ca-certificates psmisc \
        python3 python3-pip python3-venv python3.12-venv \
        build-essential 2>/dev/null || \
    run_root DEBIAN_FRONTEND=noninteractive apt-get install -y \
        git curl ca-certificates psmisc \
        python3 python3-pip python3-venv \
        build-essential
}

ensure_project_dir() {
    if [[ -f "$PROJECT_DIR/src/main.py" ]]; then
        return
    fi

    if [[ -d "$PROJECT_DIR/.git" ]]; then
        die "ریپو در $PROJECT_DIR ناقص است — src/main.py پیدا نشد"
    fi

    log "کلون ریپو از $REPO_URL (branch: $GIT_BRANCH)..."
    mkdir -p "$PROJECT_DIR"
    git clone --branch "$GIT_BRANCH" "$REPO_URL" "$PROJECT_DIR"
}

git_update() {
    cd "$PROJECT_DIR"
    if [[ ! -d .git ]]; then
        warn "پوشه git نیست — git pull رد شد"
        return
    fi

    local current_branch
    current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
    if [[ "$current_branch" != "$GIT_BRANCH" ]]; then
        log "تغییر شاخه: $current_branch → $GIT_BRANCH"
    fi

    log "دریافت آخرین کد از origin/$GIT_BRANCH ..."
    git fetch origin "$GIT_BRANCH"
    git checkout "$GIT_BRANCH"
    git reset --hard "origin/$GIT_BRANCH"
    git clean -fd -e data -e .env -e .venv
    log "کد به‌روز شد: $(git log -1 --oneline)"
}

detect_python() {
    if command -v python3.12 >/dev/null 2>&1; then
        PYTHON_BIN="python3.12"
    elif command -v python3 >/dev/null 2>&1; then
        PYTHON_BIN="python3"
    else
        die "python3 پیدا نشد — apt install python3-venv را اجرا کنید"
    fi
    log "Python: $($PYTHON_BIN --version)"
}

setup_venv() {
    detect_python
    cd "$PROJECT_DIR"

    if [[ ! -d .venv ]]; then
        log "ساخت محیط مجازی..."
        "$PYTHON_BIN" -m venv .venv
    fi

    # shellcheck disable=SC1091
    source .venv/bin/activate
    python -m pip install --upgrade pip wheel setuptools -q
    log "نصب/آپدیت پکیج‌های Python..."
    pip install -r requirements.txt -q
}

setup_env_file() {
    cd "$PROJECT_DIR"
    if [[ ! -f .env ]]; then
        cp .env.example .env
        log "فایل .env ساخته شد (توکن تلگرام اختیاری است)"
    else
        log "فایل .env حفظ شد"
    fi
    mkdir -p data
}

run_pipeline() {
    cd "$PROJECT_DIR"
    # shellcheck disable=SC1091
    source .venv/bin/activate
    export PYTHONPATH="$PROJECT_DIR"

    log "init-db..."
    python -m src.main init-db

    log "جمع‌آوری داده..."
    python -m src.main collect

    log "تحلیل..."
    python -m src.main analyze

    if [[ "$SKIP_OPTIMIZE" -eq 0 ]]; then
        log "بهینه‌سازی بک‌تست..."
        python -m src.main optimize || warn "بهینه‌سازی با خطا مواجه شد"
    fi
}

stop_port_process() {
    local port
    port="$(get_api_port)"
    if command -v fuser >/dev/null 2>&1; then
        fuser -k "${port}/tcp" 2>/dev/null || true
        sleep 1
    fi
}

stop_all() {
    log "توقف سرویس‌های در حال اجرا..."

    if has_systemd_unit; then
        run_root systemctl stop "${SERVICE_NAME}.service" 2>/dev/null || true
        run_root systemctl stop "${TELEGRAM_SERVICE_NAME}.service" 2>/dev/null || true
    fi

    if uses_docker; then
        cd "$PROJECT_DIR"
        docker compose stop btc-analyzer 2>/dev/null || true
        docker compose --profile telegram stop telegram 2>/dev/null || true
    fi

    stop_port_process

    # پروسه‌های قدیمی python مربوط به این پروژه
    pkill -f "${PROJECT_DIR}/.venv/bin/python -m src.main" 2>/dev/null || true
    sleep 1
}

write_systemd_units() {
    local user
    user="$(service_user)"

    log "نصب/آپدیت سرویس systemd (کاربر: $user)..."

  run_root tee "$SYSTEMD_DIR/${SERVICE_NAME}.service" >/dev/null <<EOF
[Unit]
Description=BTC Analyzer v2 (scheduler + dashboard)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${user}
Group=${user}
WorkingDirectory=${PROJECT_DIR}
Environment=PYTHONPATH=${PROJECT_DIR}
ExecStart=${PROJECT_DIR}/.venv/bin/python -m src.main start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

  run_root tee "$SYSTEMD_DIR/${TELEGRAM_SERVICE_NAME}.service" >/dev/null <<EOF
[Unit]
Description=BTC Analyzer Telegram Bot
After=network-online.target ${SERVICE_NAME}.service
Wants=network-online.target

[Service]
Type=simple
User=${user}
Group=${user}
WorkingDirectory=${PROJECT_DIR}
Environment=PYTHONPATH=${PROJECT_DIR}
ExecStart=${PROJECT_DIR}/.venv/bin/python -m src.main telegram
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    run_root systemctl daemon-reload
    run_root systemctl enable "${SERVICE_NAME}.service"
}

start_systemd() {
    write_systemd_units
    log "راه‌اندازی ${SERVICE_NAME}..."
    run_root systemctl restart "${SERVICE_NAME}.service"

    if grep -qE '^TELEGRAM_BOT_TOKEN=.+' "$PROJECT_DIR/.env" 2>/dev/null; then
        run_root systemctl enable "${TELEGRAM_SERVICE_NAME}.service" 2>/dev/null || true
        run_root systemctl restart "${TELEGRAM_SERVICE_NAME}.service" 2>/dev/null || true
        log "ربات تلگرام راه‌اندازی شد"
    fi
}

start_docker() {
    cd "$PROJECT_DIR"
    command -v docker >/dev/null 2>&1 || die "Docker نصب نیست"

    log "ساخت و راه‌اندازی Docker..."
    docker compose build --no-cache
    docker compose up -d --force-recreate btc-analyzer

    if grep -qE '^TELEGRAM_BOT_TOKEN=.+' .env 2>/dev/null; then
        docker compose --profile telegram up -d --force-recreate telegram
    fi
}

should_use_systemd() {
    [[ "$NO_SYSTEMD" -eq 1 ]] && return 1
    [[ "$USE_DOCKER" -eq 1 ]] && return 1
    command -v systemctl >/dev/null 2>&1 || return 1
    return 0
}

start_services() {
    [[ "$NO_START" -eq 1 ]] && return

    if uses_docker || [[ "$USE_DOCKER" -eq 1 ]]; then
        start_docker
    elif should_use_systemd; then
        start_systemd
    else
        log "راه‌اندازی مستقیم (بدون systemd)..."
        cd "$PROJECT_DIR"
        # shellcheck disable=SC1091
        source .venv/bin/activate
        export PYTHONPATH="$PROJECT_DIR"
        nohup python -m src.main start >"$PROJECT_DIR/data/install.log" 2>&1 &
        disown 2>/dev/null || true
        log "لاگ: $PROJECT_DIR/data/install.log"
    fi
}

verify_deploy() {
    local port health attempt ip
    port="$(get_api_port)"
    ip="$(hostname -I 2>/dev/null | awk '{print $1}')"

    log "تأیید نسخه داشبورد (پورت $port)..."
    for attempt in $(seq 1 20); do
        health=$(curl -sf "http://127.0.0.1:${port}/api/health" 2>/dev/null || true)
        if echo "$health" | grep -qi "$EXPECTED_BUILD"; then
            log "✓ داشبورد جدید فعال است (Clarity v1)"
            log "  http://${ip:-localhost}:${port}"
            log "  http://${ip:-localhost}:${port}/options.html"
            return 0
        fi
        if [[ -n "$health" ]]; then
            warn "سرویس پاسخ داد ولی نسخه قدیمی است — تلاش $attempt/20"
        fi
        sleep 2
    done

    if has_systemd_unit; then
        warn "لاگ سرویس:"
        run_root journalctl -u "${SERVICE_NAME}.service" -n 20 --no-pager 2>/dev/null || true
    fi
    die "داشبورد جدید بالا نیامد — health: ${health:-بدون پاسخ}"
}

print_done() {
    local port ip
    port="$(get_api_port)"
    ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
    cat <<EOF

════════════════════════════════════════════════════════
  ✓ BTC Analyzer آماده است

  داشبورد:  http://${ip:-localhost}:${port}
  آپشن:     http://${ip:-localhost}:${port}/options.html
  وضعیت:    ./install.sh status

  برای آپدیت بعدی فقط:
    ./install.sh
════════════════════════════════════════════════════════
EOF
}

detect_mode() {
    if [[ -n "$FORCE_MODE" ]]; then
        echo "$FORCE_MODE"
        return
    fi
    if [[ -d "$PROJECT_DIR/.venv" ]] || [[ -f "$PROJECT_DIR/.env" ]] || has_systemd_unit; then
        echo "update"
    else
        echo "install"
    fi
}

deploy() {
    local mode="${1:-update}"
    log "=== ${mode^^} BTC Analyzer ==="

    install_system_packages
    ensure_project_dir
    cd "$PROJECT_DIR"

    if [[ "$mode" == "update" ]]; then
        stop_all
        git_update
    elif [[ -d .git ]]; then
        git_update
    fi

    setup_venv
    setup_env_file
    run_pipeline
    start_services
    verify_deploy
    print_done

    log "=== ${mode^^} کامل شد ==="
}

status_all() {
    local port
    port="$(get_api_port)"

    if has_systemd_unit; then
        run_root systemctl status "${SERVICE_NAME}.service" --no-pager 2>/dev/null || warn "سرویس اصلی غیرفعال"
        echo ""
        run_root systemctl status "${TELEGRAM_SERVICE_NAME}.service" --no-pager 2>/dev/null || true
    fi

    if uses_docker; then
        cd "$PROJECT_DIR"
        docker compose ps
    fi

    echo ""
    curl -sf "http://127.0.0.1:${port}/api/health" 2>/dev/null && echo || warn "API روی پورت $port پاسخ نمی‌دهد"
}

main() {
    parse_args "$@"
    cd "$PROJECT_DIR" 2>/dev/null || true

    local mode
    mode="$(detect_mode)"

    case "${FORCE_MODE:-$mode}" in
        install) deploy install ;;
        update)  deploy update ;;
        start)
            stop_all
            start_services
            verify_deploy
            ;;
        stop)    stop_all ;;
        status)  status_all ;;
        *)       deploy update ;;
    esac
}

main "$@"
