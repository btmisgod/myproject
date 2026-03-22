# Repository Index

这是控制面使用的唯一仓库索引文件。后续所有人与 Codex 都应优先引用本文件中的仓库地址、分支与关键路径，而不是依赖聊天中的临时口述。

## Canonical Repositories

- `myproject`
  - GitHub: [https://github.com/btmisgod/myproject](https://github.com/btmisgod/myproject)
  - Default branch: `main`
  - Control-plane root: `docs/control-plane/`
  - Design docs root: `docs/designlog/`

- `community-skill`
  - GitHub: [https://github.com/btmisgod/community-skill](https://github.com/btmisgod/community-skill)
  - Default branch: `main`

## Canonical Working Rule

1. 服务器执行侧在开始工作前，先确认自己拉取的是以上两个仓库的 `main`
2. 控制面文档统一以 `myproject` 仓库中的 `docs/control-plane/` 为唯一正式来源
3. Skill 相关代码修改在 `community-skill` 仓库进行，但执行目标与优先级仍以 `myproject/docs/control-plane/CONTROL.md` 为准

## Current Control Files

- `docs/control-plane/CONTROL.md`
- `docs/control-plane/SERVER_REPORT.md`
- `docs/control-plane/ARCHITECT_REVIEW.md`
- `docs/control-plane/OPERATING_RULES.md`
- `docs/control-plane/SERVER_EXEC_PROMPT.md`
- `docs/control-plane/ARCHITECT_REVIEW_PROMPT.md`

