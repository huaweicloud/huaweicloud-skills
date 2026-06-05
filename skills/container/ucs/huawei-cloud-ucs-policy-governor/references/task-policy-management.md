# Task: Policy Management

## Overview

UCS policy instances enforce governance rules on managed clusters and fleet groups. Each policy instance is based on a constraint template and targets either a single cluster (via `CreateClusterPolicyInstance`) or a fleet group (via `CreateClusterGroupPolicyInstance`). This task covers creating, updating, querying, and deleting policy instances.

## Operations Catalog

| Operation                     | Method | Description              | Key Parameters                                  |
| ----------------------------- | ------ | ------------------------ | ----------------------------------------------- |
| `CreateClusterPolicyInstance` | POST   | 创建集群策略实例         | `--clusterid`, `--constraintTemplateID`, `--enforcementAction`, `--namespaces.[N]`, `--parameters` |
| `CreateClusterGroupPolicyInstance` | POST | 创建舰队组策略实例      | `--clustergroupid`, `--constraintTemplateID`, `--enforcementAction`, `--namespaces.[N]`, `--parameters` |
| `UpdatePolicyInstance`        | PUT    | 更新策略实例             | `--policyinstanceid`, `--constraintTemplateID`, `--enforcementAction`, `--namespaces.[N]`, `--parameters` |
| `ShowPolicyInstance`          | GET    | 获取策略实例详情         | `--policyinstanceid`                            |
| `DeletePolicyInstance`        | DELETE | 删除策略实例             | `--policyinstanceid`                            |
| `ListPolicyInstances`         | GET    | 列出策略实例             | `--cli-region` only (no filter params)          |
| `ListPolicyDefinitions`       | GET    | 列出策略定义             | `--cli-region` only (no filter params)          |
| `ShowPolicyDefinition`        | GET    | 获取策略定义详情         | `--policydefinitionid`                          |
| `EnableClusterPolicy`         | POST   | 启用集群策略             | `--clusterid`, `--retry`                        |
| `EnableClusterGroupPolicy`    | POST   | 启用舰队组策略           | `--clustergroupid`, `--retry`                   |
| `DisableClusterPolicy`        | POST   | 禁用集群策略             | `--clusterid`                                   |
| `DisableClusterGroupPolicy`   | POST   | 禁用舰队组策略           | `--clustergroupid`                              |

## Workflows

### W1: Discover Available Policy Definitions

Before creating a policy instance, review available definitions:

```bash
# List all policy definitions (no filter parameters available)
hcloud UCS ListPolicyDefinitions --cli-region=cn-north-4

# Show definition details to understand parameters
hcloud UCS ShowPolicyDefinition --policydefinitionid=<definition-id> --cli-region=cn-north-4
```

**Policy Definition Categories**:
- `security`: Security baseline, pod security standards, privileged container restrictions
- `compliance`: CIS benchmarks, regulatory compliance, audit logging
- `resource`: Resource quotas, resource limits, cost optimization
- `network`: Network policies, ingress/egress restrictions, service mesh rules

### W2: Create a Policy Instance for a Cluster

**Pre-creation Checklist**:
1. Verify cluster is registered in UCS: `hcloud UCS ShowClusterList --name=<cluster-name> --cli-region=cn-north-4`
2. Identify the appropriate policy definition: `hcloud UCS ListPolicyDefinitions --cli-region=cn-north-4`
3. Verify definition details: `hcloud UCS ShowPolicyDefinition --policydefinitionid=<id> --cli-region=cn-north-4`

```bash
# Create a cluster-level policy instance
hcloud UCS CreateClusterPolicyInstance --clusterid=<ucs-cluster-id> --constraintTemplateID=<template-id> --enforcementAction=deny --namespaces.1=default --namespaces.2=production --parameters='{"maxReplicas":"3"}' --cli-region=cn-north-4
```

**Post-creation Verification**:

```bash
# Show policy instance details
hcloud UCS ShowPolicyInstance --policyinstanceid=<instance-id-from-response> --cli-region=cn-north-4

# Check enforcement job status
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4
```

Expected: Policy instance created, enforcement job shows progress.

### W3: Create a Policy Instance for a Fleet Group

Apply policies across an entire fleet group for consistent governance:

```bash
# Create a fleet group-level policy instance
hcloud UCS CreateClusterGroupPolicyInstance --clustergroupid=<fleet-group-id> --constraintTemplateID=<template-id> --enforcementAction=warn --parameters='{"cpuLimit":"2"}' --cli-region=cn-north-4
```

**Post-creation Verification**:

```bash
# Show policy instance details
hcloud UCS ShowPolicyInstance --policyinstanceid=<instance-id> --cli-region=cn-north-4

# Check enforcement job status
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4
```

Expected: Enforcement job tracks policy deployment across fleet group.

### W4: Update a Policy Instance

```bash
# Update policy instance parameters and enforcement action
hcloud UCS UpdatePolicyInstance --policyinstanceid=<instance-id> --enforcementAction=deny --parameters='{"cpuLimit":"4"}' --cli-region=cn-north-4
```

**Note**: You cannot change the target scope (`clusterid`/`clustergroupid`) via update. To change the scope, delete the instance and create a new one.

### W5: List Policy Instances

```bash
# List all policy instances (no filter parameters available)
hcloud UCS ListPolicyInstances --cli-region=cn-north-4
```

**Note**: `ListPolicyInstances` does not support filter parameters like `--name`, `--cluster_id`, `--cluster_group_id`, `--limit`, `--offset`, or `--status`. To find specific instances, list all and filter from the response.

### W6: Enable/Disable Policy Enforcement

**Enable a policy** (starts or resumes enforcement):

```bash
# Enable on a specific cluster
hcloud UCS EnableClusterPolicy --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

# Enable on a fleet group
hcloud UCS EnableClusterGroupPolicy --clustergroupid=<fleet-group-id> --cli-region=cn-north-4

# Enable with retry (for retrying a failed enforcement)
hcloud UCS EnableClusterPolicy --clusterid=<ucs-cluster-id> --retry=true --cli-region=cn-north-4
```

**Disable a policy** (suspends enforcement):

```bash
# Disable on a specific cluster
hcloud UCS DisableClusterPolicy --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

# Disable on a fleet group
hcloud UCS DisableClusterGroupPolicy --clustergroupid=<fleet-group-id> --cli-region=cn-north-4
```

**Use Cases for Disabling**:
- Temporary maintenance windows where violations are expected
- Testing policy impact before full rollout
- Debugging compliance issues

**⚠️ Important**: Disabling a policy suspends violation checks but preserves existing violation records for audit.

### W7: Delete a Policy Instance

⚠️ **CAUTION**: Deleting a policy instance permanently removes the enforcement configuration. Violations will no longer be checked.

**Recommended: Disable Before Delete**:

```bash
# 1. Disable the policy first
hcloud UCS DisableClusterPolicy --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

# 2. Confirm no dependencies exist
hcloud UCS ListPolicyInstances --cli-region=cn-north-4

# 3. Delete the policy instance
hcloud UCS DeletePolicyInstance --policyinstanceid=<instance-id> --cli-region=cn-north-4
```

**Post-deletion Verification**:

```bash
# Verify deletion
hcloud UCS ShowPolicyInstance --policyinstanceid=<instance-id> --cli-region=cn-north-4
```

Expected: Returns 404 error (policy instance not found).

## Common Scenarios

### S1: Apply Security Baseline to All Production Clusters

```bash
# 1. Ensure fleet group exists for production clusters
hcloud UCS CreateClusterGroup --name=production-fleet --description="Production fleet" --cli-region=cn-north-4

# 2. Find the security baseline definition
hcloud UCS ListPolicyDefinitions --cli-region=cn-north-4

# 3. Create policy instance for the fleet group
hcloud UCS CreateClusterGroupPolicyInstance --clustergroupid=<fleet-group-id> --constraintTemplateID=<security-template-id> --enforcementAction=deny --cli-region=cn-north-4

# 4. Enable and verify
hcloud UCS EnableClusterGroupPolicy --clustergroupid=<fleet-group-id> --cli-region=cn-north-4
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4
```

### S2: Gradual Policy Rollout (Staging First, Then Production)

```bash
# 1. Create policy for staging cluster first
hcloud UCS CreateClusterPolicyInstance --clusterid=<staging-ucs-id> --constraintTemplateID=<template-id> --enforcementAction=warn --cli-region=cn-north-4

# 2. Enable and validate on staging
hcloud UCS EnableClusterPolicy --clusterid=<staging-ucs-id> --cli-region=cn-north-4
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4

# 3. If validation is acceptable, create for production fleet group
hcloud UCS CreateClusterGroupPolicyInstance --clustergroupid=<prod-fleet-id> --constraintTemplateID=<template-id> --enforcementAction=deny --cli-region=cn-north-4
hcloud UCS EnableClusterGroupPolicy --clustergroupid=<prod-fleet-id> --cli-region=cn-north-4
```

### S3: Replace a Policy with a Different Definition

```bash
# 1. Disable and delete old policy
hcloud UCS DisableClusterPolicy --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
hcloud UCS DeletePolicyInstance --policyinstanceid=<old-instance-id> --cli-region=cn-north-4

# 2. Find new definition
hcloud UCS ListPolicyDefinitions --cli-region=cn-north-4

# 3. Create new policy instance with new template
hcloud UCS CreateClusterPolicyInstance --clusterid=<ucs-cluster-id> --constraintTemplateID=<new-template-id> --enforcementAction=deny --cli-region=cn-north-4

# 4. Enable and verify
hcloud UCS EnableClusterPolicy --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4
```

### S4: Audit All Active Policies

```bash
# List all policy instances
hcloud UCS ListPolicyInstances --cli-region=cn-north-4

# Check enforcement job status
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4

# Review definitions being used
hcloud UCS ShowPolicyDefinition --policydefinitionid=<template-id> --cli-region=cn-north-4
```