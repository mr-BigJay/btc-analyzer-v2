#!/usr/bin/env bash
# BTC Analyzer v2 — نصب و به‌روزرسانی خودکار (Ubuntu 24)
set -euo pipefail

REPO_URL="${BTC_ANALYZER_REPO:-https://github.com/mr-BigJay/btc-analyzer-v2.git}"
DEFAULT_BRANCH="${BTC_ANALYZER_BRANCH:-cursor/btc-analyzer-phase4-390e}"
INSTALL_DIR="${BTC_ANALYZER_DIR:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${INSTALL_DIR:-$SCRIPT_DIR}"

SERVICE_NAME="btc-analyzer"
TELEGRAM_SERVICE_NAME="btc-analyzer-telegram"
SYSTEMD_DIR="/etc/systemd/system"

USE_SYSTEMD=0
USE_DOCKER=0
SKIP_OPTIMIZE=0
NO_START=0
FORCE_MODE=""
GIT_BRANCH="$DEFAULT_BRANCH"

log()  { echo "[btc-analyzer] $*"; }
warn() { echo "[btc-analyzer] WARNING: $*" >&2; }
die()  { echo "[btc-analyzer] ERROR: $*" >&2; exit 1; }

usage() {
    cat <<'EOF'
استفاده:
  ./install.sh                  تشخیص خودکار نصب یا آپدیت
  ./install.sh install          نصب اولیه
  ./install.sh update           آپدیت (git pull + pip + دیتابیس)
  ./install.sh start            راه‌اندازی سرویس
  ./install.sh stop             توقف سرویس
  ./install.sh status           وضعیت

گزینه‌ها:
  --systemd       نصب سرویس systemd (اجرای خودکار بعد از بوت)
  --docker        استفاده از Docker Compose
  --no-optimize   رد کردن بهینه‌سازی بک‌تست (سریع‌تر)
  --no-start      بدون راه‌اندازی در پایان
  --branch NAME   شاخه git (پیش‌فرض: cursor/btc-analyzer-phase4-390e)

متغیرهای محیطی:
  BTC_ANALYZER_REPO    آدرس ریپو
  BTC_ANALYZER_BRANCH  شاخه پیش‌فرض
  BTC_ANALYZER_DIR     مسیر نصب (پیش‌فرض: همان پوشه اسکریپت)

مثال نصب روی سرور تازه:
  git clone https://github.com/mr-BigJay/btc-analyzer-v2.git
  cd btc-analyzer-v2
  git checkout cursor/btc-analyzer-phase4-390e
  chmod +x install.sh
  ./install.sh --systemd
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            install|update|start|stop|status)
                FORCE_MODE="$1"
                shift
                ;;
            --systemd)  USE_SYSTEMD=1; shift ;;
            --docker)   USE_DOCKER=1; shift ;;
            --no-optimize) SKIP_OPTIMIZE=1; shift ;;
            --no-start) NO_START=1; shift ;;
            --branch)   GIT_BRANCH="${2:?--branch needs a value}"; shift 2 ;;
            -h|--help)  usage; exit 0 ;;
            *) die "آرگومان ناشناخته: $1 (از --help استفاده کنید)" ;;
        esac
    done
}

need_root() {
    if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
        die "برای این مرحله sudo لازم است: sudo $0 $*"
    fi
}

detect_python() {
    if command -v python3.12 >/dev/null 2>&1; then
        PYTHON_BIN="python3.12"
    elif command -v python3 >/dev/null 2>&1; then
        PYTHON_BIN="python3"
    else
        die "python3 پیدا نشد"
    fi
    log "Python: $($PYTHON_BIN --version)"
}

install_system_packages() {
    if ! command -v apt-get >/dev/null 2>&1; then
        warn "apt-get موجود نیست — نصب پکیج سیستمی رد شد"
        return
    fi

  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
        apt-get update -qq
        DEBIAN_FRONTEND=noninteractive apt-get install -y \
            git curl ca-certificates \
            python3 python3-pip python3-venv python3.12-venv \
            build-essential 2>/dev/null || \
        DEBIAN_FRONTEND=noninteractive apt-get install -y \
            git curl ca-certificates \
            python3 python3-pip python3-venv \
            build-essential
    else
        log "نصب پیش‌نیازهای سیستمی (نیاز به sudo)..."
        sudo apt-get update -qq
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
            git curl ca-certificates \
            python3 python3-pip python3-venv python3.12-venv \
            build-essential 2>/dev/null || \
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
            git curl ca-certificates \
            python3 python3-pip python3-venv \
            build-essential
    fi
}

ensure_project_dir() {
  if [[ -f "$PROJECT_DIR/src/main.py" ]]; then
        return
    fi

    if [[ -d "$PROJECT_DIR/.git" ]]; then
        die "ریپو در $PROJECT_DIR ناقص است — src/main.py پیدا نشد"
    fi

    log "کلون ریپو به $PROJECT_DIR ..."
    mkdir -p "$(dirname "$PROJECT_DIR")"
    git clone --branch "$GIT_BRANCH" --depth 1 "$REPO_URL" "$PROJECT_DIR"
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
        log "فایل .env از .env.example ساخته شد — توکن تلگرام را ویرایش کنید"
    else
        log "فایل .env موجود است (حفظ شد)"
    fi
    mkdir -p data
}

git_update() {
    cd "$PROJECT_DIR"
    if [[ ! -d .git ]]; then
        warn "پوشه git نیست — git pull رد شد"
        return
    fi

    log "دریافت آخرین تغییرات (branch: $GIT_BRANCH)..."
    git fetch origin "$GIT_BRANCH" --depth 1 2>/dev/null || git fetch origin
    git checkout "$GIT_BRANCH" 2>/dev/null || true
    git pull origin "$GIT_BRANCH" --ff-only 2>/dev/null || git pull --ff-only
}

run_app() {
    cd "$PROJECT_DIR"
    # shellcheck disable=SC1091
    source .venv/bin/activate
    export PYTHONPATH="$PROJECT_DIR"

    log "init-db..."
    python -m src.main init-db

    log "جمع‌آوری داده (ممکن است چند دقیقه طول بکشد)..."
    python -m src.main collect

    log "تحلیل..."
    python -m src.main analyze

    if [[ "$SKIP_OPTIMIZE" -eq 0 ]]; then
        log "بهینه‌سازی بک‌تست (حدود ۱–۲ دقیقه)..."
        python -m src.main optimize || warn "بهینه‌سازی با خطا مواجه شد — ادامه می‌دهیم"
    else
        log "بهینه‌سازی رد شد (--no-optimize)"
    fi
}

service_user() {
    if [[ "${EUID:-$(id -u)}" -eq 0 ]] && [[ -n "${SUDO_USER:-}" ]]; then
        echo "$SUDO_USER"
    else
        id -un
    fi
}

write_systemd_units() {
    need_root
    local user shell
    user="$(service_user)"
    shell="$(getent passwd "$user" | cut -d: -f7)"
    [[ -z "$shell" ]] && shell="/bin/bash"

    log "نصب سرویس systemd برای کاربر $user ..."

    cat > "$SYSTEMD_DIR/${SERVICE_NAME}.service" <<EOF
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

    cat > "$SYSTEMD_DIR/${TELEGRAM_SERVICE_NAME}.service" <<EOF
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

    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}.service"
    log "سرویس ${SERVICE_NAME} فعال شد (اجرای خودکار بعد از بوت)"
}

start_systemd() {
    if systemctl is-active --quiet "${SERVICE_NAME}.service" 2>/dev/null; then
        log "ری‌استارت ${SERVICE_NAME}..."
        systemctl restart "${SERVICE_NAME}.service"
    else
        log "شروع ${SERVICE_NAME}..."
        systemctl start "${SERVICE_NAME}.service"
    fi

    if grep -qE '^TELEGRAM_BOT_TOKEN=.+$' "$PROJECT_DIR/.env" 2>/dev/null; then
        if systemctl list-unit-files | grep -q "${TELEGRAM_SERVICE_NAME}"; then
            systemctl enable "${TELEGRAM_SERVICE_NAME}.service" 2>/dev/null || true
            systemctl restart "${TELEGRAM_SERVICE_NAME}.service" 2>/dev/null || \
                systemctl start "${TELEGRAM_SERVICE_NAME}.service" 2>/dev/null || true
        fi
    fi
}

stop_systemd() {
    systemctl stop "${SERVICE_NAME}.service" 2>/dev/null || true
    systemctl stop "${TELEGRAM_SERVICE_NAME}.service" 2>/dev/null || true
    log "سرویس‌ها متوقف شدند"
}

status_systemd() {
    systemctl status "${SERVICE_NAME}.service" --no-pager 2>/dev/null || warn "سرویس ${SERVICE_NAME} نصب نشده"
    echo ""
    systemctl status "${TELEGRAM_SERVICE_NAME}.service" --no-pager 2>/dev/null || true
}

start_docker() {
    cd "$PROJECT_DIR"
    if ! command -v docker >/dev/null 2>&1; then
        die "Docker نصب نیست — ابتدا Docker را نصب کنید یا بدون --docker اجرا کنید"
    fi
    docker compose build --quiet
    docker compose up -d btc-analyzer
    if grep -qE '^TELEGRAM_BOT_TOKEN=.+$' .env 2>/dev/null; then
        docker compose --profile telegram up -d telegram
    fi
    log "Docker containers در حال اجرا هستند"
}

start_foreground_hint() {
    cd "$PROJECT_DIR"
    cat <<EOF

════════════════════════════════════════════════════════
  نصب کامل شد.

  داشبورد:  http://$(hostname -I 2>/dev/null | awk '{print $1}'):8000
  آپشن:     http://$(hostname -I 2>/dev/null | awk '{print $1}'):8000/options.html

  برای اجرای دستی:
    cd $PROJECT_DIR
    source .venv/bin/activate
    PYTHONPATH=. python -m src.main start

  برای نصب سرویس دائمی:
    sudo ./install.sh --systemd
════════════════════════════════════════════════════════
EOF
}

detect_mode() {
    if [[ -n "$FORCE_MODE" ]]; then
        echo "$FORCE_MODE"
        return
    fi
    if [[ -d "$PROJECT_DIR/.venv" ]] && [[ -f "$PROJECT_DIR/data/btc_analyzer.db" || -f "$PROJECT_DIR/.env" ]]; then
        echo "update"
    else
        echo "install"
    fi
}

do_install() {
    log "=== نصب اولیه BTC Analyzer ==="
    install_system_packages
    ensure_project_dir
    cd "$PROJECT_DIR"
    setup_venv
    setup_env_file
    run_app

    if [[ "$USE_DOCKER" -eq 1 ]]; then
        start_docker
    elif [[ "$USE_SYSTEMD" -eq 1 ]]; then
        write_systemd_units
        [[ "$NO_START" -eq 0 ]] && start_systemd
    elif [[ "$NO_START" -eq 0 ]]; then
        start_foreground_hint
    fi
}

do_update() {
    log "=== آپدیت BTC Analyzer ==="

    if systemctl is-active --quiet "${SERVICE_NAME}.service" 2>/dev/null; then
        log "توقف موقت سرویس برای آپدیت..."
        stop_systemd
        RESTART_AFTER=1
    else
        RESTART_AFTER=0
    fi

    install_system_packages
    ensure_project_dir
    git_update
    setup_venv
    setup_env_file
    run_app

    if [[ "$USE_SYSTEMD" -eq 1 ]]; then
        write_systemd_units
    fi

    if [[ "$USE_DOCKER" -eq 1 ]]; then
        start_docker
    elif [[ "${RESTART_AFTER:-0}" -eq 1 ]] || [[ "$USE_SYSTEMD" -eq 1 ]]; then
        [[ "$NO_START" -eq 0 ]] && start_systemd
    fi

    log "=== آپدیت کامل شد ==="
}

main() {
    parse_args "$@"
    cd "$PROJECT_DIR" 2>/dev/null || true

    local mode
    mode="$(detect_mode)"

    case "$mode" in
        install) do_install ;;
        update)  do_update ;;
        start)
            if [[ "$USE_DOCKER" -eq 1 ]] || docker compose ps btc-analyzer &>/dev/null; then
                start_docker
            elif systemctl list-unit-files | grep -q "${SERVICE_NAME}.service"; then
                start_systemd
            else
                cd "$PROJECT_DIR"
                # shellcheck disable=SC1091
                source .venv/bin/activate
                export PYTHONPATH="$PROJECT_DIR"
                exec python -m src.main start
            fi
            ;;
        stop)  stop_systemd ;;
        status) status_systemd ;;
        *) die "حالت نامعتبر: $mode" ;;
    esac
}

main "$@"
