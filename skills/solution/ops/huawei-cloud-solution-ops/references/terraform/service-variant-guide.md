# Service Variant Guide

这份文档用于补齐第一档里“高价值字段规则”和“同一服务不同变体怎么选”的信息。

目标不是枚举所有 provider 字段，而是回答更实用的问题：
- 这个服务到底该选哪种形态
- 关键字段为什么不一样
- 哪些参数最容易在组合场景里被用错

## ECS

### 常见变体
- `basic`: 最小计算实例
- `attached-volume`: ECS + EVS 数据盘
- `instance-with-userdata`: 启动时自举应用
- `instance-associate-eip`: 单机直接绑定公网入口
- `prepaid-instance`: 包年包月计费
- `attached-interface`: 多网卡或双臂网络

### 什么时候选哪种
- 只想起一台云主机：`basic`
- 要挂应用数据盘或日志盘：`attached-volume`
- 要做初始化安装或云配置：`instance-with-userdata`
- 要让单机直接对公网暴露：`instance-associate-eip`
- 有明确长期包周期采购诉求：`prepaid-instance`
- 要接入多个网络平面：`attached-interface`

### 高价值字段
- `flavor_id`: 不要硬编码，优先 discovery
- `image_id`: 优先发现公共镜像或私有镜像
- `system_disk_type` / `system_disk_size`: 最容易受 AZ 库存影响
- `key_pair` / `admin_pass`: 二选一，优先 key pair
- `user_data`: 适合自举，但要避免写入敏感信息
- `charging_mode` / `period_unit` / `period`: 只在包周期场景使用

### 常见误区
- 把 `userdata` 当成部署系统来用，而不是初始化入口
- 先创建 EIP，再忘记真正关联到 ECS
- 把单机公网暴露方案和 ELB 入口方案混用

## ELB

### 常见变体
- 最小入口：`elb_stack`
- 完整入口链：`elb_member_stack`
- `dedicated-loadbalancer-with-full-configuration`
- `shared-loadbalancer-with-full-configuration`
- `dedicated-loadbalancer-with-as`

### 什么时候选哪种
- 先有一个最小公网入口：最小入口
- 同时要 listener、pool、member、monitor：完整入口链
- 要细控独享实例规格和能力：独享型 full configuration
- 只是共用平台负载均衡能力：共享型 full configuration
- 要和自动伸缩联动：`dedicated-loadbalancer-with-as`

### 高价值字段
- `loadbalancer_provider`: 共享型与独享型的核心区别
- `vip_subnet_id`: 决定入口所在网络
- `l4_flavor_id` / `l7_flavor_id`: 独享型常见
- `protocol` / `protocol_port`: listener 和 pool 必须对齐
- `lb_algorithm`: 后端调度策略
- `healthmonitor`: 监控类型必须与后端协议一致

### 常见误区
- 共享型和独享型字段混用
- 只配了 ELB 本体，忘了 EIP 关联
- listener 是 HTTP，但 monitor 却按 TCP 或错误 URL 去探测

## CCE

### 常见变体
- `standard-cluster`
- `turbo-cluster`
- `node-pool`
- `node`
- `node-partition`
- `addon-autoscaler`
- `addon-coredns`

### 什么时候选哪种
- 常规业务集群：`standard-cluster`
- 对高性能网络或高密度有要求：`turbo-cluster`
- 想按池管理节点伸缩：`node-pool`
- 想精确管理单节点：`node`
- 对数据盘和分区有明确要求：`node-partition`
- 进入生产可用性治理：`addon-autoscaler`、`addon-coredns`

### 高价值字段
- `cluster_type`: 标准型和 Turbo 的根差异
- `container_network_type`: 决定集群网络模型
- `flavor_id`: 集群规格
- `root_volume` / `data_volumes`: 节点池和节点最容易踩坑的地方
- `runtime`: 某些版本和插件组合依赖它
- `addons`: 不同版本和集群类型的兼容性重点

### 常见误区
- subnet 有网段，但没配 DNS
- 集群建好了就直接装 addon，没先对齐版本
- 把单节点配置和 node pool 伸缩配置混在一起

## RDS

### 常见变体
- `mysql-single-instance`
- `postgresql-ha-instance`
- `read-replica-instance`
- `sqlserver-single-instance`
- `mysql-instance-associate-eip`

### 什么时候选哪种
- 只要单实例数据库：single instance
- 生产数据库、高可用优先：HA instance
- 读写分离：read replica
- 有固定引擎要求：按数据库类型分支
- 需要公网访问：associate EIP，但只在明确需要时用

### 高价值字段
- `db.type` / `db.version`: 先决定引擎，再决定 flavor
- `ha_replication_mode`: 主备才需要
- `availability_zone`: 单机和主备填写方式不同
- `volume.type` / `volume.size`: 存储性能和容量的关键
- `public_ips` 或 EIP 关联能力：仅在公网访问场景使用

### 常见误区
- 把单机 flavor 直接套到主备
- 先决定 flavor，再去倒推引擎和 AZ
- 还没确认安全边界就给数据库直接公网暴露

## OBS

### 常见变体
- `bucket-with-encryption`
- `bucket-with-website`
- `object-upload-with-content`
- `object-upload-with-source`
- `object-upload-with-encryption`

### 什么时候选哪种
- 只要安全桶：bucket + encryption
- 要托管静态网站：website
- 只是想演示内联对象：upload with content
- 要上传本地资源：upload with source
- 要控制对象级别加密：upload with encryption

### 高价值字段
- `acl`: 默认应保守
- `versioning`: 适合关键业务桶
- `website`: 静态托管才需要
- `sse_algorithm` / `kms_key_id`: 桶级与对象级都可能出现
- `source` / `content`: 对象上传二选一

### 常见误区
- 把网站托管场景和私有加密桶场景混在一起
- 桶级已加密，却又误解对象级加密是必填
- 对象上传直接把大文件内容内联到 HCL

## DMS

### 常见变体
- `rabbitmq`
- `kafka`
- `rocketmq`

### 什么时候选哪种
- 要队列和传统消息模型：RabbitMQ
- 要日志流、事件流和消费组：Kafka
- 要事务消息或更偏 RocketMQ 生态：RocketMQ

### 高价值字段
- `engine`: 先决定消息引擎
- `engine_version`: 与规格和 AZ 绑定很强
- `storage_spec_code` / `partition_num` / `broker_num`: 引擎不同字段差异很大
- `security_group_id` / `subnet_id`: 内网可达性基础

### 常见误区
- 把 RabbitMQ、Kafka、RocketMQ 的容量/分区参数混用
- 只考虑实例建不建得起来，忽略客户端网络可达性

## DCS

### 常见变体
- `redis-single-instance`
- `redis-high-availability-instance`
- `redis-data-sync`

### 什么时候选哪种
- 最小缓存：single
- 生产可用性优先：high availability
- 做跨集群或跨实例同步：data sync

### 高价值字段
- `engine_version`
- `capacity`
- `flavor`
- `available_zones`
- `maintain_begin` / `maintain_end`

### 常见误区
- 想做高可用却还在用单实例思维选 flavor
- 先填密码，后面才发现网络和 AZ 不匹配

## APIG

### 常见变体
- 最小实例与插件
- `api-custom-authorizer-with-functiongraph`
- `kafka-forward-plugin`
- `proxy-cache-plugin`

### 什么时候选哪种
- 只要把 API 平台先搭起来：最小实例
- 要自定义认证：custom authorizer
- 要把流量转 Kafka：kafka-forward
- 要做代理缓存：proxy-cache

### 高价值字段
- `instance_mode`
- `group_id`
- `environment_id`
- `publish_id`
- `plugin_type`
- `backend_params`

### 常见误区
- API、group、environment、publishment 没串起来
- 插件挂上了，但跟 API 或 stage 没关联

## 如何把这些变体继续沉淀进 skill

优先顺序建议：
1. 先把最接近真实项目的变体做成增强版示例
2. 再把跨服务组合链路提炼成组合型示例
3. 最后才考虑是否需要继续新增更多独立 `*_stack`
