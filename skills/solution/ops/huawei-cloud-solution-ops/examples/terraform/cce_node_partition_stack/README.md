# Huawei CCE Node Partition Stack Example

这个示例吸收上游 `cce/node-partition` 变体，用于在现网 CCE 集群上创建 partition，并把 node pool 放入该 partition。

使用前必须确认：
- 目标集群支持 partition。
- `partition_subnet_id` 和 `container_subnet_ids` 属于正确 VPC/ENI 网络。
- public border group 和 AZ 与集群网络规划匹配。

apply 后查询 partition、node pool、节点状态和 pod 调度结果。
