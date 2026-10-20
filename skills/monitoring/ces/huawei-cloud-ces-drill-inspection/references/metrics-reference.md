# Supported Cloud Services and Metrics Reference

19 supported services, 238 metrics total. DRS and VPC Bandwidth metrics are defined in metrics.json but not yet supported by status collection.

When configuring `input.json`, the `metrics` field should contain the **metric display names** (Chinese) from the tables below.


## APIG API Gateway (apig) — 1 metric

| Metric Name | Unit |
|-------------|------|
| APIG请求次数 | Times/min |

## CCE Cloud Container Engine (cce) — 8 metrics

| Metric Name | Unit |
|-------------|------|
| CCE CPU利用率 | % |
| CCE POD CPU利用率 | % |
| CCE POD物理内存使用率 | % |
| CCE master节点CPU使用率 | % |
| CCE内存利用率 | % |
| CCE磁盘使用率 | % |
| CCE节点CPU利用率 | % |
| CCE节点磁盘使用率 | % |

## CSS Search Service (css) — 11 metrics

| Metric Name | Unit |
|-------------|------|
| CSS节点JVM堆使用率 | % |
| CSS节点cpu利用率 | % |
| CSS节点可用内存比例 | % |
| CSS节点最大磁盘IO使用率 | % |
| CSS节点最大磁盘使用率 | % |
| CSS节点磁盘IOPS超限次数 | Count |
| CSS节点磁盘写带宽 | Byte/s |
| CSS节点磁盘读带宽 | Byte/s |
| CSS集群最大CPU利用率 | % |
| CSS集群最大JVM堆使用率 | % |
| CSS集群最大磁盘使用率 | % |

## DC Physical Connection (dc) — 4 metrics

| Metric Name | Unit |
|-------------|------|
| DC物理连接网络流入带宽 | bit/s |
| DC物理连接网络流出带宽 | bit/s |
| DC网络流入带宽 | bit/s |
| DC网络流出带宽 | bit/s |

## DCS Distributed Cache (dcs) — 31 metrics

| Metric Name | Unit |
|-------------|------|
| DCS Proxy节点内存利用率 | % |
| DCS Proxy节点平均时延 | μs |
| DCS Proxy节点最大CPU使用率 | % |
| DCS Proxy节点最大时延 | μs |
| DCS Proxy节点每秒并发操作数 | count |
| DCS Proxy节点活跃的客户端数量 | count |
| DCS Proxy节点网络瞬时输入流量 | KiB/s |
| DCS Proxy节点网络瞬时输出流量 | KiB/s |
| DCS Proxy节点连接数使用率 | % |
| DCS 内存使用率 | % |
| DCS 命令最大时延 | ms |
| DCS 带宽使用率 | % |
| DCS 数据节点内存利用率 | % |
| DCS 数据节点命令最大时延 | ms |
| DCS 数据节点带宽使用率 | % |
| DCS 数据节点平均时延 | μs |
| DCS 数据节点最大CPU使用率 | % |
| DCS 数据节点最大时延 | μs |
| DCS 数据节点每秒并发操作数 | count |
| DCS 数据节点流控次数 | count |
| DCS 数据节点连接数使用率 | % |
| DCS 最大CPU使用率 | % |
| DCS 最大时延 | μs |
| DCS 每秒并发操作数 | count |
| DCS 活跃的客户端数量 | count |
| DCS 流控次数 | count |
| DCS 网络瞬时输入流量 | KiB/s |
| DCS 网络瞬时输出流量 | KiB/s |
| DCS 连接数使用率 | % |
| DCS读平均时延 | μs |
| DCS写平均时延 | μs |

## DDS Document Database (dds) — 1 metric

| Metric Name | Unit |
|-------------|------|
| DDS CPU利用率 | % |

## DMS Message Queue (dms) — 33 metrics

**Note**: DMS requires specifying the `engine` parameter in `input.json`; different engines correspond to different metrics.


### engine=kafka (12 metrics)

| Metric Name | Unit |
|-------------|------|
| DMS Kafka Broker CPU使用率 | % |
| DMS Kafka Broker 内存使用率 | % |
| DMS Kafka Broker 生产请求平均处理时长 | ms |
| DMS Kafka Broker 磁盘容量使用率 | % |
| DMS Kafka Broker 磁盘平均写操作耗时 | ms |
| DMS Kafka Broker 磁盘平均读操作耗时 | ms |
| DMS Kafka Broker 网络带宽利用率 | % |
| DMS Kafka Broker 连接数 | Count |
| DMS Kafka主题数 | Count |
| DMS Kafka分区使用率 | % |
| DMS Kafka分区数 | Count |
| DMS Kafka消息堆积数 | Count |

### engine=rabbitmq (14 metrics)

| Metric Name | Unit |
|-------------|------|
| DMS RabbitMQ flow状态连接数 | Count |
| DMS RabbitMQ 可消费消息数 | Count |
| DMS RabbitMQ 未确认消息数 | Count |
| DMS RabbitMQ 节点 CPU使用率 | % |
| DMS RabbitMQ 节点 内存使用率 | % |
| DMS RabbitMQ 节点 内存高水位状态 | 不涉及 |
| DMS RabbitMQ 节点 磁盘容量使用率 | % |
| DMS RabbitMQ 节点 磁盘平均写操作耗时 | ms |
| DMS RabbitMQ 节点 磁盘平均读操作耗时 | ms |
| DMS RabbitMQ 节点 磁盘高水位状态 | 不涉及 |
| DMS RabbitMQ 达到channel上限连接数 | Count |
| DMS RabbitMQ 连接数 | Count |
| DMS RabbitMQ 通道数 | Count |
| DMS RabbitMQ 队列数 | Count |

### engine=rocketmq (7 metrics)

| Metric Name | Unit |
|-------------|------|
| DMS RocketMQ Broker CPU使用率 | % |
| DMS RocketMQ Broker 内存使用率 | % |
| DMS RocketMQ Broker 生产成功率 | % |
| DMS RocketMQ Broker 磁盘容量使用率 | % |
| DMS RocketMQ Broker 节点生产请求P99.9处理时长 | ms |
| DMS RocketMQ 实例磁盘容量使用率 | % |
| DMS RocketMQ 消费组消息堆积数 | Count |

## DRS Data Replication Service (drs) — 8 metrics

| Metric Name | Unit |
|-------------|------|
| DRS cpu使用率 | % |
| DRS内存使用率 | % |
| DRS磁盘利用率 | % |
| DRS任务状态 | — |
| DRS同步状态 | — |
| DRS同步线程数量 | Count |
| DRS数据同步延迟 | s |
| DRS源库WAL抽取延迟 | s |

## DWS Data Warehouse (dws) — 11 metrics

| Metric Name | Unit |
|-------------|------|
| DWS CPU使用率 | % |
| DWS会话数 | count |
| DWS内存使用率 | % |
| DWS数据量大小 | MB |
| DWS活跃SQL数 | count |
| DWS节点CPU使用率 | % |
| DWS节点内存使用率 | % |
| DWS节点硬盘写耗时 | Second |
| DWS节点硬盘读耗时 | Second |
| DWS节点磁盘利用率 | % |
| DWS节点网络输入吞吐量 | byte/s |

## ECS Elastic Cloud Server (ecs) — 7 metrics

| Metric Name | Unit |
|-------------|------|
| ECS CPU使用率 | % |
| ECS入方向带宽 | Byte/s |
| ECS出方向带宽 | Byte/s |
| ECS网络连接数 | Count |
| ECS虚拟机入方向PPS | Packet/s |
| ECS虚拟机出方向PPS | Packet/s |
| ECS虚拟机整机新建连接数 | connect/s |

## SFS Turbo File System (efsturbo) — 9 metrics

| Metric Name | Unit |
|-------------|------|
| EFS-Turbo IOPS | Count |
| EFS-Turbo inode使用率 | % |
| EFS-Turbo元数据读写带宽 | byte/s |
| EFS-Turbo写带宽 | byte/s |
| EFS-Turbo客户端连接数 | Count |
| EFS-Turbo容量使用率 | % |
| EFS-Turbo已用容量 | byte |
| EFS-Turbo总带宽 | byte/s |
| EFS-Turbo读带宽 | bytes/s |

## EIP Elastic Public IP (eip) — 4 metrics

| Metric Name | Unit |
|-------------|------|
| EIP入网带宽 | bit/s |
| EIP入网带宽使用率 | % |
| EIP出网带宽 | bit/s |
| EIP出网带宽使用率 | % |

## ELB Load Balancer (elb) — 12 metrics

| Metric Name | Unit |
|-------------|------|
| ELB 4层入带宽使用率 | % |
| ELB 4层出带宽使用率 | % |
| ELB 4层并发连接使用率 | % |
| ELB 4层新建连接数使用率 | % |
| ELB 7层入带宽使用率 | % |
| ELB 7层出带宽使用率 | % |
| ELB 7层并发连接使用率 | % |
| ELB 7层新建连接数使用率 | % |
| ELB 7层查询速率 | Count/s |
| ELB 7层查询速率使用率 | % |
| ELB并发连接数 | Count |
| ELB新建连接数 | Count/s |

## ER Enterprise Router (er) — 2 metrics

| Metric Name | Unit |
|-------------|------|
| ER入方向带宽 | bit/s |
| ER出方向带宽 | bit/s |

## EVS Cloud Disk (evs) — 7 metrics

| Metric Name | Unit |
|-------------|------|
| EVS IOPS达到上限(次数) | count |
| EVS带宽达到上限(次数) | count |
| EVS平均写操作耗时 | ms/op |
| EVS平均读操作耗时 | ms/op |
| EVS磁盘写带宽 | Byte/s |
| EVS磁盘读写使用率 | % |
| EVS磁盘读带宽 | Byte/s |

## GeminiDB Cloud-Native NoSQL (geminidb) — 20 metrics

| Metric Name | Unit |
|-------------|------|
| GeminiDB Cassandra CPU使用率 | % |
| GeminiDB Cassandra 内存使用率 | % |
| GeminiDB Cassandra 写耗时 | ms |
| GeminiDB Cassandra 大key数量 | Counts |
| GeminiDB Cassandra 存储容量使用率 | % |
| GeminiDB Cassandra 最大写时延 | ms |
| GeminiDB Cassandra 最大读时延 | ms |
| GeminiDB Cassandra 读耗时 | ms |
| GeminiDB Redis CPU利用率 | % |
| GeminiDB Redis 内存利用率 | % |
| GeminiDB Redis 存储容量使用率 | % |
| GeminiDB Redis 客户端单次请求发送的最大参数个数 | Counts |
| GeminiDB Redis 客户端单次请求发送的最大字节数 | Bytes |
| GeminiDB Redis 客户端单次请求获取的最大元素个数 | Counts |
| GeminiDB Redis 客户端单次请求获取的最大字节数 | Bytes |
| GeminiDB Redis 节点入带宽利用率 | % |
| GeminiDB Redis 节点出带宽利用率 | % |
| GeminiDB Redis 连接数使用率 | % |
| GeminiDB Redis每秒AUTH认证失败次数 | Counts |
| GeminiDB Redis每秒未认证导致请求失败数 | Counts |

## NAT Gateway (nat) — 11 metrics

| Metric Name | Unit |
|-------------|------|
| NAT SNAT连接数 | Count |
| NAT SNAT连接数使用率 | % |
| NAT丢包数(EIP端口分配超限) | Count |
| NAT丢包数(PPS超限) | Count |
| NAT丢包数(SNAT连接数超限) | Count |
| NAT入方向pps | Count |
| NAT入方向带宽 | bit/s |
| NAT入方向带宽使用率 | % |
| NAT出方向pps | Count |
| NAT出方向带宽 | bit/s |
| NAT出方向带宽使用率 | % |

## RDS Relational Database (rds) — 32 metrics

| Metric Name | Unit |
|-------------|------|
| RDS CPU使用率 | % |
| RDS MSSQL CPU使用率 | % |
| RDS MSSQL modified内存大小 | % |
| RDS MSSQL paged pool内存大小 | % |
| RDS MSSQL内存使用率 | % |
| RDS MSSQL工作线程使用率 | % |
| RDS MSSQL慢SQL数量 | % |
| RDS MSSQL数据同步延迟 | % |
| RDS MSSQL磁盘利用率 | % |
| RDS MSSQL磁盘吞吐量使用率 | % |
| RDS PG复制时延 | % |
| RDS PG已执行3s的SQL数 | % |
| RDS PG已执行5s的SQL数 | % |
| RDS PG最大数据库年龄 | % |
| RDS PG最滞后副本滞后量 | % |
| RDS PG最长事务存活时长 | % |
| RDS PG最长未决事务存活时长 | % |
| RDS PG连接数使用率 | % |
| RDS PG非活跃逻辑复制槽数量 | % |
| RDS QPS | count/s |
| RDS内存使用率 | % |
| RDS实时复制时延 | s |
| RDS当前活跃连接数 | count |
| RDS慢日志个数统计 | count/min |
| RDS活跃连接数使用率 | % |
| RDS硬盘写耗时 | ms |
| RDS硬盘读耗时 | ms |
| RDS磁盘写吞吐量 | Byte/s |
| RDS磁盘利用率 | % |
| RDS等待行锁事务数 | count |
| RDS连接数使用率 | % |
| RDS长事务指标 | s |

## TaurusDB Distributed Database (taurusdb) — 18 metrics

| Metric Name | Unit |
|-------------|------|
| TaurusDB CPU使用率 | % |
| TaurusDB IO写IOPS | counts/s |
| TaurusDB IO读IOPS | counts/s |
| TaurusDB QPS | Times/s |
| TaurusDB TPS | Times/s |
| TaurusDB undo空间未清理事务个数 | Count |
| TaurusDB 内存使用率 | % |
| TaurusDB 存储写时延 | ms |
| TaurusDB 存储读时延 | ms |
| TaurusDB 当前活跃连接数 | Count |
| TaurusDB 慢日志个数统计 | Count/min |
| TaurusDB 数据同步延迟 | s |
| TaurusDB 磁盘使用率 | % |
| TaurusDB 网络输入吞吐量 | Bytes/s |
| TaurusDB 网络输出吞吐量 | Bytes/s |
| TaurusDB 连接数使用率 | % |
| TaurusDB最长事务持续时间 | s |
| TaurusDB未关闭的长事务个数 | count |

## VPC Bandwidth (bandwidth) — 4 metrics

| Metric Name | Unit |
|-------------|------|
| Bandwidth入网带宽 | bit/s |
| Bandwidth入网带宽使用率 | % |
| Bandwidth出网带宽 | bit/s |
| Bandwidth出网带宽使用率 | % |

## VPCEP VPC Endpoint (vpcep) — 4 metrics

| Metric Name | Unit |
|-------------|------|
| VPCEP终端节点活跃连接数 | count |
| VPCEP终端节点流入带宽 | bit/s |
| VPCEP终端节点流出带宽 | bit/s |
| VPCEP终端节点连接数 | count |
