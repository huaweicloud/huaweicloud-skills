# CCE Event List

Source: <https://support.huaweicloud.com/usermanual-cce/cce_10_0902.html>

Usage rules:
- When creating event alarm rules, prefer the `Chinese event description##Event name` format for `event_name`.
- If only the event name (e.g., `NodeHasDiskPressure`) or Chinese event description (e.g., "节点磁盘空间不足") is provided, the tool will attempt to auto-map to the full format.

## Workload-Related Events

| Category | Event Description (CN) | Event Name | Event Level |
|---|---|---|---|
| Pod | Pod OOM killed (Pod内存不足OOM) | PodOOMKilling | Important |
| Pod | Start failed (启动失败) | FailedStart | Important |
| Pod | Image pull failed (拉取镜像失败) | FailedPullImage | Important |
| Pod | Start retry failed (启动重试失败) | BackOffStart | Important |
| Pod | Scheduling failed (调度失败) | FailedScheduling | Important |
| Pod | Image pull retry failed (拉取镜像重试失败) | BackOffPullImage | Important |
| Pod | Creation failed (创建失败) | FailedCreate | Important |
| Pod | Status abnormal (状态异常) | Unhealthy | Minor |
| Pod | Delete failed (删除失败) | FailedDelete | Minor |
| Pod | Image never pulled error (未拉取镜像异常) | ErrImageNeverPull | Minor |
| Pod | Scale-out failed (扩容失败) | FailedScaleOut | Minor |
| Pod | Standby failed (待机失败) | FailedStandBy | Minor |
| Pod | Reconfig failed (更新配置失败) | FailedReconfig | Minor |
| Pod | Activation failed (激活失败) | FailedActive | Minor |
| Pod | Rollback failed (回滚失败) | FailedRollback | Minor |
| Pod | Update failed (更新失败) | FailedUpdate | Minor |
| Pod | Scale-in failed (缩容失败) | FailedScaleIn | Minor |
| Pod | Restart failed (重启失败) | FailedRestart | Minor |
| Deployment | Label selector conflict (标签选择器冲突) | SelectorOverlap | Minor |
| Deployment | ReplicaSet creation error (副本集创建异常) | ReplicaSetCreateError | Minor |
| Deployment | Rollback revision not found (部署回滚版本未发现) | DeploymentRollbackRevisionNotFound | Minor |
| DaemonSet | Label selector anomaly (标签选择器异常) | SelectingAll | Minor |
| Job | Too many active Pods (太多活跃Pod) | TooManyActivePods | Minor |
| Job | Too many succeeded Pods (太多成功Pod) | TooManySucceededPods | Minor |
| CronJob | Query failed (查询失败) | FailedGet | Minor |
| CronJob | Pod list query failed (查询Pod列表失败) | FailedList | Minor |
| CronJob | Unexpected Job (未知Job) | UnexpectedJob | Minor |

## Network-Related Events

| Category | Event Description (CN) | Event Name | Event Level |
|---|---|---|---|
| Service | Load balancer creation failed (创建负载均衡失败) | CreatingLoadBalancerFailed | Minor |
| Service | Load balancer deletion failed (删除负载均衡失败) | DeletingLoadBalancerFailed | Minor |
| Service | Load balancer update failed (更新负载均衡失败) | UpdateLoadBalancerFailed | Minor |

## Node-Related Events

| Category | Event Description (CN) | Event Name | Event Level |
|---|---|---|---|
| Node | Node rebooted (节点重启) | Rebooted | Important |
| Node | Node unschedulable (节点不可调度) | NodeNotSchedulable | Important |
| Node | Node status abnormal (节点状态异常) | NodeNotReady | Important |
| Node | Node creation failed (节点创建失败) | NodeCreateFailed | Important |
| Node | Node EVS disk attach/detach failed (节点挂载或卸载EVS盘失败) | FailedToAttachDetach | Important |
| Node | Node kubelet down (节点kubelet故障) | KUBELETIsDown | Minor |
| Node | Unregistered network device found (节点上发现未注册的网络设备) | UnregisterNetDevice | Minor |
| Node | Network card not found (网卡未发现) | NetworkCardNotFound | Minor |
| Node | Node kube-proxy down (节点kube-proxy故障) | KUBEPROXYIsDown | Minor |
| Node | Node disk full (节点磁盘空间已满) | NodeOutOfDisk | Minor |
| Node | Node task hung (节点任务夯住) | TaskHung | Minor |
| Node | CIDR not available (CIDR不可用) | CIDRNotAvailable | Minor |
| Node | Node conntrack table full (节点的连接跟踪表已满) | ConntrackFull | Minor |
| Node | Node disk pressure (节点磁盘空间不足) | NodeHasDiskPressure | Minor |
| Node | Node enrollment failed (节点纳管失败) | NodeInstallFailed | Minor |
| Node | Node kernel oops (节点操作系统内核故障) | KernelOops | Minor |
| Node | Node OOM killed process (节点内存不足强杀进程) | OOMKilling | Minor |
| Node | Node docker down (节点docker故障) | DOCKERIsDown | Minor |
| Node | CIDR assignment failed (CIDR分配失败) | CIDRAssignmentFailed | Minor |
| Node | Node docker hung (节点docker夯住) | DockerHung | Minor |
| Node | Node filesystem read-only (节点文件系统只读) | FilesystemIsReadOnly | Minor |
| Node | Node NTP down (节点ntp服务故障) | NTPIsDown | Minor |
| Node | Node uninstall failed (节点卸载失败) | NodeUninstallFailed | Minor |
| Node | Node AUFS unmount hung (节点磁盘卸载夯住) | AUFSUmountHung | Minor |
| Node | Node CNI plugin down (节点cni插件故障) | CNIIsDown | Minor |
| Namespace | Stale node cleanup (废弃节点清理) | DeleteNodeWithNoServer | Minor |

## Storage-Related Events

| Category | Event Description (CN) | Event Name | Event Level |
|---|---|---|---|
| PV | Host detach volume failed (主机卸载块存储失败) | DetachVolumeFailed | Minor |
| PV | Volume reclaim policy unknown (卷回收策略未知) | VolumeUnknownReclaimPolicy | Minor |
| PV | Volume setup failed (挂载数据卷失败) | SetUpAtVolumeFailed | Minor |
| PV | Volume recycle failed (数据卷回收失败) | VolumeFailedRecycle | Minor |
| PV | Wait for host attach volume failed (等待主机挂载块存储失败) | WaitForAttachVolumeFailed | Minor |
| PV | Volume delete failed (数据卷删除失败) | VolumeFailedDelete | Minor |
| PV | Mount device failed (挂载盘符失败) | MountDeviceFailed | Minor |
| PV | Volume teardown failed (卸载数据卷失败) | TearDownAtVolumeFailed | Minor |
| PV | Unmount device failed (卸载盘符失败) | UnmountDeviceFailed | Minor |
| PV | Host attach volume failed (主机挂载块存储失败) | AttachVolumeFailed | Minor |
| PVC | Volume resize failed (数据卷扩容失败) | VolumeResizeFailed | Minor |
| PVC | PVC claim lost (卷PVC丢失) | ClaimLost | Minor |
| PVC | Volume provisioning failed (创建卷失败) | ProvisioningFailed | Minor |
| PVC | Volume provisioning cleanup failed (创建卷清理失败) | ProvisioningCleanupFailed | Minor |
| PVC | Volume claim misbound (卷误绑定) | ClaimMisbound | Minor |

## Autoscaling-Related Events

| Category | Event Description (CN) | Event Name | Event Level |
|---|---|---|---|
| Autoscaler | Scale-up node timed out (扩容节点超时) | ScaleUpTimedOut | Important |
| Autoscaler | Node pool resources available (节点池资源充足) | NodePoolAvailable | Important |
| Autoscaler | Scale-down node (缩容节点) | ScaleDown | Important |
| Autoscaler | Scale-up not triggered (未触发节点扩容) | NotTriggerScaleUp | Important |
| Autoscaler | Delete unregistered node succeeded (删除未注册节点成功) | DeleteUnregistered | Important |
| Autoscaler | Scale-down empty node succeeded (缩容空闲节点成功) | ScaleDownEmpty | Important |
| Autoscaler | Scale-down node failed (缩容节点失败) | ScaleDownFailed | Important |
| Autoscaler | Node pool scale-up failed (节点池扩容节点失败) | FailedToScaleUpGroup | Important |
| Autoscaler | Node pool scale-up succeeded (节点池扩容节点成功) | ScaledUpGroup | Important |
| Autoscaler | Scale-up node failed (扩容节点失败) | ScaleUpFailed | Important |
| Autoscaler | Fix node pool size succeeded (修复节点池节点个数成功) | FixNodeGroupSizeDone | Important |
| Autoscaler | Node pool in back-off retry (节点池退避重试中) | NodeGroupInBackOff | Important |
| Autoscaler | Fix node pool size failed (修复节点池节点个数失败) | FixNodeGroupSizeError | Important |
| Autoscaler | Node pool sold out (节点池资源售罄) | NodePoolSoldOut | Important |
| Autoscaler | Scale-up triggered (触发节点扩容) | TriggeredScaleUp | Important |
| Autoscaler | Node pool scale-up starting (节点池扩容节点启动) | StartScaledUpGroup | Important |
| Autoscaler | Delete unregistered node failed (删除未注册节点失败) | DeleteUnregisteredFailed | Important |
| HPA | HPA invalid target range (HPA非法指标范围) | InvalidTargetRange | Important |
| HPA | HPA get scale object failed (HPA获取伸缩对象失败) | FailedGetScale | Important |
| HPA | HPA compute metric replicas failed (HPA计算资源扩缩副本数失败) | FailedComputeMetricsReplicas | Important |
| HPA | HPA get object metric failed (HPA获取对象指标失败) | FailedGetObjectMetric | Important |
| HPA | HPA get pod resource metric failed (HPA获取Pod资源指标失败) | FailedGetPodsMetric | Important |
| HPA | HPA get cluster resource metric failed (HPA获取集群资源指标失败) | FailedGetResourceMetric | Important |
| HPA | HPA get container resource metric failed (HPA获取容器资源指标失败) | FailedGetContainerResourceMetric | Important |
| HPA | HPA get external metric failed (HPA获取外部指标失败) | FailedGetExternalMetric | Important |
| HPA | HPA rescale failed (HPA伸缩Pod失败) | FailedRescale | Important |
| HPA | Pod rescale succeeded (Pod扩缩容成功) | SuccessfulRescale | Minor |
| CronHPA | CronHPA scale failed (CronHPA伸缩失败) | ScaleFailed | Important |
| CronHPA | CronHPA get associated HPA failed (CronHPA查询关联HPA失败) | FailedGetHorizontalPodAutoscaler | Important |
| CronHPA | CronHPA get scale target failed (CronHPA查询伸缩对象失败) | FailedGetHpaScale | Important |
| CronHPA | CronHPA update associated HPA failed (CronHPA更新关联HPA失败) | UpdateHPAFailed | Important |
| CronHPA | HPA update strategy succeeded (更新HPA策略成功) | UpdateHPASuccess | Minor |
| CronHPA | Skip HPA update (跳过更新HPA策略) | SkipUpdateHPA | Minor |
| CronHPA | Skip target update (跳过更新工作负载实例数) | SkipUpdateTarget | Minor |
| CronHPA | Target update succeeded (更新工作负载实例数成功) | UpdateTargetSuccess | Minor |
| CustomedHPA | CustomedHPA parse cooldown failed (CustomedHPA解析冷却时间失败) | FailedSetPolicySettings | Important |
| CustomedHPA | CustomedHPA process rule failed (CustomedHPA处理定时/指标规则失败) | FailedSubmitRule | Important |
| CustomedHPA | CustomedHPA compute replicas failed (CustomedHPA计算资源扩缩副本数失败) | FailedComputeReplicas | Important |
| CustomedHPA | CustomedHPA scale failed (CustomedHPA伸缩Pod失败) | FailedScale | Important |
| CustomedHPA | CustomedHPA metric scale succeeded (CustomedHPA指标扩缩容成功) | MetricScaleSuccess | Minor |
| CustomedHPA | CustomedHPA cron scale succeeded (CustomedHPA周期扩缩容成功) | CronScaleSuccess | Minor |

## Cluster Control Plane Events

| Event Description (CN) | Event Name | Event Level |
|---|---|---|
| Internal error (内部故障) | Internal error | Important |
| External dependency error (外部依赖异常) | External dependency error | Important |
| Failed to initialize process thread (初始化执行线程失败) | Failed to initialize process thread | Important |
| Failed to update database (更新数据库失败) | Failed to update database | Important |
| Failed to create node by nodepool (节点池触发创建节点失败) | Failed to create node by nodepool | Important |
| Failed to delete node by nodepool (节点池触发删除节点失败) | Failed to delete node by nodepool | Important |
| Failed to create yearly/monthly subscription node (创建包周期节点失败) | Failed to create yearly/monthly subscription node | Important |
| Failed to cancel the authorization of accessing the image of the master (解除资源租户访问控制节点镜像的授权失败) | Failed to cancel the authorization of accessing the image of the master. | Important |
| Failed to create the virtual IP for the master (创建虚拟IP失败) | Failed to create the virtual IP for the master | Important |
| Failed to delete the node VM (删除节点虚拟机失败) | Failed to delete the node VM | Important |
| Failed to delete the security group of node (删除节点安全组失败) | Failed to delete the security group of node | Important |
| Failed to delete the security group of master (删除控制节点安全组失败) | Failed to delete the security group of master | Important |
| Failed to delete the security group of port (删除控制节点网卡安全组失败) | Failed to delete the security group of port | Important |
| Failed to delete the security group of eni or subeni (删除集群ENI/SubENI安全组失败) | Failed to delete the security group of eni or subeni | Important |
| Failed to detach the port of master (解绑控制节点网卡失败) | Failed to detach the port of master | Important |
| Failed to delete the port of master (删除控制节点网卡失败) | Failed to delete the port of master | Important |
| Failed to delete the master VM (删除控制节点虚拟机失败) | Failed to delete the master VM | Important |
| Failed to delete the key pair of master (删除控制节点密钥对失败) | Failed to delete the key pair of master | Important |
| Failed to delete the subnet of master (删除控制节点subnet失败) | Failed to delete the subnet of master | Important |
| Failed to delete the VPC of master (删除控制节点VPC失败) | Failed to delete the VPC of master | Important |
| Failed to delete certificate of cluster (删除集群证书失败) | Failed to delete certificate of cluster | Important |
| Failed to delete the server group of master (删除控制节点云服务器组失败) | Failed to delete the server group of master | Important |
| Failed to delete the virtual IP for the master (删除虚拟IP失败) | Failed to delete the virtual IP for the master | Important |
| Failed to get floating IP of the master (获取控制节点浮动IP失败) | Failed to get floating IP of the master | Important |
| Failed to get cluster flavor (获取集群规格信息失败) | Failed to get cluster flavor | Important |
| Failed to get cluster endpoint (获取集群endpoint失败) | Failed to get cluster endpoint | Important |
| Failed to get kubernetes connection (获取Kubernetes集群连接失败) | Failed to get kubernetes connection | Important |
| Failed to update secret (更新集群Secret失败) | Failed to update secret | Important |
| Operation timed out (处理用户操作超时) | Operation timed out | Important |
| Connecting to Kubernetes cluster timed out (连接Kubernetes集群超时) | Connecting to Kubernetes cluster timed out | Important |
| Failed to check component status or components are abnormal (检查组件状态失败或组件状态异常) | Failed to check component status or components are abnormal | Important |
| The node is not found in kubernetes cluster (无法在Kubernetes集群中找到该节点) | The node is not found in kubernetes cluster | Important |
| The status of node is not ready in kubernetes cluster (节点在Kubernetes集群中状态异常) | The status of node is not ready in kubernetes cluster | Important |
| Can't find corresponding vm of this node in ECS (无法在ECS服务中找到该节点对应的虚拟机) | Can't find corresponding vm of this node in ECS | Important |
| Failed to upgrade the master (升级控制节点失败) | Failed to upgrade the master | Important |
| Failed to upgrade the node (升级节点失败) | Failed to upgrade the node | Important |
| Failed to change flavor of the master (变更控制节点规格失败) | Failed to change flavor of the master | Important |
| Change flavor of the master timeout (变更控制节点规格超时) | Change flavor of the master timeout | Important |
| Failed to pass verification while creating yearly/monthly subscription node (创建包周期节点校验不通过) | Failed to pass verification while creating yearly/monthly subscription node | Important |
| Failed to install the node (安装节点失败) | Failed to install the node | Important |
| Failed to clean routes of cluster container network in VPC (清理VPC中集群容器网络路由表条目失败) | Failed to clean routes of cluster container network in VPC | Important |
| Cluster status is Unavailable (集群状态不可用) | Cluster status is Unavailable | Important |
| Cluster status is Error (集群状态故障) | Cluster status is Error | Important |
| Cluster status is not updated for a long time (集群状态长时间不更新) | Cluster status is not updated for a long time | Important |
| Failed to update master status after upgrading cluster timeout (集群升级超时后更新控制节点状态失败) | Failed to update master status after upgrading cluster timeout | Important |
| Failed to update running jobs after upgrading cluster timeout (集群升级超时后更新运行中的任务失败) | Failed to update running jobs after upgrading cluster timeout | Important |
| Failed to update cluster status (更新集群状态失败) | Failed to update cluster status | Important |
| Failed to update node status (更新节点状态失败) | Failed to update node status | Important |
| Failed to remove the static node from database (纳管节点超时后移除数据库中的节点记录失败) | Failed to remove the static node from database | Important |
| Failed to update node status to abnormal after node processing timeout (节点处理超时后更新节点状态为异常失败) | Failed to update node status to abnormal after node processing timeout | Important |
| Failed to update the cluster endpoint (更新集群访问地址失败) | Failed to update the cluster endpoint | Important |
| Failed to delete the unavailable connection of the Kubernetes cluster (删除不可用的Kubernetes连接失败) | Failed to delete the unavailable connection of the Kubernetes cluster | Important |
| Failed to sync the cluster cert (同步集群证书失败) | Failed to sync the cluster cert | Important |