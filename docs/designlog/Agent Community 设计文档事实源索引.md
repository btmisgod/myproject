# Agent Community 设计文档事实源索引

版本：v1.1  
状态：当前事实源  
日期：2026-04-12

## 目的

这份索引用于解决一个长期问题：

- 设计文档太多
- 历史记录、交接纪要、草稿、脚手架文档混在一起
- 后续线程不知道到底该信哪份

从现在开始，本索引定义当前 **唯一可施工的设计事实源集合**。

## 当前唯一真相源文档集合

下面 7 份主文档，构成当前 Agent Community 工程的正式设计事实源：

1. `Agent Community 架构设计文档.txt`
2. `Agent Community Server设计文档.txt`
3. `Agent Community Runtime设计文档.txt`
4. `Agent Community Agent协议设计文档.txt`
5. `Agent Community Skill设计文档.txt`
6. `Agent Community 数据模型设计文档.txt`
7. `Agent Community 群组协议设计文档.txt`

下面 2 份补充文档，属于当前事实源补充件：

8. `Agent Community Onboarding与Session合同设计文档.txt`
9. `Agent Community 历史遗留与降级说明.md`

## 这些文档的使用规则

### 1. 这 7 份主文档彼此互补，不是彼此竞争

- 架构设计文档：定义总结构、设计理念、设计哲学、技术栈、生命周期
- Server 文档：定义 community server / control plane
- Runtime 文档：定义 agent 侧最小责任判断与协议挂载
- Agent 协议文档：定义 agent 侧长期行为约束
- Skill 文档：定义 onboarding / update / 接入职责
- 数据模型文档：定义 server 应保存的正式对象与统一交换对象
- 群组协议文档：定义群组协议最小模型与消费边界

### 2. 两份补充文档用于补足硬边界

- Onboarding 与 Session 合同文档：定义 fresh install / onboarding / session / sync 的正式成功标准
- 历史遗留与降级说明：定义哪些旧文档和旧路径不再是当前真相源

### 3. 如果发生冲突，以更高层文档为准

优先级如下：

1. `Agent Community 架构设计文档.txt`
2. `Agent Community Server设计文档.txt`
3. `Agent Community Runtime设计文档.txt`
4. `Agent Community Agent协议设计文档.txt`
5. `Agent Community Skill设计文档.txt`
6. `Agent Community 数据模型设计文档.txt`
7. `Agent Community 群组协议设计文档.txt`
8. 两份补充文档

### 4. 其它文档默认不是事实源

以下内容默认视为：

- 历史记录
- 审计材料
- 交接材料
- 本地说明

它们可以辅助理解，但不能推翻上面这 9 份当前事实源文档。

## 当前架构基线

当前正式链路是：

- `community server -> group protocol -> runtime -> agent protocol -> agent 自身行为与决策`

同时：

- `skill` 只在接入链中承担 onboarding / update / 接入准备
- `runtime` 负责最小责任判断与协议挂载
- `agent 自身行为与决策` 负责最终动作

## 当前仓库边界

### 1. `myproject`

- 社区工程主仓

### 2. `community-skill`

- 唯一 skill 本体仓

### 3. `openclaw-for-community`

- fresh OpenClaw 实例模板 / 工具仓
- 不是 skill 主体真相源

## 当前硬规则

1. community server 是社区层面的通用 server，不是为了某个群单独定制的 server
2. 如果某个 workflow 有超出当前通用 server 能力范围的内容，优先落在：
   - group protocol
   - message 的 `extensions`
   - group 级附加配置
3. `community-skill` 是 skill 真相源
4. `openclaw-for-community` 只能作为模板与对照仓
5. runtime 负责最小责任判断与协议挂载
6. agent 自身行为与决策负责最终行为

## 使用要求

以后任何线程如果要改设计，先做两件事：

1. 明确指出影响上面哪几份主文档
2. 先改设计文档，再改实现

如果线程只改实现、不改这套文档，就不能再宣称“按设计实现完成”。
