# Troubleshooting

## 1. flavor 和 image 不匹配

症状：
- `terraform plan` 看起来没问题
- `terraform apply` 创建 ECS 时报兼容性错误

处理：
- 先检查 image 的架构、OS 和最小磁盘要求
- 再检查 flavor 所在 AZ 是否可用
- 优先通过 `huaweicloud_compute_flavors` 和 `huaweicloud_images_image` 重新筛选，而不是反复重试同一组值

## 2. flavor 查询结果为空，`ids[0]` 报错

症状：
- `terraform plan` 或 `terraform apply` 报 index out of range
- 常见于 `data.huaweicloud_compute_flavors.ecs.ids[0]`

处理：
- 先检查 AZ、CPU、内存和 `performance_type` 的组合是否在当前 region 有可用规格
- 如果是联动模式，优先先通过 `hcloud` 或控制台确认现网可用 flavor
- 不要只改一个参数盲试，优先重新确认 region、AZ 和规格约束

如果示例已经使用了 `local + precondition`：
- Terraform 会给出更明确的错误原因
- 优先按错误里提示的过滤条件回退排查，而不是继续依赖默认值

## 3. 指定的系统盘类型在 AZ 中不可用

症状：
- ECS 创建失败
- 常见于指定了某种系统盘类型，但该 AZ 无库存或不支持

处理：
- 检查 `system_disk_type`
- 如无强约束，优先改成当前 region/AZ 常见可用值
- 必要时切换 AZ 再试

## 4. subnet / security group 名称查询不到

症状：
- `data "huaweicloud_vpc_subnet"` 或 `data "huaweicloud_networking_secgroup"` 返回空或多条

处理：
- 优先改用 ID 查询
- 如果是联动模式，先通过 `hcloud` 查询真实资源
- 不要只靠模糊名称硬猜

## 5. OBS bucket 名冲突

症状：
- Bucket 创建失败

原因：
- OBS bucket 名是全局唯一

处理：
- 提醒用户更换 bucket 名
- 不要默认沿用示例里的固定名字

## 6. RDS flavor / AZ / HA 组合不合法

症状：
- RDS 创建失败
- 单机和主备切换时 flavor 或 availability zone 参数不匹配

处理：
- 先确认用户要单机还是主备
- 主备模式要校验 `availability_zone` 列表长度和 `flavor` 是否支持 HA
- 不要把单机 flavor 直接套到主备场景
- 如果使用 `huaweicloud_rds_flavors` discovery，优先检查 `db_version`、`instance_mode`、`group_type`、`vcpus`、`memory` 和 `availability_zone`

## 7. 双变量集冲突

症状：
- shell 里同时存在 `HW_*` 和 `HUAWEI_*`
- 生成的 Terraform 使用的 region/credential 与 MCP 调用结果不一致

处理：
- 明确指出 Terraform provider 官方优先关注 `HW_*`
- 如果任务是联动模式，生成代码前应提醒用户确认两套变量是否指向同一账号/区域

## 8. 什么时候优先联动 `hcloud`

以下情况不要只靠 Terraform 猜测：
- 需要先确认账号中已有资源
- 需要确认 region/project 的真实候选值
- 用户只给了资源名称，没有 ID
- apply 错误看起来和云上库存、权限、现网状态有关

## 9. CCE 集群 flavor 不可用

症状：
- `huaweicloud_cce_flavor_specifications` 结果为空
- 或 precondition 报没有可售卖的 cluster flavor

处理：
- 先确认 `cluster_type`
- 再确认当前 region 是否有可售卖的 cluster flavor
- 如有明确企业标准规格，可直接设置 `cluster_flavor_id`

## 10. CCE 节点池规格查不到

症状：
- `huaweicloud_compute_flavors` 返回空
- 或 precondition 报没有匹配的节点 flavor

处理：
- 先检查 AZ、`node_performance_type`、CPU、内存组合
- 再确认该 region 当前是否还有对应节点规格
- 如果用户已有标准规格，可直接改为显式 flavor ID

## 11. CCE 子网缺少 DNS

症状：
- 集群创建成功，但后续节点加入或安装异常

处理：
- 确认 subnet 配置了 `primary_dns` 和 `secondary_dns`
- 对新建子网，优先在 Terraform 里显式写出 DNS
- 对复用子网，优先先通过 `hcloud` 或控制台确认 DNS 配置

## 12. ELB 创建成功但没有公网入口

症状：
- `huaweicloud_lb_loadbalancer` 已创建
- 但访问时没有公网地址

处理：
- 确认是否已经关联 EIP
- 确认使用的是 `huaweicloud_vpc_eipv3_associate` 或等价绑定方式
- 不要默认认为创建 ELB 就自动有公网入口

## 13. NAT Gateway 创建成功但 SNAT 不生效

症状：
- NAT Gateway 和 EIP 已创建
- 私网资源仍无法正常出网

处理：
- 先确认 `huaweicloud_nat_snat_rule` 是否已创建
- 再确认 `source_type`、`subnet_id` 或 `cidr` 是否与实际出网范围匹配
- 如果是 CIDR 型 SNAT，确认 `snat_cidr` 是否正确

## 14. EIP 已创建但没有绑定到目标资源

症状：
- `huaweicloud_vpc_eip` 已创建
- 但目标 ECS、ELB 或 NAT 没有真正走公网

处理：
- 确认是否还缺少关联资源，比如 `huaweicloud_vpc_eipv3_associate`
- 不要把“创建 EIP”和“完成绑定”当成同一件事

## 15. DNAT 规则创建成功但公网访问不到后端

症状：
- `huaweicloud_nat_dnat_rule` 已创建
- 外部端口访问仍无法连到后端服务

处理：
- 确认 `port_id` 指向的是正确的后端网卡端口
- 确认后端安全组已放通 `backend_port`
- 确认 `frontend_port` 和 `backend_port` 映射符合预期

## 16. ELB 已创建但后端一直不健康

症状：
- `huaweicloud_lb_member` 已创建
- `huaweicloud_lb_monitor` 存在
- 后端状态仍不健康

处理：
- 先确认 security group 是否允许来自 ELB 的探测流量
- 再确认 monitor 的 `type`、`url_path`、`expected_codes` 是否与后端服务一致
- 如果后端服务不是 HTTP，不要默认继续用 HTTP monitor

## 17. 镜像选到了但实例仍无法创建

症状：
- `huaweicloud_images_image` 能查到镜像
- 但 ECS / CCE 节点创建时仍因镜像不兼容失败

处理：
- 把问题拆成 IMS 和计算资源两个层面排查
- 先确认镜像本身是否适合当前架构和启动方式
- 再确认目标 flavor、系统盘类型和目标服务是否支持该镜像

## 18. EVS 盘型在目标 AZ 不可用

症状：
- volume 创建时报盘型不支持或库存不足

处理：
- 优先先查目标 AZ 下的 volume type
- 如果是复用快照恢复，确认快照与目标盘型是否兼容
- 必要时切换 AZ 或切换 volume type

## 19. DNS 记录已创建但解析不生效

症状：
- `huaweicloud_dns_recordset` 已创建
- 但客户端查询结果没有更新

处理：
- 先确认 zone 类型和 recordset 类型是否正确
- 再确认 TTL 和 nameserver 是否已经生效
- 私网 DNS 场景还要确认 VPC 关联是否正确

## 20. VPCEP 端点创建成功但访问不通

症状：
- endpoint 已创建
- 但私网访问目标服务失败

处理：
- 确认 endpoint 对应的 service 是否在当前 region 可用
- 确认 subnet、security group、port_id 是否正确
- 如果是自建服务，确认 approval / service connection 状态已放通

## 21. WAF 域名已接入但业务仍异常

症状：
- WAF domain / policy 已创建
- 但用户访问出现 4xx、回源失败或证书错误

处理：
- 先确认回源地址和监听端口是否正确
- 再确认证书、域名接入方式和策略是否匹配
- 如果是独享模式，确认实例容量和绑定关系是否正确

## 22. AS 组创建成功但没有按预期扩缩容

症状：
- scaling group 已存在
- 但实例数没有变化，或策略不触发

处理：
- 先确认 scaling configuration 是否可用
- 再确认 policy 类型、冷却时间和通知配置
- 如果已有实例挂载，确认 group 状态是否允许继续扩缩

## 23. SWR 仓库已创建但镜像链路不通

症状：
- repository 已创建
- 但镜像 push / pull、同步或保留策略行为不符合预期

处理：
- 先确认 organization / repository 路径是否正确
- 再确认访问权限、同步区域和触发策略
- 如果是企业版，确认实例、域名和网络访问控制是否一致

## 24. DCS 实例创建失败或连不上

症状：
- DCS 申请失败，或实例建好但客户端连不上

处理：
- 先确认 flavor、AZ、容量和实例形态是否匹配
- 再确认 subnet、安全组、密码和维护窗口
- 如果是联动模式，优先先查现网可用规格和网络入口，而不是盲改 engine/version

## 25. APIG 已创建但 API 无法正常发布或调用

症状：
- API、group 或 environment 已创建
- 但发布失败、后端不可达或调用返回异常

处理：
- 先确认 API 所属 group、environment 和 publish 动作是否完整
- 如果走私网后端，确认 VPC channel 指向正确
- 再确认 ACL、throttling、plugin 和签名配置是否把正常请求挡掉

## 26. CDN 域名已接入但加速效果异常

症状：
- CDN domain 已创建
- 但回源异常、缓存不生效或证书校验失败

处理：
- 先确认源站地址、业务类型和加速区域
- 再确认缓存规则、刷新预热和证书绑定
- 如果是新域名，确认归属校验和 DNS 切流是否完成

## 27. ER 资源已创建但网络仍不通

症状：
- ER instance、attachment 或 route table 已存在
- 但 VPC 之间、VPC 与 VPN 之间仍不互通

处理：
- 优先检查 attachment 是否真的挂到了目标实例
- 再检查 route table 和静态路由的目的网段
- 不要只看资源“创建成功”，还要核对转发关系是否完整

## 28. VPN 已创建但两端仍无法通信

症状：
- gateway、customer gateway、connection 均已创建
- 但流量不通或连接反复重建

处理：
- 先确认本地网段、对端网段、peer 地址和协议参数
- 再确认安全组、路由和健康检查
- 如果是远程接入，额外确认用户、证书和接入策略

## 29. CBR 已建 vault 但资源没有真正被保护

症状：
- vault 和 policy 已创建
- 但目标 ECS / 磁盘 / 数据库没有进入备份策略

处理：
- 先确认 protectable resources 和资源绑定关系
- 再确认 policy 是否真正关联到 vault
- 恢复和复制场景要额外确认 backup / checkpoint 是否存在

## 30. IAM 授权写进 Terraform 后与现网不一致

症状：
- Terraform 中已声明授权关系
- 但实际账号权限效果与预期不一致

处理：
- 先确认现网真实的用户、用户组、agency 和 policy 结构
- 如果组织结构复杂，优先先联动 `hcloud` 或控制台确认，再写 Terraform
- 当前不要把 IAM 当作“可以盲猜结构”的服务

## 31. LTS 已创建日志组或转储，但日志仍看不到

症状：
- group / stream / transfer 已创建
- 但日志未写入或转储未生效

处理：
- 先确认日志来源和接入方式
- 再确认 group、stream、transfer 或 access 的绑定关系
- 如果涉及 CCE、WAF 或主机采集，确认上游来源侧配置已打开

## 32. ELB 独享型和共享型字段混用

症状：
- `terraform validate` 报字段不支持
- 或 apply 时提示实例规格、provider 类型不匹配

处理：
- 先确认目标是独享型还是共享型
- 独享型再考虑 `l4_flavor_id` / `l7_flavor_id`
- 不要把共享型最小模板直接加几个独享字段就当成完整配置

## 33. CCE addon 安装失败或版本不兼容

症状：
- addon 资源存在
- 但安装报版本不兼容、依赖缺失或状态异常

处理：
- 先确认 cluster version、cluster type 和 addon 版本的兼容性
- 再确认 VPC、DNS、镜像拉取和节点池状态
- 不要在基础集群还没稳定时就叠加多个 addon

## 34. RDS 只读副本或跨引擎模板套错

症状：
- 想创建 read replica、MySQL 或 SQL Server
- 但仍沿用 PostgreSQL 单机模板，导致字段或 flavor 不匹配

处理：
- 先确认数据库引擎和部署形态
- 再决定 `db.type`、`db.version`、`group_type`、`instance_mode`
- 不要把“数据库最小模板”当作所有引擎都通用

## 35. OBS 网站托管和私有加密桶目标冲突

症状：
- 同时要求 website hosting、严格私有、对象级加密
- 结果配置相互打架或行为与预期不一致

处理：
- 先确认目标到底是静态网站，还是私有对象存储
- 桶级权限、website hosting、对象上传和对象加密要分层考虑
- 如果需求同时存在，优先拆成“托管桶”和“私有数据桶”

## 36. DMS 消息引擎切换后配置仍报错

症状：
- 从 RabbitMQ 切到 Kafka 或 RocketMQ
- 但仍保留旧引擎字段，导致校验失败或创建异常

处理：
- 先确认实例所属消息引擎
- 再重新检查版本、分区/队列、规格和网络参数
- 不要只改 `engine` 一个字段，其余参数要跟着一起切换

## 32. SMN Topic 已创建但通知没有送达

症状：
- topic 和 subscription 已存在
- 但消息没有被接收端收到

处理：
- 先确认 protocol 和 endpoint 是否正确
- 再确认 subscription 是否已确认生效
- 如果用了模板或通知策略，确认策略没有过滤掉目标事件

## 33. TMS 标签已下发但资源侧看不到预期结果

症状：
- 标签资源已创建
- 但目标资源没有按预期带上标签或标签查询结果不一致

处理：
- 先确认 resource type 和 resource ID 是否匹配
- 再确认标签键值是否符合平台限制
- 批量治理场景优先先验证单个资源，再放大到批量资源

## 34. Anti-DDoS 已开启但防护效果不符合预期

症状：
- 防护资源已创建
- 但流量侧状态、策略或日志结果与预期不一致

处理：
- 先确认绑定的是不是目标公网 EIP
- 再确认基础防护、默认策略和日志配置是否对应当前实例
- 不要把“已开通防护”直接等同于“策略已经调优完成”

## 35. AOM 规则已创建但没有触发告警或展示数据

症状：
- 告警规则、通知规则或仪表盘已创建
- 但没有看到预期指标、告警或通知

处理：
- 先确认指标来源和 Prometheus 实例
- 再确认通知对象、模板和静默规则
- 如果是跨账号聚合，额外确认数据源授权链路

## 36. BMS 资源已创建但初始化或运维失败

症状：
- 裸金属实例已申请
- 但远程接入、镜像初始化或数据盘操作异常

处理：
- 先确认规格、镜像和盘型组合
- 再确认网络、密码或 SSH 策略
- 如果是挂盘或重装场景，优先核实现网实例状态

## 37. CBH 已创建但资产或运维入口不可用

症状：
- CBH 实例存在
- 但资产授权、登录地址或运维入口异常

处理：
- 先确认实例模式、可用区、网络和安全组
- 再确认 agency 授权、登录模式和配额
- 如果是高可用模式，确认主备角色和绑定关系

## 38. CCI 资源已创建但工作负载仍无法运行

症状：
- namespace、network 或 PVC 已存在
- 但容器侧仍无法正常调度或访问存储

处理：
- 先确认 VPC / subnet / namespace 边界
- 再确认网络和存储卷配置是否匹配
- 不要把 CCI 与 CCE 的资源模型直接混写

## 39. COC 对象已创建但流程没有真正跑起来

症状：
- script、document、group 或 incident 已存在
- 但自动化流程、工单或诊断任务没有按预期执行

处理：
- 先确认 Terraform 管理的是“稳定对象”还是“一次性动作”
- 再确认对象之间的引用关系和执行入口
- 临时运维动作优先交给现网工具，不要强行都写进 Terraform

## 40. CTS 已配置但审计事件仍查不到或没有投递

症状：
- tracker、notification 或 configuration 已存在
- 但事件查询为空，或日志未投递到目标位置

处理：
- 先确认追踪范围和资源范围
- 再确认 OBS、SMN 或其他落地目标是否可用
- 如果用户诉求是“查询历史事件”，不要误配成“新建追踪器”

## 41. DMS 实例或主题已创建但消息链路异常

症状：
- Kafka / RabbitMQ / RocketMQ / 队列资源已存在
- 但生产、消费、连接或权限行为异常

处理：
- 先确认引擎类型、实例形态和 AZ/网络设置
- 再确认 topic、queue、user、quota 和安全组
- 如果是消息级问题，不要只盯 Terraform，优先分清实例问题还是业务协议问题

## 42. FGS 函数已部署但触发或执行异常

症状：
- function、dependency、trigger 已创建
- 但函数不触发、执行失败或日志不完整

处理：
- 先确认 runtime、handler、依赖和超时配置
- 再确认 trigger 类型和事件源
- 如果接了 VPC、日志或其他外围资源，确认这些依赖已准备好

## 43. CC 资源已创建但跨网互通仍未建立

症状：
- central network、connection 或 bandwidth package 已存在
- 但跨区域或跨 VPC 流量仍不通

处理：
- 先确认网络实例和连接关系是否完整
- 再确认带宽、权限和路由边界
- 不要只看资源存在，还要核对拓扑是否闭环

## 44. CES 已配置但监控或告警没有按预期工作

症状：
- alarm rule、template 或 dashboard 已创建
- 但没有数据、没有告警或图表为空

处理：
- 先确认 metric namespace 和 metric 名称
- 再确认周期、阈值和告警动作
- 如果资源侧本身没有暴露指标，先回头确认数据源是否存在

## 45. DC 资源已创建但专线侧仍不可用

症状：
- connect gateway、virtual gateway 或 virtual interface 已存在
- 但专线链路仍不可达

处理：
- 先确认 VLAN、带宽、对端网络和路由模式
- 再确认运营商侧和本地侧配置是否对齐
- 对专线场景，不要把所有问题都归因于 Terraform 配置

## 46. DEH 已申请但实例承载效果不符合预期

症状：
- 专属主机资源已存在
- 但实例放置、容量或隔离效果不符合预期

处理：
- 先确认 host 类型和放置策略
- 再确认实例规格是否能真正落到目标主机
- 如果只是一般性计算需求，先重新确认是否真的需要 DEH

## 47. DEW 资源已创建但证书或密钥链路仍不通

症状：
- 证书、私有 CA 或相关对象已存在
- 但下游服务仍报证书、签发或密钥问题

处理：
- 先确认管理对象是证书、CA 还是密钥
- 再确认下游服务是否真正引用了目标对象
- 对临时运维动作，不要误以为 Terraform 已覆盖全部流程

## 48. EG 资源已创建但事件没有流到目标

症状：
- event channel、source、subscription 或 stream 已存在
- 但目标服务没有收到事件

处理：
- 先确认 source、channel、subscription、target 的链路是否完整
- 再确认过滤规则和目标连接是否正确
- 如果是跨服务桥接，优先逐段排查，不要一次改所有配置

## 49. ESW 已创建但交换网络仍不符合预期

症状：
- instance、connection 或 vport 绑定已存在
- 但网络交换或连接效果异常

处理：
- 先确认实例规格、连接对象和 vport 绑定关系
- 再确认它与上游网络产品的职责边界
- 如果用户想解决的是路由问题，不要误用 ESW 去替代其他网络服务

## 50. HSS 策略已下发但安全效果或资产状态不一致

症状：
- 策略组、主机防护或网页防篡改资源已存在
- 但资产状态、漏洞或防护效果不符合预期

处理：
- 先确认保护对象范围和当前现网状态
- 再确认策略组、配额和告警配置
- 对 HSS 这类治理服务，优先先把“现网状态”和“Terraform 目标状态”分开看

## 51. Identity Center 资源已创建但账号分配或登录链路异常

症状：
- instance、user、group、permission set 或 account assignment 已存在
- 但统一登录、授权或账号映射效果异常

处理：
- 先确认组织结构、账号 ID 和权限集关系
- 再确认 assignment 是否落到了正确账号和主体
- 对复杂身份治理场景，优先先确认现网组织模型，再写 Terraform

## 52. OMS 任务已创建但迁移或同步没有按预期推进

症状：
- migration task 或 sync task 已存在
- 但任务卡住、增量不同步或目标桶状态异常

处理：
- 先确认源端、目标端和 bucket 配置
- 再确认同步模式、凭据和网络可达性
- 如果是迁移状态问题，不要只看 Terraform，优先结合任务运行状态排查

## 53. Organizations 对象已创建但组织树或策略效果异常

症状：
- 组织、账号、OU 或策略已存在
- 但层级关系、委派服务或有效策略不符合预期

处理：
- 先确认真实组织树
- 再确认 policy attach 的目标和作用域
- 对组织类对象，优先保证层级正确，再谈策略细节

## 54. RAM 共享已创建但资源没有被正确访问

症状：
- resource share、permission 或 accepter 已存在
- 但对端账号看不到资源或无法按预期使用

处理：
- 先确认 principal、resource ARN 和 permission
- 再确认共享邀请是否已接受，或组织级共享是否已生效
- 跨账号场景优先先核对主体身份

## 55. RGC 已配置但治理落地效果不一致

症状：
- landing zone、account、control 或 template 已存在
- 但治理控制、账号归属或模板下发生效不一致

处理：
- 先确认 Organizations、Identity Center 和 home region 关系
- 再确认 control、OU 和 account 的绑定关系
- RGC 场景优先先理顺治理拓扑，再排具体控制项

## 56. RMS 已配置但合规结果或聚合结果不符合预期

症状：
- recorder、aggregator 或 policy assignment 已存在
- 但资源盘点、策略评估或 remediation 结果异常

处理：
- 先确认 recorder 和 aggregator 的范围
- 再确认 policy definition、assignment scope 和 remediation 配置
- 如果是结果为空，先确认资源是否真的被纳入记录

## 57. SDRS 已配置但主备复制或演练不符合预期

症状：
- protection group、replication pair 或 protected instance 已存在
- 但复制状态、演练或故障切换效果异常

处理：
- 先确认主备拓扑和复制关系
- 再确认 server、disk、network 和 RPO 目标
- SDRS 问题优先按业务拓扑排查，不要只看单个资源

## 58. SecMaster 对象已创建但安全运营链路没有真正跑起来

症状：
- alert、rule、incident、playbook 或 workflow 已存在
- 但告警处置、编排或工作流行为与预期不一致

处理：
- 先确认 workspace、数据源和对象之间的引用关系
- 再确认 playbook / workflow 的触发条件
- 对安全运营对象，区分“规则配置问题”和“现网数据流问题”

## 59. SFS Turbo 已创建但挂载或目录能力不符合预期

症状：
- Turbo 文件系统、目录或权限规则已存在
- 但客户端挂载失败、权限异常或容量行为异常

处理：
- 先确认 share type、VPC、subnet 和挂载目标
- 再确认目录、权限规则、配额和 OBS 目标
- 如果是挂载问题，优先回到计算节点和网络路径核查

## 60. SMS 项目或任务已创建但迁移流程异常

症状：
- migration project、source server 或 task 已存在
- 但迁移波次、连通性或进度结果异常

处理：
- 先确认源端主机状态和模板
- 再确认目标 region、网络连通性和任务波次
- 如果是迁移失败，优先结合任务日志和源端状态排查
