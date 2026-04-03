#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="${CONTROL_PLANE_SERVICE_NAME:-openclaw-control-plane-worker.service}"
INSTALL_PATH="${CONTROL_PLANE_INSTALL_PATH:-/root/agent-community}"
PYTHON_BIN="${CONTROL_PLANE_PYTHON_BIN:-/usr/bin/python3}"
SYSTEMCTL_BIN="${CONTROL_PLANE_SYSTEMCTL_BIN:-/bin/systemctl}"
POLL_SECONDS="${CONTROL_PLANE_POLL_SECONDS:-120}"
CODEX_BIN="${CONTROL_PLANE_CODEX_BIN:-codex}"
MODEL="${CONTROL_PLANE_MODEL:-}"

if [[ ! -d "${INSTALL_PATH}" ]]; then
  echo "install path does not exist: ${INSTALL_PATH}" >&2
  exit 1
fi

mkdir -p "${INSTALL_PATH}/docs/control-plane/.runtime"
mkdir -p /etc/systemd/system

cat > "/etc/systemd/system/${SERVICE_NAME}" <<EOF
[Unit]
Description=OpenClaw Control-Plane Worker
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_PATH}
Environment=HOME=/root
Environment=PATH=/root/.nvm/versions/node/v22.22.1/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=CONTROL_PLANE_POLL_SECONDS=${POLL_SECONDS}
Environment=CONTROL_PLANE_CODEX_BIN=${CODEX_BIN}
Environment=CONTROL_PLANE_MODEL=${MODEL}
ExecStart=${PYTHON_BIN} ${INSTALL_PATH}/scripts/control_plane_worker.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

${SYSTEMCTL_BIN} daemon-reload
${SYSTEMCTL_BIN} enable "${SERVICE_NAME}"
${SYSTEMCTL_BIN} restart "${SERVICE_NAME}"
${SYSTEMCTL_BIN} status "${SERVICE_NAME}" --no-pager || true

echo "installed and restarted ${SERVICE_NAME}"
