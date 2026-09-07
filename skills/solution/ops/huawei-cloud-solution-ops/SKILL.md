---
name: huawei-cloud-solution-ops
description: |
  A skill for Huawei Cloud solution operations.
  It helps agents inspect, plan, operate, troubleshoot, and verify Huawei Cloud resources through hcloud, Huawei Cloud SDKs, Terraform, and MaaS capabilities.
  Use this when users want to query or change Huawei Cloud resources, troubleshoot authentication and API issues, assess environments, plan infrastructure, manage costs, or verify operational outcomes.
Trigger: 华为云运维, 华为云资源管理, 华为云资源查询, 华为云环境评估, 华为云故障排查, 上云, 用云, 管云, huawei cloud operations, huawei cloud assessment, hcloud, KooCLI, Huawei Cloud SDK, Terraform, IaC, MaaS
tags: [huawei-cloud, cloud-ops, hcloud, koocli, sdk, terraform, maas]
---

# Huawei Cloud Agent Skill

## 概述（核心定位）

- 单一 skill 覆盖华为云上云、用云、管云场景，默认以租户体验和可验证闭环为中心。
- 云资源默认优先使用 `hcloud`：它更适合 Agent 做 operation 发现、一次性查询/变更、dry-run 和回读。Agent 仍根据任务意图、运行时能力和证据质量自行选择 `hcloud`、SDK 或 Terraform，详细决策见 `references/backend-selection.md`。
- SDK 是受支持的程序化后端，适合类型化请求、复杂 body、分页/并发、结构化异常，或 hcloud 当前确有覆盖/解析障碍的任务。`hcloud_sdk_readonly.py` 的 allowlist 只约束该便捷 runner，不限制 Agent 编写任务专用 SDK 代码。
- Terraform 由 IaC 意图触发，用于可重复创建、环境复制、长期纳管、import 或 drift；它不是 hcloud 失败后的普通兜底。前置发现和后置验证优先用 hcloud，也允许等价 SDK/API、data source 和业务探测证据。
- 高频脚本是对上述后端的可选封装，不是第四种后端。脚本覆盖目标时优先复用其版本选择、参数校验、脱敏、输出收敛和错误分类；未覆盖的长尾任务可直接使用有证据的 hcloud、官方 SDK 或 Terraform。
- 文档中的 `python3 scripts/<name>.py ...` 假设当前目录是 Skill 根目录。当前目录不确定时，用 `bin/hcloud-skill <name> ...`；Windows 用 `bin/hcloud-skill.cmd <name> ...`。这个稳定入口只定位当前 Skill 自带脚本并原样传递参数，不替 Agent 选择服务、operation、参数或调用顺序。
- 面向 Agent 的脚本成功结果至少提供布尔 `success`；默认最终 stdout 是 JSON object。大结果或已选择的结构化入口可进一步提供 `huaweicloud_skill_public_result_v1` artifact 回执，但小型 planner/inspector 不需要机械增加 `--output-file`。显式 Markdown、shell-command 和逐项图片进度模式见 `references/public-script-contract.md`。
- `hcloud` 不可用不等于整个 Skill 不可用；如果 SDK 或 Terraform 符合任务且运行条件完备，可以继续。无论使用哪个后端，没有真实执行和回读证据时都不能宣称已经查询、修改或完成。
- MaaS 是 API-first 能力面。模型调用使用 MaaS API Key；用量统计是治理查询，按本地 AK/SK 签名规划处理。不要让用户在对话里粘贴密钥。
- 目标不是背命令，而是稳定完成：识别上下文 -> 发现资源/operation -> 构造安全命令 -> 查询或变更 -> 回读验证 -> 处理错误。

## 什么时候使用

优先在这些场景使用本 skill：

- 用户提到华为云、`hcloud`、KooCLI、CLI、命令行、云资源查询、创建、变更、排障或治理。
- 用户需要查看 service/operation、构造 `--cli-jsonInput`、使用 `--cli-query`、`--dryrun`、`--cli-waiter` 等 CLI 能力。
- 用户需要华为云认证、region/project、profile、meta cache、网络或输出格式排查。
- 用户明确需要 Terraform/IaC、MaaS 大模型/图像/视频，或华为云 Web/OBS/CDN/ECS 站点资产辅助。

不要把本 skill 当成非华为云的通用云知识问答、无证据 API 猜测器、自动 Terraform apply 器，或非华为模型服务兜底。

hcloud 命令应显式携带当前任务的区域，标准形态为：

```bash
hcloud <Service> <Operation>/<version> --cli-region=<region> <business-parameters>
```

全局服务确认不需要 region 时才可省略；跨区域任务不得依赖 profile 的隐式默认值。

## 跨服务和多轮任务

本 skill 用少量共享语义帮助不同服务场景保持目标、事实来源和完成口径一致，但它不是任务执行控制器。Agent 仍然负责理解现场情况，并自主选择或调整服务、工具、参数和操作次序。

- 多轮、跨服务、有副作用、异步或可能中断的任务需要可恢复记忆。宿主已有持久 task state 时优先复用；宿主提供持久且可写的 workspace 时，可用 `task.md` 或等价文件记录目标、约束、授权、重要进展、artifact 和下一步。宿主没有文件 workspace 时，使用其可用状态机制并说明恢复限制，不得仅因缺少特定 task ID、文件工具或目录而阻断云任务。
- 用户要求变化时重新判断复杂度并更新可恢复状态。运行时 task ID 对 Agent 可见时原样复用；不可见时可使用稳定任务描述符，但不得冒充平台 ID。具体建议见 `references/task-workspace-guide.md`，模板只是可选起点。
- 创建、删除、替换或绑定付费/有副作用资源时，应保留逻辑角色、预期数量、canonical 资源和待决操作。待决操作尚未确认终态或结果未知时，先回读收敛，避免重复副作用。
- 未经处理的云 API、网页或工具大输出保存在 artifact；任务状态只保留可信摘要和引用。企业网站、跨服务资源盘点、成本治理等宽泛目标可按需读取 `references/goal-capability-guide.md`、router 和命中的 playbook；状态表达见 `references/interaction-guidance.md`。这些都是可选辅助，不替 Agent 决定架构、工具、参数和次序。

## 默认工作流

1. 先选择候选后端并确认上下文：
   - 默认先考虑 hcloud；根据实际后端运行 `python3 scripts/hcloud_environment_doctor.py --need <dependency> --pretty`。选择 SDK 时用 `--need sdk --sdk-service <SERVICE>`，选择 Terraform 时用 `--need terraform`；需要真实 API、网络或大结果文件时再分别加 `--need live`、`--need network`、`--need artifacts`。完整规则见 `references/runtime-dependencies.md`。
   - doctor/context 只能观察当前进程环境和本地 profile；未观察到 AK/SK 或 MaaS API Key 只表示配置状态未知，不得断言用户未配置。使用凭据 broker 的运行时可能只在受授权的执行子进程中注入凭据。
   - 需要项目级服务的 `project_id` 时，用 `python3 scripts/hcloud_project_resolve.py --region=<region> --pretty`，按显式值、环境变量、本地 profile 缓存、IAM `KeystoneListProjects` 的顺序解析；不要因为 IAM SDK 未安装而改写签名请求。
   - 若 `hcloud.found=false`，不要执行 hcloud 路径；按 `references/backend-selection.md` 判断 SDK 或 Terraform 是否能可靠完成，否则只给方案草稿和环境缺口。
2. 宽泛或架构不明确的目标按需路由：
   - `hcloud_scenario_router.py` 可帮助找到少量 playbook、guide、planner、SDK 和 Terraform 候选；目标、运行载体和服务已经明确时可跳过 router。
   - 宽泛或架构不明确的网站部署任务可先读取 router 的 `architecture_decision` 和 `matches`；它是决策辅助，不是所有网站任务的前置门禁，也不替 Agent 预设 ECS、OBS、Flexus 或具体规格。
   - 网站部署任务先读取顶层 `architecture_decision`，再看 `matches`。`explicit_constraints` 是用户约束，不是成本优化提示；用户指定机器、ECS、公网 IP、SSH、Nginx 或 Docker 时，不得自动改成 OBS。
   - `change_execution_blocked=true` 时，原样围绕 `clarification_question` 澄清运行载体或动态能力；确认前禁止生成或执行创建、购买、上传、公开访问等变更。`change_execution_blocked=false` 只表示当前不需要架构澄清，**不表示用户已授权执行**。
   - 网站任务涉及资源计费、公网暴露、域名/DNS/HTTPS 或 MaaS 图片/视频调用时，先向用户给出一份合并方案再等待确认。方案至少说明：推荐架构与资源、region、网络和公网入口、域名/HTTPS 处理方式、MaaS 资产数量与用途、持续费用和主要风险；持续费用优先引用变更计划中的 `cost_estimate`，若其 `status=unknown`，必须原样说明原因和范围，不能用资源清单或经验价冒充实时询价。用户首条“帮我搭建/部署/上线”只授权规划和只读预检，不授权付费资源创建、MaaS API 调用、上传或公网暴露；只有用户在看见该方案后明确回复“按此方案继续”或等效确认，才可进入执行。
   - 只读取命中的少量资料，不全量浏览 catalog、Terraform 示例或长 reference。
3. 查询类默认稳定化：
   - Agent 自主决定查什么和传什么业务参数；通过当前 runtime 的普通命令执行工具直接运行本 Skill 的专用 CLI，不依赖宿主专属 Function Calling 名称，也不要臆造不存在的平台 Tool。
   - 账号级多服务盘点使用 `python3 scripts/hcloud_account_inventory.py --region <region> --execute --strict --output-file <workspace-result.json>`。脚本会在每个区域解析并复用一次 `project_id`，有限并发查询服务，并在 stdout 返回紧凑摘要和完整结果文件位置。可能被宿主运行时中断时，加 `--checkpoint-file <private-checkpoint.json> --time-budget <seconds>`；下一轮用相同查询参数和 `--resume` 只继续未完成检查，不重复已完成服务。
   - 账单、成本或费用记录使用 `python3 scripts/hcloud_billing_live_read.py ... --execute --confirm-live-billing-read READ_BILLING_DATA --output-file <workspace-result.json>`。脚本在安全上限内自动分页和合并；Agent 不手工维护普通总额查询的下一页 `offset`。长分页可使用独立 `--checkpoint-file` 和 `--time-budget`，恢复时复用已接受页面并从 `pagination.next_offset` 继续。checkpoint 含未脱敏的执行中间数据，只能保存在受限 workspace 中，不能读入对话或当作公共结果。
   - 单次资源变更的持续费用证据使用 `python3 scripts/hcloud_cost_estimate.py --service <SERVICE> --region <region> --project-id <project-id> --resource-spec <sku> --quantity <count> ...`。默认只生成 BSS 询价计划，`cost_estimate.status=unknown` 且 `amount=null`；只有显式 `--execute --confirm-live-billing-read READ_BILLING_DATA` 返回 `status=quoted` 后，才可引用金额。`scope` 必须说明包含/排除的组件、计费模式、用量或周期；询价不是历史账单，也不创建订单。EIP 必须明确选择 `eip-bw`、`eip-flow` 或 `eip-ip`，不能把地址、带宽和流量混成一个价格。
   - 收到 stdout 文件回执后，先读 `outcome_status`、`summary` 和 `result_file`。需要资源明细时用 `jq` 等工具从结果文件提取当前回答所需字段，不要把完整大文件一次性读回模型上下文。命令退出码非零时仍要检查结果文件；`partially_succeeded` 表示可使用成功部分并明确失败服务，不等于整项查询没有结果。
   - 参数错误、凭据错误、超时、版本解析错误或部分成功时，先根据结构化错误判断根因。可修正同一路径，也可在 hcloud 确有覆盖/解析障碍、SDK 更适合类型化或程序化处理时切换 SDK；切换要保留原因和重新验证项，不重复已经成功的查询或副作用。
   - 正例（北京4资源盘点）：运行 `hcloud_account_inventory.py --region cn-north-4 --execute --strict --output-file <workspace>/beijing4-inventory.json`；stdout 返回回执后，从该文件提取资源名称、ID、状态和关系，并保留失败服务清单。
   - 正例（北京4区域成本）：运行 `hcloud_billing_live_read.py --operation cost-data --region-code cn-north-4 --begin-time <start> --end-time <end> --execute --confirm-live-billing-read READ_BILLING_DATA --output-file <workspace>/beijing4-cost.json`。只有 `pagination.complete=true`、`complete_result_claim_allowed=true` 时，才能把 `verified_monetary_totals` 表述为完整总额。`monthly-sum` 是全账号汇总，不能直接当作北京4费用，本月累计事实与月底预测也要分开说明。
   - 正例（部分成功）：盘点因 time budget 返回 `partially_succeeded` 且 `execution_progress.pending_check_count>0` 时，用原 checkpoint 加 `--resume` 继续；服务本身失败时读取完整结果文件，使用成功服务的数据并明确列出失败服务，修复原因后可按 service 定向重跑。
   - 反例：专用盘点脚本超时后，连续运行 IAM 探测、临时 Python SDK 和一批裸 hcloud 命令；或账单返回 `total_count=11`、`record_count=10`、`complete_result_claim_allowed=false` 时，把 10 条小计写成“完整合计”。空摘要也不等于费用为 0。
   - hcloud 路径的调用优先级为“匹配的专用场景脚本 -> `hcloud_resource_discovery.py` / `hcloud_resource_query.py` -> resolver/safe exec 或有 metadata/help 证据的直接 hcloud”。脚本是捷径，不是白名单；直接命令仍须确认 operation 版本、参数、风险、输出策略和验证方式。
   - 多版本 operation 先用 `hcloud_operation_resolver.py` 按参数选择版本；普通小查询的直接 `hcloud` 命令显式写成 `Operation/vN`，命中大输出策略时解析器改为生成 `hcloud_safe_exec.py --output-mode=auto`。`hcloud_safe_exec.py` 和 `hcloud_resource_query.py` 已内置同一版本解析逻辑。
   - 以下 operation 均属于大输出；命中时禁止先执行裸 `hcloud` 试探响应大小，直接使用 `hcloud_safe_exec.py --output-mode=auto`：
     - 镜像、规格和资源列表：`IMS:ListImages`、`IMS:GlanceListImages`、`ECS:ListFlavors`、`ECS:ListFlavorSellPolicies`、`ECS:ListServersDetails`、`DNS:ListRecordSets`。
     - 日志、事件和指标：`LTS:ListLogs`、`CTS:ListTraces`、`CFW:ListAccessControlLogs`、`CFW:ListAttackLogs`、`CFW:ListFlowLogs`、`CES:BatchListMetricData`、`CES:BatchListSpecifiedMetricData`、`CES:ShowMetricData`。
     - 全租户和工作负载资源：`RMS:ListAllResources`、`RMS:ListResources`、`COC:ListResources`、`CCI:listCoreV1PodForAllNamespaces`、`CCI:listNamespacedPods`、`CCI:listCoreV1NamespacedPod`、`CCI:listCoreV1NamespacedEvent`、`CCI:listMetricsV1beta1NamespacedPodMetrics`、`SWR:ListRepositoryTags`。
     - 文件和下载：`CodeArtsRepo:ShowFileContent`、`CodeArtsRepo:ShowFileRaw`、`CodeArtsRepo:ShowReadmeFile`、`CodeArtsRepo:DownloadArchive`、`CodeArtsRepo:ShowRepositoryArchive`、`RDS:DownloadErrorlog`、`RDS:DownloadSlowlog`、`DDS:DownloadErrorlog`、`DDS:DownloadSlowlog`。
   - 以下命名规则同样直接按大输出处理，不允许先裸跑：下载/导出/文件内容/归档/diff/构建日志；日志/事件/审计/告警/历史；CES/AOM 指标、时序和采样点；BSS/RMS/COC/CONFIG/SECMASTER/HSS 的全租户 `List*`、`Search*`、`Query*`、聚合和资源历史 operation。
   - 命中大输出策略后，Agent 只读取摘要、数量、字段结构、少量样本和落盘路径；不得把完整列表、完整文件或完整 `parsed_json` 再输出到对话。
   - `OUTPUT_POLICY_REQUIRED` 不是云 API 失败；按返回的 `corrected_command` 或补齐 `corrected_command_template` 中的时间/范围参数后再执行一次，不要原样重试。
   - 返回为空不等于失败；必要时检查 region/project、过滤条件、权限和状态码。
4. 变更类先计划再执行：
   - 先查现状证据，再生成 change plan 或 dry-run；执行授权使用宿主可用的确认交互，Skill 不假设特定平台函数名。
   - 复杂 body 先看 resolver/change plan 返回的 `request_contract`。`body_shape_confidence=top_level_only` 时，不能从顶层字段猜测 `.1` 或嵌套点号参数；优先使用 `--cli-jsonInput`，必要时按 `sdk_evidence_command` 读取官方 SDK 的有限深度请求 schema。
   - 写好 `cli-jsonInput` 后、dry-run 或 submit 前，先运行 `hcloud_request_preflight.py`；通用 change plan 在收到 `--json-input-file` 时也会自动预检。明确的 JSON、位置、必填字段和类型错误必须修正；`validation_status=partial` 表示本地证据不完整，应继续用 dry-run、operation help 或官方文档补证，不能把它误写成云 API 失败。
   - `hcloud_safe_exec.py` 返回的 `execution_semantics` 分开描述请求结果和资源状态：mutation 的 `request_outcome=succeeded` 仍需回读；`request_outcome=outcome_unknown` 或 `retry_strategy=verify_before_retry` 时，先查询目标资源或异步 job，再决定是否重试，禁止原样重复提交。
   - 批量或异步 operation 命中 `operation_behavior` 时，以其中的目标路径、submit receipt、逐项 outcome 和资源回读条件为准；也可先运行 `hcloud_operation_behavior.py --service <SERVICE> --operation <Operation>`。涉及创建前置条件或删除依赖时，再读取 planner 返回的 `dependency_evidence`，或运行 `hcloud_dependency_evidence.py --service <SERVICE> --operation <Operation>`；它只提供前置资源、阻断项、关联资源和回读证据，执行顺序仍由 Agent 根据实时状态决定。Agent 可以直接轮询声明的查询 API，不要求公共轮询框架；辅助 waiter 只是高频捷径，job 成功仍不能替代逐资源终态验证。
   - 按所选工具的真实结果契约解释输出。本 Skill 的 execute 脚本如果返回
     `outcome_status`，以该结构化字段为业务结果；裸 `hcloud`、帮助探测和其他
     未声明结构化结果的命令必须同时保留 stdout、stderr 和退出码，不能只因进程
     退出码为 `0` 就断言云操作成功。
   - 对可能产生费用或影响线上服务的云资源操作，先形成一套或多套候选方案。Agent 可以调用现有工具、专家能力或自行分析来制定方案；每套方案应说明目标资源、预期影响、持续费用（如适用）、主要风险和验证方式。
   - 将候选方案交由用户选择并明确确认后，才能执行对应操作；用户仅提出初始需求不构成执行授权。
   - 真实 submit，以及会产生计费或外部副作用的 MaaS 图片/视频生成，必须有用户在查看本次方案后作出的明确确认；初始任务请求、路由成功、dry-run 成功或 `change_execution_blocked=false` 都不是执行授权。安全、身份、密钥、治理类 mutation 默认 hard guard。
5. P0 高频服务闭环：
   - 先运行 `hcloud_closure_plan.py --tier lifecycle` 生成 lifecycle plan 和 `acceptance_evidence_plan`。
   - 再用 `hcloud_acceptance_closure.py plan/run/evaluate/chain` 做采证计划、受支持探测和 evidence 结果判定。
   - 做真实账号回归或服务晋级时，用 `hcloud_live_validation_plan.py` 列出 ECS/VPC/EIP/OBS/ELB/RDS 的目标输入、读回、probe 和晋级缺口。
6. 完成声明要诚实：
   - `job_id`、`accepted`、云侧 `ACTIVE`、Terraform plan 成功、MaaS `task_id` 都不等于业务可用。
   - 需要协议、健康、机内、日志、指标或用户路径证据时，必须说明已采集、缺失或被阻塞。

## 安全边界摘要

详细规则在 `references/runtime-safety-boundaries.md`。执行创建、变更、网络暴露、ECS 机内操作、COC/SSH fallback、应用验收或排障前先读取该 reference。

| 风险点 | 默认处理 |
| --- | --- |
| 凭据、AK/SK、API Key、私钥 | 不在对话、日志、manifest、站点代码中回显或保存；支持文档列出的同家族环境变量别名，不得跨家族拼接 AK/SK。命令/API 输出中的 `***`、`****` 或更多连续星号表示“值存在但已脱敏”，不表示缺失。 |
| 安全组入口 | SSH `22` 和开发端口不得开放到 `0.0.0.0/0`。用户确认公网网站方案后，直连 ECS 的精确 TCP `80/443` 可使用 `--allow-public-web` 规划；该参数不替代 submit 确认，复用安全组仍要读回规则并做外网协议探测。 |
| 异步云任务 | 跟到 job 终态，再做资源状态、协议或业务验收。 |
| Terraform 状态 | import/state/remote state 是高影响操作；必须显式确认，不能自动 apply/destroy。 |
| MaaS 视频和异步任务 | `task_id` 只是受理凭据，必须查询终态。 |
| 账单/成本 | 不从资源清单推断费用；账单结果要脱敏、区分 fact/grain/money basis/scope。 |
| 自动 live probe | 只执行 plan 派生的 HTTP/TCP/DNS/TLS；元数据/link-local 目标拒绝，内网/localhost 需显式确认。 |
| 结果叙事 | 只描述真实发生的命令、输出和验证；不要编造失败-恢复过程或把计划态写成已执行。 |

## 首选入口

完整脚本说明和命令模板在 `references/scripts.md`。这里仅保留默认入口，避免在运行时让模型浏览长脚本表。

| 任务 | 首选入口 |
| --- | --- |
| 环境、认证、profile、region/project | `hcloud_environment_doctor.py`、`hcloud_context_inspect.py`、`hcloud_project_resolve.py` |
| 自然语言场景路由 | `hcloud_scenario_router.py` |
| hcloud 版本选择、批量/异步与资源依赖证据、真实查询或受控系统命令 | `hcloud_operation_resolver.py`、`hcloud_operation_behavior.py`、`hcloud_dependency_evidence.py`、`hcloud_safe_exec.py` |
| 多服务发现、目标查询、readiness/live validation（含 CCI 工作负载前检） | `hcloud_resource_discovery.py`、`hcloud_resource_query.py`、`hcloud_service_readiness.py`、`hcloud_live_validation_plan.py`、`hcloud_cci_workload_plan.py` |
| 创建/变更请求预检、风险校验和回读帮助 | `hcloud_request_preflight.py`、`hcloud_change_plan.py`、`hcloud_service_change_plan.py`、`hcloud_guarded_change_flow.py` |
| P0/P1/P2 闭环计划和验收 | `hcloud_closure_plan.py`、`hcloud_acceptance_closure.py` |
| 盘点、闲置、成本、治理 | `hcloud_account_inventory.py`、`hcloud_idle_audit.py`、`hcloud_billing_readonly.py`、`hcloud_billing_live_read.py`、`hcloud_cost_estimate.py` |
| Terraform/IaC | `hcloud_terraform_context_inspect.py`、`hcloud_terraform_router.py`、`hcloud_terraform_operations_plan.py` |
| MaaS 模型调用、图片/视频、用量治理 | `maas_models.py`、`maas_chat.py`、`maas_image_generation.py`、`maas_video_generation.py`、`maas_usage_request_plan.py` |
| 脚本边界、维护分层、完整命令模板 | `references/scripts.md`、`references/script-audience-manifest.json` |

## 资料入口

按任务需要读取，不要一次性加载所有资料：

- 后端选择、运行依赖、基础流程和安全：`references/backend-selection.md`、`references/runtime-dependencies.md`、`references/workflow.md`、`references/runtime-safety-boundaries.md`、`references/auth-and-context.md`
- 跨服务事实、可恢复状态和交互：`references/unified-principles.md`、`references/task-workspace-guide.md`、`references/goal-capability-guide.md`、`references/interaction-guidance.md`
- 场景路由和服务资料：`references/scenario-router.json`、`references/guides/service-guides.md`、`references/playbooks/playbook-index.md`
- CLI 安装、认证和 IAM 权限：`references/cli-installation-guide.md`、`references/auth-and-context.md`、`references/iam-policies.md`
- 命令构造和错误处理：`references/command-construction.md`、`references/error-playbook.md`、`references/output-and-query.md`、`references/hcloud-output-policies.json`
- 脚本索引和公共契约：`references/scripts.md`、`references/public-script-contract.md`、`references/script-audience-manifest.json`
- Terraform：`references/terraform-workflow.md`、`references/terraform/terraform-assets.md`、`references/terraform/operations.md`
- MaaS：`references/maas-model-calls.md`、`references/playbooks/maas-api-readiness.md`、`references/playbooks/maas-usage-governance.md`
- 验证与验收：`references/verification-method.md`、`references/acceptance-criteria.md`、`references/live-validation-profiles.json`
- 覆盖和晋级：`references/service-coverage.md`、`references/operation-behavior-profiles.json`、`references/resource-dependency-profiles.json`、`references/service-curation-profiles.json`、`hcloud_closure_maturity_audit.py`；维护问题覆盖样例时读取 `references/maintenance/question-coverage/question-coverage.md`
- 跨 Agent 评估：`references/cross-agent-evaluation.md`、`references/cross-agent-evaluation-cases.json`、`hcloud_cross_agent_eval.py`；支持本地基线/候选比较和脱敏 journal 摘要，结果仅为建议证据，不是平台门禁
- 版本与兼容策略：`references/versioning-policy.md`
- 知识所有权、渐进加载和材料溯源：`references/source-map.md`、`references/materials-sources.json`

原始 KooCLI 材料在 `materials/` 下，仅作为资料源，不直接当最终指令集使用。涉及 API 字段语义时，以华为云官方文档和实际 `hcloud --dryrun`/查询结果为准。

## 能力边界

- ECS guidance 最完整，覆盖创建前校验、dry-run、job 终态、ACTIVE 回读、SSH 和应用验收。
- P0 高频服务有 lifecycle planner 和 acceptance closure；P1/P2 主要是 governance/scenario planner，不能说成完整执行闭环。
- OBS、MaaS、Billing、SDK、Terraform 都有专门边界；MaaS 是 API-first，Terraform 由 IaC 意图触发，SDK 可在程序化处理或 hcloud 障碍时成为任务后端。
- 长尾安全、数据库、治理、身份和 key 类服务多为 metadata-backed evidence gap；先做发现、计划和证据缺口，不默认执行 mutation。
- 自动 live probe 只支持内置 HTTP/TCP/DNS/TLS；内网、localhost 或 `.local` 目标必须带 `--allow-private-targets` 且来自已审阅的 evidence plan，其他 evidence 需要人工或专用工具采集后再 evaluate。
- 真实账号回归、Terraform state-changing import、计费资源创建/释放仍需要用户提供隔离环境、资源 ID、profile/region 和明确确认。
