#!/usr/bin/env bash
# BTC Analyzer v2 — auto install/update (Ubuntu 24)
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
NON_INTERACTIVE=0
FORCE_MODE=""
GIT_BRANCH="$DEFAULT_BRANCH"

log()  { echo "[btc-analyzer] $*"; }
warn() { echo "[btc-analyzer] WARNING: $*" >&2; }
die()  { echo "[btc-analyzer] ERROR: $*" >&2; exit 1; }

read_tty() {
    local prompt="$1" default="${2:-}"
    local reply=""
    if [[ "$NON_INTERACTIVE" -eq 1 ]]; then
        echo "$default"
        return
    fi
    if [[ -e /dev/tty ]]; then
        if [[ -n "$default" ]]; then
            read -r -p "$prompt [$default]: " reply </dev/tty || true
            reply="${reply:-$default}"
        else
            read -r -p "$prompt " reply </dev/tty || true
        fi
    fi
    echo "$reply"
}

ask_yes_no() {
    local prompt="$1" default="${2:-y}"
    local reply
    reply="$(read_tty "$prompt" "$default")"
    reply="${reply:-$default}"
    [[ "$reply" =~ ^[Yy] ]]
}

usage() {
    cat <<'EOF'
BTC Analyzer — auto install/update

  ./install.sh              install ya update (pishfarz)
  ./install.sh install      nasb az sefr
  ./install.sh update       update kamel
  ./install.sh status       vaziat service

Optional flags:
  --docker        estefade az Docker be jaye systemd
  --no-systemd    bedoon service (faghat dev)
  --no-optimize   rad kardan backtest optimize
  --no-start      bedoon rah-andazi dar payan
  --yes           bedoon soal (non-interactive)
  --branch NAME   git branch (pishfarz: main)

Ubuntu server:
  curl -fsSL https://raw.githubusercontent.com/mr-BigJay/btc-analyzer-v2/main/bootstrap.sh | bash
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            install|update|start|stop|status)
                FORCE_MODE="$1"
                shift
                ;;
            --systemd)  shift ;;
            --docker)   USE_DOCKER=1; shift ;;
            --no-systemd) NO_SYSTEMD=1; shift ;;
            --no-optimize) SKIP_OPTIMIZE=1; shift ;;
            --no-start) NO_START=1; shift ;;
            --yes|-y)   NON_INTERACTIVE=1; shift ;;
            --branch)   GIT_BRANCH="${2:?--branch needs a value}"; shift 2 ;;
            -h|--help)  usage; exit 0 ;;
            *) die "argument nashnakhte: $1" ;;
        esac
    done
}

run_root() {
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

set_env_var() {
    local key="$1" val="$2" file="$PROJECT_DIR/.env"
    python3 - "$key" "$val" "$file" <<'PY'
import sys

key, val, path = sys.argv[1:4]
lines = []
found = False
try:
    with open(path, encoding="utf-8") as handle:
        lines = handle.readlines()
except FileNotFoundError:
    pass

out = []
for line in lines:
    if line.startswith(f"{key}="):
        out.append(f"{key}={val}\n")
        found = True
    else:
        out.append(line)
if not found:
    out.append(f"{key}={val}\n")
with open(path, "w", encoding="utf-8") as handle:
    handle.writelines(out)
PY
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

interactive_preflight() {
    local mode="$1"

    if [[ "$NON_INTERACTIVE" -eq 1 ]]; then
        return
    fi

    if [[ "$mode" == "update" ]]; then
        if ! ask_yes_no "Nasb ghabli peida shod. Update va restart konim?" "y"; then
            die "install laghv shod"
        fi
    fi

    if [[ "$SKIP_OPTIMIZE" -eq 0 ]]; then
        if ! ask_yes_no "Backtest optimize ejra beshe? (chand daghighe tool mikeshe)" "y"; then
            SKIP_OPTIMIZE=1
            log "backtest optimize skip shod"
        fi
    fi

    if [[ "$USE_DOCKER" -eq 0 ]] && [[ "$NO_SYSTEMD" -eq 0 ]] && command -v systemctl >/dev/null 2>&1; then
        if ask_yes_no "Ba systemd service nasb beshe? (pishnahad shode)" "y"; then
            NO_SYSTEMD=0
        else
            NO_SYSTEMD=1
            log "systemd skip shod - ejraye mostaghim"
        fi
    fi
}

interactive_telegram() {
    local token chat_id

    if [[ "$NON_INTERACTIVE" -eq 1 ]]; then
        return
    fi

    if grep -qE '^TELEGRAM_BOT_TOKEN=.+' "$PROJECT_DIR/.env" 2>/dev/null; then
        if ! ask_yes_no "Telegram ghablan tanzim shode. dobare tanzim konim?" "n"; then
            return
        fi
    fi

    if ! ask_yes_no "Mikhahid Telegram bot tanzim konid? (ekhtiari)" "n"; then
        return
    fi

    token="$(read_tty "TELEGRAM_BOT_TOKEN (az @BotFather):" "")"
    if [[ -z "$token" ]]; then
        warn "token khali bud - telegram skip shod"
        return
    fi

    chat_id="$(read_tty "TELEGRAM_CHAT_ID:" "")"
    if [[ -z "$chat_id" ]]; then
        warn "chat id khali bud - telegram skip shod"
        return
    fi

    set_env_var "TELEGRAM_BOT_TOKEN" "$token"
    set_env_var "TELEGRAM_CHAT_ID" "$chat_id"
    log "telegram dar .env zakhire shod"
}

install_system_packages() {
    if ! command -v apt-get >/dev/null 2>&1; then
        warn "apt-get vojud nadarad - nasb package systemi skip shod"
        return
    fi

    log "nasb pish-niaz haye systemi..."
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
        die "repo dar $PROJECT_DIR naqes ast - src/main.py peida nashod"
    fi

    log "clone repo az $REPO_URL (branch: $GIT_BRANCH)..."
    mkdir -p "$PROJECT_DIR"
    git clone --branch "$GIT_BRANCH" "$REPO_URL" "$PROJECT_DIR"
}

git_update() {
    cd "$PROJECT_DIR"
    if [[ ! -d .git ]]; then
        warn "pooshe git nist - git pull skip shod"
        return
    fi

    local current_branch
    current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
    if [[ "$current_branch" != "$GIT_BRANCH" ]]; then
        log "taghir branch: $current_branch -> $GIT_BRANCH"
    fi

    log "daryaft akharin code az origin/$GIT_BRANCH ..."
    git fetch origin "$GIT_BRANCH"
    git checkout "$GIT_BRANCH"
    git reset --hard "origin/$GIT_BRANCH"
    git clean -fd -e data -e .env -e .venv
    log "code be-rooz shod: $(git log -1 --oneline)"
}

detect_python() {
    if command -v python3.12 >/dev/null 2>&1; then
        PYTHON_BIN="python3.12"
    elif command -v python3 >/dev/null 2>&1; then
        PYTHON_BIN="python3"
    else
        die "python3 peida nashod - apt install python3-venv ro ejra konid"
    fi
    log "Python: $($PYTHON_BIN --version)"
}

setup_venv() {
    detect_python
    cd "$PROJECT_DIR"

    if [[ ! -d .venv ]]; then
        log "sakht mohit majazi (venv)..."
        "$PYTHON_BIN" -m venv .venv
    fi

    # shellcheck disable=SC1091
    source .venv/bin/activate
    python -m pip install --upgrade pip wheel setuptools -q
    log "nasb/update package haye Python..."
    pip install -r requirements.txt -q
}

setup_env_file() {
    cd "$PROJECT_DIR"
    if [[ ! -f .env ]]; then
        cp .env.example .env
        log "file .env sakhte shod (telegram ekhtiari ast)"
    else
        log "file .env negah dashte shod"
    fi
    mkdir -p data
    interactive_telegram
}

run_pipeline() {
    cd "$PROJECT_DIR"
    # shellcheck disable=SC1091
    source .venv/bin/activate
    export PYTHONPATH="$PROJECT_DIR"

    log "init-db..."
    python -m src.main init-db

    log "jam-avari dade (collect)..."
    python -m src.main collect

    log "tahlel (analyze)..."
    python -m src.main analyze

    if [[ "$SKIP_OPTIMIZE" -eq 0 ]]; then
        log "behbood backtest (optimize)..."
        python -m src.main optimize || warn "optimize ba khata movajeh shod - edame midim"
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
    log "toghif service haye dar hal ejra..."

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
    pkill -f "${PROJECT_DIR}/.venv/bin/python -m src.main" 2>/dev/null || true
    sleep 1
}

write_systemd_units() {
    local user
    user="$(service_user)"

    log "nasb/update service systemd (user: $user)..."

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
    log "rah-andazi ${SERVICE_NAME}..."
    run_root systemctl restart "${SERVICE_NAME}.service"

    if grep -qE '^TELEGRAM_BOT_TOKEN=.+' "$PROJECT_DIR/.env" 2>/dev/null; then
        run_root systemctl enable "${TELEGRAM_SERVICE_NAME}.service" 2>/dev/null || true
        run_root systemctl restart "${TELEGRAM_SERVICE_NAME}.service" 2>/dev/null || true
        log "robot telegram rah-andazi shod"
    fi
}

start_docker() {
    cd "$PROJECT_DIR"
    command -v docker >/dev/null 2>&1 || die "Docker nasb nist"

    log "sakht va rah-andazi Docker..."
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
        log "rah-andazi mostaghim (bedoon systemd)..."
        cd "$PROJECT_DIR"
        # shellcheck disable=SC1091
        source .venv/bin/activate
        export PYTHONPATH="$PROJECT_DIR"
        nohup python -m src.main start >"$PROJECT_DIR/data/install.log" 2>&1 &
        disown 2>/dev/null || true
        log "log: $PROJECT_DIR/data/install.log"
    fi
}

verify_deploy() {
    local port health attempt ip
    port="$(get_api_port)"
    ip="$(hostname -I 2>/dev/null | awk '{print $1}')"

    log "taeed dashboard (port $port)..."
    for attempt in $(seq 1 20); do
        health=$(curl -sf "http://127.0.0.1:${port}/api/health" 2>/dev/null || true)
        if echo "$health" | grep -qi "$EXPECTED_BUILD"; then
            log "OK - dashboard faal ast (Clarity v1)"
            log "  http://${ip:-localhost}:${port}"
            log "  http://${ip:-localhost}:${port}/options.html"
            return 0
        fi
        if [[ -n "$health" ]]; then
            warn "service pasokh dad vali noskhe ghadimi - talash $attempt/20"
        fi
        sleep 2
    done

    if has_systemd_unit; then
        warn "log service:"
        run_root journalctl -u "${SERVICE_NAME}.service" -n 20 --no-pager 2>/dev/null || true
    fi
    die "dashboard bala nayamad - health: ${health:-bedoon pasokh}"
}

print_done() {
    local port ip
    port="$(get_api_port)"
    ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
    cat <<EOF

============================================================
  INSTALL TAMOM SHOD!

  Dashboard:  http://${ip:-localhost}:${port}
  Options:    http://${ip:-localhost}:${port}/options.html
  Status:     ./install.sh status

  Baraye update badi:
    ./install.sh
    ya:
    curl -fsSL https://raw.githubusercontent.com/mr-BigJay/btc-analyzer-v2/main/bootstrap.sh | bash
============================================================
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

    cd "$PROJECT_DIR" 2>/dev/null || mkdir -p "$PROJECT_DIR"

    # Pull latest code FIRST so install.sh and app code are current.
    if [[ -d "$PROJECT_DIR/.git" ]]; then
        if [[ "$mode" == "update" ]]; then
            stop_all
        fi
        git_update
    fi

    interactive_preflight "$mode"
    install_system_packages
    ensure_project_dir
    cd "$PROJECT_DIR"

    if [[ "$mode" != "update" ]] && [[ -d .git ]]; then
        git_update
    fi

    setup_venv
    setup_env_file
    run_pipeline
    start_services
    verify_deploy
    print_done

    log "=== ${mode^^} DONE ==="
}

status_all() {
    local port
    port="$(get_api_port)"

    if has_systemd_unit; then
        run_root systemctl status "${SERVICE_NAME}.service" --no-pager 2>/dev/null || warn "service asli gheyre-faal"
        echo ""
        run_root systemctl status "${TELEGRAM_SERVICE_NAME}.service" --no-pager 2>/dev/null || true
    fi

    if uses_docker; then
        cd "$PROJECT_DIR"
        docker compose ps
    fi

    echo ""
    curl -sf "http://127.0.0.1:${port}/api/health" 2>/dev/null && echo || warn "API roye port $port pasokh nemidehad"
}

main() {
    parse_args "$@"
    cd "$PROJECT_DIR" 2>/dev/null || true

    # Auto-update install.sh from git before doing anything (fixes stale Persian scripts).
    if [[ -z "${BTC_INSTALL_UPDATED:-}" ]] && [[ -d "$PROJECT_DIR/.git" ]]; then
        export BTC_INSTALL_UPDATED=1
        git -C "$PROJECT_DIR" fetch origin "$GIT_BRANCH" -q 2>/dev/null || true
        git -C "$PROJECT_DIR" checkout "$GIT_BRANCH" -q 2>/dev/null || true
        git -C "$PROJECT_DIR" reset --hard "origin/$GIT_BRANCH" -q 2>/dev/null || true
        exec "$PROJECT_DIR/install.sh" "$@"
    fi

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
