# CCE Guide

CCE 任务要同时看集群、节点、网络、负载均衡、监控和 Kubernetes 层状态。本 skill 当前以只读/planner-only 为主。

## hcloud-first 路径

1. 读取 `references/playbooks/cce-cluster-readiness.md`、`vpc-network-readiness.md` 和 `observability-readiness.md`。
2. 如果目标是 CCE 环境评估或云原生成熟度，先用 `hcloud_cce_assessment_plan.py` 生成维度化证据计划。
3. 用 `hcloud_closure_plan.py --tier scenario --group CCE` 获取场景级只读证据计划。
4. 用 `hcloud_resource_discovery.py --service CCE` 查询集群和基础资源线索。
5. 已知 cluster ID 后，用 `hcloud_resource_query.py` 查询目标集群详情。
6. 如涉及公网入口，继续按 ELB/VPC 指南验证 listener、member、security group 和协议探测。

## SDK 补充

- 可用 SDK 补充：`CCE:ShowCluster`。
- 用途：补充 `cluster_id` 类型、path 证据和 SDK 请求结构。
- 不用途：不要用 SDK runner 创建、删除、升级集群或改节点池。

## 不要做

- 不要把 hcloud 集群详情查询等同于 Kubernetes workload 健康。
- 不要在缺少 kubeconfig、RBAC 和变更窗口时承诺集群内修改。
- 不要自动改节点池、网络插件或集群版本。
