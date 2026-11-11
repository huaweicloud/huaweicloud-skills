# CCE Python Script Usage Guide

本指南说明 `huawei-cloud-computing-query` 技能的 CCE（云容器引擎）**只读查询**脚本用法。
全部脚本仅调用 CCE 原生 OpenAPI（`huaweicloudsdkcce` v3），**不做任何写操作**。

---

## 1. 能力范围（Scope）

| 脚本 | 用途 | CCE OpenAPI |
|------|------|-------------|
| `scripts/cce/list_clusters.py` | 集群列表 | `ListClusters` |
| `scripts/cce/show_cluster.py` | 集群详情 | `ShowCluster` |
| `scripts/cce/list_nodes.py` | 节点列表 | `ListNodes` |
| `scripts/cce/show_node.py` | 节点详情 | `ShowNode` |
| `scripts/cce/list_node_pools.py` | 节点池列表 | `ListNodePools` |
| `scripts/cce/show_node_pool.py` | 节点池详情 | `ShowNodePool` |
| `scripts/cce/show_cluster_tags.py` | 集群标签 | `GetResourceTags` |
| `scripts/cce/list_node_pools_by_tag.py` | 按标签/标签(label)过滤节点池（客户端过滤） | `ListNodePools` |
| `scripts/cce/show_quota.py` | 配额查询 | `ShowQuotas` |

---

## 2. 执行方式

按 `SKILL.md` 的要求，脚本在技能包内执行：宿主提供 `skill action=exec` 时优先用它，否则用技能 venv 的 Python 直接执行；不要把脚本复制到技能目录外运行。
本地调试查看参数时可执行 `python scripts/cce/<脚本名>.py -h`。

统一前置：设置 `HW_ACCESS_KEY` / `HW_SECRET_KEY`（临时凭证再加 `HW_SECURITY_TOKEN`）。
`--region` 为可选参数：不传时回退环境变量 `HW_REGION_NAME`（缺省 `cn-north-4`）；`--project_id` 不传时脚本会通过 IAM API 按 region 自动获取。

空结果与失败提示：脚本会在空结果时给出排查建议（region/项目/权限/过滤条件），并把 401/403/404/超时/网络类异常翻译成中文原因与处理建议，同时带上 region、project_id、集群 ID 等上下文。

---

## 3. 脚本清单与用法

### 3.1 list_clusters.py — 集群列表

```
python scripts/cce/list_clusters.py --region cn-north-4
python scripts/cce/list_clusters.py --region cn-north-4 --status Available --type VirtualMachine
python scripts/cce/list_clusters.py --region cn-north-4 --detail true --all
```

参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--region` | 否 | 区域，默认回退 `HW_REGION_NAME`（缺省 cn-north-4） |
| `--project_id` | 否 | 项目 ID，不传则根据 `--region` 自动获取 |
| `--detail` | 否 | 是否返回集群详细信息，取值 true/false |
| `--status` | 否 | 集群状态过滤，例如 Available、Unavailable、ScalingUp、ScalingDown、Creating、Deleting、Error、Freezed |
| `--type` | 否 | 集群类型过滤：VirtualMachine（普通集群，含 CCE Turbo）、ARM64、Autopilot |
| `--version` | 否 | 集群版本过滤，例如 v1.28、v1.29 |
| `--all` | 否 | 展示全部集群（该接口不支持分页，默认最多展示 50 个） |

输出字段（制表符表格）：`id（集群 UUID）`、`name`、`status（phase）`、`type`、`version`、`flavor`、`category`、`created`。
加 `--detail true` 时，末尾追加「集群明细」段：每个集群输出 `alias`、`annotations`（`key=value` 列表）、`cluster_tags`（`key=value` 列表）。
输出末尾统一附一行生态能力指路（工作负载/事件/日志、资源使用率、节点池扩缩容）。

### 3.2 show_cluster.py — 集群详情

```
python scripts/cce/show_cluster.py --region cn-north-4 --cluster_id <cluster_id>
python scripts/cce/show_cluster.py --region cn-north-4 --cluster_id <cluster_id> --detail true
```

参数：`--cluster_id`（必填，UUID，可由 list_clusters.py 获取）、`--detail`（可选）、`--region` / `--project_id`（可选）。

输出为 `key: value` 逐行形式：`id`、`name`、`alias`、`status`、`type`、`category`、`version`、`platform_version`、
`flavor`、`az`、`billing_mode`、`kube_proxy_mode`、`ipv6enable`、`deletion_protection`、`description`、`created`、`updated`、
`container_network`、`service_network`、`host_network`、`eni_network`、`endpoints`（`type=url` 列表）、`is_locked`、
`reason`、`message`、`conditions`。

### 3.3 list_nodes.py — 节点列表（全量分页）

```
python scripts/cce/list_nodes.py --region cn-north-4 --cluster_id <cluster_id>
python scripts/cce/list_nodes.py --region cn-north-4 --cluster_id <cluster_id> --limit 100 --marker <next_marker>
python scripts/cce/list_nodes.py --region cn-north-4 --cluster_id <cluster_id> --all
python scripts/cce/list_nodes.py --region cn-north-4 --cluster_id <cluster_id> --all --verify
```

参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--region` | 否 | 区域，默认取 `HW_REGION_NAME` |
| `--cluster_id` | 是 | 集群 ID（UUID） |
| `--project_id` | 否 | 项目 ID |
| `--limit` | 否 | 每页展示条数，默认 50，服务端单次请求上限 100 |
| `--marker` | 否 | 分页标记，从上次输出的 `next_marker` 获取 |
| `--all` | 否 | 按 marker 自动翻页拉取**全部**节点，避免节点数 > 一页时数量比控制台少 |
| `--verify` | 否 | 与节点池 `current_node` 汇总数交叉校验；不一致时给出差值说明（创建/删除中的节点会造成临时差值） |

输出字段：`id（节点 UUID）`、`name`、`status（phase）`、`flavor`、`az`、`private_ip`、`public_ip`、`server_id`、`created`。
末页提示 `共 N 条 CCE 节点`；还有更多时提示可用的 `--marker` 或推荐 `--all`。

> 节点数与控制台不一致时，优先使用 `--all`；`--verify` 会额外调用 `ListNodePools` 做数量自校验。

### 3.4 show_node.py — 节点详情

```
python scripts/cce/show_node.py --region cn-north-4 --cluster_id <cluster_id> --node_id <node_id>
```

参数：`--cluster_id`、`--node_id`（均必填，节点 ID 可由 list_nodes.py 获取）、`--region` / `--project_id`（可选）。

输出为 `key: value` 逐行形式：`id`、`name`、`status`、`flavor`、`az`、`os`、`billing_mode`、`ecs_group_id`、`partition`、
`created`、`updated`、`server_id`、`private_ip`、`public_ip`、`job_id`、`last_probe_time`、`configuration_up_to_date`、
`ssh_key`（仅密钥名，不输出任何凭据值）、`root_volume`、`data_volumes`、`nodepool_name`、`nodepool_id`。

### 3.5 list_node_pools.py — 节点池列表

```
python scripts/cce/list_node_pools.py --region cn-north-4 --cluster_id <cluster_id>
python scripts/cce/list_node_pools.py --region cn-north-4 --cluster_id <cluster_id> --show_default_node_pool true --all
```

参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--region` | 否 | 区域，默认回退 `HW_REGION_NAME`（缺省 cn-north-4） |
| `--cluster_id` | 是 | 集群 ID（UUID） |
| `--project_id` | 否 | 项目 ID |
| `--show_default_node_pool` | 否 | 是否展示默认节点池，true/false，不传则默认不展示 |
| `--advance_status` | 否 | 是否返回节点池详细状态，true/false |
| `--all` | 否 | 展示全部节点池（该接口不支持分页，默认最多展示 50 个） |

输出字段：`id`、`name`、`type`、`flavor`、`initial_node_count`、`current_node`、`autoscaling`（on(min-max)/off）、`phase`、`created`。

### 3.6 show_node_pool.py — 节点池详情

```
python scripts/cce/show_node_pool.py --region cn-north-4 --cluster_id <cluster_id> --nodepool_id <nodepool_id>
python scripts/cce/show_node_pool.py --region cn-north-4 --cluster_id <cluster_id> --nodepool_id <nodepool_id> --advance_status true
```

参数：`--cluster_id`（必填）、`--nodepool_id`（必填，可由 list_node_pools.py 获取）、`--advance_status`（可选，true/false）、
`--region` / `--project_id`（可选）。

输出为 `key: value` 逐行形式：`id`、`name`、`type`、`initial_node_count`、`autoscaling(on(min-max)/off)`、
`flavor`、`az`、`os`、`billing_mode`、`root_volume`、`data_volumes`、`user_tags`、`k8s_tags`、`taints`、`runtime`、
`current_node`、`active_node`、`creating_node`、`deleting_node`、`phase`、`created`、`updated`、`conditions`。

### 3.7 show_cluster_tags.py — 集群标签

```
python scripts/cce/show_cluster_tags.py --region cn-north-4 --cluster_id <cluster_id>
```

参数：`--cluster_id`（必填）、`--region` / `--project_id`（可选）。调用 `GetResourceTags`
（`resource_type=cce-cluster`），输出 `tag_key / tag_value` 表与 `sys_tag_key / sys_tag_value` 表，末尾汇总数量。
集群本身没有标签时脚本会给出空结果说明，而不是静默返回空表。

### 3.8 list_node_pools_by_tag.py — 按标签过滤节点池

```
python scripts/cce/list_node_pools_by_tag.py --region cn-north-4 --cluster_id <cluster_id> --tag env=prod
python scripts/cce/list_node_pools_by_tag.py --region cn-north-4 --cluster_id <cluster_id> --tag env=prod --label zone=a
```

参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--cluster_id` | 是 | 集群 ID（UUID） |
| `--tag` | 否 | 按节点池 `userTags` 过滤，`key=value`，可重复，多个之间为 AND |
| `--label` | 否 | 按节点池 `k8s_tags`（Kubernetes label）过滤，`key=value`，可重复，多个之间为 AND |
| `--include_default` | 否 | 一并查询默认节点池（`show_default_node_pool=true`） |
| `--advance_status` | 否 | 是否返回节点池详细状态，true/false |
| `--region` / `--project_id` | 否 | 区域 / 项目 ID |

至少指定一个 `--tag` 或 `--label`。`ListClusters` 本身不支持按 tags 过滤，因此该脚本先拉取节点池列表再在客户端过滤，
输出 `id`、`name`、`phase`、`current_node`、`flavor`、`user_tags`、`k8s_tags`、`created`，末尾给出 `共 M 个节点池，匹配 N 个`。

### 3.9 show_quota.py — 配额查询

```
python scripts/cce/show_quota.py --region cn-north-4
```

参数：`--region` / `--project_id`（可选）。

输出字段：`quota_key`、`quota_limit`、`used`、`remain`（quota_limit - used）、`unit`、`region_id`、`availability_zone_id`；
末尾汇总 `共 N 项 CCE 配额`。

---

## 4. 权限要求

只读查询所需的最小 IAM action（CCE 服务级）：

| Action | 用途 |
|--------|------|
| `cce:cluster:list` | ListClusters 集群列表 |
| `cce:cluster:get` | ShowCluster 集群详情 |
| `cce:node:list` | ListNodes 节点列表 |
| `cce:node:get` | ShowNode 节点详情 |
| `cce:nodepool:list` | ListNodePools 节点池列表 |
| `cce:nodepool:get` | ShowNodePool 节点池详情 |
| `cce:tag:get` | GetResourceTags 集群标签 |
| `cce:quota:get` | ShowQuotas 配额查询 |

也可直接授予系统策略 `CCEReadOnlyPolicy`。此外 `--project_id` 未显式传入时，脚本会调用 IAM
`KeystoneListProjects` 自动获取项目 ID，需具备 IAM 项目列表只读权限。

---

## 5. 能力边界（本技能不支持）

- **只读**：仅执行上述查询接口，不创建/修改/删除集群、节点、节点池，不扩缩容、不升级、不绑定 EIP。
- **不含 Kubernetes 数据面**：**工作负载（Deployment/StatefulSet/DaemonSet/Job/CronJob）、命名空间（Namespace）、
  Event、Pod、Service、ConfigMap/Secret、PVC 等 Kubernetes 资源不属于本技能范围**——这些需要通过 Kubernetes API
  （kubectl / kubeconfig）访问，请使用 `container/cce/` 下的既有技能：
  - `huawei-cloud-kubectl-cce-installer`：在目标机安装 kubectl 与 kubectl-cce 插件，为 kubectl 访问集群做准备。
  - `huawei-cloud-cce-kubernetes-event-analyzer`：查询与分析集群 Kubernetes Event。
  - 其他 CCE 运维场景（集群管理、迁移、日志、告警关联等）见 `container/cce/` 目录下的对应技能。
- **不含证书读接口**：CCE v3 只有创建/吊销/轮转证书（写操作），没有证书查询接口；证书状态请通过控制台查看，本技能不会调用写接口。
- **生态能力指路**：集群/节点 CPU、内存等资源使用率请用 `huawei-cloud-cce-metric-analyzer`（`scripts/huawei_cloud/cce_cluster_monitoring.py`）；
  插件（add-on）巡检与节点池扩缩容等写操作请用 `huawei-cloud-cce-cluster-management`。
- **不含其他云服务**：ECS/BMS/IMS/AS 由本技能其它脚本覆盖；EVS/OBS/SFS/CBR 等存储类查询请使用 `huawei-cloud-storage-query`。
