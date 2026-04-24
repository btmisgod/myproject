# Minimal Acceptance Chain 2026-04-24

本文件不是新的总体真相源，而是对以下 cutover 真相源的**当前主验收收口**：

1. `docs/designlog/TRUTH_SOURCE_CUTOVER_20260424.md`
2. `docs/design-facts/COMMUNITY_SKILL_SERVER_BOUNDARY_CUTOVER_20260424.md`
3. `openclaw-for-community/docs/design/newsflow-agentic-workflow-spec-cutover-20260424.md`
4. `community/protocols/drafts/newsflow.json`

若与上述文档冲突，以上述文档为准。

## 1. 当前主验收

当前只验收一条最小主链：

1. `step0 -> step1 -> step2 -> formal_start` 成功完成
2. `cycle.start` 成功完成
3. 进入 `material.collect`
4. 群组时间线中出现**至少一条真实正文内容**

这里的“真实正文内容”必须同时满足：
- 来自 agent/LLM 的可见群组 `text`
- 不是本地模板拼装
- 不是 fallback 文案
- 不是纯 ACK/确认/等待/知悉
- 不是只存在于 `payload` 的结构化空壳

## 2. 当前不作为主验收的内容

以下内容当前仍重要，但不作为本轮最小通过标准：
- collect 全量收齐
- manager 最终 close 完整稳定
- draft.compose 之后的所有阶段
- 讨论/复盘/优化阶段

## 3. 失败判定

出现以下任一情况，本轮不能算通过：
- bootstrap 没完成
- formal_start 没完成
- 没进入 `material.collect`
- 只出现模板化/空心/控制层噪音消息，没有真实正文内容
- 真实内容只存在于 `payload`，群组 `text` 中不可见

## 4. 目的

这个最小主验收的目的不是缩小设计边界，而是先验证底层工具链是否满足：
- server 能推进
- skill 能正确消费社区消息
- skill 能正确输出 server 可消费内容
- runtime 能把群组和阶段上下文正确挂给 agent
- agent 能在群组正文中产出真实内容

只有这条主链稳定后，才继续扩大到完整内容产出流程与后续阶段。
