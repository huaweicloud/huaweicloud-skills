# ECS Create Readiness Playbook

## 目标

在真正创建 ECS 前，把依赖项和购买约束查清楚，避免直接拼 `CreateServers` 失败。

## 适用场景

- 用户要创建 ECS
- 用户要生成创建命令或 `cli-jsonInput`
- 用户要评估某个 region / AZ / flavor 是否可用

## 已验证可直接参考的 ECS operation

- `ListServerAzInfo`
- `ListFlavors`
- `ListFlavorSellPolicies`
- `CreateServers`
- `CreatePostPaidServers`

## 默认执行顺序

### 1. 上下文确认

先确认：

- 当前 region
- 当前 project
- 当前 profile

推荐：

```bash
python3 scripts/hcloud_context_inspect.py --pretty
```

### 2. 可用区确认

```bash
python3 scripts/hcloud_safe_exec.py \
  --service ECS \
  --operation ListServerAzInfo \
  --arg=--cli-region=cn-north-4 \
  --arg=--project_id=<project-id> \
  --arg=--cli-output=json \
  --expect-json \
  --pretty
```

### 3. 规格确认

```bash
python3 scripts/hcloud_safe_exec.py \
  --service ECS \
  --operation ListFlavors \
  --arg=--cli-region=cn-north-4 \
  --arg=--project_id=<project-id> \
  --arg=--limit=50 \
  --arg=--cli-output=json \
  --expect-json \
  --pretty
```

### 4. 售卖策略确认

```bash
python3 scripts/hcloud_safe_exec.py \
  --service ECS \
  --operation ListFlavorSellPolicies \
  --arg=--cli-region=cn-north-4 \
  --arg=--project_id=<project-id> \
  --arg=--limit=50 \
  --arg=--cli-output=json \
  --expect-json \
  --pretty
```

### 5. 规格和售卖策略的大输出处理

`ListFlavors` 和 `ListFlavorSellPolicies` 都可能返回较大的列表。创建前只需要少量候选时，优先加 `limit`、规格名、规格族、AZ 等过滤；需要完整判断“某规格在某 AZ 是否可创建”或需要把规格与售卖策略做交叉分析时，优先落盘再处理。

推荐方式：

- 小样本阶段：用 `--limit` 和 `--cli-output=json` 确认字段结构。
- 全量核验阶段：用 `--result-file=<result-json-file>` 和 `--parsed-json-file=<parsed-json-file>` 保存完整返回。
- 对话输出：只返回候选规格、售卖状态分布、不可售原因摘要、匹配到的目标 flavor/AZ，以及落盘文件位置。
- 后续分析：用短脚本或 `jq` 读取落盘文件做 join，不要把完整规格表或售卖策略表直接贴回对话。

### 6. 创建 JSON 本地校验

把已确认的镜像、规格、网络、密钥对、磁盘参数写入 `cli-jsonInput` 文件后，先做本地校验：

```bash
python3 scripts/hcloud_ecs_create_plan.py \
  --json-input-file=<path-to-json> \
  --operation=CreateServers \
  --region=cn-north-4 \
  --pretty
```

通过标准：

- `success=true`
- `validation.errors` 为空
- 没有 `<project_id>`、`<image_id>`、`<subnet_id>` 等占位符
- 嵌入式占位符如 `ecs-<env>` 也必须清掉
- `body.server.count` 默认不能超过保守上限 10；如果确实要更多实例，先确认费用、配额和回滚，再使用 `--allow-large-count`
- 输出中生成了 `commands.safe_exec`
- 输出中生成了 `commands.safe_exec_shell`，可人工复制执行

如果 `validation.errors` 不为空，先修 JSON，不要进入 dry-run。

若创建 JSON 含内联 EIP、NIC、磁盘等嵌套对象，先读取 operation resolver 的 `request_contract`。顶层
catalog 不能证明嵌套字段时，用下面的静态 SDK schema 补证，不要猜 `.1` 或点号参数：

```bash
python3 scripts/hcloud_sdk_catalog.py \
  --service=ECS \
  --operation=CreateServers \
  --schema-depth=5 \
  --pretty
```

例如内联 EIP 的 `iptype` 必须来自当前 region 支持的公网 IP 类型查询，而不是从别的区域硬编码。

### 7. dry-run

执行上一步输出的 `commands.safe_exec`，或者手动使用：

```bash
python3 scripts/hcloud_safe_exec.py \
  --service ECS \
  --operation CreateServers \
  --arg=--cli-region=cn-north-4 \
  --arg=--dryrun \
  --arg=--cli-output=json \
  --json-input-file=<path-to-json> \
  --expect-json \
  --pretty
```

dry-run 通过只说明命令和参数骨架可被校验，不代表资源已经创建。

### 8. 真实提交和终态验证

只有当用户明确确认会产生费用的真实创建后，才生成非 dry-run 命令：

```bash
python3 scripts/hcloud_ecs_create_plan.py \
  --json-input-file=<path-to-json> \
  --operation=CreateServers \
  --region=cn-north-4 \
  --mode=submit \
  --confirm-submit \
  --pretty
```

真实提交返回 `job_id` 后，必须轮询到终态：

```bash
python3 scripts/hcloud_ecs_wait_job.py \
  --job-id=<job-id> \
  --region=cn-north-4 \
  --project-id=<project-id> \
  --server-id=<server-id-if-known> \
  --pretty
```

`hcloud_ecs_wait_job.py` 只验证 job 终态，输出中会标记 `verification_scope=job_terminal_only`。只有 job 进入 `SUCCESS` 后，再用下面的资源验证确认目标实例 `ACTIVE`，才可以说 ECS 创建完成：

```bash
python3 scripts/hcloud_ecs_verify_active.py \
  --server-id=<server-id> \
  --region=cn-north-4 \
  --project-id=<project-id> \
  --pretty
```

如果 submit 返回里暂时没有 server ID，可以先按资源名查，但同名资源可能不唯一；优先在 submit 结果或后续列表结果里拿到明确 ID。

submit 若返回 `execution_semantics.request_outcome=outcome_unknown`，不能再次执行同一创建命令。先按
资源名、请求标签、已知 job ID 或其他稳定标识查询是否已经创建，再决定继续等待、补充验证或重试。

## 还需要确认的外部依赖

除了 ECS 本身，还要确认：

- 镜像
- 密钥对
- VPC
- 子网
- 安全组
- 网站需要公网访问或用户要求返回 IP 时，还需要 EIP 与带宽
- 根盘和数据盘类型

当前版本 skill 对这些依赖不硬编码 operation 名，而是要求先发现当前 CLI 中可用的 operation：

- `hcloud IMS --help`
- `hcloud KPS --help`
- `hcloud VPC --help`

如果当前环境下 service 级帮助都因 metadata 失败拿不到，就退回本地缓存和 raw materials，不要直接猜。

## 网站部署和公网 IP 闭环

用户要求“部署到机器”“返回 IP”或从公网访问 ECS 时，ECS `ACTIVE` 仍不代表任务完成：

1. 读取 `ecs-user-data-service-readiness.md`，通过幂等 user-data、SSH 或 COC 部署并启动 Web 服务。
2. 读取 `eip-public-ip-readiness.md`，创建或选择 EIP，绑定到目标 ECS/port。
3. 回读 EIP 状态、公网地址和绑定对象，确认不是未绑定或绑定到其他资源。
4. 从公网地址探测 HTTP/HTTPS，并确认服务进程和目标端口在机内监听。
5. 最终返回经过验收的 EIP 公网地址、HTTP 状态和绑定目标。不能返回私网 IP、OBS 域名或仅创建未绑定的 EIP。

## 安全组选择与权限降级

公网应用服务器通常需要同时满足：

- SSH 登录：入方向 TCP 22
- Web 服务：入方向 TCP 80
- 可选 HTTPS：入方向 TCP 443

创建 ECS 前先确认目标安全组是否已经具备这些规则：

```bash
python3 scripts/hcloud_safe_exec.py \
  --service VPC \
  --operation ListSecurityGroups \
  --arg=--cli-output=json \
  --expect-json \
  --pretty

python3 scripts/hcloud_safe_exec.py \
  --service VPC \
  --operation ListSecurityGroupRules \
  --arg=--security_group_id.1=<security-group-id> \
  --arg=--cli-output=json \
  --expect-json \
  --pretty
```

把上述读回结果保存成 JSON artifact 后，传给 ECS 创建前校验：

```bash
python3 scripts/hcloud_ecs_create_plan.py \
  --json-input-file=<path-to-ecs-json> \
  --security-group-evidence-file=<security-group-readback-json> \
  --operation=CreateServers \
  --region=<region> \
  --pretty
```

如果 `body.server.security_groups[*].id` 引用了已有安全组但没有提供规则证据，创建计划必须停在本地校验阶段，不生成可运行命令。

如果目标安全组缺少规则，先按普通变更流程尝试补规则；但遇到明确的 SCP/IAM 拒绝时，例如 `SYS.0403`、`AccessDenied`，或错误消息包含 `vpc:securityGroupRules:create`，不要反复重试同一个补规则动作。

此时允许复用已有安全组，前提是同时满足：

- 与目标 ECS 在同一 VPC 或同一企业项目边界内，且可以绑定到目标子网。
- 入方向已开放任务要求的端口，例如 TCP 22/80/443。
- 规则来源范围符合任务风险边界；SSH `22` 和常见 Web 入口 `80`、`443`、`3000`、`5000`、`8000`、`8080` 不允许使用 `0.0.0.0/0`，即使用户只说“公网可访问”也要收敛到固定客户端 IP、办公网 CIDR、VPN CIDR、跳板机/堡垒机来源、负载均衡来源或私网 CIDR。
- 出方向不限制基础软件安装和健康检查，或已有证据说明服务初始化不依赖外部访问。

复用时，把该安全组 ID 写入 `body.server.security_groups`，不要再创建同名安全组或继续提交被拒绝的 `CreateSecurityGroupRule`。最终回复必须说明：

- 原计划使用或创建的安全组名称。
- 被拒绝的 operation、错误码和关键消息。
- 实际复用的安全组名称、ID、规则 ID、端口和来源网段。
- 这是安全组命名上的偏离，但端口能力和实例可达性已通过验证。

## 创建命令构造原则

### 1. 默认不要直接手拼大 body

优先：

- `--skeleton`
- `--cli-jsonInput`

### 2. 默认先 `--dryrun`

例如：

```bash
python3 scripts/hcloud_ecs_create_plan.py \
  --json-input-file=<path-to-json> \
  --operation=CreateServers \
  --region=cn-north-4 \
  --pretty
```

### 3. 真执行前先讲清前提

建议在真正执行前至少说明：

- 用哪个 region / project
- 用哪个 flavor / AZ
- 用哪个 image / keypair / subnet
- 这是试运行还是真实创建
- 如果是真实创建，返回的 `job_id` 是什么，以及用什么命令轮询到终态
- 用什么命令确认 ECS 实例达到 `ACTIVE`

## 不要做的事

- 不要在镜像、网络、keypair 未确认时直接创建
- 不要把几十个参数都硬塞进一行命令
- 不要先真执行再补解释
- 不要只看到 `job_id` 就说创建成功
