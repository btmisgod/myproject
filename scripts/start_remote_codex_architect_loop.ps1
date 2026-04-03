$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = if ($env:REMOTE_CODEX_ARCHITECT_PYTHON_BIN) { $env:REMOTE_CODEX_ARCHITECT_PYTHON_BIN } else { "python" }

Push-Location $root
try {
  & $python ".\scripts\remote_codex_architect_loop.py"
} finally {
  Pop-Location
}
