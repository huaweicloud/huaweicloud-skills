# Pre-Migration Readiness Checklist

Before initiating workload and data migration to Huawei Cloud CCE, complete this checklist to identify compatibility gaps, networking bottlenecks, and quota constraints.

---

## 1. Source Cluster Assessment Matrix

|Dimension|Verification Item|Assessment Command / Tool|Acceptance Criteria|
|-|-|-|-|
|**Kubernetes Version**|Source API version vs Target CCE version|`kubectl version -o json`|Version gap ≤ 2 minor versions (e.g. v1.26 to v1.28).|
|**Deprecated APIs**|Removal of deprecated API versions|`pluto detect-helm` or `kubent`|No deprecated APIs (e.g., ensure `Ingress` uses `networking.k8s.io/v1`).|
|**Node Architecture**|Worker node CPU architecture|`kubectl get nodes -o wide`|Identify x86_64 vs ARM64 (Kunpeng) workloads.|
|**Resource Footprint**|Aggregated CPU and Memory requests|`kubectl top nodes` / Resource quotas|Total capacity must fit workload requests + at least 2 vCPUs and 4 GiB memory reserved for CCE system add-ons (CoreDNS, Everest, Kubelet).|
|**Pod Density & Sub-ENIs**|Total Pod count vs ECS auxiliary ENI limit|`kubectl get pods -A --no-headers \| wc -l`|In CCE Turbo (Yangtse CNI), 1 Pod = 1 sub-interface (auxiliary ENI). Target node count must satisfy both compute requests and sub-interface quotas.|
|**Container Images**|Image registries in use|`kubectl get pods -A -o jsonpath='{..image}'`|Inventory all external images (and `velero/restore-helper`) to be mirrored to Huawei Cloud SWR.|
|**PV / Storage**|StorageClasses and volume capacity|`kubectl get pvc,pv -A -o wide`|Categorized into Block (EVS, min 10Gi; `csi-disk-topology` for multi-AZ), Shared File (SFS Turbo, min 500Gi/1.2TB), or Object (OBS). Note: `csi-nas` is sunset.|
|**ConfigMaps**|App configs, Corefile, environment vars|`kubectl get cm -A`|Inventory external hostnames/IPs needing re-pointing to Huawei Cloud VPC.|
|**Secrets & Certs**|TLS secrets, passwords, tokens|`kubectl get secrets -A`|Identify TLS certs, Opaque keys; exclude `service-account-token` and `paas.elb` secrets.|
|**External Dependencies**|ExternalName services, headless endpoints|`kubectl get svc -A --field-selector spec.type=ExternalName`|Inventory all external FQDNs, partner APIs, and on-premises endpoints.|
|**Public Egress & NAT**|Workload internet egress & image registries|Customer audit / Network diagram|Confirm whether workloads call external APIs or pull from docker.io; if yes, NAT Gateway is required.|
|**Network & Ingress**|Ingress controllers, static public IPs|`kubectl get ingress -A`|Target cluster must be CCE Turbo (supports `ClusterIP`); CCE Standard requires `NodePort`.|

---

## 2. Target Huawei Cloud CCE Readiness Matrix

|Verification Item|Command / Check Method|Acceptance Criteria|
|-|-|-|
|**CCE Cluster Status**|`hcloud CCE ShowCluster --cluster_id=<id> --cli-region=<region_id>`|Status is `Available`, phase is `Active`, cluster architecture is **CCE Turbo**.|
|**Kubeconfig Access**|`hcloud CCE update-kubeconfig --cluster-id=<id> --region=cn-north-4`|`kubectl cluster-info` executes without TLS errors.|
|**Everest CSI Plugin**|`hcloud CCE ListAddonInstances --cluster_id=<id> --cli-region=<region_id>`|`everest` plugin is installed and `running`.|
|**VPC & Subnet Capacity**|`hcloud VPC ShowSubnet --subnet_id=<id> --cli-region=<region_id>`|Sufficient free IP addresses for all worker nodes and pods ($\ge \text{Pods} \times 1.3$).|
|**ECS Sub-ENI Quota**|`hcloud ECS ListFlavors --cli-region=<region_id> --flavor_id=<flavor_id>`|Node flavor's `quota:sub_network_interface_max_num` multiplied by node count exceeds total Pod count.|
|**NAT Gateway & Egress**|`hcloud NAT ListNatGatewaySnatRules --cli-region=<region_id>`|Active if workloads call external APIs or non-SWR images are pulled; optional if 100% SWR + private.|
|**Hybrid Connectivity**|Direct Connect / VPN route checks|Subnets reachable to on-premises IDCs and internal legacy services.|
|**CoreDNS Forwarding**|`kubectl get cm coredns -n kube-system`|Upstream DNS servers configured for enterprise private domains.|
|**Security Groups**|CCE cluster security group rules|Inbound traffic open for required ports; intra-cluster traffic unrestricted.|
|**SWR Organization**|`hcloud SWR ListNamespaces --cli-region=<region_id>`|Dedicated SWR namespace created and accessible.|
|**IAM Authorization**|Check assigned policies in IAM|`CCEFullPolicy` or `CCEMigrationOperatorCustomPolicy` attached.|
|**Service Quotas**|EVS disks, ECS instances, EIPs|Quota headroom exceeds total migrated workload requirements.|
|**Dedicated ELB & Public EIP**|`hcloud ELB ListLoadBalancers/v3 --cli-region=<region_id>`, `hcloud EIP ListPublicips/v3 --cli-region=<region_id>`|Dedicated ELB active with public EIP bound, or EIP/ELB quotas verified for auto-creation.|

---

## 3. CCE Turbo Node Sizing & Pod Density (Sub-Interface Architecture)

In Huawei Cloud CCE Turbo (Yangtse Cloud Native 2.0 network), container networking bypasses overlay encapsulation:

- **1 Pod = 1 Sub-Interface (Auxiliary ENI / Sub-ENI)**: Each pod directly binds a VPC sub-interface attached to the underlying ECS worker node.
- **Hardware Quota Ceiling**: The maximum number of pods a worker node can host is strictly bounded by the ECS flavor's auxiliary network interface quota (`quota:sub_network_interface_max_num`), regardless of remaining CPU or memory.

### Target CCE Cluster Master Flavor vs. Turbo Architecture

> [!WARNING] > **Cluster Master Flavor Naming Convention**:
>
> - Cluster master specifications are strictly named `cce.s1.<scale>` (single-master) or `cce.s2.<scale>` (multi-AZ HA master):
>   - `cce.s1.small` (max 50 nodes, dev/test)
>   - `cce.s1.medium` (max 200 nodes, standard production)
>   - `cce.s1.large` (max 1000 nodes, large production)
>   - `cce.s2.small` (max 50 nodes, HA test/prod)
>   - `cce.s2.medium` (max 200 nodes, HA production)
>   - `cce.s2.large` (max 1000 nodes, large HA production)
>   - `cce.s2.xlarge` (max 2000 nodes, ultra-large HA)

### Sizing Quota Query via KooCLI

Query ECS flavor sub-interface quotas before selecting node specifications:

```bash
hcloud ECS ListFlavors --cli-region=<region_id> --flavor_id=<flavor_id>
```

Look for `os_extra_specs["quota:sub_network_interface_max_num"]`

### Node Count Determination Formula

Calculate target worker node count considering both compute and network interface bounds:
$$\text{Nodes}_{\text{compute}} = \max\left(\left\lceil \frac{\sum \text{CPU requests} + 2\text{ vCPU}}{\text{Node allocatable CPU}} \right\rceil, \left\lceil \frac{\sum \text{Memory requests} + 4\text{ GiB}}{\text{Node allocatable Mem}} \right\rceil \right)$$
$$\text{Nodes}_{\text{network}} = \left\lceil \frac{\text{Total Workload Pod Count}}{\min(\text{Flavor Sub-ENI Quota}, \text{maxPods Config})} \right\rceil$$
$$\text{Target Node Count} = \max(\text{Nodes}_{\text{compute}}, \text{Nodes}_{\text{network}})$$

> [!IMPORTANT]
> For microservice architectures with high pod counts and low resource requests (e.g. 100 pods of 0.2 vCPU), `Nodes_network` often exceeds `Nodes_compute`. Selecting smaller node flavors with insufficient sub-ENI quotas will cause scheduling bottlenecks (`TooManyPods` or IP allocation timeouts).

### VPC Pod Subnet IP Sizing

Ensure the dedicated Pod Subnet CIDR assigned to the CCE Turbo cluster has sufficient IP headroom:
$$\text{Available Subnet IPs} \ge \text{Peak Pod Count} \times 1.3$$

---

## 4. Storage Type Pre-Migration Validation

Prior to initiating data replication:

1. **EVS (Block Storage)**: Ensure EVS quota in target region can accommodate all `ReadWriteOnce` persistent volumes (minimum 10 GiB per disk). For multi-AZ clusters, mandate `csi-disk-topology` (`WaitForFirstConsumer`) to prevent cross-AZ volume mount failures. See `references/storage-pv-migration-guide.md`.
2. **SFS Turbo (Shared File)**: Pre-create target SFS Turbo file systems. Note `csi-nas` is sunset; all RWX must use `csi-sfsturbo`. Ensure provisioned capacity meets platform minimums (500 GiB for Standard/Performance, 1.2 TB for HPC). For workloads < 500 GiB, adopt Dynamic SFS Turbo Subpath Provisioning (see `references/storage-pv-migration-guide.md` Section 2). Verify security group allows NFS port 2049.
3. **OBS (Object Storage)**: Pre-create the migration backup bucket (e.g., `cce-migration-backup-<account-id>`) in the same region as the target CCE cluster. Verify bucket access using `obsutil ls obs://<bucket-name>`.
4. **HostPath Volume Audit**: Velero and CCE CSI do **not** support `hostPath` volume migration. Identify all `hostPath` mounts and refactor them to EVS (`csi-disk`) or SFS Turbo (`csi-sfsturbo`) PVCs.
5. **PV Reclaim Policy Audit**: If PVs have `reclaimPolicy: Delete`, ensure they are not restored before PVCs to prevent accidental volume deletion; switch reclaim policy to `Retain` during the migration window.

---

## 5. External Connection & Egress Dependency Validation

Prior to shifting production traffic:

1. **Egress IP Whitelisting**: Ensure target CCE's NAT Gateway SNAT EIP has been registered with all third-party API providers (payment gateways, bank channels, SMS services).
2. **On-Premises Route Table**: Confirm routes from CCE VPC to on-premises subnets via Direct Connect / VPN are in `ACTIVE` state.
3. **CoreDNS Enterprise Domains**: Validate that enterprise domain resolution (`*.corp.internal`) is configured in the CCE Corefile ConfigMap.
4. **Egress & Route Verification**: Verify SNAT rule status via `hcloud NAT ListNatGatewaySnatRules` and validate routes to all external and on-premises endpoints.

---

## 6. Ingress & Workload Access Pre-Migration Validation

Prior to cutover:

1. **Dedicated ELB Provisioning**: Ensure a Dedicated ELB instance is provisioned with suitable L4/L7 flavor capacity and in `ACTIVE` status (`hcloud ELB ShowLoadBalancer/v3`).
2. **Public EIP Binding**: Verify the Dedicated ELB is associated with an active public EIP with sufficient dedicated bandwidth (`hcloud EIP ListPublicips/v3 --associate_instance_type.1=ELB`).
3. **SSL/TLS Certificates**: Replicate production SSL certificates into Huawei Cloud ELB certificate manager (`hcloud ELB ListCertificates/v3`) or Kubernetes TLS Secrets.
4. **NodePort Security Group Ingress**: Verify Node Security Group permits TCP ingress on `30000-32767` from the VPC CIDR for ELB backend node communication (`hcloud VPC ListSecurityGroupRules/v3`).

---

## 7. Migration Toolchain Decision Matrix (k8clone vs Velero)

|Evaluation Criteria|Primary: `k8clone` + Direct DB Logical Restore|Alternative: `Velero` (Mandatory restic)|
|-|-|-|
|**Target Workload Profile**|Microservices, standard DBs (PostgreSQL/MySQL/Redis), AI stacks (Dify)|Monolithic file systems, raw non-DB volumes without logical export|
|**Cluster Footprint**|Zero in-cluster components; runs from client workstation|Heavy; deploys controller pods and daemonsets on both clusters|
|**S3 / OBS Dependency**|None; streams over kubectl pipe directly|Mandatory OBS bucket; requires `--uploader-type=restic`|
|**Manifest Adaptation**|Native automated SWR/SC rewriting via `restore.json`|Requires post-restore patching across containers and initContainers|
|**Consistency Guarantee**|100% transactional consistency via native dump utilities|Requires backup hooks or scale-down with placeholder pod|
|**EVS 10 GiB Handling**|Simple local batch `sed` in dump folder prior to restore|Requires manual pre-provisioning on CCE with `restorePVs: false`|
