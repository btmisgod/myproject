$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = if ($env:LOCAL_CONTROL_PLANE_PYTHON_BIN) { $env:LOCAL_CONTROL_PLANE_PYTHON_BIN } else { "python" }
$runtimeDir = if ($env:LOCAL_CONTROL_PLANE_RUNTIME_DIR) { $env:LOCAL_CONTROL_PLANE_RUNTIME_DIR } else { Join-Path $env:USERPROFILE ".codex\control-plane-local-runtime" }

New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

$env:LOCAL_CONTROL_PLANE_RUNTIME_DIR = $runtimeDir
if (-not $env:LOCAL_CONTROL_PLANE_POLL_SECONDS) {
  $env:LOCAL_CONTROL_PLANE_POLL_SECONDS = "120"
}

Push-Location $root
try {
  & $python ".\scripts\local_control_plane_controller.py"
} finally {
  Pop-Location
}
