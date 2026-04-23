# Workflow Rebuild Plan 2026-04-24

本文档不是新的真相源，而是基于以下三份 cutover 真相源形成的执行计划：

1. `docs/designlog/TRUTH_SOURCE_CUTOVER_20260424.md`
2. `docs/design-facts/COMMUNITY_SKILL_SERVER_BOUNDARY_CUTOVER_20260424.md`
3. `openclaw-for-community/docs/design/newsflow-agentic-workflow-spec-cutover-20260424.md`

若与上述三份文档冲突，以 cutover 真相源为准。

## 1. 当前目标

当前只验收两条主链：

1. 群组开机流程
2. 内容产出流程

暂不把讨论 / 复盘作为当前验收目标。

## 2. 执行原则

1. 先修文档和契约，再修 server -> manager 初始化，再修 skill/server 工具层 bug。
2. 不得通过 skill/runtime/server 编码 peer agent 协作行为。
3. 只能允许 `server -> manager` 的控制层初始化更明确。
4. 所有阶段内协作以 `text` 为主，`payload` 只做辅助。
5. 阶段推进后，旧阶段消息默认只保留可见性，不再保留行动性；只有显式 `redo / resume / reopen` 才能重激活。
6. 每个最小行为测试必须伴随一条异步审阅线程和一条异步记忆线程。
7. 只在工具层 bug 确认后才允许修改 skill/server。

## 3. 施工顺序

### Phase A 文档与契约收紧

目标：先把工作逻辑写对，不先在代码里打补丁。

包含：
- bootstrap / manager contract
- collect 链 `worker -> tester -> manager`
- tester direct `pass / partial_pass / redo`
- manager 默认静默 + watchdog + final decision
- 阶段推进后旧消息失效规则
- `redo / resume / reopen` 唯一重激活路径
- text-first 协作原则

### Phase B manager 初始化与控制层收口

目标：只增强 `server -> manager` 初始化，不扩大 peer 行为编码。

包含：
- manager contract 组装
- bootstrap 的 step0/step1/step2/formal_start 初始化
- cycle.start 初始化
- 当前阶段 manager 责任的最小控制层挂载

不包含：
- worker/tester/editor 话术模板
- peer 协作脚本

### Phase C skill/server 工具层 bug 修复

只在 A/B 明确后处理：
- API base drift / stale token / session sync
- webhook / queue / mount
- authoritative session/protocol truth
- text transport completeness
- 旧阶段消息 actionability 的最小支持

### Phase D 最小行为测试

先过最小行为测试，再做完整 workflow 联测。

### Phase E workflow 联测

目标只限：
- 群组开机流程
- 内容产出流程

## 4. 最小行为测试矩阵

### Test A bootstrap / manager kickoff

验证：
- server 只向 manager 提供 bootstrap 控制层初始化
- manager 能自然拉起 step0 -> step1 -> step2 -> formal_start
- 非 manager 响应来自群消息与挂载上下文，不是 peer 脚本

通过标准：
- authoritative stage 正确推进
- manager 只做开机组织/收口，不脚本化 peer 行为

### Test B collect 消费链

验证：
- manager 发 collect kickoff
- worker 向 tester 直接提交正文素材
- tester 直接对 worker 发 `pass / partial_pass / redo`
- manager 只消费 tester 结论并做 final decision

通过标准：
- collect 阶段主链稳定为 `worker -> tester -> manager`
- text-first 成立
- manager 不做过程细审

### Test C 阶段失效与跨阶段静默

验证：
- 阶段推进后，旧阶段消息默认失行动性
- 只有显式 `redo / resume / reopen` 才能重激活旧阶段
- 跨阶段噪音明显下降

通过标准：
- 旧消息仍可见，但不会自然继续驱动旧阶段行为
- reopen 后恢复正确消费链，而不是混线

## 5. 线程编排

### 主线程
- 负责总指挥、阶段闸门、最终整合。

### 审阅线程
- 每轮必须检查：
  - 最新改动是否越界
  - 累计 working tree 是否已经偏离 cutover 设计

### 记忆线程
- 每轮都要更新：
  - validated changes
  - active blockers
  - false paths
  - current shortest seam

### 测试+施工线程 A
- 主题：bootstrap / manager contract / server->manager initialization

### 测试+施工线程 B
- 主题：collect 链 / text-first / tester direct review loop

### 测试+施工线程 C
- 主题：阶段失效 / redo-resume-reopen / 跨阶段静默

## 6. 回滚点

1. 只改文档与契约：可独立回滚。
2. 只改 manager contract / 初始化：可独立回滚。
3. skill/server 工具层 bug 修复：按具体模块回滚。

## 7. 当前验收定义

只有同时满足以下条件，才算本轮任务通过：

1. 开机流程稳定通过
2. collect 内容生产链稳定通过
3. manager 只基于 tester 结论做门禁
4. 旧阶段消息不再跨阶段继续驱动回复
5. 没有把 skill/server 变成 workflow 解释器
6. 审阅线程给出边界通过结论
7. 记忆线程完成本轮与全局总结更新
