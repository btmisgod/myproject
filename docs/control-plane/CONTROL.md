# CONTROL

## Current Objective

`修复 myproject 的 POST /messages MissingGreenlet，并重跑 targeted / non-targeted / status 三条最小回归。`

## Scope

- 允许修改的仓库：
  - `myproject`
  - `community-skill`
- 允许修改的模块：
  - `myproject/app/services/community.py`
  - `myproject/app/services/message_protocol_mapper.py`
  - `myproject/app/services/event_bus.py`
  - 与 `POST /api/v1/messages` 活链直接相关的模型/序列化代码

## Forbidden

- 不扩展新功能
- 不同时推进多个大方向
- 不跳过已定义的验收链路
- 不为了“先跑通”而绕过关键安全/协议检查

## Acceptance

写明本轮验收标准。示例：

- `/agents/me` 返回 200
- `targeted run => execute + reply`
- `non-targeted run => observe_only / no outbound / no reply`
- `status => 进入系统但 agent 不自动回复`

## Deliverables

- 提交的 commit id
- 修改文件列表
- 测试结果
- 唯一阻塞点（如果失败）
