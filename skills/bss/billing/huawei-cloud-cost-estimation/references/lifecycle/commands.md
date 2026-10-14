# 开通命令白名单

KooCLI 7.2.2 证据快照。这里只保存可执行开通命令的主体与精确语义；参数必须在执行时通过 `hcloud <Service> <Operation> --help` 获取。少数前置或配置动作会明确标注为非独立计费。退订不在白名单内，只按 `concepts.md` 指引用户前往控制台。

依赖列是查询方向，不代替 help：`P` 项目、`ORG` 账号、`EP` 企业项目、`N` 网络、`AZ` 可用区、`IMG` 镜像、`DISK` 云盘类型、`KEY` 密钥对、`SPEC` 规格、`PRODUCT` 产品、`PARENT` 父资源、`STACK` IDE 技术栈、`H` 仅以运行时 help 为准。

## 开通命令（74）

| 主体 | 语义 | 计费 | 依赖 |
| --- | --- | --- | --- |
| `APIG/CreateInstanceV2` | 创建API网关（API Gateway，APIG）按需专享版实例（V2） | 按需 | P, EP, N |
| `APIG/CreateOrder` | 创建API网关（API Gateway，APIG）包周期专享版实例订单（V2） | 包周期 | P, EP, N, PRODUCT |
| `BMS/CreateBareMetalServers` | 创建一台或多台裸金属服务器（Bare Metal Server，BMS） | 按需/包周期 | P, EP, N, AZ, IMG, DISK, KEY, SPEC |
| `CBH/CreateCbh` | 创建待下单的云堡垒机（Cloud Bastion Host，CBH）实例 | 下单前置，非独立计费 | P, EP, N, AZ, SPEC |
| `CBH/CreateInstance` | 创建包周期云堡垒机（Cloud Bastion Host，CBH）实例 | 包周期 | P, EP, N, AZ |
| `CBH/CreateInstanceOrder` | 创建包周期云堡垒机（Cloud Bastion Host，CBH）实例订单 | 包周期 | P, PRODUCT |
| `CBR/CreatePolicy` | 创建云备份（Cloud Backup and Recovery，CBR）备份或复制策略 | 非独立计费 | P |
| `CBR/CreatePostPaidVault` | 创建云备份（Cloud Backup and Recovery，CBR）包周期存储库 | 包周期 | P, EP |
| `CBR/CreateVault` | 创建云备份（Cloud Backup and Recovery，CBR）存储库 | help 决定 | P, EP, AZ |
| `CCE/CreateAutopilotCluster` | 创建云容器引擎（Cloud Container Engine，CCE）按需 Autopilot 空集群 | 按需 | P, N, AZ, IMG, SPEC |
| `CCE/CreateCluster` | 创建云容器引擎（Cloud Container Engine，CCE）Standard/Turbo 空集群 | 按需/包周期 | H |
| `CCE/CreateNode` | 在指定云容器引擎（Cloud Container Engine，CCE）集群中创建节点 | 按需/包周期 | P, N, AZ, IMG, DISK, SPEC, PARENT |
| `CCE/CreateNodePool` | 在指定云容器引擎（Cloud Container Engine，CCE）集群中创建节点池，可同时初始化节点 | 节点按需/包周期 | H |
| `CCE/SubscribePackageProducts` | 订购云容器引擎（Cloud Container Engine，CCE）套餐包 | help 决定 | PRODUCT |
| `CDM/CreateCluster` | 创建云数据迁移（Cloud Data Migration，CDM）集群 | help 决定 | H |
| `CDN/CreateDomain/v1` | 创建内容分发网络（Content Delivery Network，CDN）加速域名（KooCLI v1 绑定） | help 决定 | H |
| `CDN/CreateDomain/v2` | 创建内容分发网络（Content Delivery Network，CDN）加速域名（KooCLI v2 绑定） | help 决定 | H |
| `CFW/CreateEastWestFirewall` | 为既有云防火墙（Cloud Firewall，CFW）实例创建东西向防火墙 | 配置动作，非独立计费 | P, EP |
| `CFW/CreateFirewall` | 购买云防火墙（Cloud Firewall，CFW）实例 | 按需/包周期 | P, EP, N, SPEC |
| `CloudTable/CreateCloudTableCluster` | 创建表格存储服务（CloudTable Service，CloudTable）HBase、Doris 或 ClickHouse 集群 | help 决定 | H |
| `CloudTable/CreateCluster` | 创建表格存储服务（CloudTable Service，CloudTable）集群（V2 旧接口，已废弃） | help 决定 | H |
| `CloudIDE/CreateInstance` | 创建 CodeArts IDE Online 云端开发环境实例 | 按需 | ORG, STACK |
| `CodeArtsInspector/CreatePurchaseOrder` | 创建漏洞管理服务（CodeArts Inspector，原 VSS）网站漏洞扫描套餐订购订单 | 付费订购，help 决定 | P, PRODUCT |
| `CSE/CreateEngine` | 创建微服务引擎（Cloud Service Engine，CSE）ServiceComb 引擎专享版、注册配置中心或应用网关 | 按需 | P, N, SPEC |
| `CSS/CreateCluster/v1` | 创建云搜索服务（Cloud Search Service，CSS）单节点角色 Elasticsearch 集群（V1 旧接口，已废弃） | 按需/包周期 | P, EP, N, AZ, DISK, SPEC |
| `CSS/CreateCluster/v2` | 创建云搜索服务（Cloud Search Service，CSS）多节点角色组合集群（V2） | 按需/包周期 | P, EP, N, AZ, DISK, SPEC |
| `DataArtsStudio/PayForDgcOneKey` | 一键购买数据治理中心（DataArts Studio，原 DGC）实例 | help 决定 | H |
| `DBSS/CreateDbEncryptInstancePeriod` | 包周期购买数据库安全服务（Database Security Service，DBSS）数据库加密实例 | 包周期 | P, EP, N, AZ, IMG, SPEC |
| `DBSS/CreateDbOmInstancePeriod` | 包周期购买数据库安全服务（Database Security Service，DBSS）数据库运维实例 | 包周期 | P, EP, N, AZ, IMG, SPEC |
| `DBSS/CreateInstancesPeriodOrder` | 包年/包月创建数据库安全服务（Database Security Service，DBSS）数据库审计实例（待下线接口） | 包周期 | P, EP, N, AZ, IMG, SPEC |
| `DBSS/CreateInstancesPeriodOrderNew` | 包年/包月创建数据库安全服务（Database Security Service，DBSS）数据库审计实例（现行接口） | 包周期 | P, EP, N, AZ, IMG, SPEC |
| `DCS/CreateInstance` | 创建分布式缓存服务（Distributed Cache Service，DCS）缓存实例（V2 推荐接口） | 按需/包周期 | P, EP, N, SPEC |
| `DDM/CreateDdmInstance` | 购买分布式数据库中间件（Distributed Database Middleware，DDM）实例（V3） | help 决定 | H |
| `DDM/CreateInstance` | 购买分布式数据库中间件（Distributed Database Middleware，DDM）实例（V1） | help 决定 | H |
| `DDS/CreateInstance` | 创建文档数据库服务（Document Database Service，DDS）集群、副本集或单节点实例（V3） | 按需/包周期 | P, EP, N, AZ, SPEC |
| `DeH/CreateDedicatedHost` | 分配一台或多台专属主机（Dedicated Host，DeH） | help 决定 | H |
| `DSC/CreateProductOrder` | 提交数据安全中心（Data Security Center，DSC）实例订单 | help 决定 | P, PRODUCT |
| `DWS/CreateCluster` | 创建数据仓库服务（Data Warehouse Service，DWS）集群（V1.0 旧接口，仅维护现有功能） | help 决定 | P, EP, N, AZ, KEY, SPEC |
| `DWS/CreateClusterV2` | 创建数据仓库服务（Data Warehouse Service，DWS）集群（V2 推荐接口） | help 决定 | P, EP, N, AZ, KEY, SPEC |
| `ECS/CreatePostPaidServers` | 创建一台或多台按需弹性云服务器（Elastic Cloud Server，ECS）（V1） | 按需 | P, EP, N, AZ, IMG, DISK, KEY, SPEC |
| `ECS/CreateServers` | 创建一台或多台弹性云服务器（Elastic Cloud Server，ECS）（V1.1） | 按需/包周期 | P, EP, N, AZ, IMG, DISK, KEY, SPEC |
| `EIP/CreatePrePaidPublicip` | 申请包年/包月弹性公网IP（Elastic IP，EIP） | 包周期 | P, EP |
| `EIP/CreatePublicip` | 申请按需 IPv4 或 IPv6 弹性公网IP（Elastic IP，EIP） | 按需 | P, EP |
| `EIP/CreateSharedBandwidth` | 创建弹性公网IP（Elastic IP，EIP）共享带宽（V2.0） | help 决定 | P, EP |
| `ELB/CreateLoadBalancer/v2` | 创建弹性负载均衡（Elastic Load Balance，ELB）共享型私网负载均衡器（V2） | help 决定 | P, EP, N |
| `ELB/CreateLoadBalancer/v3` | 创建弹性负载均衡（Elastic Load Balance，ELB）独享型负载均衡器（V3） | 按需/包周期 | P, EP, N, AZ, SPEC |
| `EPS/CreateEnterpriseProject` | 创建企业项目管理（Enterprise Project Management Service，EPS）企业项目 | 免费逻辑治理对象，非资源订单 | P |
| `ESW/CreateInstance` | 创建企业交换机（Enterprise Switch，ESW）实例 | 按需 | H |
| `EVS/CreateVolume` | 创建云硬盘（Elastic Volume Service，EVS）（V2.1） | 按需/包周期 | P, EP, AZ, IMG, DISK |
| `GaussDB/CreateGaussMySqlInstance` | 创建云数据库 TaurusDB 实例 | 按需/包周期 | P, EP, N, AZ, SPEC |
| `GaussDB/CreateStarrocksInstance` | 为指定云数据库 TaurusDB 实例创建 HTAP 标准版 StarRocks 实例 | 按需/包周期 | P, N, SPEC, PARENT |
| `GaussDBforNoSQL/CreateInstance` | 创建云数据库 GeminiDB 新实例，或将备份/指定时间点数据恢复为新实例 | 按需/包周期 | P, EP, N, AZ, SPEC, PRODUCT |
| `GaussDBforopenGauss/CreateDatabaseInstance` | 通过 API v3.2 创建云数据库 GaussDB 实例 | 按需/包周期 | P, EP, N, AZ, SPEC |
| `GaussDBforopenGauss/CreateDbInstance` | 通过 API v3.1 创建云数据库 GaussDB 实例 | 按需/包周期 | P, EP, N, AZ, SPEC |
| `GaussDBforopenGauss/CreateGaussDbInstance` | 通过 API v5 和 IAM 新平面认证创建云数据库 GaussDB 实例 | 按需/包周期 | P, EP, N, AZ, SPEC |
| `GaussDBforopenGauss/CreateInstance` | 通过历史 API v3 创建云数据库 GaussDB 企业版或集中式实例 | 按需/包周期 | P, EP, N, AZ, SPEC |
| `HSS/CreateAntiVirusPaidTask` | 创建企业主机安全（Host Security Service，HSS）付费病毒扫描任务 | 付费 | P, EP |
| `HSS/CreateQuotasOrder` | 订购企业主机安全（Host Security Service，HSS）包周期防护配额 | 包周期 | P, EP |
| `IEC/CreateInstance` | 创建智能边缘云（Intelligent Edge Cloud，IEC）边缘实例 | help 决定 | H |
| `Kafka/CreatePostPaidKafkaInstance` | 创建分布式消息服务Kafka版（Distributed Message Service for Kafka，DMS for Kafka）实例 | 按需/包周期 | P, EP, N, PRODUCT |
| `MetaStudio/CreateMetaStudioOrders` | 订购数字内容生产线 MetaStudio 的包周期、一次性或按需套餐包产品 | 包周期/一次性/按需套餐包 | H |
| `MRS/CreateCluster/v1` | 通过 API V1.1 创建 MapReduce 服务（MapReduce Service，MRS）集群并提交一个作业 | 按需/包周期 | P, EP, N, DISK |
| `MRS/CreateCluster/v2` | 通过 API V2 创建 MapReduce 服务（MapReduce Service，MRS）集群 | 按需/包周期 | P, EP, N, AZ, KEY |
| `NAT/CreateNatGateway` | 创建 NAT 网关（NAT Gateway，NAT）公网 NAT 网关实例 | 按需/包周期 | P, EP, N |
| `RabbitMQ/CreatePostPaidInstanceByEngine` | 创建分布式消息服务RabbitMQ版（Distributed Message Service for RabbitMQ，DMS for RabbitMQ）实例 | 按需/包周期 | P, EP, N, PRODUCT |
| `RDS/CreateInstance` | 创建云数据库 RDS（Relational Database Service，RDS）单机、主备、集群或只读实例 | 按需/包周期 | P, EP, N, AZ, SPEC |
| `RDS/CreateInstanceIam5` | 通过 v5 接口创建云数据库 RDS（Relational Database Service，RDS）实例，支持 RAM 共享 KMS 密钥的包周期加密场景 | 按需/包周期 | P, EP, N, AZ, SPEC |
| `RocketMQ/CreateInstanceByEngine` | 创建分布式消息服务RocketMQ版（Distributed Message Service for RocketMQ，DMS for RocketMQ）实例 | 按需/包周期 | P, EP, N, PRODUCT |
| `SCM/SubscribeCertificate` | 通过 SSL 证书管理（SSL Certificate Manager，SCM）购买公网 SSL 证书并生成待申请证书 | 付费 | H |
| `SecMaster/CreateSubscriptionOrder` | 开通或配置安全云脑（SecMaster）服务版本、配额及增值包 | 按需/包周期/配置 | P, PRODUCT |
| `VPN/CreateVpnServer` | 在既有终端入云 VPN（Point-to-Cloud VPN，P2C VPN）网关下创建 SSL VPN 服务端模块 | 配置动作，非独立计费 | P, N, PARENT |
| `WAF/CreateCloudWafPostPaidResource` | 开通 Web 应用防火墙（Web Application Firewall，WAF）云模式按需计费资源 | 按需 | P, EP |
| `WAF/CreateInstance` | 创建 Web 应用防火墙（Web Application Firewall，WAF）按需独享引擎实例 | 按需 | P, EP, N, SPEC |
| `WAF/CreatePrepaidCloudWaf` | 购买 Web 应用防火墙（Web Application Firewall，WAF）云模式包年/包月服务版本及扩展包 | 包周期 | P, EP, PRODUCT |

## 依赖查询命令

只读查询也必须先看运行时 help；这里不给参数。

| 标签 | 命令主体 | 语义 |
| --- | --- | --- |
| P | `IAM/KeystoneListAuthProjects`, `IAM/KeystoneListProjects` | 项目范围 |
| ORG | `IAM/KeystoneListAuthDomains` | 当前账号（domain）范围 |
| EP | `EPS/ListEnterpriseProject` | 企业项目（EPS 不支持 `cn-north-1`，查询时使用 `--cli-region=cn-north-4` 等 EPS 可用区域） |
| N | `VPC/ListVpcs/v3`, `VPC/ListSubnets`, `VPC/ListSecurityGroups/v3` | VPC、子网、安全组 |
| AZ | `ECS/NovaListAvailabilityZones`, `ECS/ListServerAzInfo` | 可用区 |
| IMG | `IMS/ListImages` | 镜像 |
| DISK | `EVS/CinderListVolumeTypes` | 云硬盘类型 |
| KEY | `ECS/NovaListKeypairs` | 密钥对 |
| SPEC | `ECS/NovaListFlavors`; 各产品 `ListFlavors` | 当前服务规格 |
| PRODUCT | `Kafka/ListEngineProducts`, `RabbitMQ/ListEngineProducts`, `RocketMQ/ListEngineProducts`, `SecMaster/ListSubscriptionProduct` | 可售产品 |
| PARENT | `CCE/ListClusters`, `GaussDB/ListGaussMySqlInstances`; 服务自身 `List*` | 父集群、父实例或父网关 |
| STACK | `CloudIDE/ListStacks` | CodeArts IDE Online 技术栈与可用规格 |
| H | `hcloud <Service> <Operation> --help` | 运行时发现；help 失败即停止 |
