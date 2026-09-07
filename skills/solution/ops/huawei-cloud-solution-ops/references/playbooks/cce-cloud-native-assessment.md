# CCE Cloud-Native Assessment Playbook

## 目标

把 CCE / Kubernetes 环境评估拆成可执行、可验收、可改进的证据计划，帮助租户判断当前容器平台是否适合承载业务、哪里有风险、下一步该怎么修。这里不复制外部多 skill 工作流，也不自动采集真实集群数据；默认先生成本地评估计划。

## 适用场景

- 用户说“CCE 环境评估”“云原生评估”“Kubernetes 集群体检”“容器平台成熟度”
- 上线前需要确认 CCE 集群、节点池、插件、工作负载、入口、日志、监控是否完整
- 已有 CCE 集群运行不稳定，需要按维度定位短板
- 用户想做集群治理、扩容评估、升级准备或成本优化

## 评估维度

| 维度 | 重点问题 |
| --- | --- |
| 集群控制面 | 集群状态、版本、endpoint、升级信息、网络绑定 |
| 节点与容量 | 节点状态、节点池、规格、可用区、资源利用率、弹性能力 |
| 核心插件 | CoreDNS、Everest、metrics-server、网络/存储/监控插件状态 |
| 工作负载 | Pod、Deployment/StatefulSet/DaemonSet、事件、镜像拉取、探针、滚动发布 |
| 网络与入口 | Service、Ingress、ELB、EIP、安全组、DNS/HTTPS、CDN/WAF |
| 可观测 | CES 指标、LTS 日志、告警、业务探针、入口探测 |
| 安全与权限 | RBAC、access policy、kubeconfig、Secret、镜像来源、公网 API server |
| 韧性与升级 | 多 AZ、副本、PDB、备份/快照、升级路径、回滚窗口 |
| 成本与治理 | 节点利用率、闲置入口资源、日志保留、标签、owner/env/cost-center |

## 标准流程

### 1. 生成评估计划

只生成云侧和 Kubernetes 层证据计划：

```bash
python3 scripts/hcloud_cce_assessment_plan.py \
  --cluster-id <cluster-id> \
  --namespace <namespace> \
  --include-kubernetes \
  --pretty
```

如果没有 cluster ID，先生成发现计划：

```bash
python3 scripts/hcloud_cce_assessment_plan.py --pretty
```

只看某几个维度：

```bash
python3 scripts/hcloud_cce_assessment_plan.py \
  --cluster-id <cluster-id> \
  --dimension control_plane \
  --dimension addons \
  --dimension observability \
  --pretty
```

### 2. 云侧 hcloud 证据

优先使用只读 hcloud 计划：

- `ListClusters` / `ShowCluster`
- `ShowClusterEndpoints`
- `ListNodes`
- `ListNodePools`
- `ListAddonInstances`
- `ListAccessPolicy`
- `ListClusterUpgradePaths`
- `ListClusterMasterSnapshotTasks`

如果某个 operation 需要 `cluster_id`、`nodepool_id` 等参数，先输出缺失参数，不猜资源 ID。

### 3. Kubernetes 层证据

Kubernetes 层只在用户确认 kubeconfig/RBAC 后执行。典型证据包括：

- `kubectl get nodes`
- `kubectl get pods -A -o wide`
- `kubectl get deploy,sts,ds`
- `kubectl get svc,ingress -A -o wide`
- `kubectl top nodes`
- `kubectl top pods`
- `kubectl get events --sort-by=.lastTimestamp`
- `kubectl get role,rolebinding,clusterrolebinding -A`

kubeconfig、token、证书和 Secret 都必须脱敏，不写入报告正文或 planning 文件。

### 4. 指标空序列的判断顺序

指标为空不能解释成“0 错误”或“资源健康”。先沿采集链逐层取证：

1. AOM Prometheus 插件/实例是否与目标集群真实绑定。
2. 目标组件是否暴露 metrics endpoint。
3. etcd、controller-manager、scheduler 是否存在对应 ServiceMonitor。
4. autoscaler、ingress、GPU 等组件是否存在对应 PodMonitor。
5. Ingress 请求类指标是否在采集白名单中显式启用。
6. 最后才检查 query、label、step 和时间窗。

任一采集前置缺失时，结论是 `evidence_gap`，不能继续用空序列评价负载。

指标语义还要避免两类常见误判：

- CoreDNS 的 NXDOMAIN 可能是正常的不存在域名查询，应与 SERVFAIL、超时等真实解析失败分开。
- apiserver 的 WATCH/CONNECT 是长连接语义，应从常规请求延迟中排除或单列；P95 需要按 verb 下钻后再解释。

固定利用率阈值只能作为排查线索。是否异常还需要历史基线、持续时间、容量目标和业务影响。只有能证明 ELB 与 LoadBalancer Service/IP、NAT 与集群 VPC、EIP 与具体 ELB/NAT/Service 的绑定关系时，才能把外部资源指标归到该集群；同 region、名称相似或同时波动都不够。

### 5. 告警关联与复盘

- 当前故障查询 active 告警；复盘近期故障必须同时查询历史/已恢复告警。active 为空不能证明时间窗内没有故障。
- 优先按 resource ID、cluster、namespace、node、workload、event type 和时间窗分组；仅凭标题或关键词相似不能合并。
- `burst`、`sustained`、`recovered-and-repeated`、`possible-noise` 只表示调查时序：
  - 短时集中出现可标为 `burst`；
  - 长时间保持可标为 `sustained`；
  - 恢复后多次再现可标为 `recovered-and-repeated`；
  - 同源重复上报但没有资源状态变化可标为 `possible-noise`。
- 这些标签只决定下一条证据，不直接生成根因，也不触发告警清理、禁用或自动处置。
- 只有标题、没有精确资源 ID 时，只能标记弱关联。

### 6. 评分建议

可以按每个维度给 0 到 3 分：

- 3：证据完整，满足生产建议
- 2：基本满足，有明确可接受风险
- 1：部分满足，需要短期修复
- 0：缺关键能力或证据不足

最终可归一成 5 分制成熟度：

- 0-1：传统/不可生产
- 1-2：基础可用
- 2-3：服务化
- 3-4：自动化
- 4-5：治理成熟

每个维度评分必须带证据状态：

- `evidence_found`：有 hcloud/kubectl/监控/日志证据支撑。
- `evidence_gap`：缺权限、缺参数、未接 kubeconfig 或未开启监控。
- `not_applicable`：该集群或场景不适用。

不要因为某个维度没拿到证据就默认给低分；先标为 `evidence_gap`，并输出最小补证据动作。

## 治理检查清单

| 维度 | 检查点 |
| --- | --- |
| 生产 readiness | 多 AZ、节点池隔离、副本数、PDB、滚动发布、回滚方式 |
| 观测 | CES、LTS、Prometheus/metrics-server、告警通知、入口探测 |
| 安全 | API server 暴露、RBAC 最小权限、Secret 管理、镜像来源、私有仓拉取 |
| 网络 | Service/Ingress/ELB 绑定、健康检查、DNS、TLS、WAF/CDN 边界 |
| 存储 | Everest、PVC/PV、备份、快照、扩容策略和删除回收策略 |
| 成本 | 节点利用率、闲置 LB/EIP、日志保留、镜像保留、标签归属 |
| 升级 | 版本支持、插件兼容、节点 OS、维护窗口、灰度和回滚 |

## 高风险边界

这些动作不能由评估流程自动执行：

- 创建、删除、休眠、唤醒、升级 CCE 集群
- 新增、删除、扩缩容节点或节点池
- cordon、uncordon、drain 节点
- 安装、升级、卸载插件
- 下载、保存或打印 kubeconfig/token/证书
- 修改 RBAC、Secret、Service、Ingress、工作负载或镜像
- 修改 ELB/EIP/DNS/CDN/WAF 或安全组入口规则

如需修复，必须从评估报告转入单独的 guarded change flow。

## 最终输出

评估输出应包含：

- 集群事实：集群 ID、版本、状态、VPC/subnet、endpoint、节点数量
- 维度评分：控制面、节点、插件、工作负载、网络、观测、安全、韧性、成本
- P0/P1/P2 改进项：
  - P0：影响生产可用或安全的阻塞项
  - P1：短期必须修复的稳定性/可观测/容量问题
  - P2：治理、成本、自动化优化项
- 证据缺口：哪些数据没拿到、缺什么权限或参数
- 下一步最小动作：只给最小修复或补证据步骤，不直接扩大变更范围

如果证据不足，不要输出成熟度结论；先输出缺口和下一条最小收集命令。
