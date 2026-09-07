# 后端选择与职责边界

本文件帮助 Agent 在 `hcloud`、华为云 Python SDK 和 Terraform 之间选择合适的执行方式。
它是决策指南，不是固定状态机，也不要求宿主平台提供某个专有 Tool。

## 一句话规则

默认优先级是 `hcloud > SDK > Terraform`，但这不是机械回退链：Agent 自行选择与当前意图、
运行时能力和完成证据最匹配的后端。Terraform 由 IaC 意图触发；高频脚本不是第四种后端，
只是对某个后端的可选便捷封装。

## 三种后端

| 后端 | 适合场景 | 选择证据 | 不应误用 |
| --- | --- | --- | --- |
| `hcloud` | 默认的查询、诊断、一次性变更、dry-run 和回读 | CLI 可用；metadata/help 能确认 operation、版本和参数；输出可稳定解析 | 不要凭记忆猜命令；不要只看退出码判断 API 成功 |
| SDK | 类型化请求、复杂 body、分页/并发、程序化转换；或 hcloud metadata、服务覆盖、输出解析存在实际障碍 | 官方 package 可用；已核对 client/version/request model、region/endpoint、认证和异常结构 | 不要因“不熟 hcloud”就盲写 SDK；不要把便捷 runner 的 allowlist 当成全局禁令 |
| Terraform | 用户明确需要 IaC、可重复环境、评审 diff、长期纳管、import 或 drift | provider/schema 可用；目标适合声明式资源；用户愿意管理配置和 state | 不是 hcloud 报错后的普通兜底；不要把 apply/state 成功当成业务完成 |

MaaS 模型调用是独立的 API-first 能力面，不进入上述云资源后端排序。

## Agent 决策流程

1. 识别任务是查询、一次性变更、程序化处理还是 IaC 生命周期管理。
2. 检查候选后端的真实运行条件：可执行文件/package/provider、凭据来源、region/project、网络和
   metadata/schema。
3. 默认先考虑 hcloud。现有高频脚本正好覆盖任务时优先复用；脚本不覆盖时，Agent 可以基于
   metadata、resolver 或 live help 直接构造经过验证的 hcloud 命令。
4. hcloud 不可用、当前服务/operation 覆盖不足，或者 SDK 在类型化、分页、并发和结构化异常方面
   明显更可靠时，可以使用官方 SDK。先检查已安装 package；确有必要时再安装单个服务 package。
5. 只有 IaC 意图成立时选择 Terraform。不要因为前一个命令失败就自动把任务改写成 Terraform。
6. 执行后按任务完成条件回读。API 接受、进程退出码、job ID、Terraform apply 和资源 `ACTIVE`
   都只能作为对应层级的证据。

## 后端切换

切换后端前保留三个信息：原路径失败的结构化证据、切换理由、切换后必须重新验证的事实。不要把
同一无效参数原样搬到另一个后端，也不要重复已经确认成功的副作用。

- hcloud operation/参数不明确：先查 metadata/help/resolver；SDK metadata 也可提供类型和路径证据。
- hcloud 服务元数据缺失或输出无法可靠解析：如果官方 SDK package 覆盖该 API，可以改用 SDK。
- SDK package 缺失：优先安装所需的单服务 package；不能安装时回到可用的 hcloud 或明确报告缺口。
- Terraform provider 下载失败：可交付草案和缺口，但不能声称 init/plan/apply 已完成；一次性任务可
  重新评估 hcloud 或 SDK 是否更合适。
- 认证、权限、配额和业务参数错误通常跨后端存在；更换后端不会自动修复这些问题。

## Terraform 的发现和验收

Terraform 前后使用 hcloud 有明确价值：前置发现减少对现网依赖的猜测，后置回读避免把 state/apply
成功误认为云侧或业务完成。因此它是首选证据组合，但不是硬性依赖。

如果 hcloud 不可用，可以使用等价的 SDK/API 查询、Terraform data source/provider refresh、用户提供
并重新核验的精确资源 ID，以及 HTTP/TCP/DNS/TLS/SSH 等业务探测。关键要求是证据等价，而不是工具
名字相同。

## 高频脚本

脚本只在能减少重复工作、统一已知错误处理或控制大输出时优先使用：

- planner：只生成可审查计划；
- inspector/router：观察环境或帮助选择少量资料；
- query executor：可选真实只读查询；
- mutation helper：帮助校验、提交和回读特定变更；
- artifact/media producer：生成文件或外部媒体产物。

脚本的 registry 或参数边界只描述该脚本能做什么，不限制 Agent 使用官方 hcloud、SDK 或 Terraform
完成脚本未覆盖的长尾任务。公共脚本输出约定见 `script-audience-manifest.json`。

## 职责边界

- Agent：理解目标、选择后端和 operation、编排跨步骤依赖、处理异常并向用户解释结果。
- Skill：提供华为云事实、后端攻略、参数/错误经验、高频脚本、输出与验收约定。
- 宿主平台：提供凭据与进程隔离、命令执行、超时/事件传输、持久化能力和确认交互。

Skill 可以要求 Huawei 业务语义上的风险披露、明确授权和结果回读，但不假设宿主一定有特定函数名、
审批 Tool、session 模型或文件目录。
