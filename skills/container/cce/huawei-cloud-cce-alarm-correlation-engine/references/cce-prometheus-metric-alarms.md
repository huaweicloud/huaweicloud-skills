# CCE Alarm Center Prometheus Metric Alarm Reference

> This document only lists "alarm type = metric" rules, for direct reference when creating Prometheus metric alarm rules.

## Usage Constraints

- Cluster version: `v1.17` and above
- Base dependency: Cloud-native monitoring plugin (metrics reported to AOM Prometheus)
- `problem_gauge` rules additionally require: Node Problem Detector (NPD) plugin

## 1) Workload Rule Set (Metric Type)

| Alarm Item (CN) | Alarm Description | PromQL |
|---|---|---|
| Pod status abnormal (Pod状态异常) | Check whether Pod status is abnormal | `sum(min_over_time(kube_pod_status_phase{phase=~"Pending\|Unknown\|Failed"}[10m]) and count_over_time(kube_pod_status_phase{phase=~"Pending\|Unknown\|Failed"}[10m]) > 18 ) by (namespace,pod,phase,cluster_name,cluster) > 0` |
| Pod frequent restart (Pod频繁重启) | Check whether Pod is restarting frequently | `increase(kube_pod_container_status_restarts_total[5m]) > 3` |
| Deployment replica mismatch (Deployment副本数不匹配) | Check whether Deployment replicas match | `(kube_deployment_spec_replicas != kube_deployment_status_replicas_available) and (changes(kube_deployment_status_replicas_updated[5m]) == 0)` |
| StatefulSet replica mismatch (Statefulset副本数不匹配) | Check whether StatefulSet replicas match | `(kube_statefulset_status_replicas_ready != kube_statefulset_status_replicas) and (changes(kube_statefulset_status_replicas_updated[5m]) == 0)` |
| Container CPU usage > 80% (容器CPU使用率大于80%) | Check whether container CPU usage exceeds 80% | `100 * (sum(rate(container_cpu_usage_seconds_total{image!="",container!="POD"}[1m])) by (cluster_name,pod,node,namespace,container,cluster) / sum(kube_pod_container_resource_limits{resource="cpu"}) by (cluster_name,pod,node,namespace,container,cluster)) > 80` |
| Container memory usage > 80% (容器内存使用率大于80%) | Check whether container memory usage exceeds 80% | `(sum(container_memory_working_set_bytes{image!="",container!="POD"}) by (cluster_name,node,container,pod,namespace,cluster) / sum(container_spec_memory_limit_bytes > 0) by (cluster_name,node,container,pod,namespace,cluster) * 100) > 80` |
| Container status abnormal (容器状态异常) | Check whether container status is abnormal | `sum by (namespace,pod,container,cluster_name,cluster) (kube_pod_container_status_waiting_reason) > 0` |

## 2) Node Resource Rule Set (Metric Type)

| Alarm Item (CN) | Alarm Description | PromQL |
|---|---|---|
| Kube persistent volume usage high (Kube持久卷使用率高) | Check whether node PV usage is too high | `(kubelet_volume_stats_available_bytes{job="kubelet"} / kubelet_volume_stats_capacity_bytes{job="kubelet"}) < 0.03 and kubelet_volume_stats_used_bytes{job="kubelet"} > 0` |
| Kube PVC status abnormal (Kube持久卷声明状态异常) | Check whether PVC status is abnormal | `kube_persistentvolumeclaim_status_phase{phase=~"Failed\|Pending\|Lost"} > 0` |
| Kube PV status abnormal (Kube持久卷状态异常) | Check whether PV status is abnormal | `kube_persistentvolume_status_phase{phase=~"Failed\|Pending"} > 0` |
| Node CPU usage > 80% (节点CPU使用率超过80%) | Check whether node CPU usage exceeds 80% | `100 - (avg by(node,cluster_name,cluster) (rate(node_cpu_seconds_total{mode="idle"}[2m])) * 100) > 80` |
| Node memory available < 10% (节点内存可用率不足10%) | Check whether node available memory is below 10% | `node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100 < 10` |
| Node disk available < 10% (节点磁盘可用率不足10%) | Check whether node available disk is below 10% | `avg((node_filesystem_avail_bytes * 100) / node_filesystem_size_bytes) by (device,node,cluster_name,cluster) < 10` |
| Node EmptyDir storage pool abnormal (节点EmptyDir存储池异常) | Check whether temporary volume storage pool is abnormal | `problem_gauge{type="EmptyDirVolumeGroupStatusError"} >= 1` |
| Node memory insufficient (节点内存资源不足) | Check whether node overall memory is sufficient | `problem_gauge{type="MemoryProblem"} >= 1` |
| Node PV storage pool abnormal (节点持久卷存储池异常) | Check whether PV storage pool is abnormal | `problem_gauge{type="LocalPvVolumeGroupStatusError"} >= 1` |
| Node mount point abnormal (节点挂载点异常) | Check whether mount point is abnormal | `problem_gauge{type="MountPointProblem"} >= 1` |
| Node FD insufficient (节点文件句柄数不足) | Check whether FD resources are sufficient | `problem_gauge{type="FDProblem"} >= 1` |
| Node disk IO hung (节点磁盘卡IO) | Check whether disk IO is hung | `problem_gauge{type="DiskHung"} >= 1` |
| Node disk read-only (节点磁盘只读) | Check whether disk is read-only | `problem_gauge{type="DiskReadonly"} >= 1` |
| Node disk abnormal (节点磁盘异常) | Check system/data disk abnormality | `problem_gauge{type="DiskProblem"} >= 1` |
| Node disk slow IO (节点磁盘慢IO) | Check whether disk has slow IO | `problem_gauge{type="DiskSlow"} >= 1` |
| Node PID insufficient (节点进程资源不足) | Check whether PID resources are sufficient | `problem_gauge{type="PIDProblem"} >= 1` |
| Node conntrack table insufficient (节点连接跟踪表不足) | Check whether conntrack table is sufficient | `problem_gauge{type="ConntrackFullProblem"} >= 1` |

## 3) Node Status Rule Set (Metric Type)

| Alarm Item (CN) | Alarm Description | PromQL |
|---|---|---|
| ResolvConf configuration file abnormal (ResolvConf配置文件异常) | Check ResolvConf configuration anomaly | `problem_gauge{type="ResolvConfFileProblem"} >= 1` |
| Node CNI component abnormal (节点CNI组件异常) | Check CNI component status | `problem_gauge{type="CNIProblem"} >= 1` |
| Node CRI component abnormal (节点CRI组件异常) | Check Docker/Containerd runtime status | `problem_gauge{type="CRIProblem"} >= 1` |
| Node Kube-proxy down (节点Kube-proxy故障) | Check kube-proxy runtime status | `problem_gauge{type="KUBEPROXYProblem"} >= 1` |
| Node Kubelet abnormal (节点Kubelet异常) | Check kubelet status | `problem_gauge{type="KUBELETProblem"} >= 1` |
| Node has scheduled event (节点存在计划事件) | Check host scheduled event | `problem_gauge{type="ScheduledEvent"} >= 1` |
| Node status flapping (Node状态抖动) | Check Ready status frequent fluctuation | `sum(changes(kube_node_status_condition{status="true",condition="Ready"}[15m])) by (cluster_name,node,cluster) > 2` |
| Node Containerd frequent restart (节点Containerd频繁重启) | Check Containerd frequent restart | `problem_gauge{type="FrequentContainerdRestart"} >= 1` |
| Node D-state process abnormal (节点进程D异常) | Check D-state process anomaly | `problem_gauge{type="ProcessD"} >= 1` |
| Node Z-state process abnormal (节点进程Z异常) | Check Z-state (zombie) process anomaly | `problem_gauge{type="ProcessZ"} >= 1` |
| Node CRI frequent restart (节点CRI频繁重启) | Check CRI frequent restart | `problem_gauge{type="FrequentCRIRestart"} >= 1` |
| Node Docker frequent restart (节点Docker频繁重启) | Check Docker frequent restart | `problem_gauge{type="FrequentDockerRestart"} >= 1` |
| Node Kubelet frequent restart (节点Kubelet频繁重启) | Check Kubelet frequent restart | `problem_gauge{type="FrequentKubeletRestart"} >= 1` |
| Node NTP service down (节点NTP服务故障) | Check ntpd/chronyd service status | `problem_gauge{type="NTPProblem"} >= 1` |

## Configuration Recommendations (for Tool Implementation)

- Recommended default threshold period: `period=60`, `evaluation_periods=3`
- Rule naming recommendation: `{cluster_name}-{rule_short_name}`
- Default enterprise project: `all_granted_eps` (use specified enterprise project only when explicitly passed as parameter)
- If the expression uses `problem_gauge`, check NPD plugin status before creating the rule