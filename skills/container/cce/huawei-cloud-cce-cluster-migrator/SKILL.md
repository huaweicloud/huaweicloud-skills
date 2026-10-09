---
name: huawei-cloud-cce-cluster-migrator
description: |
  End-to-end Kubernetes cluster migration assistant for migrating self-hosted, on-premise, or third-party cloud Kubernetes workloads to Huawei Cloud Cloud Container Engine (CCE).
  Covers source cluster assessment, CCE cluster sizing, container image synchronization to SWR, multi-type persistent volume (PV/PVC) migration across EVS, SFS Turbo, and OBS, ConfigMap and Secret migration with endpoint adaptation, Velero workload backup and restore, and smooth traffic cutover with Huawei Cloud Dedicated ELB and DNS.
  Triggers include: "CCE集群迁移", "Kubernetes迁移到CCE", "自建K8s迁移华为云", "K8s跨云迁移", "CCE Workload Migration", "migrate kubernetes to CCE", "migrate k8s to huawei cloud cce", "cce cluster migrator".
tags: [huawei-cloud, cce, kubernetes, migration]
---

# Huawei Cloud CCE Cluster Migrator

## Overview

The **Huawei Cloud CCE Cluster Migrator** skill automates and orchestrates the end-to-end migration of Kubernetes workloads, cluster configurations, ConfigMaps, Secrets, and persistent storage from external or third-party cloud Kubernetes environments to Huawei Cloud Cloud Container Engine (CCE). It supports multi-type storage re-mapping (EVS, SFS Turbo, OBS), image synchronization to SWR, and traffic cutover with Dedicated ELB.

## Prerequisites

1. **Tooling & CLIs**:
   - KooCLI (`hcloud`) installed and authenticated on the central operator host. See `references/cli-installation-guide.md`.
   - `kubectl` configured with access to the source cluster and target CCE cluster.
   - `velero` CLI and/or `k8clone` installed for workload metadata and volume migration.
   - `skopeo` or `image-migrator` installed for container image synchronization to SWR.
2. **IAM Authorization**:
   - The operator or agency credentials must have `CCEFullPolicy` (or `CCEMigrationOperatorCustomPolicy`), `SWRFullAccessPolicy`, `EVSFullAccessPolicy`, `VPCFullAccessPolicy`, and `ELBFullAccessPolicy`. See `references/iam-policies.md`.
3. **Network & Cluster Readiness**:
   - Target CCE cluster (prefer CCE Turbo) provisioned and healthy.
   - VPC subnet routing, NAT Gateway SNAT rules (if public egress needed), and security group rules verified. See `references/pre-migration-checklist.md`.

## Workflow

|Phase|Core Objectives & Gates|Key Actions & References|
|-|-|-|
|**Phase 1: Assessment & Sizing**|Workload inventory, egress audit, and sizing|Audit workloads, external APIs, and storage. Reserve min 2 vCPU / 4 GiB for CCE add-ons. Size nodes by compute and CCE Turbo sub-interface capacity (1 Pod = 1 auxiliary ENI). Ref: `references/pre-migration-checklist.md`.|
|**Phase 2: Plan Confirmation Gate**|Formal written plan & customer sign-off|Consult referenced guides below and `templates/migration-plan-template.md` to materialize `implementation_plan.md` (specs, storage, NAT, DB consistency, ELB ingress, rollback). **Must obtain explicit user approval before proceeding.**|
|**Phase 3: Target CCE Readiness**|Cluster, network & security group verification|Verify CCE Turbo status, Everest CSI, sync central `kubeconfig`, open NodePort `30000-32767` (if Standard), and verify NAT SNAT rules. Ref: `references/external-dependency-audit-guide.md`.|
|**Phase 4: Container Image Mirroring**|Replicate images to Huawei Cloud SWR|Bulk mirror images + Velero suite (`velero`, `aws-plugin`, `restore-helper`) via `skopeo` with `set -o pipefail` and `skopeo list-tags` validation. Ref: `references/swr-image-sync-guide.md`.|
|**Phase 5: Multi-Type PV Migration**|Re-map & replicate storage|Classify volumes into EVS (min 10Gi, single-Pod exclusive RWO; StatefulSet for multi-replica, Recreate strategy for Deployment; `csi-disk-topology` for multi-AZ), SFS Turbo (pre-created instance; min 500Gi/1.2TB, multi-Pod RWX via static PV or dynamic subpath), or OBS. Apply Velero SC mapping ConfigMap. Enforce DB consistency hooks. Ref: `references/storage-pv-migration-guide.md`.|
|**Phase 6: Workload & Secret Restore**|Restore configs, secrets & workloads|**Primary / Recommended**: **k8clone** (zero-cluster-overhead metadata cloning with automated StorageClass/ImageRepo rewrite via `restore.json`) paired with direct database logical dump/restore (`pg_dump`/`psql`).<br>**Secondary / Alternative**: **Velero** (full filesystem state with mandatory `--uploader-type=restic`, pre-provisioned 10Gi PVCs, and post-restore remediation). Exclude legacy `service-account-token` and `paas.elb`; preserve Headless Service `clusterIP: None`. Inject `default-secret` for SWR. Ref: `references/k8clone-migration-guide.md`, `references/velero-migration-guide.md`.|
|**Phase 7: Ingress & Traffic Cutover**|Dedicated ELB, smoke test & DNS switch|Configure Ingress (Dedicated ELB + EIP; `ClusterIP` for Turbo, `NodePort` for Standard). Smoke test via `curl --resolve`. Switch DNS. Ref: `references/traffic-cutover-guide.md`.|

### Phase 2 Plan Formulation Reference Matrix

> [!IMPORTANT]
> The agent must thoroughly read and review all referenced documents listed below and populate `templates/migration-plan-template.md` before beginning to write `implementation_plan.md`. Do not start drafting the migration plan until these reference guides have been consulted.

When drafting the formal migration plan document in Phase 2, the agent must consult `templates/migration-plan-template.md` and incorporate:

1. **Architecture Baseline & Quality Gates**:
   - `references/pre-migration-checklist.md` — Source/target readiness matrix, CCE Turbo sizing (compute and sub-interface quotas), and system overhead reservation.
   - `references/dataflow-diagram.md` — Centralized control plane topology and data migration sequence flows.
2. **Network Egress, Ingress & Connectivity**:
   - `references/external-dependency-audit-guide.md` — NAT Gateway + SNAT decision matrix and upstream API allowlisting.
   - `references/traffic-cutover-guide.md` — Dedicated ELB, `ClusterIP` (Turbo) vs `NodePort` (Standard), and DNS cutover schedule.
3. **Storage & Transactional Database Consistency**:
   - `references/storage-pv-migration-guide.md` — Multi-type PV mapping.
   - `references/velero-migration-guide.md` — Velero Backup Hooks (`pre.hook`/`post.hook`) or ingress cutoff / maintenance freeze.
4. **Image Synchronization, Workload Cloning & Configuration Sanitization**:
   - `references/swr-image-sync-guide.md` — SWR namespace, image inventory, complete Velero suite mirroring, and target CCE `imagePullSecrets` configuration.
   - `references/k8clone-migration-guide.md` — Zero-cluster-overhead metadata backup and restore, `restore.json` for StorageClass substitution (`csi-disk`/`csi-sfsturbo`/`csi-obs`) and ImageRepo rewriting (`docker.io` $\to$ SWR), `--exclude-having-owner-ref` rule, and Headless Service `clusterIP: None` preservation.
   - `references/configmap-secret-migration-guide.md` — Endpoint re-pointing, SSR variable audit, and `paas.elb` exclusion.

## Core Commands

### 1. Assessment & Sizing

```bash
# Query CCE cluster flavors (x86 architecture)
hcloud CCE GetClusterFlavorSpecs --cli-region=<region_id> --clusterType=VirtualMachine

# List target clusters & inspect active add-ons
hcloud CCE ListClusters --cli-region=<region_id>
hcloud CCE ShowCluster --cli-region=<region_id> --cluster_id={target_cluster_id} --detail=true
```

### 2. Kubeconfig & Target Readiness

```bash
# Sync CCE kubeconfig on operator host (intranet or public EIP access)
hcloud CCE update-kubeconfig --cluster-id={target_cluster_id} --region=cn-north-4 --output=~/.kube/cce-config

# Verify Everest CSI add-on
hcloud CCE ListAddonInstances --cli-region=<region_id> --cluster_id={target_cluster_id}

# Verify NAT Gateway and SNAT rules (for workload/image internet egress)
hcloud NAT ListNatGateways --cli-region=<region_id>
hcloud NAT ListNatGatewaySnatRules --cli-region=<region_id>
```

### 3. Container Image Synchronization (SWR)

```bash
# Retrieve temporary SWR login credentials
SWR_AUTH=$(hcloud SWR CreateSecret --cli-region=<region_id> | jq -r '.auths["swr.cn-north-4.myhuaweicloud.com"].auth' | base64 -d)

# Replicate image via skopeo with pipefail
set -euo pipefail
skopeo copy --dest-creds="${SWR_AUTH}" --insecure-policy docker://{source_image} docker://swr.cn-north-4.myhuaweicloud.com/{org}/{image}:{tag}
skopeo list-tags --creds="${SWR_AUTH}" docker://swr.cn-north-4.myhuaweicloud.com/{org}/{image} | grep -q "{tag}"
```

### 4. Workload Restore & Verification

```bash
# Option A (Primary / Recommended): k8clone Metadata Clone + Direct DB Logical Restore
k8clone backup --kubeconfig=~/.kube/source-config --exclude-having-owner-ref=true --local-dir=./k8clone-dump
k8clone restore --kubeconfig=~/.kube/cce-config --local-dir=./k8clone-dump.zip --restore-conf=./restore.json
# Logical DB stream (example: PostgreSQL)
kubectl exec -i {source_db_pod} -n {namespace} -- pg_dump -U {user} {dbname} | kubectl exec -i {cce_db_pod} -n {namespace} -- psql -U {user} {dbname}

# Option B (Secondary / Alternative): Velero Full State Restore (--uploader-type=restic)
kubectl apply -f templates/velero-sc-mapping.yaml -n velero
velero restore create cce-migration-restore --from-backup {backup_name} --restore-pvs=false --wait

# Verify workloads and database consistency post-restore
kubectl get pods,deployments,statefulsets,pvc -A
kubectl exec -i {db_pod} -n {namespace} -- psql -U {user} -d {dbname} -c "SELECT count(*) FROM accounts;"
```

### 5. Ingress & Traffic Cutover

```bash
# Inspect Dedicated ELB and public EIPs
hcloud ELB ListLoadBalancers/v3 --cli-region=<region_id>
hcloud EIP ListPublicips/v3 --cli-region=<region_id> --associate_instance_type.1=ELB

# Smoke test Ingress endpoint before DNS switch
curl -Iv https://app.example.com --resolve app.example.com:443:{target_elb_eip}
```

## Parameter Confirmation

Prior to executing any resource provisioning, data migration, or traffic switchover, the agent **must confirm** the following parameters with the user:

|Parameter|Description|Default / Example|Confirmation Scope|
|-|-|-|-|
|`target_cluster_id`|Huawei Cloud CCE cluster ID|e.g. `cce-cluster-abc12345`|Phase 2 / Phase 3|
|`target_region`|Huawei Cloud region identifier|`cn-north-4`|Phase 1 / Phase 2|
|`migration_toolchain`|Workload restore toolchain|`k8clone + DB Dump (Primary)` or `Velero restic (Secondary)`|Phase 2 / Phase 6|
|`swr_organization`|Target SWR organization/namespace|e.g. `cce-migration-repo`|Phase 2 / Phase 4|
|`storage_class_mapping`|Mapping of source StorageClasses to CCE|`gp2 -> csi-disk-topology`, `efs -> csi-sfsturbo`|Phase 2 / Phase 5|
|`nat_gateway_strategy`|Whether NAT Gateway is required for egress|`No (100% SWR)` or `Yes (External APIs)`|Phase 2 / Phase 3|
|`elb_instance_id`|Dedicated ELB instance for Ingress|Pre-provisioned or auto-create|Phase 2 / Phase 7|
|`dns_cutover_strategy`|Weighted canary cutover vs immediate switch|`Weighted (10% -> 50% -> 100%)`|Phase 2 / Phase 7|

## KooCLI Command Format Standard

All Huawei Cloud CLI commands in this skill must adhere to the following standards:

1. **Service and Operation Names**: Service names start with uppercase/title case (e.g. `CCE`, `NAT`, `SWR`, `VPC`, `ELB`, `EIP`, `IAM`). Operation names use PascalCase (e.g. `ListClusters`, `ShowCluster`, `ListNatGateways`).
2. **Region Specification**: Every standard `hcloud` command must explicitly include `--cli-region=<region>` (or `--region=<region>` for `update-kubeconfig`).
3. **Safe Parameter Passing**: Complex body parameters (e.g. security group rules, NAT gateway specs) must use the appropriate object prefix syntax (e.g. `--security_group_rule.*`, `--nat_gateway.*`, `--snat_rule.*`) verified against `hcloud <Service> <Operation> --help`.

## Reference Documents

- `references/cli-installation-guide.md` — Installation and setup procedures for KooCLI, kubectl, velero, and obsutil
- `references/configmap-secret-migration-guide.md` — ConfigMap/Secret sanitization, parameter adaptation, SSR environment audit, and `paas.elb` exclusion
- `references/dataflow-diagram.md` — Mermaid architecture and sequence diagrams
- `references/external-dependency-audit-guide.md` — External dependency discovery, NAT Gateway decision matrix, and network probing
- `references/iam-policies.md` — Verified IAM 5.0 policies and least-privilege action definitions
- `references/k8clone-migration-guide.md` — Lightweight Kubernetes metadata cloning and automated restore via k8clone
- `references/pre-migration-checklist.md` — Source and target readiness checklist, CCE Turbo sizing (compute and sub-interface quotas), and system add-on sizing
- `references/related-commands.md` — Complete quick-reference table of verified KooCLI and kubectl commands
- `references/storage-pv-migration-guide.md` — Multi-type PV migration across EVS, SFS Turbo, and OBS
- `references/swr-image-sync-guide.md` — Image replication via skopeo, pipefail error handling, complete Velero suite mirroring, and CCE `imagePullSecrets` configuration
- `references/traffic-cutover-guide.md` — Dedicated ELB, Ingress backend rules (`ClusterIP` vs `NodePort`), `elb.autocreate`, and DNS cutover
- `references/troubleshooting-guide.md` — Diagnostic playbooks for T-01 through T-20 (storage, 401 pulls, autocreate, NodePort, sizing)
- `references/velero-migration-guide.md` — Velero installation with full SWR image suite, backup hooks, and restore
