# CCE Migration Implementation Plan

**Target**: `<source_cluster>` $\to$ `[NEW: <cluster_name> | EXISTING: <target_cce_cluster_id>]`  
**Migration Strategy**: `[OFFLINE_DOWNTIME | ONLINE_ZERO_DOWNTIME]` | **Status**: `[DRAFT | APPROVED]`

- _If OFFLINE_: Maintenance Window: `<YYYY-MM-DD HH:MM - HH:MM>` (Cut off source ingress traffic to block writes)
- _If ONLINE_: Live replication / delta sync catch-up (Zero-downtime canary switch)

---

## 1. Target Cluster & Network (Phase 3)

- **Target Mode**: `[NEW_PROVISION | EXISTING]`
- **Target Region**: `<region_id>`
- **Cluster Definition**:
  - _If NEW_: Name: `<cluster_name>`, Architecture: `CCE Turbo`, Master Flavor: `<cce.s1.* | cce.s2.*>`, K8s Version: `v<1.xx>`
  - _If EXISTING_: Cluster ID: `<target_cce_cluster_id>`
- **Network & VPC**:
  - _If NEW_: VPC CIDR: `<vpc_cidr>`, Node Subnet: `<node_cidr>`, Container/Pod Subnet: `<pod_cidr>`
  - _If EXISTING_: VPC ID: `<target_vpc_id>`, Subnet ID: `<target_subnet_id>`
- **Worker Node Pool (If NEW)**: Flavor: `<node_flavor>`, Node Count: `<count>`, OS: `<os_image>`, Disk: `<disk_spec>`
- **NAT Gateway Egress**: `[NEW: <spec> | EXISTING: <nat_gateway_id> (EIP: <nat_eip>) | NONE]`
- **Kubeconfig Output**: `~/.kube/cce-config` _(written/verified during Phase 3)_

---

## 2. Container Images & Registry (Phase 4)

- **Image Pull Mode**: `[SWR | PUBLIC_REGISTRY]`
  - _If SWR_: SWR Org: `<swr_organization>`, Registry: `swr.<region_id>.myhuaweicloud.com`
  - _If PUBLIC_REGISTRY_: Direct external pull (Requires NAT Gateway in Section 1)
- **SA imagePullSecrets**: `[REQUIRED | NONE]`
  - **Secret Name**: `[default-secret | <custom_secret_name>]`
  - **Target ServiceAccount**: `[default | <custom_sa_name>]`
- **Image Inventory**:
  |Source Image|Target Registry Image|
  |-|-|
  |`<source_registry>/<image>:<tag>`|`swr.<region_id>.myhuaweicloud.com/<swr_organization>/<image>:<tag>`|
  |`velero/restore-helper:<tag>`|`swr.<region_id>.myhuaweicloud.com/<swr_organization>/restore-helper:<tag>`|

---

## 3. Storage & PVC Remapping (Phase 5)

|Namespace|Source PVC|Target StorageClass|Requested Size|Share / Subpath / Bucket Reference|
|-|-|-|-|-|
|`<namespace>`|`<pvc_name>`|`csi-disk-topology`|`<size_min_10Gi>`|Dynamic EVS provision|
|`<namespace>`|`<pvc_name>`|`csi-sfsturbo`|`<size>`|Pre-created Share: `<share_id>` (Mode: `[Subpath: <subpath>|Static PV]`)|
|`<namespace>`|`<pvc_name>`|`csi-obs`|`<size>`|Bucket: `<target_bucket_name>`|

---

## 4. Workload Restore & Configuration Rewrites (Phase 6)

- **Restore Tool**: `[k8clone | velero]`
- **Target Namespaces**: `[<ns_1>, <ns_2>]`
- **Sanitization & Headless Protection**: Strip `paas.elb`, `service-account-token`; preserve `clusterIP: "None"` on Headless Services
- **State Consistency & Quiescence**:
  - _If OFFLINE_: Cut off source ingress traffic (LB/Ingress disabled) before final data stream
  - _If ONLINE_: Keep source workloads active; execute final delta sync / CDC catch-up
- **Database Logical Migration**:
  - **Source Pod**: `<source_namespace>/<source_db_pod>`
  - **Target Pod**: `<target_namespace>/<target_db_pod>`
  - **Database / User**: `<db_name>` / `<db_user>`
  - **Command**: `kubectl exec -i <source_db_pod> -n <source_ns> -- pg_dump -U <user> <dbname> | kubectl exec -i <target_db_pod> -n <target_ns> -- psql -U <user> <dbname>`
- **Endpoint & Service Rewrites**:
  |Source Endpoint / Host|Target Endpoint / Host|Scope / Namespace|
  |-|-|-|
  |`<source_db_endpoint>`|`<target_rds_or_internal_ip>`|`<namespace>`|
  |`<source_middleware_endpoint>`|`<target_service_endpoint>`|`<all|namespace>`|

---

## 5. Ingress & Traffic Cutover (Phase 7)

- **Dedicated ELB**: `[AUTOCREATE | EXISTING]`
  - _If EXISTING_: ELB ID: `<elb_instance_id>`, Public EIP: `<elb_eip>`
  - _If AUTOCREATE_: Class: `dedicated`, Network: `ClusterIP`, EIP Bandwidth: `<bandwidth_mbps>`
- **Ingress Endpoints**:
  |Domain|Namespace|Service Name|Service Port|Path|
  |-|-|-|-|-|
  |`<domain>`|`<namespace>`|`<service_name>`|`<port>`|`/*`|
- **DNS Cutover**: `<domain>` $\to$ Target ELB EIP (Strategy: `[OFFLINE: Immediate 100% | ONLINE: Canary (10%->50%->100%)]`)
- **Rollback Target**: Revert `<domain>` to `<source_ingress_eip_or_cname>`

---

## 6. Execution Confirmation Gate

- **Customer Approval**: `[YES | NO]`
- **Approved By**: `<user_or_representative>`
- **Approval Timestamp**: `<YYYY-MM-DD HH:MM:SS>`
