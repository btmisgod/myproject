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

## 4. 当前建议的最小实现

如果需要进入 Batch 2，当前建议的最小实现只有：

1. 在 `community_integration.mjs` 中新增 `GROUP_SESSION_PATH`
2. 新增 `loadGroupSession(state, groupId, session = null)`
3. 在 `receiveCommunityEvent(...)` 传给 runtime 的 adapter 中加入 `loadGroupSession`
4. 如仍不足，再允许接入 `resolveGroupSessionObligation(...)`，但只用于 `server -> manager` control turn

## 5. 验收标准

Batch 2 完成后，至少应能回答：

1. `group_session.updated` 是否被正确消费并持久化
2. manager 是否能基于 server->manager 初始化进入正确阶段组织
3. worker/tester 是否仍然只通过群组对话协作，而不是被工具层脚本化
4. 最小主验收链是否因此稳定通过

## 6. 审阅要求

任何 Batch 2 代码改动前后，都必须经过审阅线程复核：

1. 这次补丁是否仍停留在工具层
2. 是否把 workflow 解释权重新塞回了 skill/runtime
3. 是否新增了 peer 行为硬编码
