# IAM Policies and Permission Diagnosis

处理权限设计、403、`AccessDenied`、`Forbidden`、`Unauthorized` 或缺少 action/scope 的任务时读取本文件。目标是得到最小、可验证的权限建议，而不是根据服务名称猜测宽泛管理员权限。

## 权限判断顺序

1. 确认当前 profile、domain、project、region 和认证方式，见 `references/auth-and-context.md`。
2. 保留失败请求的服务、operation/version、HTTP 状态、request ID 和云侧错误码；先排除 region/project 或 token 过期等上下文问题。
3. 从 operation metadata、云侧错误和 `references/iam-actions-catalog.json` 提取候选 IAM action。catalog 仅是提示，不能代替华为云官方 IAM 文档或租户实际策略验证。
4. 区分系统策略、自定义策略、企业项目范围和组织级 SCP。下层策略已允许但上层显式拒绝时，不要反复扩大 IAM 用户权限。
5. 先用相同 scope 重试必要的最小只读请求；涉及策略新增、绑定或提权时，向用户展示拟增加的 action、资源范围和影响，并等待明确授权。

## 最小权限输出

权限建议至少说明：

- 需要完成的业务动作以及对应 service/operation。
- 候选 IAM action 和作用域是 domain 级、project 级还是企业项目级。
- 证据来自实际错误、operation metadata、官方文档还是本地提示 catalog。
- 仍需管理员确认的未知项，以及授权后的验证请求。

不要输出或保存凭据，不要把“拥有认证信息”和“拥有业务权限”混为一谈，也不要用全局管理员权限掩盖缺少的单个 action。详细错误归类和命令步骤见 `references/playbooks/iam-context-bootstrap.md` 与 `references/playbooks/iam-permission-diagnostics.md`。
