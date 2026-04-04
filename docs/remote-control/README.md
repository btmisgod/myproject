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

## Controller behavior

The local architect loop is intentionally conservative:

- It supports ordered multi-phase objectives.
- It does not treat one finished subtask as completion of the whole objective.
- It prefers local cheap-path decisions when:
  - the server is still running the same task,
  - there is no new result,
  - or the latest result has already been handled.
- It hard-blocks immediately on infrastructure/auth failures such as `401 Unauthorized` instead of repeatedly burning tokens.
- It tracks repeated bug work with controller policy limits.

Default controller policy:

```json
{
  "max_narrow_operations": 3,
  "max_fix_operations": 3,
  "design_review_after_repairs": 3,
  "max_repairs": 5
}
```

Meaning:

- the same bug may use at most 3 narrowing operations before blocking,
- once the blocker is narrowed, the same point may use at most 3 fix attempts,
- after 3 repair cycles the controller should stop and require design review,
- after 5 repair cycles the controller must stop and mark a blocker.

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

The executor root path now serves a simple status UI:

```bash
curl http://127.0.0.1:18789/
```

For raw page data:

```bash
curl http://127.0.0.1:18789/ui-data
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

You can also add optional long-running controller metadata:

```json
{
  "controller_policy": {
    "max_narrow_operations": 3,
    "max_fix_operations": 3,
    "design_review_after_repairs": 3,
    "max_repairs": 5
  },
  "design_docs": [
    "/absolute/path/to/design.md"
  ]
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
