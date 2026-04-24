# Implementation Batch 1 2026-04-24

本文件基于当前 cutover 真相源与 active draft，定义第一批实现变更的范围。

## 1. 前置结论

### 1.1 当前 `server` 侧主 seam

`app/services/group_session.py` 的阶段引擎已经能够通用消费：
- `initial_stage`
- `accepted_status_blocks`
- `completion_condition`
- `next_stage`

当前没有证据表明第一批实现应先重做 server gate engine。

### 1.2 当前 `skill/runtime` 侧主 seam

`community-runtime-v0.mjs` 当前仍然过于扁平：
- 只把 `workflow_contract / group_context / status` 视为 context update
- 还没有把 `group_session`、`group_context`、`workflow_contract` 收成统一挂载链
- obligation 仍主要依赖 `targeted / mentioned / visible collaboration`
- 这不足以支撑 cutover 后的 bootstrap + content-output 工作逻辑

### 1.3 当前 `skill` 不应做的事

本批实现明确禁止：
- 编码 peer 行为脚本
- 在 skill/runtime 里解释 workflow 阶段内协作
- 使用自然语言黑名单/白名单压噪音
- 通过更多 `observe_only` 规则充当主修法

## 2. Batch 1 目标

只解决以下问题：

1. `skill` 正确消费 server 语义
2. `skill` 正确挂载群组/阶段/身份上下文
3. `skill` 正确输出 server 可消费的 formal control message
4. agent 在群组 `text` 中产出真实正文内容

## 3. Batch 1 范围

### 3.1 Runtime 输入收口

把以下输入统一纳入 context-mount 范围：
- `group_session.updated`
- `group_context`
- `workflow_contract`

要求：
- 这些输入默认不直接生成 peer 行为
- 这些输入只更新当前群组对应的 mounted context
- 同一 agent 在多个群组并发收到消息时，必须能按 group_id 挂对上下文

### 3.2 Runtime 最小义务判断

保持最小义务判断，但只做：
- 当前消息属于哪个群组
- 当前消息是否 directed to self
- 当前消息是否只是 context update
- 当前 stage 是否已变化，旧 stage 消息是否失行动性

不做：
- peer 行为脚本化
- collect/review 的细粒度协作塑形

### 3.3 Skill 出站约束

出站只保证：
- `text-first`
- formal close 时带 manager `status_block`
- 不把命名工件当硬门槛
- 不向 peer 行为注入模板

### 3.4 Server->Manager 初始化

本批实现允许强化：
- `server -> manager` 的 group-level immutable manager contract
- bootstrap / cycle.start 的 manager 初始化挂载

本批实现禁止强化：
- `server -> worker/tester/editor` 行为脚本
- skill 对 peer 行为的补充 prompt

## 4. 本批最小测试

### Test A
- bootstrap `step0 -> step1 -> step2 -> formal_start`
- manager 通过 mounted contract 组织 bootstrap
- 非 manager 响应来自群组消息 + mounted context

### Test B
- `cycle.start -> material.collect`
- 至少一条真实正文内容出现在群组 `text`
- 不是 payload-only，不是 ACK，不是模板

### Test C
- stage advance 后，旧阶段消息默认失行动性
- 只有显式 `redo / resume / reopen` 才能重新激活旧阶段

## 5. 成功标准

Batch 1 通过时，至少要满足：
- manager 能完成 bootstrap 与 cycle.start 组织
- 能进入 `material.collect`
- 至少出现一条真实正文内容
- 没有新增 peer 脚本化逻辑
- 审阅线程确认没有边界越界

## 6. 不在本批解决的问题

以下内容暂不纳入 Batch 1：
- collect 全量收齐
- tester direct review loop 全链闭环
- draft.compose 之后的全部阶段
- 讨论 / 复盘 / 优化
