#!/usr/bin/env bash
# BTC Analyzer v2 — one-command installer (Ubuntu)
set -euo pipefail

REPO_URL="${BTC_ANALYZER_REPO:-https://github.com/mr-BigJay/btc-analyzer-v2.git}"
GIT_BRANCH="${BTC_ANALYZER_BRANCH:-main}"
INSTALL_DIR="${BTC_ANALYZER_DIR:-$HOME/btc-analyzer-v2}"

log()  { echo "[bootstrap] $*"; }
warn() { echo "[bootstrap] WARNING: $*" >&2; }
die()  { echo "[bootstrap] ERROR: $*" >&2; exit 1; }

read_tty() {
    local prompt="$1" default="${2:-}"
    local reply=""
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

run_root() {
    if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
        env "$@"
    else
        sudo env "$@"
    fi
}

ensure_git() {
    if command -v git >/dev/null 2>&1; then
        return
    fi
    if ! command -v apt-get >/dev/null 2>&1; then
        die "git peida nashod. avval git ro nasb konid."
    fi
    log "git peida nashod - dar hale nasb..."
    run_root apt-get update -qq
    run_root DEBIAN_FRONTEND=noninteractive apt-get install -y git curl ca-certificates
}

sync_repo() {
    if [[ -f "$INSTALL_DIR/src/main.py" ]]; then
        if [[ -d "$INSTALL_DIR/.git" ]]; then
            if ask_yes_no "Nasb ghabli dar $INSTALL_DIR peida shod. Update konim?" "y"; then
                log "update code az origin/$GIT_BRANCH ..."
                git -C "$INSTALL_DIR" fetch origin "$GIT_BRANCH"
                git -C "$INSTALL_DIR" checkout "$GIT_BRANCH"
                git -C "$INSTALL_DIR" reset --hard "origin/$GIT_BRANCH"
                git -C "$INSTALL_DIR" clean -fd -e data -e .env -e .venv
            else
                log "update code skip shod - faghat install edame peyda mikone"
            fi
        fi
        return
    fi

    if [[ -d "$INSTALL_DIR" ]] && [[ -n "$(ls -A "$INSTALL_DIR" 2>/dev/null || true)" ]]; then
        if ! ask_yes_no "Pooshe $INSTALL_DIR khali nist. edame bedim?" "y"; then
            die "install laghv shod"
        fi
    fi

    log "clone az $REPO_URL (branch: $GIT_BRANCH)..."
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone --branch "$GIT_BRANCH" "$REPO_URL" "$INSTALL_DIR"
}

main() {
    echo ""
    echo "=========================================="
    echo "  BTC Analyzer v2 — Installer"
    echo "=========================================="
    echo ""

  if [[ -t 0 ]] || [[ -e /dev/tty ]]; then
        local custom_dir
        custom_dir="$(read_tty "Masir nasb (Enter = $INSTALL_DIR):" "$INSTALL_DIR")"
        INSTALL_DIR="${custom_dir:-$INSTALL_DIR}"
        export BTC_ANALYZER_DIR="$INSTALL_DIR"
    fi

    ensure_git
    sync_repo

    if [[ ! -f "$INSTALL_DIR/install.sh" ]]; then
        die "install.sh dar $INSTALL_DIR peida nashod"
    fi

    chmod +x "$INSTALL_DIR/install.sh"
    log "shoroo install.sh ..."
    exec "$INSTALL_DIR/install.sh" "$@"
}

main "$@"
