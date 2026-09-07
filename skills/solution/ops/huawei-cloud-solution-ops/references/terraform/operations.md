# Terraform Operations: Import, Drift, and Remote State

Terraform 在本 Skill 中是由 IaC 意图触发的执行面，适合长期纳管、环境复制、plan review 和 drift 管理。现网真相、资源发现、权限诊断和后置验收优先使用 `hcloud`，也允许等价 SDK/API、data source/provider refresh 和业务探测证据。

## 适用场景

- 用户要把现网资源纳入 Terraform 管理。
- 用户担心 Terraform state 和云上资源不一致。
- 用户要多人协作或 CI/CD，需要 remote state。
- 用户要 review drift，但不确定能不能直接 apply。
- 用户已有 Terraform 代码，要确认 plan 是否会替换或删除资源。

## 总原则

- 先做现网只读发现，再决定 import、data source 还是新建；hcloud 优先，但不是唯一证据源。
- 不自动执行 `terraform import`、`terraform state rm`、`terraform state mv`、`terraform apply` 或 `terraform destroy`。
- 不把 `terraform.tfstate*`、真实 `terraform.tfvars`、`.terraform/`、AK/SK、token、密码、私钥提交进仓库。
- drift review 的结论必须区分“Terraform 配置不一致”“state 过旧”“云侧资源被手工改动”“provider schema 变更”和“数据源解析变化”。
- apply 后必须做实时资源 readback 和业务验收。

## Import 流程

1. 明确 import 目标：
   - service / resource type
   - region / project / enterprise project
   - 云上 resource ID
   - Terraform resource address，例如 `huaweicloud_vpc_vpc.main`

2. 优先用 hcloud 查询资源事实；不可用时使用等价 SDK/API 或 data source/provider refresh：

```bash
python3 scripts/hcloud_resource_discovery.py \
  --service <SERVICE> \
  --region=<region> \
  --pretty
```

有 ID 后再用 target-scoped query 确认：

```bash
python3 scripts/hcloud_resource_query.py \
  --service <SERVICE> \
  --operation <ShowOperation> \
  --region=<region> \
  --param <id_param>=<resource_id> \
  --pretty
```

3. 查 provider import 线索：

```bash
python3 scripts/hcloud_terraform_provider_inventory.py \
  --provider-root <provider-source-root> \
  --signal-kind resources \
  --signal-name <provider_resource_name> \
  --pretty
```

4. 先写最小 Terraform resource block，不填无法确定的可选字段。

5. 只生成 import 命令草案：

```bash
terraform import <resource_address> <resource_id>
terraform plan -refresh-only
terraform plan
```

6. import 后 review state 与配置差异，不能立刻 apply。

## Drift Review 流程

1. 检查工作区：

```bash
python3 scripts/hcloud_terraform_context_inspect.py --pretty
```

2. 拉取/刷新 state 前先确认 backend、workspace 和锁。

3. 运行只读 drift 检查：

```bash
terraform plan -refresh-only
terraform plan -detailed-exitcode
```

4. 对差异分类：

| 差异类型 | 判断 | 下一步 |
| --- | --- | --- |
| 云侧手工改动 | hcloud readback 与 Terraform 配置不同 | 决定保留云侧变更并更新 `.tf`，或用 Terraform 改回。 |
| state 过旧 | 云侧事实正确，但 state 没刷新 | 先 refresh-only，慎用 state 命令。 |
| 配置 drift | `.tf` 与目标状态不同 | review plan，确认新增/修改/删除/替换。 |
| provider/schema 变化 | provider 升级后 plan 改变 | 固定版本、读 changelog、重新 validate。 |
| data source 变化 | 查询条件不精确或返回对象变化 | 收紧过滤条件，避免名称模糊匹配。 |

5. 输出用户能判断的摘要：新增、修改、删除、替换、ForceNew、停机、费用、回滚方式。

本地可以先生成 import / drift / remote state 的受控执行计划：

```bash
python3 scripts/hcloud_terraform_operations_plan.py \
  --operation full \
  --import-target 'huaweicloud_compute_instance.app=<server-id>' \
  --readback ECS:ShowServer:server_id=<server-id> \
  --pretty
```

该工具默认不执行 `terraform import`。如果确实要执行 state-changing import，先 review 计划里的 `confirm_token`，再显式传入：

```bash
python3 scripts/hcloud_terraform_operations_plan.py \
  --operation import \
  --import-target 'huaweicloud_compute_instance.app=<server-id>' \
  --execute-import \
  --allow-state-change \
  --confirm-token <confirm-token>
```

## Remote State 流程

remote state 的目标是协作和锁，不是把 state 暴露给更多人。启用前确认：

- backend 类型、bucket/container、region、加密、访问控制。
- state lock 是否可用。
- workspace 命名和环境隔离。
- 谁可以读 state；state 可能含敏感字段。
- CI/CD 用的凭据和本地用户凭据是否分离。

建议先用本地 backend 完成最小 plan，再迁移 remote state。迁移前备份本地 `terraform.tfstate`，迁移后确认：

```bash
terraform init -migrate-state
terraform state list
terraform plan -refresh-only
```

不要在没有备份、锁和访问控制评审的情况下迁移生产 state。

## State 命令边界

| 命令 | 风险 | 边界 |
| --- | --- | --- |
| `terraform state list/show` | 可能输出敏感字段 | 输出前脱敏。 |
| `terraform state mv` | 改变资源地址 | 需要清晰的 address 映射和备份。 |
| `terraform state rm` | 让 Terraform 忘记资源 | 不删除云资源，但会造成失管，必须确认。 |
| `terraform import` | 写 state | 先确认云资源 ID 和 resource address。 |
| `terraform refresh` | 可能更新 state | 优先用 `plan -refresh-only` review。 |

## 实时后置验证

Terraform 操作完成后至少做：

- 优先用 hcloud 查询 imported/changed resources；不可用时使用等价 SDK/API 或 data source/provider refresh。
- 对网络资源查 VPC/subnet/security group/EIP/ELB 绑定关系。
- 对计算和容器资源查状态、事件、日志和指标。
- 对数据库查实例状态、备份、连接和参数。
- 对外部访问路径做协议探测或证据收集。

没有实时云侧 readback 和所需业务证据，不应声称 Terraform 操作已经闭环。
