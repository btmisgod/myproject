# Server Execution Prompt Template

你现在在服务器上执行任务。你的唯一共享上下文来源是：

- `docs/control-plane/CONTROL.md`
- `docs/control-plane/OPERATING_RULES.md`
- `docs/designlog/`

你的工作方式：

1. 只执行 `CONTROL.md` 中定义的当前唯一目标
2. 不扩展功能
3. 优先修活链，再做回归
4. 完成后只更新 `SERVER_REPORT.md`

输出要求：

- 当前 commit id
- 修改文件列表
- 实际执行命令
- 日志证据
- 回归结果
- 唯一阻塞点
- 下一步最小建议

