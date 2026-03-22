# CONTROL

## Current Objective

`修复 myproject 的 POST /messages MissingGreenlet，并重跑 targeted / non-targeted / status 三条最小回归。`

## Instruction Source

当前唯一正式指令源按优先级排序：

1. 用户在当前主对话中对产品总监侧 Codex 下达的新指令
2. 本文件 `CONTROL.md`
3. `ARCHITECT_REVIEW.md` 中的最新最小动作

规则：

- 用户在聊天中下达的新指令，不会直接要求服务器执行
- 产品总监侧 Codex 必须先把它同步进 GitHub 控制面文档
- 服务器执行侧只认仓库中的最新文档，不认聊天记录

## Scope

- 允许修改的仓库：
  - `myproject`
  - `community-skill`
- 允许修改的模块：
  - `myproject/app/services/community.py`
  - `myproject/app/services/message_protocol_mapper.py`
  - `myproject/app/services/event_bus.py`
  - 与 `POST /api/v1/messages` 活链直接相关的模型和序列化代码

## Forbidden

- 不扩展新功能
- 不同时推进多个大方向
- 不跳过已定义的验收链路
- 不为了“先跑通”而绕过关键安全或协议检查

## Acceptance

- `/agents/me` 返回 200
- `targeted run => execute + reply`
- `non-targeted run => observe_only / no outbound / no reply`
- `status => 进入系统但 agent 不自动回复`

## Deliverables

- 提交的 commit id
- 修改文件列表
- 测试结果
- 唯一阻塞点（如果失败）

## Polling

- 服务器执行侧默认高频轮询本文件
- 推荐轮询间隔：`2 分钟`
- 如果服务器正在执行较重任务，可在安全检查点刷新，而不是中断当前执行
