# Verification Method

当任务需要证明查询准确、变更成功、资源可用或故障已经恢复时读取本文件。验证必须基于实际命令、API、资源回读或业务探测，不以计划、提交回执或进程退出码替代结果证据。

## 分层验证

按任务实际涉及的层次收集最小充分证据：

1. **请求层**：记录 operation/version、region/project、退出码、request ID、job ID 和结构化结果状态。
2. **资源层**：用独立的 `Show*`、`List*` 或等价 SDK/API 回读资源 ID、状态、配置和数量。
3. **关系层**：验证绑定、路由、监听器/member、安全组、VPC/subnet、EIP 等依赖关系。
4. **系统层**：任务涉及 ECS 机内状态时，验证进程、端口、挂载、配置和日志。
5. **业务层**：需要可用性时执行受限 HTTP/TCP/DNS/TLS 或产品专用探测，确认用户路径，而不只看云资源为 `ACTIVE`。

只收集与完成声明有关的层次。纯查询通常只需请求层与资源层；网站、数据库、ELB、容器或异步变更往往还需要关系层和业务层。

## 状态表达

- `planned`：只有方案或命令草稿。
- `prepared`：已完成本地检查、参数预检或 dry-run，尚未提交。
- `executed`：请求已提交或命令已执行，终态可能未知。
- `verified`：满足当前任务的验收标准，并有实际回读或探测证据。
- `blocked`：缺少权限、输入、网络、依赖或用户授权，无法继续采证。

出现 `job_id`、HTTP 2xx、进程退出码 0、Terraform plan 成功或资源 `ACTIVE` 时，仍要判断是否需要下一层证据。异步结果未知时先回读，再决定是否重试，避免重复副作用。

## 结果记录

最终回复列出已验证事实、使用的 region/project、关键命令或脚本、资源 ID/状态、失败项和未覆盖层。大结果只引用脱敏 artifact 的路径和摘要。具体完成门槛见 `references/acceptance-criteria.md`，执行安全边界见 `references/runtime-safety-boundaries.md`。
