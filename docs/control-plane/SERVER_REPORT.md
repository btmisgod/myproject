# SERVER REPORT

## Environment

- Host: `/root`
- Repo:
  - `myproject`: `/root/agent-community`
  - `community-skill`: `/root/openclaw-33/workspace/skills/community-skill`
- Current commit:
  - `myproject`: `7445681b1e7c5712e427d7a05ca37b8e8b040f8f`
  - `community-skill`: `b4048a203fc25784a59720edd236b635262d6172`
- Service names:
  - `agent-community-api-1`
  - `agent-community-postgres-1`
  - `agent-community-redis-1`
  - `openclaw-community-ingress.service`
  - `openclaw-community-webhook-openclaw-33.service`
- Active ports / paths:
  - Community API: `127.0.0.1:8000`
  - Shared ingress: `127.0.0.1:8848`
  - Webhook path: `/webhook/openclaw-33`
  - Send path: `/send/openclaw-33`

## Work Performed

- Read control-plane docs:
  - `docs/control-plane/REPO_INDEX.md`
  - `docs/control-plane/CONTROL.md`
  - `docs/control-plane/OPERATING_RULES.md`
  - `docs/designlog/`
- Repaired the `myproject` ORM mapper block so `/api/v1/agents/me` and agent bootstrap recovered:
  - restored `Group.tasks`
  - removed stale `Task.messages`
- Repaired `POST /api/v1/messages` active-chain async lazy-load / `MissingGreenlet` failure:
  - refreshed `message` before event payload serialization
  - made protocol-v2 message serialization JSON-safe
- Re-verified the live skill webhook path and baseline regression set:
  - `targeted run => execute + reply`
  - `non-targeted run => observe_only / no outbound / no reply`
  - `status => enters system / no auto reply`

## Files Changed

- `/root/agent-community/app/models/group.py`
  - restore `Group.tasks` so ORM mapper matches `Task.group`
- `/root/agent-community/app/models/task.py`
  - remove stale `Task.messages` relationship
- `/root/agent-community/app/services/community.py`
  - refresh `message` before payload/event serialization
- `/root/agent-community/app/services/message_protocol_mapper.py`
  - emit JSON-safe scalars in protocol-v2 serialization

## Validation

- Command:
  - `git -C /root/agent-community rev-parse HEAD`
  - `git -C /root/openclaw-33/workspace/skills/community-skill rev-parse HEAD`
  - `curl -sS -X POST http://127.0.0.1:8000/api/v1/messages ...`
  - `docker compose logs api`
  - `docker exec agent-community-postgres-1 psql ...`
  - `journalctl -u openclaw-community-webhook-openclaw-33.service`
- Result:
  - `/api/v1/agents/me` recovered and bootstrap completed
  - `POST /api/v1/messages` no longer returns 500
  - `targeted run` generated a persisted reply
  - `non-targeted run` was observed and did not reply
  - `status` entered the system and did not trigger an automatic reply

## Logs / Evidence

- API log:
  - `GET /api/v1/agents/me HTTP/1.1" 200 OK`
  - `POST /api/v1/messages HTTP/1.1" 200 OK`
- Targeted run evidence:
  - inbound message id: `270b7510-e02c-454d-8d93-095a4b3b158a`
  - agent reply id: `358010f9-cdd1-4866-9391-2799ea17204c`
  - webhook log: `"obligation":"required"`, `"action":"full_reply"`
- Non-targeted run evidence:
  - message id: `756bac1d-5bc2-4981-9182-5e996cbab118`
  - webhook log: `"observed": true`, `"action":"observe_only"`
  - no auto-reply from agent33 persisted in the database
- Status evidence:
  - message id: `a6990739-5211-4a39-9c4c-18e022a59ceb`
  - webhook log: `"category":"status"`, `"action":"observe_only"`
  - no auto-reply from agent33 persisted in the database

## Current Status

- Passed:
  - `myproject` current main chain restored agent bootstrap
  - `POST /api/v1/messages` current main chain restored
  - `targeted run => execute + reply`
  - `non-targeted run => observe_only / no outbound / no reply`
  - `status => enters system / no auto reply`
- Failed:
  - no new active-chain failure; the remaining blocker is the long-range acceptance target

## Single Blocking Point

`community-skill` current main `b4048a203fc25784a59720edd236b635262d6172` still reflects an older runtime semantic vocabulary path (`obligation/decision` style wording). The minimal regressions pass, but the formal long-range acceptance item for "install on a fresh OpenClaw instance and auto-connect correctly" has not yet been completed and recorded.

## Recommendation

Do exactly one next step: install the current `community-skill main` on a fresh OpenClaw instance and verify that automatic onboarding and the minimal collaboration chain match the baseline.
