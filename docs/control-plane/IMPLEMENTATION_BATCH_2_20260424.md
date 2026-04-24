# Implementation Batch 2 2026-04-24

本文档定义 **Batch 2** 的最小工具层补丁边界。它不是授权立即改代码，而是当 Batch 1 最小主验收仍不过时，允许采用的最小工具层修复方案。

## 1. 前提

仅当以下判断成立时，才进入 Batch 2：

1. workflow 真相源与 active draft 已经足够表达当前最小主验收语义
2. 仍无法稳定通过 `bootstrap -> cycle.start -> material.collect -> 至少一条真实 visible text concrete material submission`
3. blocker 被确认在 `integration/runtime` 对 server 语义的消费与挂载链，而不是 workflow 语义本身

## 2. 允许的补丁边界

Batch 2 只允许做以下三类改动：

1. 正确消费 `group_session` 并按 group 持久化
2. 正确把 `group_session / group_context / workflow_contract` 挂到 agent 的 runtime 上下文
3. 为 `server -> manager` 的控制层初始化提供 opt-in hook

## 3. 明确禁止

Batch 2 明确禁止：

1. peer agent 行为脚本
2. worker/tester/editor 回复模板
3. 基于 regex/关键词的 peer 行为硬编码
4. 用工具层解释“谁该先消费谁、谁该怎么说”的 workflow 逻辑
5. 把命名工件升格为 send-time 硬门槛
6. 用 `observe_only` 当主要噪音治理手段

## 4. 当前选定的最小实现路径

本轮实际选定的 Batch 2 最小补丁路径是：

1. server 在 `group_session` declaration/view 中显式暴露：
   - `manager_agent_ids`
   - `manager_control_turn`
2. `manager_control_turn` 只表达显式 `server -> manager` 控制层门禁信号，不表达任何 peer 行为脚本
3. runtime 内建最小消费：
   - 当前 agent 在 `manager_control_turn.required_agent_ids` 中时，判定为 `required`
   - 同一 `turn_id` 做最小去重
4. 这条 built-in runtime 行为只服务于 manager control-turn，不得扩展成 worker/tester/editor 的行为解释器

## 5. 当前仍未进入的扩展路径

以下路径目前仍然属于 **后续 seam**，不是这轮最小补丁的直接目标：

1. `community_integration.mjs` 内完整的 `group_session` 持久化与 catch-up 回填
2. 基于 `group_session` 的更丰富 runtime context card
3. 任何 peer 阶段行为的工具层路由解释

## 6. 验收标准

Batch 2 完成后，至少应能回答：

1. `group_session.updated` 是否被正确消费并挂载为 `server -> manager` 控制层门禁信号
2. manager 是否能基于显式 `manager_control_turn` 进入正确的 bootstrap / cycle.start deliberation
3. worker/tester 是否仍然只通过群组对话协作，而不是被工具层脚本化
4. 最小主验收链是否因此更稳定地通过 `bootstrap -> cycle.start -> material.collect`

## 7. 审阅要求

任何 Batch 2 代码改动前后，都必须经过审阅线程复核：

1. 这次补丁是否仍停留在工具层
2. 是否把 workflow 解释权重新塞回 skill/runtime
3. 是否新增了 peer 行为硬编码
4. 是否把 `manager_control_turn` 扩展成了 peer 编排器
