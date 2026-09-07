# Terraform Generation Guardrails

本文件统一可复用的 Terraform 生成规则：先发现现网，再生成 IaC 草案；先 plan review，再由用户明确确认 apply；apply 后必须用实时云侧和业务证据验收。发现与回读优先 hcloud，也允许等价 SDK/API、Terraform data source/provider refresh 和协议探测。

## 生成前必须确认的事实

不要编造这些信息：

- region、project、企业项目
- AZ、镜像、规格、磁盘类型
- VPC、subnet、安全组、EIP、ELB、RDS、CCE 等现有资源 ID
- 价格、库存、售罄状态
- apply、验证或修复过程

事实来源只能是：

- 用户明确输入
- hcloud 只读查询和现网发现
- 官方 SDK/API 的当前只读查询
- Terraform data source 在 plan 阶段解析出的结果
- 本地 provider schema / inventory 提供的字段结构线索

如果事实没有确认，只能标成 pending 或 recommendation，不能写成已验证结论。

## 汇报叙事必须真实

Terraform 生成和验证过程里，最终汇报只能描述真实发生过的动作和真实输出：

- 没有运行 `terraform init`、`validate`、`plan`、`apply`、`import`、`state` 或实时 readback，就不要写成已运行。
- 如果第一次 `plan` 就通过，不要虚构“先失败再修复”的过程。
- 如果只生成了文件或命令草案，状态是 `prepared`，不是 `verified`。
- 如果只做了 `terraform plan`，状态是 IaC 层可计划，不等于云资源已存在或业务可用。
- 如果 apply 后没有云侧 readback、健康检查或协议探测，不要说“上线完成”。

推荐输出按状态分组：`planned`、`generated`、`validated`、`planned_by_terraform`、`applied`、
`verified_by_cloud_readback`、`blocked`。缺少哪一层，就明确写缺口。

## 首选证据流程

1. 优先用 `hcloud_context_inspect.py` 和服务发现脚本确认账号、region、project 和现网资源；hcloud
   不可用时使用等价 SDK/API 或 data source/provider refresh。
2. 用 `hcloud_terraform_context_inspect.py` 检查 Terraform CLI、provider cache、环境变量、mirror 配置和禁止提交产物。
3. 用 `hcloud_terraform_router.py` 只选择少量相关 example/reference。
4. 对目标 region 做资源可用性和依赖校验，不能把其它 region 的规格、镜像或 AZ 直接套用。
5. 生成或改造 Terraform 草案。
6. 运行 `terraform fmt`、`terraform init`、`terraform validate`、`terraform plan`。
7. 摘要 plan 里的新增、修改、删除、替换、停机和计费风险。
8. 用户明确确认 exact plan 后才能 apply。
9. apply 后优先回到 hcloud 做资源 readback；不可用时使用等价 SDK/API 查询，并继续健康检查、
   协议探测和业务验收。

## 生成前可用性校验

Terraform 代码生成前，必须先确认目标 region 中的关键候选值是否可用。没有确认的值只能保留为变量、待确认项或 data source 过滤条件，不能写成“已验证默认值”。

| 场景 | 必查事实 | 推荐来源 |
| --- | --- | --- |
| ECS | AZ、flavor、image、subnet、安全组、EIP 需求 | hcloud 发现、`hcloud_resource_discovery.py`、官方 SDK/API |
| OBS 静态站 | bucket name、region、website endpoint、自定义域名和 DNS 归属 | `hcloud_obs_readonly.py`、`obs-static-website-hosting.md` |
| RDS | 引擎版本、实例模式、flavor、AZ 组合、备份和连接边界 | hcloud 发现、RDS playbook、provider data source |
| CCE | cluster flavor、subnet DNS、节点 flavor、key pair、addon 变体 | hcloud 发现、CCE playbook、provider data source |
| ELB/NAT/CDN/DNS | subnet、EIP、listener/record/origin 参数、region 限制 | hcloud 发现、对应 playbook |

如果查询失败，不能直接用模型经验继续生成可执行配置。正确处理方式是：

- 把失败原因归类为认证、权限、region/project、网络、参数或服务不可用。
- 给出缺口和下一步检查命令。
- 只输出草案或变量模板，不宣称 plan 可通过。

## 费用提示

在 `terraform plan` 通过后、任何 apply 建议之前，必须用用户能理解的方式列出可能产生持续费用的资源：

- ECS/Flexus、EVS、EIP/带宽、ELB、RDS、CCE node、OBS/CDN/DNS/SCM。
- 如果没有准确价格，只能说“请以价格计算器/订单页为准”，不能编造金额。
- 删除、替换、停机、包周期购买、退订和公网带宽都要单独提示。

## 文件结构规则

推荐示例结构：

- `versions.tf`
- `provider.tf`
- `variables.tf`
- `main.tf`
- `outputs.tf`，只在有明确验收价值时添加
- `terraform.tfvars.example`
- `README.md`

禁止提交：

- 真实 `terraform.tfvars`
- `.terraform/`
- `terraform.tfstate*`
- `crash.log`
- AK/SK、token、密码、私钥、证书私钥

## Provider 和凭据规则

- Provider 源必须是 `huaweicloud/huaweicloud`。
- 新示例优先使用 `HW_*` 变量语义，并兼容 `OS_*` / `HUAWEICLOUD_*` 诊断。
- 不要在 `.tf` 或 `tfvars` 中写真实 AK/SK。
- 不要在对话中要求用户粘贴 AK/SK、token、密码或私钥。
- shared hcloud config 只有在未加密且用户理解风险时才适合 Terraform provider 复用。

## Data Source 优先规则

这些值优先通过 data source 或 hcloud 发现，不要硬编码：

- ECS image、flavor、AZ
- CCE cluster flavor、node flavor、addon template
- RDS flavor、引擎版本、AZ 组合
- ELB flavor、可用区
- 现网 VPC、subnet、安全组、EIP、port

Data source 查询必须使用精确过滤条件。不要用模糊名称猜资源，也不要在结果为空时静默 fallback 到硬编码值。

## Import / Drift / State 规则

- 现网资源纳管先读 `references/terraform/operations.md`，再决定 import、data source 还是重建。
- `terraform import`、`terraform state mv`、`terraform state rm`、`terraform init -migrate-state` 都会影响 state，不自动执行。
- drift review 先跑 `terraform plan -refresh-only` 和 `terraform plan -detailed-exitcode`，再分类差异来源。
- remote state 迁移前必须确认 backend、锁、加密、访问控制、workspace 和 state 备份。
- state 可能包含敏感字段，任何 `terraform state show` 输出都要脱敏。
- import 或 drift 处理后仍要回到 hcloud 做资源 readback 和业务验收。

## 安全组规则

- 端口必须是 `1-65535`，不能使用 `0`。
- SSH、数据库、管理端口、常见 Web 端口不应默认开放给 `0.0.0.0/0`。
- 示例里的公网来源 CIDR 应使用文档占位，例如 `203.0.113.10/32`，并提醒用户替换为真实授权来源。
- 内网服务优先限制在 VPC CIDR、subnet CIDR 或明确的后端安全组。

## 敏感字段规则

示例中如果需要密码：

- 优先使用 `random_password` 或要求用户在本地 `terraform.tfvars` 中填写。
- 不要把生成出的真实密码写进 README、日志或提交文件。
- 不要把密码输出成 Terraform output，除非有明确的安全处理策略。

## 验证门禁

每个吸收进 `examples/terraform` 的示例至少满足：

- `terraform.tfvars` 已改成 `terraform.tfvars.example`
- `README.md` 不要求用户在对话中暴露敏感信息
- catalog 能被 `hcloud_terraform_router.py` 命中
- `hcloud_terraform_context_inspect.py` 不报告 forbidden artifact
- `terraform fmt -check -recursive` 通过
- 在 provider 可用时，`terraform init -backend=false` 和 `terraform validate` 通过

## 不吸收的上游行为

- 不把外部 generator 作为 `huawei-cloud-solution-ops` 的默认入口。
- 不自动安装 Terraform 或 provider。
- 不自动 apply。
- 不自动 destroy。
- 不把 provider mirror 网络下载当成默认执行动作。
