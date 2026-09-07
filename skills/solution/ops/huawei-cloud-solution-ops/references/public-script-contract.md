# 公共脚本契约

本 Skill 的公共脚本是 Agent 可直接运行的高频捷径。脚本文件可以各自保持清晰职责，不需要合并成
一个大 dispatcher；调用方通过统一分类、输出和退出语义判断如何使用它们。

机器可读声明位于 `script-audience-manifest.json`。当前采用渐进迁移：优先覆盖云访问、协议探测或可能
产生大结果的公共入口；小型有界 inspector/planner 可以只输出完整 JSON，不机械增加 artifact 参数。

## 两层契约

公共 CLI 分为两层，避免把“大结果传输”和“所有脚本都能稳定调用”混成一件事：

1. `huaweicloud_skill_agent_cli_v1` 是 55 个真实 Agent 入口的最小分母。入口由 manifest 中
   `default_runtime`、`guarded_change` 和 `runtime_supplement` 三组确定；可从稳定 launcher 调用，
   成功结果至少有布尔 `success`，默认最终 stdout 是一个 JSON object，退出码表示 CLI 契约是否完成。
2. `huaweicloud_skill_public_result_v1` 是较丰富的扩展，面向可能产生大结果或需要稳定 artifact
   回执的入口，增加 `mode`、`outcome_status` 和私有 `result_file`。它不是所有小 planner/inspector
   都必须实现的统一外壳。

只有四类显式例外：behavior/dependency inspector 的 `--format=markdown`、resolver 的
`--emit-command`，以及 `maas_text_to_image.py` 的逐项进度后最终 JSON。例外必须在 manifest 声明；
默认模式不能静默从 JSON 变成文本。这样 Agent 只需记住一个最小成功口径，再按任务决定是否使用
artifact 扩展，而不是记忆每个脚本的私有结果协议。

## 脚本分类

| kind | 作用 | 是否访问云 |
| --- | --- | --- |
| `planner` | 校验输入并生成可审查计划 | 默认不访问 |
| `inspector_router` | 观察本地环境或选择少量资料/入口 | 通常不访问业务 API |
| `query_executor` | 计划或执行只读查询 | 只有显式 execute 时访问 |
| `mutation_helper` | 规划、校验、执行或回读特定变更 | 由脚本参数和授权边界决定 |
| `artifact_media_producer` | 生成文件、图片、视频或其他外部产物 | 由具体后端决定 |

`backend` 说明脚本包装的是 hcloud、SDK、Terraform、MaaS API 还是本地逻辑。脚本本身不是第四种
执行后端，registry 也不是 Agent 可使用 API 的总白名单。

## 默认兼容行为

- 不传 `--output-file`：继续把原有完整 JSON 写到 stdout；已有调用方无需修改。
- 传 `--output-file <path>`：完整 JSON 原样写入该文件，权限为 `0600`；stdout 只返回紧凑回执。
- `--pretty` 同时控制落盘 JSON 和 stdout 回执的可读格式，不改变字段语义。
- 脚本不因为落盘而重新汇总、删字段或改写 provider 响应；调用方按需从结果文件提取字段。

## 紧凑回执

`huaweicloud_skill_public_result_v1` 在最小 CLI 契约之上至少包含：

```json
{
  "result_contract": "huaweicloud_skill_public_result_v1",
  "success": true,
  "mode": "plan",
  "outcome_status": "planned",
  "result_file": {
    "path": "/workspace/result.json",
    "bytes": 1234,
    "sha256": "...",
    "permissions": "0600"
  }
}
```

结果存在时还可带 `service`、`operation`、有界 `summary` 或 `planning_status`。完整结果始终原样存在
`result_file` 指向的文件中，紧凑回执不会复制 records/checks 等大数组。

`outcome_status` 只使用 `planned`、`succeeded`、`partially_succeeded`、`failed`、
`outcome_unknown`。plan 成功为 `planned`，execute/verify/audit/check 成功为 `succeeded`，失败为
`failed`；脚本明确声明的 partial/unknown 保留。非标准 provider 状态不会直接污染公共枚举，而是
归一化为 `outcome_unknown`，原值仍保留在完整结果文件中。

`success` 表示脚本是否按自己的契约产生了可用结果，不替代领域完成判断。例如环境 doctor 可以
`success=true` 但 `summary.ready=false`；plan 可以 `outcome_status=planned`，同时
`planning_status=partially_succeeded` 暴露计划缺口。

## 可恢复读取扩展

账号盘点和 Billing 分页可选支持 `--checkpoint-file`、`--time-budget` 和 `--resume`。checkpoint
不是新的公共结果格式，也不替代宿主 task state：它只保存一个脚本内部已经完成的只读检查或已接受
页面，使下一次同 scope 调用不重复工作。文件按 `0600` 原子写入，scope digest、契约版本、结构、大小
和权限会在任何云调用前校验；完整资源响应或未脱敏 Billing 页面可能存在其中，因此只能作为私有执行
中间态。紧凑回执只暴露 checkpoint 路径/文件回执和有界进度，不复制 checkpoint 内容。

## 退出语义

- `success=true` 返回退出码 `0`；
- `success=false` 返回非零；
- 非零退出不表示没有结果文件，调用方仍应检查 stdout 回执或已知 `--output-file`；
- provider/API 的业务错误不能仅凭子进程退出码判断，脚本需要解析其结构化返回；
- `partially_succeeded`、`outcome_unknown` 由具体脚本在确有证据时声明，公共 emitter 原样保留。

## 已迁移入口

- `hcloud_resource_discovery.py`
- `hcloud_resource_query.py`
- `hcloud_obs_readonly.py`
- `hcloud_sdk_readonly.py`
- `hcloud_account_inventory.py`
- `hcloud_billing_live_read.py`
- `hcloud_cost_estimate.py`
- `hcloud_lts_readonly.py`
- `hcloud_service_readiness.py`
- `hcloud_resource_verify.py`
- `hcloud_idle_audit.py`
- `hcloud_acceptance_closure.py`

`hcloud_context_inspect.py` 和 `hcloud_environment_doctor.py` 是有界本地检查，继续直接输出完整 JSON。
`hcloud_safe_exec.py` 已有 output-policy、`--result-file`、parsed/raw artifact 和 provider 错误结构，保持其
专用传输契约；后续增强其 outcome 深度时不能把超时 mutation 简单误判为 `failed`。
