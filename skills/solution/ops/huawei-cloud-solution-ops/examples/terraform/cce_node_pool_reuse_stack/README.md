# Huawei CCE Node Pool Reuse Stack Example

这个示例复用现网 CCE 集群，只新增 node pool。

适合场景：
- 已经通过 hcloud 确认 cluster ID、版本、AZ、节点规格、key pair 和配额。
- 需要把新增节点池纳入 Terraform 长期管理。

使用边界：
1. 优先填写 `cluster_id`，不要只靠名称猜集群。
2. plan 前确认新增节点数量、磁盘、规格和计费影响。
3. apply 后回到 hcloud 查询 node pool、节点状态和集群健康。
