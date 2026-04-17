# Server Codex Handoff: Bootstrap + Newsflow Live Testing

更新时间：2026-04-17

## 1. 目标

把 `bootstrap + newsflow` 的 live 测试与修复工作整体切到服务器侧 Codex 执行。

这份文档的用途不是复盘历史，而是让服务器上的 Codex 直接接手继续做：
- 标准五角色运行环境建设
- clean group 创建与协议 patch
- bootstrap/newsflow 从头重跑
- 遇到 blocker 直接在服务器侧继续排查与修复

## 2. 这次交接的硬边界

必须遵守：
- 不允许为了测试通过去改 `community` / `community-skill` 逻辑配合某个群。
- 不允许手工注入 DB / route / webhook 伪状态。
- 不允许给某个群写特供配置。
- 环境必须能从空本地状态按同样流程重建。
- raw API key 不能写进 repo、文档、证据、日志。
- 优先走正式路径：service、workspace、onboarding、route、protocol、session。

大白话：
- 不能“偷偷造一个看起来成功的状态”。
- 要的是标准环境真的能搭起来，工作流真的能跑起来。

## 3. 当前项目范围

这轮只关心：
- 社区工程 `myproject`
- role-agent skill `community-skill`
- OpenClaw 模板仓 `openclaw-for-community`
- live 目标主机上承载的五角色实例

当前 workflow 源文件：
- `community/protocols/drafts/newsflow.json`

当前角色模型：
- manager: `openclaw-33`
- editor: `openclaw-33-editor`
- tester: `openclaw-33-tester`
- worker_a: `openclaw-33-worker-33`
- worker_b: `openclaw-33-worker-xhs`

## 4. 当前 GitHub 基线

### myproject
- repo: `https://github.com/btmisgod/myproject`
- branch: `codex/pr-community-v2-live-baseline-20260410`
- commit: `9f6cf773b8ac5b1be8edda4beb266ccff67537da`

### community-skill
- repo: `https://github.com/btmisgod/community-skill`
- branch: `codex/pr-skill-body-context-slimming-20260411`
- commit: `4d0487faa64cf6331869c3735bccb404680d13fe`

### openclaw-for-community
- repo: `https://github.com/btmisgod/openclaw-for-community`
- branch: `codex/pr-skill-context-slimming-clean-20260411`
- commit: `5023ef72e5eac4682c0b4e241da568fa8be05b7f`

注意：
- 服务器侧 Codex 继续工作时，先确认 live 主机拉到的就是你要用的分支/提交。
- 不要默认 main 一定包含这轮测试需要的所有内容。

## 5. 已经确认完成的事情

1. remote dispatch / terminal result 链已经修好。
- 现在 live deploy 风格任务可以返回 terminal result。
- 不要再默认把新问题归因到 controller / executor。

2. formal identity lifecycle 已补上正式 reattach 路径。
- 五角色实例可以按标准 `cleanup-local-state -> ensure-community-agent-onboarding.sh` 重建。
- 这一步不再需要手工删库或伪造 route/webhook。

3. runtime drift / provider inheritance / free-model 直连这些低层问题已经被排过一轮。
- 它们不是当前主 blocker 的默认归因点。

4. `newsflow.json` 已经形成当前最新草稿。
- 这份文件现在一并上传，服务器侧直接以它为准继续测试。

## 6. 当前测试目标

服务器 Codex 接手后，不要再先开新功能，先把这条主线走通：

### A. 标准五角色运行环境建设
交付物不是“测试通过”，而是：
- 五角色实例清单
- 安装方式
- onboarding 证据
- route / service / workspace 证据

### B. 从空环境重建
要求：
- 从 clean local state 开始
- 按正式 onboarding 路径把五角色都接回社区
- 不靠历史残留 token / socket / route 侥幸成功

### C. clean group 重跑
要求：
- 新建 clean group
- patch `newsflow.json`
- bootstrap 重跑
- newsflow 正式阶段重跑
- 只接受 authoritative session/projection 作为阶段事实

## 7. 当前最值得继续查的真实问题

### 问题 1：manager formal signal 与真实交付之间可能仍然脱节
现象：
- 前端上能看到推进消息，但实际交付内容不完整。
- 这不是单纯 UI 漏展示，而是 workflow 可信度问题。

边界要点：
- 这不是 skill 应该替 manager 做判断。
- 正确边界是：manager agent 必须真的消费交付内容，再决定是否发 formal close。
- server 只负责 gate，不负责替 manager 审稿。

服务器 Codex 接手后要查：
- manager 当前 prompt / execution path 是否真的消费了 stage 交付物
- formal signal 是否在没有对应 artifact 的情况下被机械生成
- authoritative message/event 是否丢了 stage 必需字段

### 问题 2：live role-agent 的真实 manager surface 是否与本地修复版一致
已发生过的情况：
- 本地修复成立，但 live manager 文件没真正落上去。
- read-only 审计能完成，write task 却可能不留下 deploy effect。

服务器 Codex 接手后要查：
- live 主机上真实运行中的 `community_integration.mjs` 哈希
- role-agent service 是否已重启并加载新文件
- 不能只看 repo 工作树，要看 service 实际读到的文件

### 问题 3：阶段推进不能只看 `step_status`，要看 stage 对应产物是否真的形成
要重点验：
- `cycle_task_plan`
- `candidate_material_pool`
- `material_review_feedback`
- `product_draft`
- `proofread_feedback`
- `revised_product_draft`
- `recheck_feedback`
- `publish_decision`
- 后续 retrospective / optimization 产物

如果只有推进信号、没有这些东西，不算真通过。

## 8. 服务器侧推荐执行顺序

1. 确认 live host/profile 是承载 `openclaw-33 + 4 个 role-agent` 的那台。
2. 清空本地角色运行态（不是删 server DB，而是 clean local state）。
3. 按正式脚本重建五角色环境。
4. 回收：service / workspace / socket / onboarding / route 证据。
5. 新建 clean group。
6. patch 当前 `newsflow.json`。
7. 从头跑 bootstrap。
8. 再跑 newsflow 正式阶段。
9. 每推进一阶段，都同时检查：
   - authoritative session
   - authoritative messages/events
   - 真实 stage artifact
10. 遇到 blocker 直接在服务器侧修，不要把未确认的问题重新甩回 controller/executor。

## 9. 参考文档

先读这些：

### myproject
- `docs/control-plane/README.md`
- `docs/control-plane/CONTROL.md`
- `docs/control-plane/OPERATING_RULES.md`
- `docs/control-plane/SERVER_REPORT.md`
- `community/protocols/drafts/newsflow.json`

### community-skill
- `README.md`
- `scripts/community_integration.mjs`
- `scripts/ensure-community-agent-onboarding.sh`
- `tests/community-skill-outbound-v2.test.mjs`

### openclaw-for-community
- `docs/server-verification.md`
- `scripts/server-verify-agent-onboarding.sh`

### workspace root
- `AGENTS.md`

## 10. 服务器 Codex 的验收标准

最低通过标准：
- 五角色环境能从空本地状态标准重建
- onboarding 证据完整
- clean group 能建成
- `newsflow.json` patch 成功
- bootstrap 能从头重跑
- newsflow 能至少跑到出现真实 `candidate_material_pool` 和后续真实 stage artifact
- manager formal signal 与实际交付内容一致，不再只是机械推进
- 所有结论都以 authoritative session/messages/events 为准

## 11. 这份交接文档不替代什么

它不替代：
- 服务器侧真实 service/journal 检查
- authoritative session/messages/events 取证
- live 文件哈希与 service 实际加载面的核对

大白话：
- 这份文档是路线图，不是成功证明。
- 真正的成功，还是要靠服务器侧重新跑一遍，把证据拿全。
