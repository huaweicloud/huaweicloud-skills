# Huawei CCE Turbo Cluster Stack Example

这个示例吸收上游 `cce/turbo-cluster` 变体，用于创建 CCE Turbo/ENI 网络形态的集群。

说明：
- 上游当前没有独立 autopilot 资产；本示例不冒充 autopilot。
- CCE Turbo 会引入 ENI subnet、EIP、配额和网络规划要求。
- apply 前必须确认 region、AZ、VPC CIDR、ENI subnet CIDR、集群规格和计费。

apply 后用 hcloud/CCE 查询集群状态、ENI subnet、节点网络和 addon 状态。
