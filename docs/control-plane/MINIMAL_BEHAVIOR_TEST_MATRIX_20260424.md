# Minimal Behavior Test Matrix 2026-04-24

本文档不是新的总体真相源，而是基于以下真相源抽出的最小行为测试矩阵：

1. `docs/designlog/TRUTH_SOURCE_CUTOVER_20260424.md`
2. `docs/design-facts/COMMUNITY_SKILL_SERVER_BOUNDARY_CUTOVER_20260424.md`
3. `openclaw-for-community/docs/design/newsflow-agentic-workflow-spec-cutover-20260424.md`
4. `community/protocols/drafts/newsflow.json`
5. `docs/control-plane/MINIMAL_ACCEPTANCE_CHAIN_20260424.md`

若与上述文档冲突，以上述文档为准。

## 1. 当前目标

当前最小目标不是跑完整 workflow，而是先逐个验证：

1. server 能正确发出可消费的控制层语义
2. skill/runtime 能正确消费控制层语义并挂载上下文
3. manager 能基于 server->manager 初始化建立阶段组织
4. worker/tester 能在群组正文中完成最小协作动作
5. manager 能基于 tester 结论做 formal close

## 2. 测试分层

### Layer A: 工具层最小动作

1. `group_session.updated` 到达后，runtime 能正确识别为 `group_session`
2. `group_context` / `workflow_contract` 能正确挂载到对应群组
3. agent 同时收到两个不同群组消息时，上下文不串
4. `server -> manager` 控制层初始化不会变成 peer 行为脚本
5. `text-first` 协作面不被 `payload-only` 取代

### Layer B: 单阶段协作最小动作

1. manager 发起 bootstrap kickoff
2. 非 manager 角色完成 step1 对齐回复
3. 非 manager 角色完成 step2 ready / blocker 回复
4. manager formal_start
5. manager 在 `cycle.start` 发出任务拆解与 collect 组织面
6. worker 在 `material.collect` 以群组正文提交 concrete material 或 concrete blocker
7. tester 作为第一消费者直接对 worker 发 `pass / partial_pass / redo`
8. manager 基于 tester 结论决定是否 `formal close`

### Layer C: 阶段失效与回流最小动作

1. 阶段推进后，旧阶段消息默认保留可见性但失去行动性
2. 只有显式 `redo / resume / reopen` 才能重新激活旧阶段
3. 旧阶段消息的 reply/quote 不自动 reopen 阶段
4. collect 阶段关闭后，worker 不再自然延续 collect 噪音

## 3. 单动作测试清单

### A1. Bootstrap kickoff
- Actor: manager
- Trigger: `step0` server->manager 初始化
- Expectation:
  - manager 在群组正文建立 kickoff surface
  - 内容包含群目标、角色结构、bootstrap 概览
- Failure:
  - 只发 payload / status，不发正文
  - manager 不起手

### A2. Step1 alignment
- Actor: non-manager roles
- Trigger: manager step0 kickoff + mounted context
- Expectation:
  - 每个非 manager 角色都有一条正文对齐回复
  - 体现任务理解与角色边界
- Failure:
  - 只有 ACK / ready，没有任务理解

### A3. Step2 readiness
- Actor: non-manager roles
- Trigger: manager readiness collection message + mounted context
- Expectation:
  - 每个非 manager 角色发 `task_ready` 或 `task_blocked`
  - 由正文表达 readiness/blocker
- Failure:
  - readiness 只存在于 payload
  - manager 代替非 manager 发 readiness

### B1. Cycle-start task decomposition
- Actor: manager
- Trigger: `formal_start` completed
- Expectation:
  - manager 发 group-visible text，说明 collect 阶段任务、分工、tester 第一消费、最终门禁边界
- Failure:
  - 只发 formal close，不发可读组织面

### B2. Worker concrete material submission
- Actor: worker_a / worker_b
- Trigger: cycle-start collect organization
- Expectation:
  - 至少一条 worker 群组正文是 concrete material 或 concrete blocker
  - 不是纯 ACK / 等待 / 确认
- Failure:
  - 只发 ACK
  - 只在 payload 中有内容
  - 总结 peer 进度替代提交自己的 material

### B3. Tester first consumption
- Actor: tester
- Trigger: worker concrete material submission
- Expectation:
  - tester 直接对 worker 发 `pass / partial_pass / redo`
  - collect 阶段中 tester 是第一消费者
- Failure:
  - manager 先消费 worker 提交
  - tester 只对 manager 说话，不直接对 worker 反馈

### B4. Manager final decision
- Actor: manager
- Trigger: tester stage conclusion
- Expectation:
  - manager 基于 tester 结论做 proceed / forced_proceed / pause / fail / resume
  - manager formal close 之前不做 collect 过程细审
- Failure:
  - manager 逐条消费 collect 原稿
  - manager 抢 tester 的第一审核职责

### C1. Old-stage loss of actionability
- Actor: any
- Trigger: stage advance
- Expectation:
  - 旧阶段消息仍可见，但不再自然驱动回复
- Failure:
  - collect 已关闭，worker/tester 继续自然补 collect

### C2. Explicit redo/resume/reopen
- Actor: tester or manager
- Trigger: explicit control message
- Expectation:
  - 只有显式 `redo / resume / reopen` 才重新激活旧阶段
- Failure:
  - 旧消息 quote/reply 自动 reopen

## 4. 当前主验收收口

当前代码层和 live 联测仍先收这条主链：

1. `step0 -> step1 -> step2 -> formal_start`
2. `cycle.start`
3. 进入 `material.collect`
4. 至少一条真实 visible text concrete material submission
5. tester 作为第一消费者直接消费这条提交

## 5. 当前不作为主验收的内容

以下内容后续继续做，但不是本轮第一收口：

1. 完整 `material.review`
2. `draft.compose` 之后的后续阶段
3. 讨论 / 复盘 / 优化
4. 任意命名工件是否存在

## 6. 使用方式

后续每轮改动都应先回答：

1. 这轮改动影响哪几个最小动作？
2. 对应最小动作测试是否应先过？
3. 如果最小动作不过，是否还应该继续跑整条 workflow？

答案原则：
- 最小动作不过，不应先跑长链 live
- 先修最小动作，再进联测
