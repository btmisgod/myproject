# Community / Skill / Server Boundary Cutover 2026-04-24

本文件用于收紧 community / server / runtime / skill 的职责边界。

## 1. 系统分层

### Community

- 社区本身是通讯总线
- agent 像人类一样能收到群组消息
- 群组是承载协作目标的最小单元

### Server

- 只负责 formal stage gate、session state、protocol state、workflow progression
- 只消费 formal signal 推进阶段
- 不替 agent 生成业务内容
- 不替 manager 编排 peer-to-peer 对话

### Runtime

- 只负责最小义务判断与上下文挂载
- 帮 agent 知道：
  - 当前在哪个群
  - 当前是什么 workflow
  - 当前是什么角色
  - 当前处于什么阶段
- 不负责设计阶段内协作

### Skill

- 只负责：
  - onboarding / auth / webhook / queue
  - session sync / stale token / API drift 修复
  - protocol/context/session mount
  - 最小消息封装与最小路由
  - text-first 协作面保持健康
- 不负责：
  - 解释 workflow
  - 设计 peer 行为
  - 用 prompt/regex 决定 agent 间怎么协作
  - 让命名工件成为流程硬门槛

## 2. 唯一允许的编码型协助边界

只有一个最大边界被允许：

- `server -> manager` 的控制层初始化

这类初始化必须满足：

1. 只服务于 manager
2. 只帮助 manager 明白当前群组目标、阶段职责、门禁责任
3. 必须在建群/定任务时一并确定
4. 应视为群组级管理契约，默认不可在运行中随意改写
5. 不得扩展成 peer agent 行为脚本

## 3. 群组级 manager contract

manager contract 应在建群时确定，并随群组固定。

它至少应包含：

1. 任务目标
2. 角色结构
3. 阶段模型
4. manager 允许的控制动作
5. 异常处理原则

它不能包含：

1. worker/tester/editor 的逐句行为脚本
2. peer-to-peer 的固定回复模板
3. 对 agent 间协作的硬编码规定

## 4. text-first 原则

1. agent 间协作以 `text` 为主
2. `payload` 只承载 formal signal、可选结构化引用、辅助元数据
3. `candidate_material_pool`、`material_review_feedback`、`product_draft` 等命名工件不是默认硬门槛

## 5. 阶段内与阶段间的根规则

1. 阶段内协作发生在群组消息面
2. 控制层只管门禁与上下文，不直接承载阶段内协作
3. 阶段推进后，旧阶段消息默认保留可见性，但失去行动性
4. 只有显式 `redo / resume / reopen` 才能重新激活旧阶段

## 6. 对实现的硬约束

以下行为一律视为越界：

1. 在 skill/runtime 中硬编码 peer agent 该说什么
2. 用自然语言 regex 白名单/黑名单直接决定 agent 间协作行为
3. 用 workflow 需要为理由，把 peer 协作逻辑下沉到 skill/server
4. 用 send-time 规则把命名工件变成流程硬门槛
5. 为某个特定 workflow 个案写专用逻辑
