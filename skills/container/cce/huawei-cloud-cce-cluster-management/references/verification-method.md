# Feature Verification Steps

## Overview

Functional verification process for the CCE cluster management skill (hcloud + kubectl cce architecture). Run these checks before relying on the skill in a new environment.

## Verification Checklist

| No. | Verification Item | Command |
|-----|-------------------|---------|
| 1 | hcloud version (≥ 7.2) | `hcloud version` |
| 2 | kubectl + kubectl-cce plugin installed | `kubectl cce --help` |
| 3 | Credentials env vars set | `echo $HW_ACCESS_KEY $HW_SECRET_KEY` (+ `$HW_SECURITY_TOKEN` for temp creds) |
| 4 | hcloud → CCE connectivity | `hcloud CCE ListClusters --cli-region=cn-north-4` |
| 5 | Query cluster list | `huawei_list_cce_clusters region=cn-north-4` |
| 6 | Query node list | `huawei_list_cce_nodes region=cn-north-4 cluster_id=xxx` |
| 7 | Query node pool list | `huawei_list_cce_nodepools region=cn-north-4 cluster_id=xxx` |
| 8 | Get kubeconfig | `huawei_get_cce_kubeconfig region=cn-north-4 cluster_id=xxx` |
| 9 | Node scheduling status (kubectl cce path) | `huawei_cce_node_status region=cn-north-4 cluster_id=xxx node_name=xxx` |

## Verification Steps

### Step 1: Toolchain Check

```bash
# hcloud must be 7.2+
hcloud version

# kubectl + kubectl-cce plugin for node scheduling operations
kubectl cce --help

# Python SDK retained for create-cluster / create-nodepool fallback
python3 -c "import huaweicloudsdkcce; print('cce sdk ok')"
python3 -c "import passlib; print('passlib ok')"
python3 -c "import yaml; print('pyyaml ok')"
```

### Step 2: Credential Check

```bash
# Permanent credentials
echo "AK=${HW_ACCESS_KEY:0,4}... SK=${HW_SECRET_KEY:0,4}..."

# Temporary credentials (optional) — must be set together with AK/SK
echo "SecurityToken set: $([ -n "$HW_SECURITY_TOKEN" ] && echo yes || echo no)"
```

Expected: AK and SK prefixes are visible (never print full values). If `HW_SECURITY_TOKEN` is set, all three must be set together.

### Step 3: hcloud Connectivity Test

```bash
# Direct hcloud call — confirms credentials + network + region
hcloud CCE ListClusters --cli-region=cn-north-4
```

Expected: JSON cluster list (possibly empty) with no `[NETWORK_ERROR]` / `[OPENAPI_ERROR]` tags.

### Step 4: Verify Query Functions

```bash
# Query cluster list via the skill
python3 huawei-cloud.py huawei_list_cce_clusters region=cn-north-4

# Expected: returns cluster list including cluster_id, name, status
```

### Step 5: Verify kubectl Path (Node Status)

```bash
# Exercises the full kubectl cce path: kubectl cce --cluster-id ... get node
python3 huawei-cloud.py huawei_cce_node_status \
  region=cn-north-4 \
  cluster_id=<cluster_id> \
  node_name=<node_name>

# Expected: returns "schedulable": true/false and "ready": true/false
```

If this fails, isolate the kubeconfig step:

```bash
hcloud CCE CreateKubernetesClusterCert \
  --cli-region=cn-north-4 \
  --cli-access-key="$HW_ACCESS_KEY" --cli-secret-key="$HW_SECRET_KEY" \
  --cluster_id=<cluster_id> --duration=30d \
  --cli-output=json
# Manual test with kubectl cce
HW_ACCESS_KEY=<AK> HW_SECRET_KEY=<SK> HW_SECURITY_TOKEN=<token> \
  kubectl cce --cluster-id <id> --region <region> --project-id <pid> get nodes
```

### Step 6: Verify Dangerous Operation Confirmation Mechanism

```bash
# Call delete command WITHOUT confirm parameter
python3 huawei-cloud.py huawei_delete_cce_cluster \
  region=cn-north-4 \
  cluster_id=xxx

# Expected: returns preview + warning + requires_confirmation: true, does NOT execute deletion
```

## Example

```bash
# Complete verification flow
hcloud version                                         # 1. toolchain
hcloud CCE ListClusters --cli-region=cn-north-4        # 2. connectivity
python3 huawei-cloud.py huawei_list_cce_clusters region=cn-north-4
python3 huawei-cloud.py huawei_list_cce_nodes region=cn-north-4 cluster_id=<cluster_id>
python3 huawei-cloud.py huawei_cce_node_status region=cn-north-4 cluster_id=<cluster_id> node_name=<node_name>
```
