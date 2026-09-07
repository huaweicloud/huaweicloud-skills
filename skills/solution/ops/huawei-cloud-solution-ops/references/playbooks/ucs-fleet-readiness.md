# UCS Fleet Readiness Playbook

## 目标

为 UCS curated registry 覆盖提供 fleet、cluster、policy 和 addon 的只读检查边界。

## 当前状态

- 已 live-smoked：`ListAddonTemplates`、`ListPolicyDefinitions`
- 已知 CLI shape 例外：`ListManagedClusters` 在 KooCLI 7.2.2 中拒绝 `--limit`，skill 会省略该可选参数。
- 当前 registry 覆盖只读 fleet/cluster/policy/addon discovery 和 target-scoped readback，不开放通用 mutation submit。

## Readiness 检查

```bash
python3 scripts/hcloud_resource_discovery.py --service UCS --operation ListAddonTemplates --region=<region> --pretty
python3 scripts/hcloud_resource_discovery.py --service UCS --operation ListClusterGroup --region=<region> --pretty
python3 scripts/hcloud_resource_discovery.py --service UCS --operation ListManagedClusters --region=<region> --pretty
python3 scripts/hcloud_resource_discovery.py --service UCS --operation ListPolicyDefinitions --region=<region> --pretty
```

有 cluster 或 fleet ID 后：

```bash
python3 scripts/hcloud_resource_query.py --service UCS --operation ShowCluster --region=<region> --param clusterid=<cluster-id> --pretty
python3 scripts/hcloud_resource_query.py --service UCS --operation ShowClusterGroup --region=<region> --param clustergroupid=<fleet-id> --pretty
python3 scripts/hcloud_resource_query.py --service UCS --operation ShowPolicyDefinition --region=<region> --param policydefinitionid=<policy-definition-id> --pretty
```

## 集群接入诊断

### 先区分两个 cluster ID

- 注册 CCE 集群时使用源 CCE cluster ID。
- 注册完成后的 UCS Show/Update/Delete/Policy 操作使用 UCS 分配的 cluster ID。
- `ClusterNotFound` 时先确认使用的是哪一种 ID，不要直接判断源集群不存在。

CCE 接入按以下顺序排查：

1. region/project 是否与源 CCE 一致；
2. 源 CCE 是否处于稳定可用状态；
3. UCS quota 是否足够；
4. 是否已有纳管记录；
5. 注册后的 UCS `status.phase` 和 access/fleet 可见性。

自管 Kubernetes 集群按以下顺序排查：

1. kubeconfig 结构、current-context、token/cert 有效期；
2. API server 是否能从 UCS 管理面到达，而不只是操作者本机能访问；
3. TLS/CA 是否匹配；
4. 纳管身份的 RBAC 是否满足最小权限；
5. 以上证据完整后再决定是否 retry activation。

注册 API accepted 或 UCS 对象出现只代表请求已受理。至少等到 `status.phase=Available`，并验证 access info 和 fleet 可见性后，才能写“接入完成”。`Unavailable` 时不要循环重试，先定位失败层；只有注册响应时写“已受理，未完成”。

## 治理操作清单

UCS 场景重点不是只查到 fleet，而是确认“多集群治理是否可闭环”：

- Fleet / cluster group：有哪些 fleet、包含哪些集群、集群状态和地域分布。
- Policy definition：可用策略定义、策略版本、参数要求和适用范围。
- Policy instance：策略是否已实例化、绑定目标、当前合规状态、最近更新时间。
- Compliance：哪些集群、namespace 或 resource 不合规，是否有豁免或待处理项。
- Addon：addon template、已装 addon、版本、升级风险和依赖。
- 凭据边界：kubeconfig、cluster access token、接入脚本都属于高敏材料，不输出原值。

如果要从只读治理进入写类操作，必须先生成单独 guarded plan：创建、更新、删除 policy instance，接入或移除集群，安装或升级 addon 都不能由 readiness 流程自动提交。

## Policy 渐进推广与合规语义

策略从发现进入约束时，按以下顺序推进：

1. 确认 definition、参数 schema 和目标范围。
2. 在有限 namespace 或预发 cluster 以 `warn` 运行。
3. 记录误报、例外 owner 和 workload 影响。
4. 修正规则或豁免后，扩到少量生产 cluster。
5. 只有当前目标、最近 job、violation 集合、回滚动作均清楚时，才规划 fleet 级 `deny`。

参数 schema 不清、fleet membership 不稳定、存在无法解释的 violation 或业务阻断时，停止扩大范围。

报告中必须分开以下事实：

- policy job `Success`：只证明下发/执行任务成功，不等于目标资源全部合规。
- policy enabled/disabled：禁用可能停止新检查，但历史 violation 仍可能保留。
- current compliance：需要同时给出目标范围、最近 job 时间、policy instance 状态、violation 时间戳和当前违规证据。

因此，job 成功但 violation 非空时不能写“已合规”；policy 已禁用但仍有旧 violation 时，只能标记为历史证据。

## 风险边界

UCS federation、policy、addon、kubeconfig 和 cluster 接入变更不在当前 curated registry 的 change operations 中。后续如果要加入写类能力，必须先补专用 guarded flow、凭据脱敏、集群状态回读和显式确认门禁。不得保存 kubeconfig token 或把集群凭据写入最终输出。
