# Huawei CLI Workflow

这是 `huawei-cloud-solution-ops` 的通用执行框架。Agent 按任务复杂度裁剪步骤，并根据
`backend-selection.md` 自主选择后端；不要为了满足文档机械调用无关工具。

## Phase A: Clarify Intent

先把用户任务归类为下面三类之一：

- 查询类
  - 例如列实例、查规格、查售卖策略、查配置
- 规划类
  - 例如创建前参数准备、依赖梳理、排查路径设计
- 治理类
  - 例如账号盘点、闲置审计、回收前检查、可观测证据、账单/成本请求规划
- 变更类
  - 例如创建、修改、删除、启停、扩缩容

如果用户目标是跨服务、宽泛、架构不明确或“上云/用云/管云”式任务，可以运行本地场景路由：

```bash
python3 scripts/hcloud_scenario_router.py "<user-goal>" --pretty
```

路由结果只用于选择 `references/playbooks/`、`references/guides/`、planner、SDK supplement 和 Terraform 候选。对于带 `scenario_contract` 的重点场景，还要按契约确认输入、采集证据并组织交付；它不执行 hcloud、SDK 或 Terraform 操作。

网站部署目标的运行载体或动态能力不明确时，可用顶层 `architecture_decision` 辅助澄清：

- `explicit_constraints` 是用户明确指定的运行载体或入口要求，优先于低成本默认值。
- 用户指定机器、ECS、公网 IP、SSH、Nginx 或 Docker 时，不得自动替换成 OBS。
- `change_execution_blocked=true` 时，先询问 `clarification_question`；确认前停止创建、购买、上传、公开访问和其他写操作。
- `change_execution_blocked=false` 只表示架构无需继续澄清，不表示用户已经授权执行。涉及计费资源、公网暴露、域名/DNS/HTTPS 或 MaaS 图片/视频调用时，先给出合并方案并等待用户明确确认；原始“搭建/部署”请求只授权规划和只读预检。
- 不要因为 agent 已经生成了纯 HTML/CSS/JS 文件，就反向推断用户原需求必然是 OBS 静态托管。

如果路由结果或用户原话明确指向 Terraform/IaC、环境复制、import、drift review 或长期纳管，再运行 Terraform 资产路由：

```bash
python3 scripts/hcloud_terraform_router.py "<user-goal>" --pretty
```

只读取 router 返回的少量 examples/reference。不要为了“支持 Terraform”而全量浏览 `examples/terraform/`，也不要把只读查询、状态核验或普通排障强行转成 Terraform。

## Phase B: Select Backend and Inspect Context

默认优先考虑 hcloud，并可先运行：

```bash
python3 scripts/hcloud_context_inspect.py --pretty
```

目标：

- 确认 `hcloud` 是否存在
- 确认当前 profile 是否存在
- 确认默认 region、project、domain 是否已配置
- 确认是否处于 offline mode
- 确认本地 meta cache 是否存在

如果上下文不完整，再考虑 `hcloud configure show` 或 `hcloud configure list`。

如果 hcloud 不可用或 SDK 对类型化请求、复杂处理、分页/并发更合适，检查官方服务 package、
BasicCredentials/GlobalCredentials、region/endpoint 和异常结构。不要因 hcloud 缺失就直接终止整个任务。

当用户意图明确进入 Terraform 路线时，再运行：

```bash
python3 scripts/hcloud_terraform_context_inspect.py --pretty
```

目标是确认 Terraform CLI、hcloud、认证环境变量、provider cache、catalog 和禁止提交的 runtime artifact 状态。没有 Terraform CLI 时，可以生成 IaC 草案，但不能宣称已经 fmt/init/validate/plan。

## Phase C: Discover Service and Operation

hcloud 路径的推荐顺序：

1. 查看 `references/service-registry.json`，确认当前 service 的覆盖等级、playbook、planner/verifier 和已知限制
2. `python3 scripts/hcloud_meta_lookup.py --service=<service> --pretty`
3. `hcloud --help`
4. `hcloud <service> --help`
5. `hcloud <service> <operation> --help`
6. hcloud metadata/help 不足时，可用 `python3 scripts/hcloud_sdk_catalog.py --service=<service> --operation=<operation> --pretty` 补充 SDK 参数类型、region、endpoint 或 path/query/body 证据，或改选官方 SDK 完成当前任务

原则：

- 不要先猜 operation 名。
- 先看本地 meta cache 里有没有现成线索。
- 先通过 service 级帮助确认当前 CLI 是否支持目标服务。
- 当前 CLI 的 operation 清单比记忆更可信。
- SDK 是受支持的程序化后端，但优先使用已安装 package，不要求存在 SDK 源码。便捷 runner 的 registry
  只限制该 runner，不限制 Agent 编写经核验的任务专用 SDK 代码。

## Phase D: Build a Stable Command

### 查询类默认规则

- 默认加 `--cli-output=json`
- 结果过大时优先：
  - 加 `limit`
  - 加过滤参数
  - 加 `--cli-query`
- 对 registry 中已有的 list-only 操作，可以先用 `python3 scripts/hcloud_resource_discovery.py --service=<service> ... --pretty` 生成命令，再决定是否 `--execute`
- `references/sdk-supplement-registry.json` 内的稳定 SDK 只读查询可以用 `hcloud_sdk_readonly.py` 生成
  计划或显式执行；未登记的任务可优先走 hcloud，或在核验官方 package/API 后编写最小 SDK 代码。

### 变更类默认规则

- 默认先用 `python3 scripts/hcloud_change_plan.py ... --pretty` 生成风险摘要
- 支持 dry-run 时先 `--dryrun`
- 优先把复杂 body 放进 `--cli-jsonInput`
- 不把 `hcloud_sdk_readonly.py` 扩成通用写操作 runner。具体变更优先使用有证据的 hcloud；SDK 更合适
  时可编写任务专用代码，并遵守相同的风险、授权、幂等、收敛和回读要求。Terraform 是独立 IaC 链路。
- 当用户明确需要 IaC、环境复制、import/drift review 或长期纳管时，读取 `references/terraform-workflow.md` 和 `references/terraform/terraform-assets.md`；先用 `hcloud_terraform_router.py` 选示例和 reference。发现和后置验证优先 hcloud，也允许等价 SDK/API、data source/provider refresh 和业务探测证据。
- 真执行前先补齐：
  - region
  - project
  - 依赖资源
  - 幂等和回滚考虑

### 治理类默认规则

- 账号盘点先走 `hcloud_account_inventory.py`，真实查询必须显式 `--execute`。
- 闲置审计只读取保存的 JSON 输出，走 `hcloud_idle_audit.py`，候选不等于删除授权。
- 回收前检查走 `hcloud_teardown_plan.py`，只输出依赖顺序和检查项，不生成 submit 命令。
- 可观测先走资源状态和 CES metric discovery，再按需生成 CES alarm planner 或 LTS 只读日志查询。
- Billing/Cost 先走 `hcloud_billing_cost_probe.py` 和 `hcloud_billing_readonly.py`；request spec 不等于已经签名或发送请求。

## Phase E: Execute

hcloud 命中已支持的调用时，推荐优先使用统一包装脚本：

```bash
python3 scripts/hcloud_safe_exec.py ...
```

原因：

- 有统一 JSON 结果
- 有输出脱敏
- 有错误类型识别
- 更适合后续自动化处理

脚本未覆盖不表示 operation 禁止执行。Agent 可以基于 metadata/help 直接运行经过验证的 hcloud，
或选择官方 SDK；公共脚本只是高频捷径。

## Phase F: Validate

执行后必须做结果判断：

- 非空 JSON 返回：
  - 校验核心字段
  - 只提取用户关心的部分
- 空响应体：
  - 必要时加 `--debug`
  - 查看状态码
- 长任务：
  - 谨慎考虑 `--cli-waiter`
- 异步 job：
  - 先验证 job 终态
  - 再验证资源终态，例如 ECS 还要用 `hcloud_ecs_verify_active.py` 确认目标实例 `ACTIVE`

## Phase G: Record When Needed

多步真实操作建议写 run journal：

```bash
python3 scripts/hcloud_run_journal.py \
  --journal=<path-to-jsonl> \
  --append-json='{"type":"command","success":true}' \
  --pretty
```

run journal 用于审计和断点恢复，不应写入 AK/SK、token、密码等敏感信息。

## 三层回退策略

当 operation 帮助或 live metadata 失败时，按下面顺序回退：

1. 当前命令本身返回的 service 级帮助
2. 本地 `~/.hcloud/metaRepo` 缓存
3. `references/` 中整理过的规则和 playbook
4. 原始 `materials/` 文档

不要在没有证据时直接猜参数。

## 查询类与变更类的不同交付方式

### 查询类

- 默认给结论
- 必要时给关键字段
- 大结果默认先筛选或汇总，不直接把整份结果塞回对话

### 变更类

- 默认给执行前提和变更计划
- 真执行后给：
  - 是否成功
  - 关键返回字段
  - 后续验证建议

## 何时停止并向用户确认

在以下场景，应暂停自动推进并向用户确认：

- 不可逆删除
- 真实创建或修改会产生费用
- 账单、成本、日志、审计 trace 等输出可能包含敏感数据
- 当前配置范围可能不是用户预期的账号或项目
- 关键参数有多个候选且影响较大
