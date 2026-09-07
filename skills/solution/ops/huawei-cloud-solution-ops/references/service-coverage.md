# Huawei CLI Service Coverage

本文件说明当前 `huawei-cloud-solution-ops` 对不同服务的覆盖深度。

## 覆盖等级说明

- `High`
  - 有本地 meta cache、helper script、playbook、实际验证
- `Medium`
  - 有服务级 guidance 或 playbook，但动态发现或本地缓存不完整
- `Low`
  - 只有服务存在性或文档层 guidance，暂未形成稳定执行路径
- `Metadata-backed`
  - 不在 curated registry 中，但已进入 `references/hcloud-service-catalog.index.json` 和 `references/hcloud-service-catalog/` 分片
  - 只作为保守兜底层：无必填业务参数的只读 discovery、显式参数只读查询、planner-only 变更计划
  - 不等同于有 playbook、专用 verifier 或真实云变更闭环

## 当前覆盖矩阵

机器可读版本见 `references/service-registry.json`。后续自动化脚本应优先消费 registry，本文件保留人类可读说明。

批量/异步行为证据见 `references/operation-behavior-profiles.json`，运行
`python3 scripts/hcloud_operation_behavior.py --pretty` 可将 registry 与 profile 合成为实时矩阵，
`--format markdown` 可生成下面同形态的维护视图。这里的 `Curated change` 只表示已有 planner/边界，
不表示自动 submit；机器矩阵的 `generic_metadata_backed_available` 和 `metadata_catalog_operation_count`
表示通用 catalog 兜底；`Batch/async profile` 表示有 operation-specific 结果和收敛证据，不表示存在公共轮询框架。

资源依赖证据见 `references/resource-dependency-profiles.json`，运行
`python3 scripts/hcloud_dependency_evidence.py --pretty` 或 `--format markdown` 查看创建前置条件、删除阻断项、
关联资源和回读覆盖。dependency profile 只提供证据，不代表固定执行顺序或自动清理能力。

### 高频服务批量/异步行为证据

| Service | Coverage | Curated change | Batch/async profile | Dependency profile | 当前完成证据 |
| --- | --- | ---: | --- | ---: | --- |
| `ECS` | High | 2 | `CreateServers`、`CreatePostPaidServers`、`DeleteServers` | 2 | create/delete receipt 先视为受理；轮询 `ShowJob` 后逐 ECS 验证 `ACTIVE` 或 `not_found`，并回查 EIP/EVS/ELB/VPC 关联资源 |
| `EIP` | Medium | 10 | `BatchDeletePublicIp` | 2 | 非持久 job receipt 不能轮询；逐 EIP 验证 `not_found`，删除前检查 ECS/ELB/NAT 绑定，删除后回查 DNS/带宽 |
| `VPC` | Medium | 14 | 暂无 | 3 | 子网创建、子网删除和 VPC 删除已有 bounded dependency evidence；仍按实时 List/Show 决定顺序 |
| `EVS` | Low | 8 | `CreateVolume`、`DeleteVolume`、`BatchResizeVolumes` | 3 | `ShowJob` 终态后逐卷验证状态、删除或新容量；删除前检查 ECS attachment，扩容后单独验收 guest 分区和文件系统 |
| `ELB` | Low | 15 | `BatchDeleteLoadbalancers`、`BatchDeletePools` | 5 | LB batch delete 轮询 `ShowJob`；pool batch delete按 `ret_status/ret_code` 逐项分类，并按 member/health monitor 并列阻断图回读 |
| `RDS` | Low | 11 | `CreateInstance`、`DeleteInstance`、`BatchDeleteInstance` | 2 | 通过 `ListJobInfo` 跟踪单 job 或逐实例 job，随后验证 `ACTIVE`/`not_found`；连接和备份仍是独立验收 |
| `NAT` | Low | 6 | 暂无 | 2 | 创建前验证 VPC/subnet，删除前清理 DNAT/SNAT rule，删除后单独回查 EIP |
| `DNS` | Low | 3 | `CreateRecordSet`、`DeleteRecordSet` | 1 | 读取 `PENDING_*`/`ACTIVE`/`ERROR`，最终再做 authoritative DNS、TTL 和应用协议验收 |
| `OBS` | Low | 6 | 暂无 | 1 | bucket 删除前确认对象版本、delete marker 和 multipart upload 已清空；继续走 `hcloud obs` 专用适配器 |

当前 operation profile 的直接收益是避免把 submit receipt、`job_id` 或批量命令退出码误写成逐项完成；
dependency profile 的收益是让 Agent 在提交前看到结构化前置条件/阻断项，并在提交后回查关联资源。未命中
profile 时，Agent 继续使用 resolver、help、官方文档和实时查询，不得猜测同一套状态字段或依赖图。

服务维护档案见 `references/service-curation-profiles.json`。它记录已有 curated 服务和下一批晋级候选的 readiness operation、resource query operation、playbook 和 risk profile。用 `scripts/hcloud_curated_promotion_audit.py --include-curated --pretty` 检查现有 curated 健康状态和候选缺口。

不要把三类数据混为同一个成熟度结论：curation profile 表示当前设计和维护边界，`live-validation-profiles.json` 表示希望采集的闭环证据契约，`hcloud-service-confidence.json` 中标为 `live-read-smoked` 的 operation 才表示曾有真实只读 smoke 证据。没有观测时间、环境和来源时，只能说明“存在过能力证据”，不能声称最近版本、当前账号或所有场景已经验证；只有来源还不够，完整可复现 provenance 还要求具体源码 revision。运行 `scripts/hcloud_closure_maturity_audit.py --pretty` 可查看 `evidence_provenance` 摘要；该审计不会把目标档案冒充运行历史。

| Service | Coverage | 当前状态 | 说明 |
|---------|----------|----------|------|
| `ECS` | High | 最完整 | 本地有 `apis_en.json`、部分 operation detail cache，已验证 `ListFlavors` 的 meta lookup、dry-run、本地参数校验；已有创建 JSON 校验、ShowJob 轮询和 ACTIVE 资源验证脚本 |
| `IAM` | Medium | 可做上下文和 endpoint 发现 | 当前机器仅有 endpoint cache，operation 级 detail 仍不完整 |
| `VPC` | Medium | 有 workflow、playbook、list-only discovery 和第一层 show 查询 | 本地可发现 VPC list/count 型 operation；`ShowVpc`、`ShowSubnet`、`ShowSecurityGroup` 等详情查询需要显式目标 ID |
| `IMS` | Medium | 有 workflow、playbook、list-only discovery 和镜像详情查询 | 本地可发现镜像 list 型 operation；`GlanceShowImage` 等资源级操作需要目标 ID，不作为通用 discovery 入口 |
| `KPS` | Medium | 有 workflow、playbook、list-only discovery 和 keypair 详情查询 | 本地已验证 `ListKeypairs` / `ListKeypairDetail` operation 名称；密钥创建和私钥处理需要专门风险 gate |
| `EIP` | Medium | 有 list/count 型 discovery、`ShowPublicip` 和守护式变更 flow | 本地可发现 EIP、带宽、公网 IP 池、配额等查询 operation；generated catalog 可补充识别 `ListPublicips` 的 `limit` 参数；真实 submit 仍需显式确认 |
| `ELB` | Low | 已登记常用查询入口、第一层 show 查询和 planner-only 变更入口 | service 可见但本地没有 operation detail；用于负载均衡验证和离线问题集覆盖，不等同于完整 ELB 执行能力 |
| `EVS` | Low | 已登记常用查询入口、volume/snapshot 详情和 planner-only 变更入口 | service 可见但本地没有 operation detail；云硬盘挂载、扩容、格式化仍需云侧和 ECS 内双重验收 |
| `NAT` | Low | 已登记常用查询入口、NAT/DNAT/SNAT 详情查询和 playbook | service 可见但本地没有 operation detail；NAT 创建、绑定和删除仍未开放通用变更 |
| `RDS` | Low | 已登记常用查询入口和 planner-only 变更入口 | service 可见但本地没有 operation detail；RDS detail 查询通常需要实例 ID 和引擎相关参数 |
| `OBS` | Low | 走 `hcloud obs`/obsutil 专用适配器 | 不在普通 KooCLI service metadata 中；已支持 bucket list、bucket stat、lifecycle/policy get 和 planner-only bucket/lifecycle/policy 变更计划 |
| `CCE` / `CDN` / `DNS` / `SCM` / `CES` | Low | 已登记最小验证入口、必要 playbook，部分服务支持目标查询 | 来自人工 E2E 验证集和本地 service 存在性检查，仅用于前置发现和回归统计 |
| `DCS` | Medium | 已进入 curated registry，只读 readiness 和实例级 readback | 已有 2 条 read-only live smoke；当前不开放通用 DCS mutation submit |
| `RFS` | Medium | 已进入 curated registry，stack/template/execution plan 只读检查 | 已有 2 条 read-only live smoke；当前不开放通用 RFS mutation submit |
| `UCS` | Medium | 已进入 curated registry，fleet/cluster/policy/addon 只读检查 | 已有 2 条 read-only live smoke；当前不开放通用 UCS mutation submit，`ListManagedClusters` 省略 `--limit` |
| `HSS` / `SecMaster` / `CFW` / `DBSS` / `KMS` | Metadata-backed | P2 安全姿态 evidence gap | 通过 `hcloud_closure_plan.py --tier scenario` 生成只读可见性和缺口计划；不等同于 curated coverage，不开放策略、主机 agent、防火墙、审计或密钥变更 |
| `GaussDB` / `GaussDBforNoSQL` / `GaussDBforopenGauss` / `DDS` / `DDM` / `DWS` | Metadata-backed | P2 数据库族 evidence gap | 通过 `hcloud_closure_plan.py --tier scenario` 复用 RDS 式备份、连接、参数、重启影响和回滚证据模型；不开放参数、重启、恢复、删除等数据库变更 |

`query_operations` 表示可作为通用 discovery 起点的查询。`resource_query_operations` 表示已知资源 ID 或上下文后才适合执行的查询，覆盖统计会计入，但 `hcloud_resource_discovery.py` 不会默认把它们当作 list-only 操作执行。
`hcloud_resource_query.py` 可执行 `resource_query_operations` 和需要显式目标参数的只读查询；缺少目标参数时会失败，不会替用户猜资源 ID。
`hcloud_resource_discovery.py` 和 `hcloud_resource_query.py` 会对 operation 名称做宽松匹配，因此问题集里的 `showvpc`、`listcloudservers` 这类写法可以解析到 registry 中的规范 KooCLI operation。
`query_runner` / `resource_query_runner` 用于非普通 OpenAPI-style 服务；OBS 会路由到 `scripts/hcloud_obs_readonly.py`，避免生成错误的 `hcloud OBS Operation` 命令。
`change_operations` 中的非 ECS 项当前表示 `hcloud_service_change_plan.py` 可生成 planner-only 风险计划，不表示已经允许自动提交真实变更。
`supported_cli_regions` / `preferred_cli_region` 用于记录 KooCLI 层面的区域限制；例如 CDN `ListDomains` 会从不支持的业务 region 自动落到 `cn-north-1` 执行只读 discovery。

## Generated catalog 覆盖

`references/hcloud-service-catalog.index.json` 和 `references/hcloud-service-catalog/` 是从 hcloud metadata 生成的运行时 lazy catalog；full catalog 只在维护期需要 operation 级完整 diff 时临时生成，不提交到仓库。准确服务数、operation 数和 registry 外 metadata-backed 服务清单不要在文档中手写，应从下面的脚本输出读取：

```bash
python3 scripts/hcloud_catalog_audit.py --pretty
```

主要字段：

- `catalog.service_count` / `catalog.operation_count`：generated catalog 覆盖规模。
- `registry.service_count` / `registry.*_operation_count`：curated registry 控制面规模。
- `metadata_backed.service_count` / `metadata_backed.services`：registry 外的 metadata-backed 服务清单。
- `references/hcloud-service-catalog.fingerprint.json` 的 `source` 字段：metadata 升级 review 用的小体积事实源。

这些服务的默认边界：

- `hcloud_resource_discovery.py` 只自动选择无必填业务参数的 read-only discovery 操作，并限制默认数量。
- `hcloud_resource_query.py` 可以为 read-only operation 生成命令，但必填参数必须由用户或上游工具显式提供。
- `hcloud_service_change_plan.py` 可以为 mutating operation 生成 planner-only 风险计划；真实 submit 仍需要单独确认，不会自动执行。metadata-backed mutation 的 dry-run 支持默认为 `unknown`，不会自动假设支持 dry-run。
- metadata-backed planner 会读取 catalog service `category` 作为风险下限；安全合规、身份、密钥和治理类 mutation 会标记 `risk.hard_guard=true`，通用 guarded flow 不得自动执行 submit。
- `hcloud_catalog_audit.py --fail-on-drift` 用于确认 curated registry 没有引用 catalog 中已消失的 operation。
- `hcloud_catalog_readonly_smoke.py` 用于小批只读实测，并把失败归因到命令形态、账号权限、服务开通、region/project、参数或网络等桶；新生成的 record 和 confidence suggestion 共用观测时间，并携带受限、非敏感的来源与环境信息。
- `hcloud-service-catalog.index.json` 是运行时轻量索引；`hcloud-service-catalog/` 保存 per-service payload；`hcloud-service-catalog.fingerprint.json` 是 review 用小体积指纹；`hcloud-service-confidence.json` 是 live smoke/confidence/dry-run 支持性的 sidecar。

当前 metadata-backed operation 级 live smoke 证据见 `references/hcloud-service-confidence.json` 和 `tests/manual-validation-2026-06-05.md`。已通过只读 smoke 的 operation 可以标为 `live-read-smoked`；只有服务写入 `references/service-registry.json` 后才算 curated registry 覆盖。

`DCS`、`RFS`、`UCS` 已从候选提升为 read-only curated registry 覆盖。下一批候选包括 `WAF`、`CodeArtsRepo`、`DLI`、`CTS`、`TMS`、`CBR`、`RMS`、`Config`、`LTS`。这些服务已有 candidate profile、playbook、risk profile 和用户价值标签；是否进入 registry 仍取决于 live read smoke 证据和维护面决策。

`CTS`、`TMS`、`CBR`、`RMS`、`Config`、`LTS` 当前用于补齐“管好云”和“用好云”的治理、审计、备份、标签、资源合规和日志能力。它们仍是 metadata-backed candidate，不等同于默认可执行覆盖；晋级前至少需要补齐只读 live smoke、目标型查询样例和失败分桶记录。

## 已实测能力

### ECS

- `hcloud ECS --help`
- `hcloud_meta_lookup.py --service=ECS`
- `hcloud_meta_lookup.py --service=ECS --operation=ListFlavors`
- `hcloud ECS ListFlavors --dryrun`
- `hcloud_safe_exec.py` 包装查询和错误分类
- `hcloud_ecs_create_plan.py` 本地校验 ECS 创建 JSON 并生成 dry-run / submit 命令
- `hcloud_ecs_wait_job.py --print-command-only` 生成 `ShowJob` 轮询命令
- `hcloud_ecs_verify_active.py --print-command-only` 生成 `ListServersDetails` ACTIVE 验证命令
- `hcloud_change_plan.py` 为变更操作生成风险摘要和 dry-run/submit 命令

### 非 ECS

已实测：

- `IMS`
- `VPC`
- `KPS`
- `EIP`
- `ELB`
- `EVS`
- `NAT`
- `RDS`
- `CCE`
- `CDN`
- `DNS`
- `SCM`
- `CES`
- `OBS` 的 `hcloud obs help`、`hcloud obs help ls`、`hcloud obs help lifecycle` 和 `hcloud obs version`

结果：

- 在 `services_en.json` 中可以看到这些 service
- 本地 template cache 覆盖深度不一致；EIP / VPC 等可能只有 operation index，ELB / EVS / NAT / RDS 等当前只有 service 入口，缺少 per-operation detail
- `hcloud_resource_discovery.py` 可以按 registry 为这些服务生成 list-only 查询命令，但真实执行仍依赖本机 hcloud metadata 和账号权限
- `hcloud_resource_query.py` 可以为 EIP `ShowPublicip`、VPC `ShowVpc/ShowSubnet/ShowSecurityGroup/ShowSecurityGroupRule`、ELB `ShowLoadBalancer/ShowListener/ListMembers`、EVS `ShowVolume/ShowSnapshot`、IMS `GlanceShowImage`、KPS `ListKeypairDetail`、NAT `ShowNatGateway/ShowNatGatewayDnatRule`、RDS `ShowConfiguration`、CCE `ShowCluster/ListNodes`、CDN `ShowDomainDetail`、DNS `ShowRecordSet`、SCM `ShowCertificate` 等目标型只读查询生成可执行命令；旧验证文本里的 CDN `ShowDomain` 和 RDS `ShowConfigurationDetail` 会被覆盖检查映射到 KooCLI 实际操作
- `hcloud_service_readiness.py` 可以按服务批量生成或执行只读 readiness 检查，并汇总资源数量和状态计数
- 默认 readiness 顺序按问题集频次广度优先排列：ECS、VPC、RDS、IMS、EVS、EIP、ELB、NAT、KPS、IAM，然后补 CCE、CDN、DNS、SCM、OBS、CES
- `hcloud_readonly_smoke.py` 可以批量生成或执行多服务只读 smoke 查询
- `hcloud_obs_readonly.py` 可以为 OBS `ListBuckets`、`StatBucket`、`GetBucketLifecycle` 和 `GetBucketPolicy` 生成或执行 `hcloud obs` 只读命令
- `hcloud_obs_change_plan.py` 可以为 OBS bucket/lifecycle/policy 变更生成 planner-only 命令和后置验证计划，不执行 submit
- `hcloud_resource_detail_probe.py` 可以顺序执行 list-then-detail 抽样；EVS/NAT 当前区域无资源时会返回 skipped，而不是把缺资源当作失败
- CDN `ListDomains` 已验证需要使用 KooCLI 支持区域；registry 会把 `cn-north-4` 调整到 `cn-north-1`
- `hcloud_service_change_plan.py` 可以为多服务变更生成风险计划和验证建议，但不会执行 submit
- `hcloud_operation_behavior.py` 和 `hcloud_dependency_evidence.py` 已为 ECS/VPC/EIP/EVS/ELB 的高频创建、删除和扩容操作提供结构化 request target、submit receipt、依赖和回读证据；这些是本地事实层，不执行轮询或工作流，也不等同于新增 live smoke
- `hcloud_cost_estimate.py` 可以复用 BSS 询价计划为一个明确 SKU 生成或获取点时价格；未执行询价时金额保持 unknown，且 ECS compute、EVS、EIP、流量等组件边界不会被合并猜测
- `hcloud_closure_plan.py --tier lifecycle` 可以为 VPC/安全组、EIP、EVS、ELB、RDS、OBS、DNS、SCM、CDN、CES/LTS 生成六阶段任务闭环计划，组合 change plan、readiness、OBS/LTS 专用适配器和本地风险策略，但不会执行真实云变更
- `hcloud_closure_plan.py --tier governance` 可以为 TMS、CTS、CBR、RMS/Config、Billing/BSS、WAF、DLI、CodeArtsRepo 生成五阶段治理闭环计划，组合 curation profile、promotion audit、read-only evidence command plan、Billing request spec 和风险/隐私门禁，但不会执行治理写操作、签名请求或访问真实账单；Billing/BSS 不生成 live query 命令
- `hcloud_closure_plan.py --tier scenario` 可以为 CCE、NAT、DCS、RFS、UCS、IAM/KPS/IMS、安全姿态和数据库族生成四阶段场景闭环计划，组合 curation profile、metadata catalog、read-only discovery、resource query 和风险边界；安全姿态和数据库族当前输出 `metadata_evidence_gap`，不会执行集群、NAT、缓存、IaC、多集群、安全、密钥、IAM 或数据库写操作
- `hcloud_eip_change_flow.py` 可以把 EIP 变更串成 Plan -> dry-run -> guarded submit -> ShowPublicip verify；默认不执行 submit，且 submit 必须显式确认
- `hcloud_guarded_change_flow.py` 可以为 VPC、ELB、EVS、NAT、RDS、CDN、DNS、SCM 等普通服务提供通用 Plan -> dry-run -> guarded submit -> resource Show* verify -> read-only smoke 的 P0 门禁；默认不执行 submit
- `hcloud_resource_verify.py` 可以基于 JSON 查询结果验证 EIP、VPC、ELB、EVS、NAT、RDS、CCE、CDN、DNS、SCM 等资源状态
- `check_question_coverage.py` 可用外部 `generated_questions` 和 `data-by-changping/data.xlsx` 回归验证 schema、CRUD type、风险分类、registry 覆盖、人工验证步骤风险线索和已注册验证 operation 的执行路径

## 对 agent 的实际意义

### 当用户任务在 ECS 范围内

可以较积极地：

- 做 command discovery
- 做 dry-run
- 做查询链路验证
- 对创建 JSON 做占位符和关键字段本地校验
- 真实创建返回 `job_id` 后轮询到终态

### 当用户任务在 VPC / IMS / KPS / IAM / EIP 范围内

当前更适合：

- 先做上下文确认
- 先用 service 级 discovery 和 playbook 梳理动作
- 已知资源 ID 时，可用 `hcloud_resource_query.py` 做第一层详情查询
- EIP 变更优先用 `hcloud_eip_change_flow.py` 生成计划、dry-run 和 `ShowPublicip` 后置验证；真实 submit 需要单独确认
- VPC 变更可用 `hcloud_guarded_change_flow.py` 生成通用门禁计划和只读 smoke 后验计划；真实 submit 需要单独确认
- 把真实变更执行建立在进一步元数据可用之后

### 当用户任务在 ELB / EVS / NAT / RDS / CCE / CDN / DNS / SCM / CES 范围内

当前只把 registry 当作查询线索：

- 先确认本地 `hcloud <service> --help` 是否能拿到 operation 帮助
- 优先执行 list/count 类低风险查询；已知目标 ID 时可用 `hcloud_resource_query.py` 执行目标型 show/list 查询
- 多服务现状检查优先用 `hcloud_service_readiness.py`，目标型检查缺参数时应明确 skipped，而不是猜测资源 ID
- 涉及创建、绑定、扩容、停用、删除、证书部署等动作时，先用 `hcloud_guarded_change_flow.py` 走通用风险门禁；集群变更等未登记 change operation 仍需要先补专门 planner 和验证器

不要伪装成已经有了和 ECS 一样完整的操作细节。

### 当用户任务在 OBS 范围内

当前走 `hcloud obs`/obsutil 路线：

- bucket list 用 `hcloud_obs_readonly.py --operation ListBuckets`
- bucket 详情或生命周期查询必须显式传 `--bucket`
- bucket、lifecycle、policy 写类操作只用 `hcloud_obs_change_plan.py` 生成 planner-only 命令
- OBS 输出是文本，不能按标准 OpenAPI JSON verifier 处理；最终需要结合 obsutil 输出和后续只读查询确认
