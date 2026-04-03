#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="${REMOTE_CODEX_EXECUTOR_SERVICE_NAME:-codex-remote-executor.service}"
INSTALL_PATH="${REMOTE_CODEX_EXECUTOR_INSTALL_PATH:-/root/agent-community}"
RUNTIME_DIR="${REMOTE_CODEX_EXECUTOR_RUNTIME_DIR:-/root/.codex-remote-executor}"
PYTHON_BIN="${REMOTE_CODEX_EXECUTOR_PYTHON_BIN:-/usr/bin/python3}"
SYSTEMCTL_BIN="${REMOTE_CODEX_EXECUTOR_SYSTEMCTL_BIN:-/bin/systemctl}"
PORT="${REMOTE_CODEX_EXECUTOR_PORT:-18789}"
WORKSPACE="${REMOTE_CODEX_EXECUTOR_DEFAULT_WORKSPACE:-/root/agent-community}"
CODEX_BIN="${REMOTE_CODEX_EXECUTOR_CODEX_BIN:-codex}"

mkdir -p "${RUNTIME_DIR}/results"
mkdir -p /etc/systemd/system

TOKEN_FILE="${RUNTIME_DIR}/auth-token.txt"
if [[ ! -f "${TOKEN_FILE}" ]]; then
  ${PYTHON_BIN} - <<'PY' > "${TOKEN_FILE}"
import secrets
print(secrets.token_hex(24))
PY
  chmod 600 "${TOKEN_FILE}"
fi

ENV_FILE="${RUNTIME_DIR}/executor.env"
cat > "${ENV_FILE}" <<EOF
REMOTE_CODEX_EXECUTOR_HOST=0.0.0.0
REMOTE_CODEX_EXECUTOR_PORT=${PORT}
REMOTE_CODEX_EXECUTOR_RUNTIME_DIR=${RUNTIME_DIR}
REMOTE_CODEX_EXECUTOR_DEFAULT_WORKSPACE=${WORKSPACE}
REMOTE_CODEX_EXECUTOR_CODEX_BIN=${CODEX_BIN}
REMOTE_CODEX_EXECUTOR_TOKEN=$(cat "${TOKEN_FILE}")
EOF
chmod 600 "${ENV_FILE}"

cat > "/etc/systemd/system/${SERVICE_NAME}" <<EOF
[Unit]
Description=Remote Codex Executor API
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_PATH}
Environment=HOME=/root
Environment=PATH=/root/.nvm/versions/node/v22.22.1/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
EnvironmentFile=${ENV_FILE}
ExecStart=${PYTHON_BIN} ${INSTALL_PATH}/scripts/remote_codex_executor_server.py
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

echo "service=${SERVICE_NAME}"
echo "port=${PORT}"
echo "token_file=${TOKEN_FILE}"
echo "env_file=${ENV_FILE}"
