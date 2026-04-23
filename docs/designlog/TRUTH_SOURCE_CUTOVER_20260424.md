# Truth Source Cutover 2026-04-24

本文件是当前阶段所有线程的**第一真相源**。
当前工作只允许在本文件明确的边界内推进。若与旧实现、旧习惯、旧补丁冲突，以本文件为准。

## 1. 真相源优先级

当前必须严格区分两类真相源，不得混用：

1. workflow 真相源  
   `/root/live-validation/openclaw-for-community/docs/design/newsflow-agentic-workflow-spec-cutover-20260424.md`

2. community / server / runtime / skill 边界真相源  
   `/root/live-validation/myproject/docs/design-facts/COMMUNITY_SKILL_SERVER_BOUNDARY_CUTOVER_20260424.md`

旧文档仍可参考，但出现冲突时，以这两份 cutover 文档为准。

## 2. 当前任务目标

当前只要求先跑通两段：

1. 群组开机流程
2. 内容产出流程

暂不要求以“讨论 / 复盘”作为当前验收目标。

本轮任务目标不是为了通过某一个 workflow 临时打补丁，而是把 community / server / skill 这类底层工具调到能够适应**普遍工作流编排逻辑**。

## 3. 当前最高原则

1. 社区是通讯总线。
2. 阶段内协作主要发生在群组 `text` 对话中。
3. `payload` 只做 formal signal、辅助引用、可选结构化补充，不是主要协作面。
4. `server` 只管阶段门禁、状态推进、上下文状态。
5. `manager` 负责阶段组织、watchdog、最终决策、formal close。
6. `worker / tester / editor` 在阶段内通过对话协作完成生产与审核。
7. `skill` 只做接入、同步、挂载、最小路由与最小封装，不解释 workflow。
8. `runtime` 只做最小义务判断与上下文挂载，不做流程设计器。
9. 除 `server -> manager` 的控制层初始化外，任何 agent 间协作行为都不得在代码里被设计或脚本化。

## 4. 当前调试边界

### 可以直接修改

1. 工具层 bug
   - API base 切换后登录异常
   - session sync / stale token / webhook / queue / mount 错误
   - 前端消息映射错误
   - server formal gate / protocol parsing 的代码 bug

2. workflow 真相源文档
   - 阶段消费链
   - manager 默认行为
   - 阶段失效规则
   - text-first 协作原则

### 不得擅自修改

1. 通过 skill/runtime 硬编码 peer agent 行为
2. 用 regex / 关键词 / 中文短句白名单硬控 agent 说什么
3. 用 skill 替 workflow 解释“谁该先消费谁”
4. 用 payload 命名工件把流程重新做成硬门槛
5. 为单次 newsflow live 测试做一条专用逻辑

## 5. 线程工作制度

所有线程都必须使用本文档作为第一真相源。

### 主线程

- 负责总指挥、问题收敛、集成决策、阶段闸门
- 不得把 workflow 语义硬塞回 skill/server

### 审阅线程

- 每轮必须先审再放行
- 不只审“最新补丁”，还要审“当前累计 working tree 是否越界”
- 审核标准：
  - 是否违反 workflow 真相源
  - 是否违反 community/skill/server 边界真相源
  - 是否出现职责过重
  - 是否出现硬编码 peer 行为

### 记忆线程

- 每轮必须更新
- 不只追加流水账，还要总结整个修复历程
- 必须持续维护：
  - validated changes
  - active blockers
  - 被证伪路径
  - 当前最短 seam

### 测试线程

- 优先做最小动作测试
- 再做 workflow 级联测试
- 每次最小行为测试必须伴随异步审阅与异步记忆
- 测试失败后把 blocker 返回主线程，不擅自改代码

### 施工线程

- 只改自己被分配的文件或模块
- 不得越权改 workflow 设计
- 修复前必须看最新真相源文档

## 6. 测试-审阅-记忆并行制度

每次最小行为测试都必须配套：

1. 一条异步审阅线程
   - 对照最新真相源审代码与测试日志
   - 若发现越界，立即向主线程报告并建议回滚/收缩

2. 一条异步记忆线程
   - 记录本轮测试、修复、证据、结论
   - 持续更新全局复盘文档

这两个线程可以与施工线程并行工作，以提升效率并节约主线程资源。

## 7. 下一阶段执行顺序

1. 以 cutover 文档统一所有线程
2. 基于 cutover 文档与现有底座重构工作逻辑
3. 先做最小动作测试
4. 单 agent 最小动作通过后，再拟合完整 workflow
5. 最终只以“开机流程 + 内容产出流程”成功为当前任务目标
6. 成功后再做一次越界审阅与汇报
