# Troubleshooting Guide

This guide provides diagnostic procedures and resolution playbooks for common failure modes encountered during Kubernetes migration to Huawei Cloud CCE.

---

## 1. Storage and Persistent Volume Errors

### T-01: EVS Volume Mount Failure (`csi-disk` Pending / FailedAttach)

- **Symptoms**: Pod status remains `ContainerCreating`. `kubectl describe pod` shows: `AttachVolume.Attach failed: volume is in different AZ`.
- **Root Cause**: EVS disks are single-AZ resources. If `csi-disk` (immediate binding) is used in a multi-AZ cluster, the volume is created before the pod is scheduled and may land in a different AZ than the node.
- **Resolution**: Use CCE's built-in delay-bound StorageClass **`csi-disk-topology`** (`volumeBindingMode: WaitForFirstConsumer`). See `references/storage-pv-migration-guide.md` Section 1 & Section 3.

### T-02: SFS Turbo Mount Timeout (`csi-sfsturbo`)

- **Symptoms**: Pod hangs during volume mount with `mount.nfs: Connection timed out`.
- **Root Cause**: Inbound port `2049` (NFS) or `111` (portmapper) is blocked by the CCE node security group or subnet ACL.
- **Resolution**: Allow inbound TCP/UDP port `2049` from VPC CIDR on the node security group (`hcloud VPC ListSecurityGroupRules/v3`). Verify reachability via `nc -zv <sfs-turbo-ip> 2049`.

### T-03: OBS Mount Error (`csi-obs`)

- **Symptoms**: Pod reports `Mount failed: invalid credentials or bucket not found`.
- **Root Cause**: Invalid AK/SK secret associated with Everest OBS CSI driver, or bucket does not exist in target region.
- **Resolution**: Verify bucket with `obsutil ls obs://<bucket-name>`. Ensure Everest add-on has valid agency permissions (`cce_admin_trust`).

### T-03A: EVS Volume Provisioning Failure Due to Minimum 10 GiB Constraint (`csi-disk`)

- **Symptoms**: PVC remains `Pending`. `kubectl describe pvc` shows `size must be greater than or equal to 10Gi`.
- **Root Cause**: Huawei Cloud EVS enforces a minimum volume size of **10 GiB**. Source manifests requested smaller volumes (e.g. 1Gi, 5Gi).
- **Resolution**: Adjust PVC request to `10Gi` minimum before applying or restoring via Velero. See `references/storage-pv-migration-guide.md`.

### T-03B: Pod Stuck in `ContainerCreating` with `Multi-Attach error for volume` on EVS

- **Symptoms**: Pod fails to start. `kubectl describe pod` shows: `Warning FailedAttachVolume attachdetach-controller Multi-Attach error for volume ... Volume is already exclusively attached to one node and can't be attached to another` or `Volume is already used by pod(s)`.
- **Root Cause**: Deployment with replicas > 1 or default `RollingUpdate` strategy attempted to attach the same EVS volume to multiple Pods concurrently.
- **Resolution**:
  1. For multi-replica workloads requiring independent persistent storage: Migrate from Deployment to `StatefulSet` with `volumeClaimTemplates` (creates 1:1 dedicated EVS disks per Pod).
  2. For multi-pod shared file access: Migrate to SFS Turbo (`csi-sfsturbo`) with `ReadWriteMany`.
  3. If single-replica Deployment: Set `spec.replicas: 1` and `spec.strategy.type: Recreate` to avoid rolling update deadlocks. See `references/storage-pv-migration-guide.md` Rule 7.

---

## 2. Velero Restore Failures

### T-04: StorageClass Mismatch During Restore

- **Symptoms**: Restored PVCs remain `Pending` with message `storageclass.storage.k8s.io "<source-sc>" not found`.
- **Root Cause**: Source StorageClass was not re-mapped to a CCE Everest class (`csi-disk`, `csi-sfsturbo`, `csi-obs`).
- **Resolution**: Deploy `templates/velero-sc-mapping.yaml` before running restore. See `references/storage-pv-migration-guide.md`.

### T-05: Velero Node-Agent DaemonSet Not Ready

- **Symptoms**: Velero file-level restore fails with `pod volume restore timed out`.
- **Root Cause**: `node-agent` daemonset is unschedulable due to resource shortages or missing node taints tolerance.
- **Resolution**: Run `kubectl -n velero describe daemonset node-agent` and add required tolerations in Velero installation.

---

## 3. Workload, Storage and Data Migration Playbooks

### T-06: `ImagePullBackOff` / `401 Unauthorized` on Migrated Pods (Private Nodes)

- **Symptoms**: Pods fail to pull images with `ErrImagePull`, `ImagePullBackOff`, or `401 Unauthorized` (e.g. `docker.io/library/postgres`, `velero/restore-helper`).
- **Root Cause**: CCE nodes in private subnets cannot reach `docker.io` without a NAT Gateway, or default containerd mirrors reject unauthenticated pulls.
- **Resolution**:
  1. **Mirror to SWR and Configure `imagePullSecrets` (Recommended)**: Mirror workloads and Velero suite to SWR. Ensure workload manifests declare `imagePullSecrets: [{"name": "default-secret"}]` (or patch the target ServiceAccount). See `references/swr-image-sync-guide.md` Section 4.
  2. **NAT Gateway Option**: If direct pulling from `docker.io` is required, provision a NAT Gateway with SNAT:
     ```bash
     hcloud NAT CreateNatGateway --cli-region=<region_id> --nat_gateway.name=cce-nat-gw --nat_gateway.spec=1 --nat_gateway.router_id=<vpc-id> --nat_gateway.internal_network_id=<subnet-id>
     hcloud NAT CreateNatGatewaySnatRule --cli-region=<region_id> --snat_rule.nat_gateway_id=<nat-id> --snat_rule.network_id=<subnet-id> --snat_rule.floating_ip_id=<eip-id>
     ```

### T-07: PVC Remains in `Lost` State (Clean `pv.kubernetes.io/bind-completed`)

- **Symptoms**: Restored PVCs show `STATUS: Lost` with capacity `0`.
- **Root Cause**: Source PVC was restored with `spec.volumeName` and runtime binding annotations (`pv.kubernetes.io/*`, `volume.beta.kubernetes.io/*`).
- **Resolution**: Delete stuck PVC and remove `spec.volumeName` and all `pv.kubernetes.io/*` / `volume.beta.kubernetes.io/*` annotations before re-applying. See `references/k8clone-migration-guide.md` Section 5.1.

### T-08: `csi-disk` Provisioning Fails with `disk access mode must be ReadWriteOnce`

- **Symptoms**: `failed to provision volume with StorageClass "csi-disk": ... disk access mode must be ReadWriteOnce`.
- **Root Cause**: PVC mapped to `csi-disk` (EVS) requested `ReadWriteMany`. EVS only supports `ReadWriteOnce`.
- **Resolution**: Remap to `csi-sfsturbo` (`csi-nas` is sunset). For < 500 GiB, pre-create the SFS Turbo instance and use Dynamic Subpath Provisioning (`templates/pvc-sfsturbo-subpath-template.yaml`); for dedicated instances, enforce $\ge 500$ GiB (or 1.2 TB for HPC) and bind via static PV (`templates/pvc-sfsturbo-template.yaml`). If single-node binding suffices, change to `ReadWriteOnce` for `csi-disk`. See `references/storage-pv-migration-guide.md`.

### T-08A: SFS Turbo Volume Provisioning Fails (Unprecreated Share or Invalid `share-expand-type`)

- **Symptoms**: PVC mapped to `csi-sfsturbo` remains `Pending` or fails with `failed to provision volume with StorageClass "csi-sfsturbo"`.
- **Root Cause**: Attempting to dynamically provision an SFS Turbo instance from scratch via a basic PVC or using the deprecated annotation `everest.io/share-expand-type`. CCE Everest CSI cannot create underlying SFS Turbo file system instances dynamically from scratch.
- **Resolution**:
  1. Pre-create the SFS Turbo instance in the target VPC via the Huawei Cloud SFS Turbo console or `hcloud SFSTurbo CreateShare`.
  2. For small volumes (< 500 GiB), use Dynamic Subpath Provisioning (`templates/pvc-sfsturbo-subpath-template.yaml`) referencing `everest.io/sfsturbo-share-id: <sfsturbo_id>`.
  3. For dedicated instances ($\ge$ 500 GiB / 1.2 TB), use Static PV/PVC Binding (`templates/pvc-sfsturbo-template.yaml`) with `volumeHandle: <sfsturbo_id>` and `everest.io/share-export-location: <export_location>`.
  4. Remove any invalid `everest.io/share-expand-type` annotations. See `references/storage-pv-migration-guide.md` Section 2.

### T-09: StatefulSet Update Fails on `volumeClaimTemplates` (`--cascade=orphan`)

- **Symptoms**: `kubectl apply` fails with `updates to statefulset spec for fields other than ... are forbidden`.
- **Root Cause**: `volumeClaimTemplates` in StatefulSets are immutable.
- **Resolution**: Delete the StatefulSet preserving pods via `kubectl delete sts <name> -n <ns> --cascade=orphan`, then re-apply with the updated StorageClass. See `references/k8clone-migration-guide.md` Section 5.2.

### T-10: Stateful Application Data Inconsistency & `/install` Setup Screen

- **Symptoms**: Restored app displays `/install` wizard screen or returns HTTP 502 due to corrupt/empty database.
- **Root Cause**: Unquiesced online backup caused torn pages, or application started before database volume restoration finished.
- **Resolution**: Enforce transactional consistency via Velero Backup Hooks (`pre.hook`/`post.hook`) or scale deployments to 0 (`kubectl scale deploy --all --replicas=0`) before backup. Verify row counts post-restore. See `references/velero-migration-guide.md` Section 4.

### T-11: Frontend SSR Pod Logs `ConnectTimeoutError` or `fetch failed`

- **Symptoms**: SSR frontend container logs `[TypeError: fetch failed]` with `ConnectTimeoutError` to source IP.
- **Root Cause**: Hardcoded source cluster IP/URL in ConfigMap or Deployment environment variables (`CONSOLE_API_URL`, `BACKEND_URL`).
- **Resolution**: Update environment variables to target CCE endpoint, ELB domain, or internal Service (`INTERNAL_API_URL=http://<svc>:<port>`). See `references/configmap-secret-migration-guide.md` Section 3.

---

## 4. Cluster Connectivity Errors

### T-12: `update-kubeconfig` Fails or Shows TLS Handshake Timeout

- **Symptoms**: `kubectl` commands hang when contacting CCE API server.
- **Root Cause**: Contacting internal cluster endpoint over the internet without `--external` flag or without public EIP on CCE master.
- **Resolution**: Add `--external` flag (`hcloud CCE update-kubeconfig --cluster-id=<id> --region=cn-north-4 --external`) and verify master EIP via `hcloud CCE ShowClusterEndpoints --cluster_id=<id> --cli-region=<region_id>`.

### T-13: Inbound Traffic to CCE NodePort Times Out (Node Security Group Isolation)

- **Symptoms**: Workloads exposed via `NodePort` (30000-32767) are unreachable from outside the node.
- **Root Cause**: CCE node security group defaults to strict intra-cluster isolation and blocks NodePort ingress.
- **Resolution**: Allow inbound TCP on ports `30000-32767` from authorized CIDRs:
  ```bash
  hcloud VPC CreateSecurityGroupRule/v3 --cli-region=<region_id> --security_group_rule.security_group_id=<node-sg-id> --security_group_rule.direction=ingress --security_group_rule.protocol=tcp --security_group_rule.multiport=30000-32767 --security_group_rule.remote_ip_prefix=<client_or_vpc_cidr> --security_group_rule.description="Allow CCE NodePort ingress"
  ```

---

## 5. System Secret and Network Errors

### T-14: CCE ELB Ingress or Everest CSI Fails After Restoring Secrets (`paas.elb`)

- **Symptoms**: ELB Ingress or Everest CSI fails with authorization errors after restoring secrets.
- **Root Cause**: Restoring `paas.elb` secret overwrote CCE's freshly rotated internal authentication token.
- **Resolution**: Delete `paas.elb` (`kubectl delete secret paas.elb -n kube-system`); CCE will automatically regenerate it within 1-2 minutes. Always exclude `paas.elb` from migration. See `references/configmap-secret-migration-guide.md` Section 2.

---

## 6. Automation and CLI Caveats

### T-15: `hcloud CCE CreateCluster` Fails with OpenAPI Parsing Error

- **Symptoms**: Running `hcloud CCE CreateCluster` outputs `[OPENAPI_ERROR] Failed to obtain API details`.
- **Root Cause**: KooCLI OpenAPI metadata parser encounters nested array type conflicts on complex cluster creation schemas.
- **Resolution**: Use `--cli-skeleton`, pass cluster definition via JSON body, or use the Python SDK (`huaweicloudsdkcce`). Read-only queries (`ListClusters`, `ShowCluster`, `update-kubeconfig`) are fully supported directly.

### T-16: Cross-Platform Kubeconfig `client-exec` Failure (`hcloud.exe` Not Found)

- **Symptoms**: `kubectl` on remote Linux host fails with `fork/exec C:\Windows\hcloud.exe: no such file or directory`.
- **Root Cause**: Kubeconfig generated on Windows embeds OS-specific binary paths.
- **Resolution**: Enforce centralized management—keep CCE kubeconfig on the operator host. For headless remote runners, generate static X.509 certs via `hcloud CCE CreateKubernetesClusterCert --cluster_id=<id> --cli-region=<region_id>`. See `references/cli-installation-guide.md` Section 2.

---

## 7. ELB & Ingress Access Errors

### T-17: Workload Inaccessible via ELB Public EIP (Timeout or HTTP 502/504)

- **Symptoms**: `curl -Iv https://app.example.com --resolve app.example.com:443:<elb-eip>` hangs or returns 502/504.
- **Root Cause**: ELB has no bound EIP, Node Security Group blocks 30000-32767, or Pod health check fails.
- **Resolution**: Verify ELB status (`hcloud ELB ShowLoadBalancer/v3 --loadbalancer_id=<id> --cli-region=<region_id>`), check listener health (`hcloud ELB ListHealthMonitors/v3 --cli-region=<region_id>`), and verify Node Security Group NodePort rules (`hcloud VPC ListSecurityGroupRules/v3 --cli-region=<region_id>`).

### T-18: Ingress ELB Auto-Creation Failure (`kubernetes.io/elb.autocreate`)

- **Symptoms**: Ingress reports `FailedCreateLoadBalancer` or webhook rejection `invalid autocreate configuration`.
- **Root Cause**: Invalid `elb_virsubnet_ids` syntax (must be plural array of VPC Subnet IDs), missing mandatory `available_zone` or `l7_flavor_name`, or attempting to update the immutable annotation in-place.
- **Resolution**: Validate syntax against `references/traffic-cutover-guide.md` Section 1.2. Delete and recreate Ingress to update parameters.

### T-19: Ingress Backend Service Type Mismatch (`GeneratePolicyFailed`)

- **Symptoms**: Ingress logs `can not found protocol port of pod xxx, skip add member` and `GeneratePolicyFailed`.
- **Root Cause**: Backend Service is `type: ClusterIP` on **CCE Standard** (only CCE Turbo supports `ClusterIP` with Dedicated ELB).
- **Resolution**: On CCE Standard, change Service to `type: NodePort` and ensure NodePort 30000-32767 is open in security group. For new clusters, mandate CCE Turbo. See `references/traffic-cutover-guide.md` Section 1.

### T-20: Pods Stuck in `Pending` Due to Insufficient CPU/Memory on Small Clusters

- **Symptoms**: Pods remain `Pending` with `0/1 nodes are available: 1 Insufficient cpu, 1 Insufficient memory`.
- **Root Cause**: Cluster sizing omitted CCE platform overhead (CoreDNS, Everest CSI, icagent consume ~2 vCPU / 4 GiB).
- **Resolution**: In dev/test, scale CoreDNS/Everest to 1 replica (`kubectl scale deploy coredns -n kube-system --replicas=1`) and lower Velero requests (`requests.cpu=100m`). In production sizing, always reserve at least 2 vCPU and 4 GiB for CCE platform add-ons. See `references/pre-migration-checklist.md` Section 1.

### T-21: Pods Stuck in `Pending` / `FailedCreatePodSandBox` (Sub-ENI Quota or Pod Subnet Exhaustion)

- **Symptoms**: Pods remain in `Pending` with `0/N nodes are available: TooManyPods` or fail with `FailedCreatePodSandBox: failed to allocate ip/sub-interface` despite ample free CPU and RAM on worker nodes.
- **Root Cause**: In CCE Turbo, each Pod occupies 1 auxiliary ENI (sub-interface) and 1 VPC IP. The node reached its ECS flavor auxiliary ENI quota (`quota:sub_network_interface_max_num`), or the cluster Pod subnet exhausted available VPC IP addresses.
- **Resolution**:
  1. Inspect the ECS flavor sub-ENI limit via `hcloud ECS ListFlavors --cli-region=<region_id> --flavor_id=<flavor_id>`.
  2. Scale out the node pool (add more worker nodes) so that total sub-interface capacity across nodes exceeds total Pod count.
  3. If VPC subnet IPs are exhausted, attach an auxiliary container subnet to the CCE Turbo cluster. See `references/pre-migration-checklist.md` Section 3.

### T-22: Target Cluster Creation Fails with "Can not find the specification of cluster flavor cce.turbo.s1.small"

- **Symptoms**: Cluster creation fails with `Can not find the specification of cluster flavor cce.turbo.s1.small` (or any `cce.turbo.*` error).
- **Root Cause**: There is no cluster flavor named `cce.turbo.*`. "Turbo" is the cluster category (`category: Turbo`) and container network mode (`container_network_type: eni`), NOT the cluster master flavor name. Cluster specifications use standard names: `cce.s1.small`, `cce.s1.medium`, `cce.s1.large`, `cce.s2.small`, `cce.s2.medium`, `cce.s2.large`, `cce.s2.xlarge`.
- **Resolution**:
  1. Specify standard cluster master flavor `cce.s1.small` (or `cce.s2.small` for multi-AZ HA).
  2. Set `container_network_type=eni` to provision the cluster as a CCE Turbo cluster.
  3. Query available cluster master flavors via `hcloud CCE GetClusterFlavorSpecs --cli-region=<region> --clusterType=VirtualMachine`. See `references/pre-migration-checklist.md` Section 3.

### T-23: Velero Kopia Uploader Reports "Completed" but OBS Prefix is Empty (Silent Fake Completion)

- **Symptoms**: `velero backup describe <backup> --details` reports `phase: Completed` and `errors: 0`, but querying OBS via `hcloud obs ls obs://<bucket>/<prefix>/repositories/` returns 0 objects / empty prefix.
- **Root Cause**: Protocol conflict. Huawei Cloud OBS strictly enforces Virtual-Hosted Style and rejects Path-Style requests. Velero 1.14's Kopia uploader has a known upstream defect (Issue #9780) where it ignores BSL virtual-hosted configuration and hardcodes Path-Style requests to OBS. Kopia's in-memory blob flush fails on OBS, but the podvolumebackup controller fails to escalate this failure, falsely reporting `Completed`.
- **Resolution**: Switch to restic uploader immediately: reinstall or patch Velero with `--uploader-type=restic`. Verify that real chunk data is uploaded to `obs://<bucket>/<prefix>/restic/`. See `references/velero-migration-guide.md` Section 2.

### T-24: Restored RWO EVS Volume Causes "Multi-Attach error" in Multi-Node CCE

- **Symptoms**: Restored stateful pods remain in `ContainerCreating`. `kubectl describe pod` shows: `Multi-Attach error for volume "pvc-xxx" Volume is already exclusively attached to one node and can't be attached to another`.
- **Root Cause**: Huawei Cloud EVS is ReadWriteOnce (RWO) block storage. While `csi-disk-topology` ensures AZ-level binding, in multi-node clusters the Kubernetes scheduler may schedule the pod to Node B while the EVS disk is still attached to Node A.
- **Resolution**: Pin workloads with EVS volumes to the specific worker node where their volume is physically attached using `nodeSelector: kubernetes.io/hostname: <node-name>`. See `references/velero-migration-guide.md` Section 5.

### T-25: Restored Workload Pods Stuck in `PodInitializing` or `ImagePullBackOff`

- **Symptoms**: Pods in target namespace stay in `PodInitializing` or fail with `ImagePullBackOff` / `401 Unauthorized` even after patching deployment container images to SWR.
- **Root Cause**: The image patching script only modified `spec.template.spec.containers` and omitted `spec.template.spec.initContainers` (e.g. init check containers like Dify's `check-api`), or failed to inject `imagePullSecrets`.
- **Resolution**: Patch both `containers` AND `initContainers` across all Deployments and StatefulSets to point to SWR, and ensure `imagePullSecrets: [{"name": "default-secret"}]` is present. See `references/velero-migration-guide.md` Section 5.

### T-26: Restored Workloads Remain at `replicas: 0`

- **Symptoms**: Workloads restore successfully on CCE, but no application pods are created (`REPLICAS: 0`).
- **Root Cause**: Workloads were scaled down to 0 on the source cluster during the maintenance window for transactional quiescence. Velero captures the live object state at backup time, restoring `replicas: 0`.
- **Resolution**: Explicitly scale workloads back up after image rewriting and secret verification: `kubectl scale deploy,sts --all --replicas=1 -n <namespace>`. See `references/velero-migration-guide.md` Section 5.

### T-27: `k8clone` Strips `clusterIP: None` from Headless Services, Breaking StatefulSet DNS Discovery

- **Symptoms**:
  - Restoring Services via `k8clone` throws `The Service "..." is invalid: spec.clusterIPs: Invalid value: []... may not be empty when clusterIP is "None"`.
  - Alternatively, the Service restores successfully, but `kubectl get svc` shows an allocated `ClusterIP` (e.g. `10.247.x.x`) instead of `None`.
  - StatefulSet pods fail to form clusters (e.g. Kafka brokers, ZooKeeper quorum, PostgreSQL repmgr) because `<pod>.<headless-svc>.<namespace>.svc.cluster.local` resolves to the single ClusterIP rather than individual Pod IPs.
- **Root Cause**: `k8clone` unconditionally strips `spec.clusterIP` and `spec.clusterIPs` across all Service objects during metadata sanitization. For Headless Services (`clusterIP: None`), removing this field causes the CCE Kubernetes API server to treat the service as a standard ClusterIP service and allocate a random IP from the Service CIDR.
- **Resolution**:
  1. **Pre-Restore Manifest Normalization**: Before executing `k8clone restore`, re-inject `spec.clusterIP: "None"` and `spec.clusterIPs: ["None"]` into exported Service manifests in `k8clone-dump/`. See `references/k8clone-migration-guide.md` Section 5.5.
  2. **Post-Restore In-Place Recreation**: Because `spec.clusterIP` is immutable once allocated, any headless service that received a ClusterIP must be deleted and recreated:
     ```bash
     kubectl delete svc <service-name> -n <namespace> --kubeconfig=~/.kube/cce-config
     kubectl apply -f <headless-svc-definition.yaml> --kubeconfig=~/.kube/cce-config
     ```
