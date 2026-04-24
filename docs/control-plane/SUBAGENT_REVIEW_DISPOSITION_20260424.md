# Subagent Review Disposition 2026-04-24

本文档记录 2026-04-24 在 cutover 重构阶段，对子线程审阅结论的采纳边界。

## 1. 采纳原则

只有同时满足以下条件的子线程结论才可采纳：

1. 仅基于当前第一真相源：
   - `docs/designlog/TRUTH_SOURCE_CUTOVER_20260424.md`
   - `docs/design-facts/COMMUNITY_SKILL_SERVER_BOUNDARY_CUTOVER_20260424.md`
   - `openclaw-for-community/docs/design/newsflow-agentic-workflow-spec-cutover-20260424.md`
2. 不得引入额外未授权文档作为主锚点。
3. 不得引入与 cutover 当前范围无关的新目标。
4. 不得把 skill/server/runtime 重新扩张成 workflow 解释器。

## 2. 本轮不采纳的子线程结论类型

以下类型一律不采纳：

1. 引用了未在当前 cutover 范围内的其它文档，尤其是：
   - 其它分支上的旧 spec
   - 未在当前任务中授权成为第一真相源的工程文档
2. 引入了与当前任务范围无关的新验收目标，尤其是把尾段 workflow 再次扩张回当前范围。
3. 引入了与当前 cutover 设计不一致的新物件、新脚本位、新 bootstrap 常驻文件语义。
4. 把 peer 行为重新脚本化、模板化，或要求 skill/server/runtime 去解释 peer 协作。

## 3. 本轮仍然采纳的结构审阅结论

当前仍采纳并作为主线推进的结论：

1. bootstrap 需要独立 workflow 建模。
2. manager contract 必须在建群时确定，并由 server 只向 manager 提供初始化。
3. collect 阶段必须收回到 `worker -> tester -> manager`。
4. tester direct `pass / partial_pass / redo` 是当前 collect/review 主链的一部分。
5. 阶段推进后，旧阶段消息默认保留可见性但失去行动性。
6. 只有显式 `redo / resume / reopen` 才能恢复旧阶段行动性。
7. `text-first` 是一级约束，命名工件不是默认硬门槛。

## 4. 当前主草稿

当前 Phase A 的主草稿是：

- `community/protocols/drafts/newsflow-bootstrap-content-cutover-v3.json`

后续最小行为测试默认围绕该草稿展开，直到它被新的 cutover 真相源正式替代。
