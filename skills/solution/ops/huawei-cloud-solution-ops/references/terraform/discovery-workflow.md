# Discovery Workflow

华为云 Terraform 的默认工作流应该是“先探测依赖，再生成资源定义”，而不是直接凭经验写死参数。

## 总原则

### 什么时候优先用 data source
- 需要复用现网资源
- 需要根据 region/AZ 动态选 flavor、image、subnet
- 需要让配置具备一定可移植性

### 什么时候优先用 `hcloud`
- 用户要先查询当前账号里已有资源
- 需要确认 project、region、候选资源是否真实存在
- 需要在写 Terraform 前先摸清现网参数
- 需要定位某个 API 级别报错的真实原因

补充参考：
- 变体怎么选，优先看 `service-variant-guide.md`
- 具体该用哪个 data source，优先看 `data-source-selection-guide.md`

## ECS 推荐流程

### 步骤
1. 确认 region
2. 确认是新建网络还是复用现有网络
3. 查询可用 AZ
4. 按 AZ 查询可用 flavor
5. 按架构 / OS / 可见性筛选 image
6. 查询或创建 subnet、security group
7. 再生成 `huaweicloud_compute_instance`

### 推荐 data source 组合

```hcl
data "huaweicloud_availability_zones" "current" {}

data "huaweicloud_compute_flavors" "ecs" {
  availability_zone = data.huaweicloud_availability_zones.current.names[0]
  performance_type  = "normal"
  cpu_core_count    = 2
  memory_size       = 4
}

data "huaweicloud_images_image" "ubuntu" {
  name        = "Ubuntu 18.04 server 64bit"
  visibility  = "public"
  most_recent = true
}
```

### 复用现网子网和安全组

```hcl
data "huaweicloud_vpc_subnet" "target" {
  id = var.subnet_id
}

data "huaweicloud_networking_secgroup" "target" {
  name = var.secgroup_name
}
```

## VPC 推荐流程

### 新建网络
- 直接创建 `huaweicloud_vpc`
- 再创建 `huaweicloud_vpc_subnet`
- 如需安全控制，再创建 `huaweicloud_networking_secgroup`

### 复用网络
- 优先通过 `data "huaweicloud_vpc_subnet"` 获取 subnet
- 再从 subnet 反查 `vpc_id`
- 避免只凭名称猜测网络关系

## OBS 推荐流程

OBS 场景比 ECS 简单，但仍需要先确认：
- bucket 是否应新建
- bucket 名是否符合全局唯一约束
- 是否需要版本控制、日志、加密、多 AZ

不要默认输出公共读写 bucket。

如果是 website hosting、对象上传或对象级加密场景，先明确这是不是“桶模板”还是“对象操作模板”，不要混成一个最小主链路。

## RDS 推荐流程

RDS 需要先确认：
- VPC / subnet / security group
- 可用 AZ
- flavor 是否匹配数据库类型和 HA 模式
- 密码和 KMS 是否已准备

RDS 比 ECS 更容易受 region、AZ、flavor、HA 组合约束影响，不要在没有校验依赖的情况下直接写死。

推荐优先通过 `huaweicloud_rds_flavors` 发现 flavor，再在必要时允许用户显式覆盖：
- 常见过滤条件包括 `db_version`、`instance_mode`、`group_type`、`vcpus`、`memory`、`availability_zone`
- 如果 discovery 结果为空，再回退到显式 `rds_flavor`，或者先用 `hcloud` / 控制台确认候选值

如果用户一开始就说的是“只读副本”“主备”“公网数据库”，先确定这是哪条变体，再决定 flavor 和网络，而不是把最小单机模板强行改过去。

## CCE 推荐流程

CCE 至少要拆成两段来思考：
- 集群本体
- 节点池

### CCE Cluster
1. 确认 region
2. 确认 VPC / subnet 是否新建
3. 确认 subnet DNS 是否已经配置
4. 确认是否需要 EIP
5. 通过 `huaweicloud_cce_flavor_specifications` 发现可售卖的 cluster flavor
6. 再生成 `huaweicloud_cce_cluster`

### CCE Node Pool
1. 确认要挂到哪个 cluster
2. 确认 node pool 所在 AZ
3. 通过 `huaweicloud_compute_flavors` 发现节点规格
4. 确认 key pair 是否已存在
5. 确认 root/data volume 类型和大小
6. 再生成 `huaweicloud_cce_node_pool`

不要在没有确认 subnet DNS、cluster flavor、node flavor 和 key pair 的情况下直接生成节点池。

如果任务已经明显进入 addon、partition 或 turbo-cluster 语义，优先先切换到对应变体思路，不要继续沿用最小 `cce_stack` 的假设。

## EIP 推荐流程

EIP 场景通常比较直接，但仍需要先确认：
- 是独立创建，还是绑定已有资源
- 是专用带宽还是共享带宽
- 是给 ECS、ELB 还是 NAT 使用

如果用户只说“给我一个公网入口”，先确认目标资源类型，再决定是独立 EIP、ELB 关联还是 NAT 出口。

## ELB 推荐流程

1. 确认是共享型还是独享型负载均衡
2. 确认负载均衡所在 subnet
3. 确认是否需要公网 EIP
4. 确认 listener 协议和端口
5. 确认 backend pool 协议和调度算法
6. 如需完整业务入口，再补 member 和 monitor

现在已提供两类 ELB 示例：
- `elb_stack`: 只覆盖入口层本体
- `elb_member_stack`: 覆盖入口层 + backend ECS + member + monitor

如果用户说的是“独享型负载均衡”“完整七层配置”“配合自动伸缩”，先确认不是共享型最小入口，再决定模板。

## NAT 推荐流程

1. 确认 VPC / subnet
2. 确认 NAT gateway 规格
3. 确认是做 SNAT 还是 DNAT
4. 确认 EIP 和带宽
5. 如果是 SNAT，确认按 subnet 还是 CIDR 出网
6. 如果是 DNAT，再补私网目标地址和端口映射

现在已提供两类 NAT 示例：
- `nat_snat_stack`: 统一出网
- `nat_dnat_stack`: 公网入站端口映射

## 联动模式建议

当用户要求“根据当前华为云账号情况生成 Terraform”时，默认顺序：
1. 用 `hcloud` 或用户给定信息确认现网资源
2. 把发现到的关键依赖抽成变量或 data source
3. 再生成 Terraform 代码

这样生成出来的配置更接近真实可执行结果。

## 第一批扩面服务的 discovery 建议

### IMS
1. 先确认是“选现成镜像”还是“导入新镜像”
2. 如果只是给 ECS / CCE 找镜像，优先 `huaweicloud_images_image`
3. 如果要做镜像导入，再区分来源是 ECS、EVS 还是 OBS
4. 如果用户只给业务标签，优先按标签或 OS 版本筛镜像，而不是凭名字猜

### EVS
1. 先确认 volume 是系统盘、数据盘还是快照恢复盘
2. 确认可用 AZ
3. 通过 `huaweicloud_evs_volume_types` 或等价 data source 确认可用盘型
4. 再确认大小、加密、快照来源

### DNS
1. 先确认是公网 zone 还是私网 zone
2. 如果是私网 zone，先确认关联 VPC
3. 再确认要创建的 recordset 类型、TTL 和 records
4. 如果是解析器场景，再补 resolver endpoint / resolver rule

### VPCEP
1. 先确认要接入的是公共服务还是自建 endpoint service
2. 确认 VPC、subnet、port_id
3. 如果接的是公共服务，优先先查 `huaweicloud_vpcep_public_services`
4. 如果是服务提供方场景，再确认 approval / service connection 流程

### WAF
1. 先确认是云模式还是独享模式
2. 先确认被防护资源是不是已经具备公网入口
3. 再确认域名、证书、策略和实例绑定关系
4. 如果只是想快速接入域名，先确认域名已备案、证书可用、源站入口明确

### AS
1. 先确认是按 ECS 组扩缩，还是围绕已有配置做策略扩缩
2. 先确认 launch configuration / scaling configuration
3. 再确认 group 的最小、最大、期望实例数
4. 最后补 policy、notification、lifecycle hook

### SWR
1. 先确认是基础镜像仓库还是企业版 SWR
2. 先确认 organization / namespace / repository 命名
3. 再确认镜像保留策略、同步区域、访问控制
4. 如果是给 CCE 用，优先先确认镜像拉取地址和认证方式

### DCS
1. 先确认是 Redis 哪个版本和实例形态
2. 先确认 region、AZ、子网和安全组
3. 优先通过 `huaweicloud_dcs_flavors` 和 `huaweicloud_dcs_az` 发现可用规格
4. 再确认密码、维护窗口、备份或高可用要求

如果用户要的是 HA 或数据同步，先把实例形态定下来，再去选 flavor 和容量。

## 第二批扩面服务的 discovery 建议

### APIG
1. 先确认是共享实例还是专享实例
2. 确认 API 所属 group、environment 和发布目标
3. 如果要接私网后端，先确认 VPC channel
4. 再补 ACL、throttling、plugin 或 signature

如果用户直接提到 FunctionGraph 授权、自定义认证、Kafka 转发或代理缓存，说明已经不是最小 APIG 模板，应直接切到对应高级变体。

### CDN
1. 先确认域名是否已经接入并完成归属校验
2. 确认源站类型、源站地址和业务类型
3. 再确认缓存、预热、刷新和证书要求
4. 如果用户主要诉求是加速静态站点，先从 domain 和 cache policy 开始

如果目标是 HTTPS、缓存、规则引擎同时生效，优先先确认域名、证书和缓存层级关系，再决定是最小模板还是增强模板。

### ER
1. 先确认是否已有 ER 实例
2. 再确认要挂载的 VPC、VPN 或其他 attachment
3. 确认 route table 和静态路由目标
4. 如果是多网络互通场景，优先画清 attachment 和 route 关系再写 Terraform

### VPN
1. 先确认是站点到站点还是远程接入
2. 先确认 gateway、customer gateway 和本地/对端网段
3. 再确认连接、健康检查和证书
4. 如果用户只说“打通两端网络”，不要跳过本地和对端 CIDR 的确认

### CBR
1. 先确认要保护的是 ECS、云盘、数据库还是文件系统
2. 先确认 vault、policy 和保护对象
3. 再确认是否涉及复制、共享或恢复
4. 如果只是要“先把备份纳入管理”，从 vault + policy + protectable resources 开始

如果目标对象不是服务器而是云盘或 SFS Turbo，先切到对应变体，而不是硬套 `cbr_stack`。

### IAM
1. 先确认任务是账号治理、委托授权还是项目级权限配置
2. 如果依赖现网账号结构，优先先用 `hcloud` / 控制台确认用户、用户组、agency 和 policy
3. Terraform 代码里优先沉淀最终确定的授权关系，而不是猜测组织结构

如果涉及 V5 IAM、跨项目授权或复杂 agency 关系，先在 Terraform 外确认结构，再决定是否需要增强模板。

### LTS
1. 先确认是日志组/流、日志接入、转储还是告警
2. 先确认日志来源是主机、CCE、WAF 还是其他服务
3. 再确认 transfer、notification template 和查询需求
4. 如果用户只是要“把日志接进来”，先建 group / stream，再补 access 或 transfer

### SMN
1. 先确认 topic、subscription、protocol 和接收端
2. 再确认是否需要模板、通知策略和日志
3. 如果要与告警或自动化联动，先确认 topic 归属和 endpoint 是否真实可达

### TMS
1. 先确认目标是“定义标签”还是“批量给资源打标签”
2. 再确认资源类型、资源 ID 和标签规范
3. 如果是全局治理场景，优先先确认标签字典和命名规则，而不是先写资源绑定

## 第三批扩面服务的 discovery 建议

### Anti-DDoS
1. 先确认被保护对象是不是公网 EIP
2. 先确认是开启基础防护、默认策略还是定制策略
3. 再确认是否要接 LTS 或其他日志联动

### AOM
1. 先确认目标是告警、Prometheus、事件还是仪表盘
2. 再确认指标来源和通知目标
3. 如果要跨账号或跨服务聚合，先确认数据源关系

如果用户提到 alarm-rule、message-template 或 Prometheus，说明已超出最小 callback 模板。

### BMS
1. 先确认是新建裸金属还是对现有实例做重装、重启、挂盘
2. 先确认可用区、规格、镜像和盘型
3. 再确认网络、SSH 或密码策略

### CBH
1. 先确认是单实例还是高可用实例
2. 先确认 VPC、subnet、安全组和可用区
3. 再确认资产授权、登录模式和运维入口

### CCI
1. 先确认是 namespace、network 还是存储卷场景
2. 先确认要挂到哪个 VPC / subnet
3. 如果要和 CCE 或其他容器平台联动，先明确边界，不要混用术语

### COC
1. 先确认目标是应用、分组、脚本、文档、工单还是故障处理
2. 先确认现网组织结构和运维流程
3. Terraform 更适合沉淀稳定对象，不适合把临时排障动作全部硬编码

### CTS
1. 先确认是追踪器、数据追踪还是通知配置
2. 再确认日志落地位置，比如 OBS 或 SMN
3. 如果用户要查审计事件，优先分清“查事件”和“配置追踪器”

### DMS
1. 先确认消息引擎是 Kafka、RabbitMQ、RocketMQ 还是队列
2. 再确认规格、AZ、网络和安全组
3. 如果只是做消息主题或用户管理，先确认实例已存在

如果引擎从 RabbitMQ 切到 Kafka 或 RocketMQ，优先先重选变体，不要只改几个字段继续沿用同一个模板。

### FGS
1. 先确认是函数本体、依赖、触发器还是应用
2. 再确认 runtime、handler、内存、超时和触发源
3. 如果要接 VPC、日志或事件源，先确认外围资源已存在

## 第四批扩面服务的 discovery 建议

### CC
1. 先确认目标是云连接、中心网络、网络实例还是带宽包
2. 先画清跨区域、跨 VPC 或跨站点的连接关系
3. 再确认权限、带宽和路由边界

### CES
1. 先确认目标是监控指标、告警规则、模板还是 dashboard
2. 再确认指标 namespace、metric 名称和触发条件
3. 如果用户只是想“监控某资源”，先确认资源本身是否已经暴露指标

### DC
1. 先确认是专线网关、虚拟网关、虚拟接口还是全局网关
2. 再确认本地和对端网络、VLAN、带宽和路由模式
3. 如果涉及物理专线接入，先确认 Terraform 管理范围和运营商侧边界

### DEH
1. 先确认是否真的需要专属主机，而不是普通 ECS / BMS
2. 再确认 host 类型、可用区和放置策略
3. 如果用户主要诉求是合规隔离，先确认主机类型与实例规格是否匹配

### DEW
1. 先确认目标是证书、私有 CA 还是密钥管理
2. 再确认要管理的是长期稳定对象，还是一次性运维动作
3. 如果要给其他服务接证书或 KMS，先确认下游资源已准备好

### EG
1. 先确认是事件通道、事件源、连接还是订阅
2. 再确认事件来源、目标服务和规则
3. 如果要做跨服务事件桥接，先画清 source -> channel -> subscription -> target

### ESW
1. 先确认是实例、连接还是 vport 绑定
2. 再确认可用区、规格和目标网络边界
3. 如果与其他网络服务组合，先确认谁负责主路由和谁负责交换

### HSS
1. 先确认是主机防护、勒索防护、基线、漏洞还是网页防篡改
2. 再确认保护对象范围和策略组
3. 如果任务是治理现网风险，优先先查现网状态，再写 Terraform 管理稳定策略

### Identity Center
1. 先确认是实例、用户、用户组、权限集还是账号分配
2. 再确认真实组织结构和账号映射
3. 如果用户只是想做统一身份入口，不要直接跳到复杂授权对象，先从 instance / user / group / permission set 开始

## 最后一批扩面服务的 discovery 建议

### OMS
1. 先确认是对象迁移、增量同步还是任务编排
2. 再确认源端、目标端、bucket 和同步模式
3. 如果涉及跨云或跨区域迁移，先确认两端凭据和网络可达性

### Organizations
1. 先确认是组织、账号、OU、策略还是委派服务
2. 再确认真实组织树和账号关系
3. 对组织类服务，先画清层级，再写 Terraform

### RAM
1. 先确认是共享资源、共享权限还是接受共享
2. 再确认共享主体、资源 ARN 和权限模板
3. 如果跨账号共享，先确认目标主体真实存在

### RGC
1. 先确认是 landing zone、账号注册、控制策略还是模板
2. 再确认组织结构、home region 和治理边界
3. 如果和 Organizations / Identity Center 联动，优先先理顺组织模型

### RMS
1. 先确认是 recorder、aggregator、policy assignment 还是 remediation
2. 再确认 scope、policy definition 和目标资源范围
3. 如果用户主要诉求是合规盘点，先从 recorder + aggregator 开始

### SDRS
1. 先确认是保护组、复制对、受保护实例还是演练
2. 再确认主备站点、磁盘复制关系和业务 RPO 目标
3. 如果用户只是要高可用，不要跳过主备拓扑确认

### SecMaster
1. 先确认目标是告警、规则、事件、playbook 还是 workflow
2. 再确认 workspace、数据源和自动化链路
3. 对安全运营对象，Terraform 更适合沉淀稳定规则，不适合直接承载临时处置动作

### SFS Turbo
1. 先确认是文件系统本体、目录、权限、配额还是 OBS 目标
2. 再确认 VPC、subnet、share type 和容量
3. 如果与计算资源联动，先确认挂载端和网络可达性

### SMS
1. 先确认是迁移项目、源端主机、任务还是模板
2. 再确认目标 region、迁移波次和网络连通性
3. 如果用户只是查迁移状态，先不要误写成创建型 Terraform
