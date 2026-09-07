# CCE Cluster Readiness Playbook

## 目标

确认 CCE 集群和节点的云侧状态，明确 kubeconfig、节点健康和工作负载检查不应被混在一起。

## 适用场景

- 查询集群清单和节点状态
- 为应用部署、容器排障或集群迁移做前置检查
- 判断是否需要进入 Kubernetes 层继续排查

## 标准检查

```bash
python3 scripts/hcloud_resource_discovery.py --service CCE --operation ListClusters --region=<region> --limit=20 --pretty
```

有集群 ID 时：

```bash
python3 scripts/hcloud_resource_query.py --service CCE --operation ShowCluster --region=<region> --param cluster_id=<cluster-id> --pretty
python3 scripts/hcloud_resource_query.py --service CCE --operation ListNodes --region=<region> --param cluster_id=<cluster-id> --pretty
```

## 风险边界

- 当前 curated 覆盖只承诺只读集群和节点发现。
- 集群创建、节点扩缩容、插件安装、kubeconfig 下载和工作负载变更不纳入自动 submit。
- 涉及 kubeconfig 或集群凭据时，输出必须脱敏，不保存 token。

## 验收

成功时给出集群 ID、版本、状态、VPC/subnet、节点数量和节点状态。需要 Kubernetes 层验证时，应明确下一步是 `kubectl`/工作负载检查，而不是继续猜 hcloud operation。
