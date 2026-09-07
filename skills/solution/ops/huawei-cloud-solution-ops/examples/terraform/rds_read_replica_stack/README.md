# Huawei RDS Read Replica Stack Example

这个示例创建 MySQL 主实例和只读副本，补齐上游 read replica 形态。

apply 前确认主实例规格、只读规格、AZ 和复制延迟接受度。apply 后查询主从状态、只读地址和监控指标。
