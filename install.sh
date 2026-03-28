#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/sheet-coin"
SERVICE_NAME="sheet-coin"
SERVICE_FILE="systemd/sheet-coin.service"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

PROJECT_FILES=(
    pyproject.toml
    uv.lock
    .env.example
    Dockerfile
    compose.yml
)

PROJECT_DIRS=(
    src
)

usage() {
    echo "Usage: sudo $0 [--uninstall]"
    echo ""
    echo "  (no args)    Install or update sheet-coin"
    echo "  --uninstall  Stop service, remove install directory and service file"
}

uninstall() {
    echo "Uninstalling $SERVICE_NAME..."
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        systemctl stop "$SERVICE_NAME"
    fi
    if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        systemctl disable "$SERVICE_NAME"
    fi
    rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
    systemctl daemon-reload
    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
    fi
    echo "Uninstalled."
}

install() {
    if ! command -v uv &>/dev/null; then
        echo "Error: uv is not installed. See https://docs.astral.sh/uv/getting-started/installation/" >&2
        exit 1
    fi

    # Verify source files exist
    for f in "${PROJECT_FILES[@]}" "$SERVICE_FILE"; do
        if [[ ! -f "$SCRIPT_DIR/$f" ]]; then
            echo "Error: Missing required file: $f" >&2
            exit 1
        fi
    done
    for d in "${PROJECT_DIRS[@]}"; do
        if [[ ! -d "$SCRIPT_DIR/$d" ]]; then
            echo "Error: Missing required directory: $d" >&2
            exit 1
        fi
    done

    # Stop service if running (update scenario)
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        echo "Stopping $SERVICE_NAME..."
        systemctl stop "$SERVICE_NAME"
    fi

    # Copy project files
    echo "Installing to $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR"
    for f in "${PROJECT_FILES[@]}"; do
        cp "$SCRIPT_DIR/$f" "$INSTALL_DIR/"
    done
    for d in "${PROJECT_DIRS[@]}"; do
        cp -r "$SCRIPT_DIR/$d" "$INSTALL_DIR/"
    done

    # Set up .env: keep existing, or copy from repo, or create from template
    if [[ -f "$INSTALL_DIR/.env" ]]; then
        echo "Existing .env preserved."
        ENV_CREATED=false
    elif [[ -f "$SCRIPT_DIR/.env" ]]; then
        cp "$SCRIPT_DIR/.env" "$INSTALL_DIR/.env"
        chmod 600 "$INSTALL_DIR/.env"
        echo "Copied .env from repo."
        ENV_CREATED=false
    else
        cp "$SCRIPT_DIR/.env.example" "$INSTALL_DIR/.env"
        chmod 600 "$INSTALL_DIR/.env"
        ENV_CREATED=true
    fi

    # Install dependencies
    echo "Installing dependencies..."
    cd "$INSTALL_DIR"
    uv sync --frozen --no-dev

    # Install systemd service
    echo "Installing systemd service..."
    cp "$SCRIPT_DIR/$SERVICE_FILE" "/etc/systemd/system/${SERVICE_NAME}.service"
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"

    echo ""
    if [[ "$ENV_CREATED" == true ]]; then
        echo "Done. Next steps:"
        echo "  1. Edit $INSTALL_DIR/.env with your credentials"
        echo "  2. sudo systemctl start $SERVICE_NAME"
    else
        systemctl start "$SERVICE_NAME"
        echo "Done. Service started. Check status: sudo systemctl status $SERVICE_NAME"
    fi
}

if [[ $EUID -ne 0 ]]; then
    echo "Error: This script must be run as root (or with sudo)." >&2
    exit 1
fi

case "${1:-}" in
    --uninstall) uninstall ;;
    --help|-h)   usage ;;
    "")          install ;;
    *)           usage; exit 1 ;;
esac
