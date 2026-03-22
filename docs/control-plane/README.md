# GitHub Control Plane

本目录用于在 GitHub 仓库内建立一套轻量的“产品总监 -> 服务器执行”协作控制面。

目标不是让两个 Codex 直接互相通信，而是让双方都读取同一组文档：

- 产品总监侧负责定义当前唯一目标、约束、优先级与下一步动作
- 服务器执行侧负责报告实际执行结果、日志证据、阻塞点与最小建议
- 双方都以仓库文档为唯一共享上下文，避免聊天记录和口头状态漂移

## 文件角色

- [CONTROL.md](./CONTROL.md)
  当前唯一目标、禁止项、优先级、验收标准
- [SERVER_REPORT.md](./SERVER_REPORT.md)
  服务器执行结果、日志、阻塞点、下一步建议
- [ARCHITECT_REVIEW.md](./ARCHITECT_REVIEW.md)
  产品/架构侧判断、是否符合设计、下一步最小动作
- [OPERATING_RULES.md](./OPERATING_RULES.md)
  双方都要遵守的工作流规则
- [SERVER_EXEC_PROMPT.md](./SERVER_EXEC_PROMPT.md)
  发给服务器 Codex 的标准执行 prompt 模板
- [ARCHITECT_REVIEW_PROMPT.md](./ARCHITECT_REVIEW_PROMPT.md)
  发给产品总监/架构侧 Codex 的标准审阅 prompt 模板

## 使用方式

1. 产品总监更新 [CONTROL.md](./CONTROL.md)
2. 服务器 Codex 阅读 `CONTROL.md + OPERATING_RULES.md + docs/designlog/`
3. 服务器 Codex 执行并更新 [SERVER_REPORT.md](./SERVER_REPORT.md)
4. 产品总监侧 Codex 阅读 `CONTROL.md + SERVER_REPORT.md + docs/designlog/`
5. 产品总监侧 Codex 更新 [ARCHITECT_REVIEW.md](./ARCHITECT_REVIEW.md)，并生成下一轮执行指令

## 高频协同模式

本控制面支持“高频轮询 + 聊天入口补充指令”的连续协作模式：

- 你仍可直接在当前主对话中向产品总监侧 Codex 下达指令
- 产品总监侧 Codex 负责把这些新指令同步进 `CONTROL.md` / `ARCHITECT_REVIEW.md`
- 服务器执行侧不依赖聊天记录，只依赖仓库中的最新控制面文档
- 双方都应高频轮询控制面文档，而不是等待人工提醒

推荐节奏：

- 服务器执行侧：每 2 分钟轮询一次 `CONTROL.md`
- 产品总监侧：每 2 分钟轮询一次 `SERVER_REPORT.md`

如果当前正在执行较重任务：

- 不应中断主进程去做高频全量扫描
- 应在单轮任务结束、或安全检查点到达时立即刷新控制面文档

## 核心原则

- 一次只允许一个“当前唯一目标”
- 服务器执行侧不得擅自扩展目标
- 产品总监侧不得要求服务器一次并行处理多个高风险方向
- 所有结论必须附带 commit id、文件路径、日志证据或测试结果
- 设计文档始终高于执行过程中的即兴理解
