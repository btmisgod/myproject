# CONTROL

## Current Objective

`完成 Community 工程并按设计文档跑通；完成 community-skill 工程，并实现“安装到一个全新的 openclaw 实例后即可自动接入社区并正确使用社区功能”；两项都完成后进行一次复盘审查，确认无误后结束本轮任务。`

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
  - `myproject` 中所有与 Community 主链、事件、webhook、group、message、presence、deployment 相关的代码与文档
  - `community-skill` 中所有与 onboarding、webhook、runtime、协议适配、agent 侧资产安装、自动接入相关的代码与文档
  - 与“全新 openclaw 实例自动接入社区”验证直接相关的部署脚本、模板 env、服务配置和测试资产

## Forbidden

- 不扩展新功能
- 不同时推进多个大方向
- 不跳过已定义的验收链路
- 不为了“先跑通”而绕过关键安全或协议检查

## Acceptance

- Community 工程按 `docs/designlog/` 中设计文档完成到可运行状态
- Community 主链真实跑通：
  - agent 注册
  - join group
  - message 持久化
  - event 广播
  - webhook 投递
  - targeted run => execute + reply
  - non-targeted run => observe_only / no outbound / no reply
  - status => 进入系统但 agent 不自动回复
- community-skill 工程完成到可运行状态
- 在一个全新的 openclaw 实例上验证通过：
  - 安装 skill
  - 自动完成 onboarding / webhook 注册 / group 加入 / 基础状态汇报
  - 正确使用社区功能
- 完成一次复盘审查
- 复盘确认无误后，本轮任务结束

## Deliverables

- 提交的 commit id
- 修改文件列表
- 测试结果
- 唯一阻塞点（如果失败）
- 全新 openclaw 实例验证记录
- 最终复盘结论

## Polling

- 服务器执行侧默认高频轮询本文件
- 推荐轮询间隔：`2 分钟`
- 如果服务器正在执行较重任务，可在安全检查点刷新，而不是中断当前执行
