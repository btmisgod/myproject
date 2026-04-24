# Tool Layer Seam Analysis 2026-04-24

本文件只分析当前 cutover 后的工具层 seam，不重新讨论 workflow 设计本身。

## 1. 当前判断

### 1.1 Server stage engine

`app/services/group_session.py` 当前已经能通用消费：
- `initial_stage`
- `accepted_status_blocks`
- `completion_condition`
- `next_stage`

因此 Batch 1 不应先重写 server gate engine。

### 1.2 当前第一批 seam

第一批最可能影响 cutover workflow 的 seam 在 `skill/runtime`：
- server 的 `group_session` / `group_context` / `workflow contract` 语义还没有在 skill/runtime 里收成统一挂载链
- runtime 当前的 obligation 仍主要基于：
  - `targeted_to_self`
  - `mentioned_to_self`
  - `visible_collaboration`
- 这不足以稳定支撑：
  - bootstrap
  - manager contract
  - text-first collect 链
  - old-stage actionability loss

## 2. 证据

### 2.1 Server 侧

`app/services/group_session.py` 里的 `_evaluate_current_stage(...)` 和 `_apply_stage_engine(...)` 已经是通用 gate 计算器。

### 2.2 Runtime 侧

`community-runtime-v0.mjs` 当前只把以下输入显式视为 context update：
- `workflow_contract`
- `group_context`
- `status`

而当前 cutover 需要的最小输入链应当至少覆盖：
- `group_session.updated`
- `group_context`
- `workflow_contract`

## 3. Batch 1 实现方向

### 3.1 不做的事

- 不新增 peer 行为脚本
- 不新增 workflow-specific prompt 规则
- 不把 `observe_only` 作为主要修法
- 不重写 server gate engine

### 3.2 要做的事

1. 统一 skill/runtime 的 context mount 输入面：
   - `group_session.updated`
   - `group_context`
   - `workflow_contract`

2. 让 runtime 在 group 维度维护 mounted context：
   - 当前 group 的 session
   - 当前 group 的 contract
   - 当前 group 的 stage
   - 当前 agent 在该 group 的 role 视图

3. 保持出站最小化：
   - `text-first`
   - formal close 由 manager 带 `status_block`
   - 不把命名工件升级成硬门槛

## 4. Batch 1 通过标准

- bootstrap 能通过
- `cycle.start` 能通过
- 能进入 `material.collect`
- 至少出现一条真实正文内容
- 不新增 peer 脚本化逻辑
