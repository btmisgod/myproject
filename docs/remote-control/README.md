# Remote Codex Direct Control

This is the direct-control version of the long-running architect/executor system.

It does **not** use GitHub control-plane docs as the high-frequency command channel.

## Architecture

- Local side:
  - `scripts/remote_codex_set_objective.py`
  - `scripts/remote_codex_architect_loop.py`
- Server side:
  - `scripts/remote_codex_executor_server.py`
  - `scripts/install_remote_codex_executor.sh`

## Communication model

- The server exposes a small HTTP executor API.
- The local architect loop polls the server state and decides the next single task.
- The local architect loop dispatches one task at a time.
- The server runs local Codex to execute that task and stores the result.

## Recommended port

- Default: `18789`
- Keep `8000` and `8848` reserved for community services.

## Fast start

### 1. On the server

Run:

```bash
bash scripts/install_remote_codex_executor.sh
```

Then read the generated token from:

```bash
cat /root/.codex-remote-executor/auth-token.txt
```

Verify the local health endpoint on the server:

```bash
curl http://127.0.0.1:18789/healthz
```

### 2. On the local architect machine

Set environment variables:

```powershell
$env:REMOTE_CODEX_SERVER_URL="http://<server-ip>:18789"
$env:REMOTE_CODEX_SERVER_TOKEN="<token>"
```

Write a single-phase objective quickly:

```powershell
python scripts\remote_codex_set_objective.py --title "..." --goal "..." --stage "..." --scope item1 item2 --acceptance item1 item2 --constraints item1 item2
```

Write a real multi-phase long-running objective from JSON:

```powershell
python scripts\remote_codex_set_objective.py --objective-file .\objective.json
```

Example `objective.json`:

```json
{
  "title": "Stabilize community communication and onboarding",
  "goal": "Agents should communicate cleanly in the community and a fresh skill install should onboard correctly.",
  "phases": [
    {
      "phase_id": "phase-1-runtime-boundary",
      "title": "Fix runtime and reply boundary bugs",
      "goal": "Remove forced public replies and suppress self-reply/relay loops.",
      "scope": ["community-skill", "runtime", "deliberation"],
      "acceptance": [
        "No mechanically forced public reply in the targeted path",
        "No self-reply or relay loop in focused short-window tests"
      ],
      "constraints": [
        "Preserve provider-usage-first token ledger"
      ],
      "notes": ""
    },
    {
      "phase_id": "phase-2-onboarding",
      "title": "Preserve fresh-install onboarding",
      "goal": "A fresh community-skill install should onboard correctly on the preserved baseline.",
      "scope": ["community-skill", "onboarding"],
      "acceptance": [
        "Fresh install onboarding succeeds",
        "Accepted single-agent onboarding behavior remains passing"
      ],
      "constraints": [
        "Do not regress completed phase behavior"
      ],
      "notes": ""
    }
  ],
  "current_phase_index": 0,
  "phase_history": []
}
```

Start the local architect loop:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_remote_codex_architect_loop.ps1
```

## Deployment notes

- The server executor is the public endpoint in this design.
- Default public port: `18789`
- Keep community ports `8000` and `8848` reserved.
- Protect the executor with the generated bearer token.
- If the server firewall is already open for `18789`, you can connect directly without adding a reverse tunnel.
