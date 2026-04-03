# Server Join Prompt

Use this prompt on the server once, in a fresh Codex session, to join the long-running control-plane workflow.

```text
Do not work ad hoc. Join the long-running control-plane workflow for this repository.

Tasks:
1. Ensure the latest `myproject` main is present locally.
2. Install or refresh the control-plane worker service by running:
   - `bash scripts/install_server_control_plane_worker.sh`
3. Start or restart the worker service.
4. Verify:
   - the worker service is active
   - `docs/control-plane/.runtime/worker-state.json` is being refreshed
   - `docs/control-plane/SERVER_REPORT.md` can be published back to GitHub
5. After verification, stop doing ad hoc work and let the worker continue the active objective from:
   - `docs/control-plane/OBJECTIVE.md`
   - `docs/control-plane/CONTROL.md`
   - `docs/control-plane/ARCHITECT_REVIEW.md`
   - `docs/control-plane/OPERATING_RULES.md`

Rules:
- Keep exactly one current blocker if something fails.
- Do not start unrelated work.
- Do not rely on chat logs after joining.
- Use the repository control-plane docs as the shared source of truth.
```
