# Verification Method — huawei-cloud-cce-cluster-migrator

This document defines the functional verification procedures for the `huawei-cloud-cce-cluster-migrator` skill, providing direct verification commands and measurable success criteria corresponding to each workflow phase in the migration lifecycle.

---

## Workflow Phase Verification Matrix

|Phase|Phase Name|Verification Method / Command|Primary Success Criteria|
|-|-|-|-|
|**Phase 1**|Assessment & Sizing|`hcloud CCE GetClusterFlavorSpecs`<br>`hcloud CCE ListClusters`|Workloads cataloged; target CCE Turbo flavor selected with >= 2 vCPU / 4 GiB reserved for add-ons.|
|**Phase 2**|Plan Confirmation Gate|Review `implementation_plan.md`|Formal written plan materialized to disk; user provides explicit sign-off prior to mutating operations.|
|**Phase 3**|Target CCE Readiness|`hcloud CCE update-kubeconfig`<br>`hcloud CCE ListAddonInstances`<br>`hcloud NAT ListNatGateways`|Cluster status `Available`; nodes `Ready`; Everest CSI active; egress SNAT rules verified.|
|**Phase 4**|Container Image Mirroring|`hcloud SWR CreateSecret`<br>`skopeo copy`<br>`skopeo list-tags`|All workload & Velero images mirrored to SWR; test pod pulls successfully without `ImagePullBackOff`.|
|**Phase 5**|Multi-Type PV Migration|Apply PVC templates<br>`kubectl get pvc`<br>Deploy `storage-verifier` pod|EVS (min 10Gi), SFS Turbo (min 500Gi/1.2TB), and OBS PVCs `Bound`; test pod passes read/write checks.|
|**Phase 6**|Workload & Secret Restore|`velero restore create --wait`<br>`kubectl get pods,deployments -A`|Restore finishes with 0 fatal errors; all deployments report desired replicas in `Running`/`Ready` state.|
|**Phase 7**|Ingress & Traffic Cutover|`hcloud ELB ListLoadBalancers/v3`<br>`curl --resolve`<br>DNS switchover|Dedicated ELB active with public EIP; smoke test returns HTTP 200; live traffic cutover without 5xx errors.|

---

## Phase 1: Assessment & Sizing Verification

### Objective

Audit source Kubernetes cluster workloads, compute footprint, persistent storage, and network egress requirements, then size the target Huawei Cloud CCE cluster.

### Verification Steps

1. Query available CCE VM cluster flavor specifications:
   ```bash
   hcloud CCE GetClusterFlavorSpecs --cli-region=<region_id> --clusterType=VirtualMachine
   ```
2. Query target region clusters:
   ```bash
   hcloud CCE ListClusters --cli-region=<region_id>
   ```
3. Audit source workloads and resource requests:
   ```bash
   kubectl get nodes -o wide
   kubectl top nodes
   kubectl get pvc,storageclass -A
   kubectl get svc -A --field-selector spec.type=ExternalName
   ```
4. Verify target ECS flavor auxiliary ENI quota for CCE Turbo pod density:
   ```bash
   hcloud ECS ListFlavors --cli-region=<region_id> --flavor_id=<flavor_id>
   ```

### Success Criteria

- **Flavor Sizing**: CCE cluster master flavor (e.g. `cce.s1.small`, `cce.s2.small`, verified via `hcloud CCE GetClusterFlavorSpecs`) matches target node capacity; worker node flavor matches or exceeds source compute capacity plus a mandatory system reservation of at least **2 vCPU and 4 GiB RAM** for cluster management add-ons (Everest, CoreDNS, ICAgent).
- **Sub-Interface & Pod Density Sizing**: Worker node count satisfies the CCE Turbo 1 Pod = 1 sub-interface constraint: `node_count * flavor_sub_eni_limit >= total_workload_pods`. The target Pod subnet CIDR contains $\ge \text{Total Pods} \times 1.3$ available IP addresses.
- **Network Compatibility**: Source and target VPC CIDR blocks do not overlap.
- **Architecture Standard**: CCE Turbo is designated as the target cluster architecture for direct elastic network interface (ENI) container networking.
- **Failure Indicator & Action**: If CIDR conflict is detected, adjust target CCE VPC/subnet CIDR before cluster provisioning. If total pods exceed total node sub-interfaces, scale out node count or select a flavor with higher `quota:sub_network_interface_max_num`.

---

## Phase 2: Plan Confirmation Gate Verification

### Objective

Materialize a complete written migration plan to disk and secure explicit user confirmation before executing any infrastructure changes or data transfers.

### Verification Steps

1. Verify the existence and contents of the written migration plan file:
   ```bash
   test -f implementation_plan.md && cat implementation_plan.md
   ```
2. Confirm the plan document follows `templates/migration-plan-template.md` and covers all mandatory architectural areas:
   - Target CCE cluster ID, flavor, and node count.
   - StorageClass mapping table (mapping source classes to `csi-disk-topology`, `csi-sfsturbo`, `csi-obs`) enforcing minimum volume sizes (EVS ≥ 10 GiB; SFS Turbo ≥ 500 GiB or 1.2 TB).
   - Egress strategy (NAT Gateway + SNAT vs intranet SWR).
   - Container image registry destination in Huawei Cloud SWR.
   - Dedicated ELB instance model and Ingress annotation configuration.
   - Database transactional consistency strategy (Velero backup hooks or application scale-down).
   - Rollback procedures and cutover go/no-go gates.
3. Verify explicit user confirmation in chat/task logs.

### Success Criteria

- **Document Materialization**: The migration plan file exists on disk, populated with concrete parameters instead of unexpanded placeholders.
- **User Approval**: Explicit user approval is recorded. No mutating cloud API or Kubernetes apply command is executed prior to this sign-off.
- **Failure Indicator & Action**: If the user requests scope modifications, update `implementation_plan.md` directly and re-confirm.

---

## Phase 3: Target CCE Readiness Verification

### Objective

Verify that the target CCE cluster, node pools, add-on components, and VPC network routing are healthy and accessible.

### Verification Steps

1. Verify target CCE cluster status:
   ```bash
   hcloud CCE ShowCluster --cli-region=<region_id> --cluster_id={target_cluster_id} --detail=true
   ```
2. Download and verify CCE cluster kubeconfig:
   ```bash
   hcloud CCE update-kubeconfig --cluster-id={target_cluster_id} --region=cn-north-4 --output=~/.kube/cce-config
   KUBECONFIG=~/.kube/cce-config kubectl get nodes
   ```
3. Verify required add-ons:
   ```bash
   hcloud CCE ListAddonInstances --cli-region=<region_id> --cluster_id={target_cluster_id}
   ```
4. Verify NAT Gateway and SNAT rules for workload egress:
   ```bash
   hcloud NAT ListNatGateways --cli-region=<region_id>
   hcloud NAT ListNatGatewaySnatRules --cli-region=<region_id>
   ```

### Success Criteria

- **Cluster State**: Cluster status is `"Available"`.
- **Node Readiness**: All cluster nodes report `STATUS: Ready`.
- **Add-on Health**: `everest` (Everest CSI driver) and `coredns` add-on instances are in `"running"` status.
- **Egress Routing**: If external API access is required, NAT Gateway is active and SNAT rules cover the CCE container and node subnets.
- **Failure Indicator & Action**: If `everest` is missing or abnormal, reinstall/upgrade the add-on via CCE console or KooCLI add-on management.

---

## Phase 4: Container Image Mirroring Verification

### Objective

Replicate all required container images from external registries to Huawei Cloud SWR and ensure the target cluster can pull images without authentication issues.

### Verification Steps

1. Generate temporary SWR login credentials:
   ```bash
   hcloud SWR CreateSecret --cli-region=<region_id>
   ```
2. Replicate images via Skopeo with pipefail enabled:
   ```bash
   set -euo pipefail
   skopeo copy --dest-creds="${SWR_AUTH}" --insecure-policy docker://{source_image} docker://swr.cn-north-4.myhuaweicloud.com/{org}/{image}:{tag}
   ```
3. Verify image tag existence in SWR:
   ```bash
   skopeo list-tags --creds="${SWR_AUTH}" docker://swr.cn-north-4.myhuaweicloud.com/{org}/{image}
   ```
4. Deploy a test image pull pod on target CCE:
   ```bash
   kubectl run swr-test --image=swr.cn-north-4.myhuaweicloud.com/{org}/{image}:{tag} --restart=Never -n default -- sleep 10
   kubectl get pod swr-test -n default
   kubectl delete pod swr-test -n default --ignore-not-found
   ```

### Success Criteria

- **SWR Credential Generation**: `CreateSecret` returns HTTP 200 with base64 auth payload.
- **Image Mirroring**: All workload images and Velero components (`velero`, `velero-plugin-for-aws`, `velero-restore-helper`) replicate to SWR.
- **Tag Inspection**: `skopeo list-tags` confirms target tag exists in SWR repository.
- **Pod Pull**: Test pod attains `Running` or `Completed` state with 0 `ImagePullBackOff` or `ErrImagePull` events.
- **Failure Indicator & Action**: If pull returns `401 Unauthorized`, verify that `default-secret` is present in the target namespace and referenced in the service account.

---

## Phase 5: Multi-Type PV Migration Verification

### Objective

Re-map persistent storage types to CCE Everest storage drivers (EVS, SFS Turbo, OBS) and verify dynamic volume provisioning and data consistency.

### Verification Steps

1. Apply test PVCs for targeted storage classes:
   ```bash
   kubectl apply -f templates/pvc-evs-template.yaml
   kubectl apply -f templates/pvc-sfsturbo-template.yaml
   kubectl apply -f templates/pvc-obs-template.yaml
   ```
2. Inspect PVC binding status:
   ```bash
   kubectl get pvc -n default
   ```
3. Deploy a verification pod to test persistent volume read/write operations:
   ```bash
   kubectl run storage-verifier --image=swr.cn-north-4.myhuaweicloud.com/{org}/busybox:latest --restart=Never -- sleep 60
   kubectl exec -i storage-verifier -- sh -c "echo 'cce-migration-test' > /data/test.txt && cat /data/test.txt"
   kubectl delete pod storage-verifier -n default
   ```
4. Clean up test PVC manifests:
   ```bash
   kubectl delete -f templates/pvc-evs-template.yaml --ignore-not-found
   kubectl delete -f templates/pvc-sfsturbo-template.yaml --ignore-not-found
   kubectl delete -f templates/pvc-obs-template.yaml --ignore-not-found
   ```

### Success Criteria

- **PVC State**: All deployed PVCs transition from `Pending` to `Bound`.
- **Driver Adherence**:
  - EVS PVCs bound via `csi-disk` or `csi-disk-topology` (minimum size ≥ 10 GiB; `csi-disk-topology` used for multi-AZ clusters).
  - SFS Turbo PVCs bound via `csi-sfsturbo` (minimum size ≥ 500 GiB or 1.2 TB; legacy `csi-nas` is sunset and must not be used).
  - OBS PVCs bound via `csi-obs`.
- **I/O Verification**: Verification pod successfully executes file writes and reads against mounted persistent volume paths.
- **Failure Indicator & Action**: If PVC remains `Pending`, inspect `kubectl describe pvc` for Everest CSI provisioner errors or insufficient disk size specifications.

---

## Phase 6: Workload & Secret Restore Verification

### Objective

Restore sanitized Kubernetes workloads, ConfigMaps, and Secrets from backup, verifying database consistency and container readiness.

### Verification Steps

1. For Velero restore, apply StorageClass mapping ConfigMap to Velero namespace:
   ```bash
   kubectl apply -f templates/velero-sc-mapping.yaml -n velero
   ```
2. Trigger workload restoration using the chosen toolchain:
   - **Option A: Velero (Stateful & Volume Data)**:
     ```bash
     velero restore create cce-migration-restore --from-backup {backup_name} --wait
     velero restore describe cce-migration-restore
     ```
   - **Option B: k8clone (Lightweight Metadata)**:
     ```bash
     k8clone restore --kubeconfig=~/.kube/cce-config --local-dir=./k8clone-dump.zip --restore-conf=./restore.json
     ```
3. Verify workload replicas and pod health:
   ```bash
   kubectl get deployments,statefulsets,daemonsets -A
   kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded
   ```
4. Execute database consistency verification:
   ```bash
   kubectl exec -i {db_pod} -n {db_namespace} -- psql -U {user} -d {dbname} -c "SELECT count(*) FROM accounts;"
   ```

### Success Criteria

- **Restore Execution**: Velero restore reports status `Completed` with `Errors: 0`, or `k8clone` restore executes cleanly with zero manifest application errors.
- **Workload Status**: All Deployments and StatefulSets achieve desired replica count; pods report status `Running` and readiness `1/1` or expected ratio.
- **Secret Sanitization**: Legacy `service-account-token` secrets and deprecated cloud annotations (`kubernetes.io/paas.elb.*`) are excluded.
- **Database Consistency**: Row counts and table checksums match pre-migration database export.
- **Failure Indicator & Action**: If pods crash due to database endpoints, verify that ConfigMaps were updated with new Huawei Cloud VPC IP addresses or private DNS names.

---

## Phase 7: Ingress & Traffic Cutover Verification

### Objective

Validate Dedicated ELB provisioning, configure Ingress routing, perform pre-cutover smoke testing, and switch DNS traffic to Huawei Cloud CCE.

### Verification Steps

1. Inspect Dedicated ELB and public EIP bindings:
   ```bash
   hcloud ELB ListLoadBalancers/v3 --cli-region=<region_id>
   hcloud EIP ListPublicips/v3 --cli-region=<region_id> --associate_instance_type.1=ELB
   ```
2. Verify Ingress manifest routing:
   ```bash
   kubectl get ingress -A -o wide
   ```
3. Perform pre-cutover HTTP smoke test resolving domain directly to ELB EIP:
   ```bash
   curl -Iv "https://app.example.com" --resolve "app.example.com:443:{target_elb_eip}"
   ```
4. Verify application monitoring after executing DNS switchover:
   - Monitor live ingress HTTP status codes in Application Operations Management (AOM) or Cloud Eye.

### Success Criteria

- **Dedicated ELB**: Load balancer status is `ACTIVE` and bound to a valid public EIP.
- **Ingress Configuration**: Ingress specifies `spec.ingressClassName: cce`, `pathType: ImplementationSpecific` with CCE `url-match-mode` property, Dedicated ELB annotations (`kubernetes.io/elb.id` or `kubernetes.io/elb.autocreate`), and uses `ClusterIP` service type for CCE Turbo (or `NodePort` with ports 30000-32767 open for CCE Standard).
- **Pre-Cutover Smoke Test**: `curl --resolve` returns valid HTTP status (e.g., `200 OK`) and matching application payload.
- **Cutover Stability**: Following DNS switch, incoming traffic arrives at CCE pods without anomalous HTTP 5xx error spikes or latency regression.
- **Failure Indicator & Action**: If `curl` times out, check ELB listener health check status and verify node/ENI security group ingress rules.
