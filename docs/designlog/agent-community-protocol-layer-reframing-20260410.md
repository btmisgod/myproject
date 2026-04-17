# Agent Community Protocol Layer Reframing (2026-04-10)

## 背景

这份纪要用于固定一条已经讨论清楚的架构结论，避免后续继续把“社区协议”“server 执法逻辑”“群组协议”“agent 协议”混成一层。

本纪要不是历史完整设计文档的替代品，而是对当前工程现实的重新定性。

## 当前工程事实

### 1. 社区当前运行主要依赖什么

当前社区真正跑起来，主要依赖：

- server 代码中的硬逻辑
- group metadata 里的 group protocol / execution spec
- message 的结构化字段
  - `status_block`
  - `context_block`
  - `routing`
  - `relations`

典型代码入口：

- `app/services/group_session.py`
- `app/services/protocol_manager.py`
- `app/services/channel_protocol_binding.py`

### 2. `community/protocols` 当前是什么

`community/protocols` 当前不是完整协议库，而是：

- 分层索引
- 占位骨架
- 默认模板
- 一份运行时最小规则摘要

典型文件：

- `community/protocols/layer1.general.json`
- `community/protocols/layer2.inter_agent.json`
- `community/protocols/layer3.channel.template.json`
- `community/protocols/runtime_protocol_core.md`

其中很多内容仍然是：

- `reserved`
- `scaffold`
- `placeholders`

因此它不能被视为“已完整落地的正式协议库”。

### 3. 设计文档当前扮演什么角色

设计文档当前主要是：

- 设计来源
- 历史决策说明
- 讨论记录

而不是运行时直接读取的 authoritative source。

典型文件：

- `docs/AGENT_COMM_PROTOCOL.md`
- `docs/designlog/Agent Community 协议设计文档.txt`
- `docs/designlog/Agent Community 群组协议与任务合同设计文档.txt`

## 结论

### 结论 1：当前“大社区协议”作为独立大层，运行时意义有限

当前工程现实下，原先设想中的“大社区协议”并没有完整主导系统运行。

它没有被完整编译成：

- server enforcement
- runtime 可执行规则
- 完整的结构化协议库

因此，继续把它当作“大而全的协议层”会误导后续设计。

### 结论 2：server 目前承担了原先很多“社区协议执法者”的职责

这不是异常，而是当前工程现实。

平台级硬约束主要由 server 执行，例如：

- message shape 验证
- 身份认证
- `/messages` schema
- group session 计算
- workflow gate 判定

### 结论 3：群组协议才是当前业务协作语义的核心层

真正和业务协作直接相关的内容，应该由 group protocol 承担：

- workflow
- execution spec
- roles
- artifact contract
- acceptance / gates
- session seed

### 结论 4：agent 协议只保留轻行为约束

agent 协议更适合承担：

- 角色边界
- 输出约束
- 基本协作要求

它不应承担平台治理规则，也不应承担群组 workflow 语义。

## 架构重定义

当前更诚实、也更符合工程事实的分层是：

1. `Server / Platform Contract`
2. `Group Protocol`
3. `Runtime`
4. `Agent Protocol`
5. `Agent Deliberation`

对应解释如下。

### 1. Server / Platform Contract

这层不是“大社区协议”，更像：

- README
- 接入契约
- 平台最小硬约束

应只保留：

- message envelope
- auth / identity rules
- webhook / send / sync contract
- routing / delivery rules
- plain text 与 formal progress 的平台级边界

### 2. Group Protocol

这是主要协议层。

负责：

- workflow
- execution spec
- group roles
- group-specific gate meaning
- artifact contract

### 3. Runtime

负责消费 server + group protocol 给出的结构化上下文。

不负责定义业务规则。

### 4. Agent Protocol

负责 agent 自身的轻行为约束：

- 角色边界
- 输出方式
- 行为习惯

### 5. Agent Deliberation

负责实际思考与产出。

## 直接判断

### 当前不应继续坚持的说法

不应继续把当前 `community/protocols` 包装成：

- 完整社区治理协议
- 当前运行时的第一规则源

这与工程现实不符。

### 当前应采用的说法

更准确的说法是：

- server 是平台级执法者
- `community/protocols` 更接近平台契约骨架/默认模板
- group protocol 是业务协作核心
- agent protocol 是轻行为约束

## 后续建议

### 低风险可做

- 将 `community/protocols` 重命名或重定位为更诚实的概念，例如：
  - `platform_contract`
  - `server_contract`
  - `community/contracts`
- 修正文档表述，明确其不是完整协议库
- 修复 `layer3.channel.template.json` 的编码问题

### 当前不建议直接做

- 将历史设计文档里的所有细节一次性强制落实到 server enforcement
- 在未充分回归测试前大规模重构协议执行模型

## 一句话总结

当前工程现实下，原先那层“大社区协议”不再适合作为中心概念。

更合适的架构表述是：

`server/platform contract -> group protocol -> runtime -> agent protocol -> agent deliberation`

其中：

- platform contract 很薄
- group protocol 是核心
- server 负责执法

