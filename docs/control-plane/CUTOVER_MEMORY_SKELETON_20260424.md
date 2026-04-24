# Cutover Memory Skeleton 2026-04-24

本文件不是新的总体真相源，而是对当前 cutover 阶段的**一级记忆**与**轮次记录骨架**进行固化。

## 1. 全局总结

本轮先做 `truth source cutover`，再重建最小行为测试，是为了把两类真相彻底拆开：

1. `workflow` 真相源
2. `community / skill / server / runtime` 边界真相源

如果不先做这一步，后续测试会把旧补丁、旧脚本化习惯、旧工件门槛一起带入，继续放大漂移。

本轮主验收先收口到最小链：

1. `step0 -> step1 -> step2 -> formal_start` 完成
2. `cycle.start` 完成
3. 进入 `material.collect`
4. 群组时间线中出现至少一条真实正文 `text`

这条主验收优先于：
- collect 全量收齐
- manager 全尾段收口
- `draft.compose` 之后阶段
- 讨论 / 复盘 / 优化

## 2. 一级记忆

1. `workflow` 真相源与 `community / skill / server / runtime` 边界真相源分离，禁止混写。
2. 唯一允许的编码型协助边界是 `server -> manager` 初始化；不得扩展成 peer 行为脚本。
3. `text-first`；`payload` 只承载 formal signal、辅助引用、可选结构化补充。
4. `collect` 主链固定为 `worker -> tester -> manager`。
5. 阶段推进后旧消息默认保留可见性，但失去行动性；只有显式 `redo / resume / reopen` 可重激活。
6. 当前最小主验收要求群组 `text` 中出现至少一条真实正文内容；`payload` 空壳、模板文案、fallback、纯 ACK 都不算通过。

## 3. 当前轮 Memory 模板

### 3.1 轮次主验收
- 目标链：`step0 -> step1 -> step2 -> formal_start -> cycle.start -> material.collect`
- 最小通过证据：群组时间线出现至少一条真实正文 `text`
- 当前非主验收：collect 全量收齐、manager 最终全尾段 close、`draft.compose` 之后阶段、讨论 / 复盘 / 优化

### 3.2 A / bootstrap
- 目标：建立群启动面、角色边界、readiness，不产出业务正文。
- 记录：`step0 / step1 / step2 / formal_start` 当前状态、manager kickoff 证据、非 manager 对齐证据、ready 或 blocker、manager formal close。
- 边界：非 manager 的响应来源应是群消息加挂载上下文，不是 direct server script。
- 失败信号：bootstrap 未闭合、manager 越权脚本化 peer、非 manager 只回模板确认。

### 3.3 B / collect
- 目标：进入 `material.collect` 后，验证 `worker -> tester -> manager` 主链和真实正文出现。
- 记录：worker 首批 concrete material / concrete blocker、tester 的 `pass / partial_pass / redo`、manager watchdog / final decision、真实正文出现时间点。
- 边界：tester 是第一消费者；manager 默认静默，不做 first-pass review；命名工件不是硬门槛。
- 失败信号：只有 ACK、正文只在 `payload`、manager 变成过程细审或中转站、worker 绕过 tester 直交 manager。

### 3.4 C / stage-supersession
- 目标：记录阶段推进后的失行动性是否成立。
- 记录：当前 active stage、被 supersede 的旧消息、是否出现跨阶段噪音、是否发生 `redo / resume / reopen`、重激活后的目标阶段与消费链。
- 默认规则：旧消息可见但不可继续驱动执行；引用旧消息也不自动 reopen。
- 失败信号：旧阶段消息自然续命、跨阶段继续触发回复、reopen 后消费链混线。

### 3.5 审阅 findings 记录框架
- `Finding ID`
- `来源类型`：workflow truth / boundary truth / minimal acceptance / drift audit / protocol draft
- `命中的一级记忆`
- `触发证据`
- `对主验收的影响`
- `裁定`：`pass / fail / defer / superseded`
- `supersession 说明`
- `需要补的最小测试`
- `下一动作`：修文档 / 修 contract / 修初始化 / 修工具层 / 仅留审计
