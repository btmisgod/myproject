# Newsflow Protocol Drift Audit 2026-04-24

本文档用于记录当前运行 draft `community/protocols/drafts/newsflow.json` 相对 2026-04-24 cutover 真相源的结构漂移。

参照真相源：

1. `docs/designlog/TRUTH_SOURCE_CUTOVER_20260424.md`
2. `docs/design-facts/COMMUNITY_SKILL_SERVER_BOUNDARY_CUTOVER_20260424.md`
3. `openclaw-for-community/docs/design/newsflow-agentic-workflow-spec-cutover-20260424.md`

## 1. 当前最明显的漂移点

### D1. 没有 bootstrap 阶段，初始阶段仍是 `cycle.start`
当前 `group_session_seed.current_stage = cycle.start`，而 cutover 已要求：
- `step0`
- `step1`
- `step2`
- `formal_start`
是独立 workflow。

影响：
- 开机流程无法作为一级真相源被验证
- manager contract 只能在 `cycle.start` 临时兼容，无法稳定收口

### D2. role_rules 仍把 manager 写得过重
当前 draft 中存在：
- `manager_has_acceptance_duty_for_every_stage = true`
- `tester_may_recommend_transition_but_must_route_via_manager = true`

与 cutover 冲突：
- manager 只应承担 final decision / formal close
- tester 在 collect/review 内应能直接对 worker 发 `pass / partial_pass / redo`

### D3. collect 阶段仍把 `candidate_material_pool` 做成显性输出中心
当前 `material.collect.output = [candidate_material_pool]`。

cutover 要求：
- text-first
- 命名工件只是可选辅助表达，不是默认硬门槛

影响：
- 容易把正文协作降级成工件协作
- 容易让 tester 和 manager 审不同对象

### D4. material.review 仍把阶段内纠错链压到 manager formal close 之下
当前 `material.review.output` 包含：
- `material_review_feedback`
- `manager_stage_close_or_intra_stage_correction`

同时 notes 写着：
- `Partial pass and redo stay inside this stage until manager emits the formal close signal`

cutover 要求：
- tester 可直接对 worker 发 `pass / partial_pass / redo`
- manager 只消费 tester 阶段结论，不做 review loop 中转

### D5. communication_rules 仍允许过宽的 direct coordination
当前包含：
- `same_stage_peer_coordination_allowed = true`
- `explicit_target_rule.required_when_directing_to_specific_agent = true`

这会让实现层很容易把 collect/review 阶段做成广域 peer 协调，而不是收敛到 `worker -> tester -> manager` 主链。

### D6. 阶段失效规则没有被显式写进 draft
cutover 要求：
- 阶段推进后旧消息默认保留可见性但失去行动性
- 只有显式 `redo / resume / reopen` 才能重激活旧阶段

当前 draft 没把这条作为一级规则写入 execution/protocol。

### D7. 当前 draft 的验收目标仍覆盖过多尾段
当前 stage_order 仍覆盖：
- discussion
- retrospective
- optimization
- self_optimize

cutover 当前任务目标只要求：
- 开机流程
- 内容产出流程

影响：
- 调试范围过宽
- 容易把尾段问题误当成当前主 blocker

### D8. manager responsibility 仍带大量阶段内编排和回顾职责
当前 `role_assignments.manager.responsibility` 包含：
- task decomposition
- stage dispatch
- stage acceptance
- formal transition
- retrospective
- next-cycle optimization prompts

这不是错，但对当前阶段而言太宽。cutover 需要先把 manager 收回到：
- 开阶段
- 发起任务
- watchdog
- final decision
- formal close

### D9. tester 的正式职责仍表述成“recommend but not directly emit formal transition”
这句话本身没错，但缺少 cutover 强调的更强描述：
- tester 是 collect 阶段第一消费者
- tester 直接对 worker 发 pass/partial_pass/redo
- manager 只消费 tester 阶段结论

### D10. 决策模型仍围绕 count/forced proceed 形式表达，缺少“最终消费者”视角
当前 `decision_model` 更像 stage 内计数/升级逻辑。
cutover 更强调：
- 阶段内由最终消费者直接消费和纠错
- manager 基于最终消费者结论决定 proceed / forced_proceed / pause / fail / resume

## 2. 必须优先修的漂移点

当前 Phase A 必须先处理：

1. D1 bootstrap 缺失
2. D2 manager 过重
3. D3 collect 工件做重
4. D4 tester direct review loop 被压扁
5. D6 阶段失效规则缺失

## 3. 当前可以延后的问题

以下问题可在开机 + 内容产出稳定后再收：

1. D7 尾段 stage_order 过宽
2. retrospective / optimization 的细节责任划分
3. product.report 与尾段阶段的进一步精炼

## 4. 建议的 Phase A 处理方式

1. 不在旧 draft 上继续零碎打补丁。
2. 先把 bootstrap + content-output 需要的最小协议语义单独重建。
3. 保留 server formal gate 所需结构，但收紧：
   - bootstrap
   - cycle.start
   - material.collect
   - material.review
   - draft.compose
4. 其余尾段后置，不作为当前验收路径。

## 5. 当前结论

当前 `newsflow.json` 不是完全不可用，但已经明显偏离了 2026-04-24 的 cutover 设计。当前最稳妥的方向不是继续在旧 draft 上增量补丁，而是：

- 以 cutover 文档为真相源
- 重建一份面向“开机 + 内容产出”的更薄 draft
- 先用最小行为测试证明该 draft 的协作逻辑正确
- 再回归 live workflow
