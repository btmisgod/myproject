# Server Install Prompt

```text
Pull the latest `myproject` main and install the direct remote Codex executor.

Steps:
1. `git pull origin main`
2. `bash scripts/install_remote_codex_executor.sh`
3. Check the service:
   - `systemctl status codex-remote-executor.service --no-pager`
4. Check the API:
   - `curl http://127.0.0.1:18789/healthz`
5. Print:
   - service status
   - token file path
   - runtime dir
   - current blocker, or `no blocker`
```
