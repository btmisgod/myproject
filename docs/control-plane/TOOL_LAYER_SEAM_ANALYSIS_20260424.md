# Tool Layer Seam Analysis 2026-04-24

本文档只分析当前 cutover 后的工具层 seam，不重新讨论 workflow 设计本身。

## 1. 当前判断

### 1.1 Server stage engine

`app/services/group_session.py` 当前已经能通用消费：
- `initial_stage`
- `accepted_status_blocks`
- `completion_condition`
- `next_stage`

因此 Batch 1 / Batch 2 都不应先重写 server gate engine。

### 1.2 当前第一批 seam

第一批最可能影响 cutover workflow 的 seam 在 `skill/runtime`：
- server 的 `group_session / group_context / workflow contract` 语义没有在 skill/runtime 里收成统一挂载链
- runtime 当前的 obligation 仍主要基于：
  - `targeted_to_self`
  - `mentioned_to_self`
  - `visible_collaboration`
- 这不足以稳定支撑：
  - bootstrap
  - manager contract
  - text-first collect 链
  - old-stage actionability loss

## 2. 已确认事实

### 2.1 Server 侧

`app/services/group_session.py` 里的 `_evaluate_current_stage(...)` 和 `_apply_stage_engine(...)` 已经是通用 gate 计算器。

### 2.2 Group context endpoint

`app/services/community.py:get_group_context(...)` 当前返回：
- `group_context(group)`
- `group_session: build_group_session_view(group)`

这意味着 canonical `/groups/{id}/context` 已经能同时提供：
- `group_context`
- `group_session`

因此当前最小工具层问题不是“server 没有 truth”，而是“runtime/integration 是否真正回拉并挂上了 canonical truth”。

### 2.3 Runtime 侧当前最轻修法

对 `group_session.updated` 而言：
- 如果 integration 已实现 `loadGroupSession(...)`，就直接走 dedicated session mount
- 如果 integration 还没有 dedicated session loader，则不应把事件自带的 partial `group_context` sync view 直接持久化为完整上下文
- 更轻的 fallback 是：强制走一次 canonical `/groups/{group_id}/context` 回拉，由现有 `loadGroupContext(...)` 挂完整 `group_context + group_session`

## 3. 当前最短 seam 排序

### 3.1 排序

1. `server -> manager` 的 `bootstrap / cycle.start` 初始化链
2. `old-stage actionability loss`
3. `collect` 阶段 `tester first consumption`

### 3.2 原因

- `collect` 的消息面在 active draft 里已经被显式写成 `worker -> tester -> manager`，并且 text-first visible evidence 规则也已收紧，所以它更像二级 seam。
- `old-stage actionability loss` 已经在真相源里作为一级规则存在，但还需要 runtime/context mount 链稳定后才能真实验证，因此排第二。
- 当前最容易直接阻断主链的是 `bootstrap / cycle.start` 初始化：如果 manager 没有通过 canonical session/context mount 拿到正确的当前 stage、gate snapshot、manager control turn，就算 collect 设计对，工作流也起不来。

## 4. 当前实现方向

### 4.1 不做的事

- 不新增 peer 行为脚本
- 不新增 workflow-specific prompt 规则
- 不把 `observe_only` 作为主要修法
- 不重写 server gate engine

### 4.2 要做的事

1. 统一 skill/runtime 的 context mount 输入面：
   - `group_session.updated`
   - `group_context`
   - `workflow_contract`

2. 保证 `group_session.updated` 在没有 dedicated session loader 时，至少能回拉 canonical context：
   - `group_context`
   - `group_session`

3. 保持出站最小化：
   - `text-first`
   - formal close 由 manager 带 `status_block`
   - 不把命名工件升级成硬门槛

## 5. 当前最需要警惕的越界点

1. 不能让 runtime 读取 `group_session.current_stage / gate_snapshot / workflow_contract` 后，开始自行推导 peer 行为顺序。
2. 不能把 `manager_control_turn` 从一次性 `server -> manager` 初始化，扩成持续编排器。
3. 不能让测试开始断言 collect/review 的具体 peer 话术、顺序或模板，否则会把 workflow 语义硬编码回代码。

## 6. 当前通过标准

- bootstrap 能通过
- `cycle.start` 能通过
- manager 能基于 `manager_control_turn + canonical context` 进入正确 deliberation
- 能进入 `material.collect`
- 至少出现一条真实正文内容
- 不新增 peer 脚本化逻辑
