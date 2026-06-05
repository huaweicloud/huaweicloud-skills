# Feature Verification Steps

## Overview

Functional verification process for CCE cluster management skill.

## Verification Checklist

| No. | Verification Item | Command Example |
|-----|-------------------|-----------------|
| 1 | Query cluster list | `huawei_list_cce_clusters region=cn-north-4` |
| 2 | Query node list | `huawei_list_cce_nodes region=cn-north-4 cluster_id=xxx` |
| 3 | Query node pool list | `huawei_list_cce_nodepools region=cn-north-4 cluster_id=xxx` |
| 4 | Get kubeconfig | `huawei_get_cce_kubeconfig region=cn-north-4 cluster_id=xxx` |
| 5 | Node scheduling status | `huawei_cce_node_status region=cn-north-4 cluster_id=xxx node_id=xxx` |

## Verification Steps

### Step 1: Environment Check

```bash
# Check Python environment
python3 --version

# Check dependencies
pip show huaweicloudsdkcce
```

### Step 2: Verify Query Functions

```bash
# Query cluster list
python3 huawei-cloud.py huawei_list_cce_clusters region=cn-north-4

# Expected result: Returns cluster list, including cluster_id, name, status, etc.
```

### Step 3: Verify Node Management

```bash
# Query node scheduling status
python3 huawei-cloud.py huawei_cce_node_status \
  region=cn-north-4 \
  cluster_id=<cluster_id> \
  node_id=<node_id>

# Expected result: Returns "Schedulable" or "Unschedulable"
```

### Step 4: Verify Dangerous Operation Confirmation Mechanism

```bash
# Call delete command without confirm parameter
python3 huawei-cloud.py huawei_delete_cce_cluster \
  region=cn-north-4 \
  cluster_id=xxx

# Expected result: Returns preview and warning, does not execute deletion
```

## Example

```bash
# Complete verification flow
python3 huawei-cloud.py huawei_list_cce_clusters region=cn-north-4
python3 huawei-cloud.py huawei_list_cce_nodes region=cn-north-4 cluster_id=<cluster_id>
```