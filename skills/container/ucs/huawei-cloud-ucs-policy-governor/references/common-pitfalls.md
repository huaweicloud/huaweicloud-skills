# Common Pitfalls & Solutions

This document contains detailed troubleshooting guides for common issues encountered when using the Huawei Cloud UCS Policy Governor skill.

## Pitfall 1: Policy Definition/Template ID Not Found

**Symptom**: `CreateClusterPolicyInstance` or `CreateClusterGroupPolicyInstance` fails with `PolicyDefinitionNotFound` error

**Root Cause**: Using an invalid or non-existent constraint template ID

**Solution**: Always list available definitions before creating a policy instance:

```bash
# List all available policy definitions
hcloud UCS ListPolicyDefinitions --cli-region=cn-north-4

# Show specific definition details to verify it exists
hcloud UCS ShowPolicyDefinition --policydefinitionid=<definition-id> --cli-region=cn-north-4
```

Use the `id` field from `ListPolicyDefinitions` response as the `--constraintTemplateID` parameter.

## Pitfall 2: Using Wrong Create Operation for the Scope

**Symptom**: `CreatePolicyInstance` fails or creates policy at wrong scope level

**Root Cause**: UCS has TWO separate create operations: `CreateClusterPolicyInstance` (for cluster-level) and `CreateClusterGroupPolicyInstance` (for fleet group-level). Using the wrong one or using a non-existent `CreatePolicyInstance` causes errors.

**Solution**: Choose the correct operation based on your target scope:

```bash
# ✅ CORRECT - Target a specific cluster
hcloud UCS CreateClusterPolicyInstance --clusterid=<ucs-cluster-id> --constraintTemplateID=<template-id> --enforcementAction=deny --cli-region=cn-north-4

# ✅ CORRECT - Target a fleet group
hcloud UCS CreateClusterGroupPolicyInstance --clustergroupid=<fleet-group-id> --constraintTemplateID=<template-id> --enforcementAction=warn --cli-region=cn-north-4

# ❌ WRONG - CreatePolicyInstance does not exist
hcloud UCS CreatePolicyInstance --name=my-policy --policy_definition_id=<def-id> --cli-region=cn-north-4
```

## Pitfall 3: Cluster Not Registered in UCS

**Symptom**: `EnableClusterPolicy` fails with `ClusterNotRegistered` error

**Root Cause**: The target cluster has not been registered to UCS, or the cluster ID used is a CCE cluster ID instead of a UCS cluster ID

**Solution**:

1. Register the cluster to UCS first (use `huawei-cloud-ucs-cluster-onboarding-manager` skill):
```bash
hcloud UCS RegisterCluster --name=my-cluster --cluster_type=CCE --cluster_id=<cce-cluster-id> --cli-region=cn-north-4
```

2. Use the UCS-assigned cluster ID (not the CCE cluster ID) for policy operations:
```bash
# ✅ CORRECT - Use UCS cluster ID
hcloud UCS EnableClusterPolicy --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

# ❌ WRONG - Using CCE cluster ID
hcloud UCS EnableClusterPolicy --clusterid=<cce-cluster-id> --cli-region=cn-north-4
```

## Pitfall 4: Fleet Group Has No Member Clusters

**Symptom**: Policy created for a fleet group but enforcement shows no compliance results

**Root Cause**: The fleet group has no member clusters assigned. Policy governance applies to clusters that are part of the fleet group.

**Solution**: Ensure clusters are registered and assigned to the fleet group before applying group-level policies. Use the `huawei-cloud-ucs-cluster-onboarding-manager` skill to register clusters and create fleet groups.

## Pitfall 5: Cannot Change Target Scope After Creation

**Symptom**: Attempting to change `clusterid` or `clustergroupid` via update fails

**Root Cause**: Target scope (`clusterid`/`clustergroupid`) is immutable after creation

**Solution**: To change the scope:
1. Delete the existing policy instance
2. Create a new policy instance with the desired scope

```bash
# 1. Delete old instance
hcloud UCS DeletePolicyInstance --policyinstanceid=<old-instance-id> --cli-region=cn-north-4

# 2. Create new instance with different scope
hcloud UCS CreateClusterGroupPolicyInstance --clustergroupid=<new-group-id> --constraintTemplateID=<template-id> --cli-region=cn-north-4
```

## Pitfall 6: Policy Enforcement on Deregistered Cluster

**Symptom**: Policy enforcement status shows errors or `Unavailable` for a cluster

**Root Cause**: The cluster was deregistered from UCS after the policy instance was created. Policy governance requires the cluster to remain registered.

**Solution**:
- Re-register the cluster to restore policy enforcement
- Or delete the policy instance if the cluster should no longer be managed

## Pitfall 7: Disabling Policy Does Not Remove Violations

**Symptom**: Compliance check still shows violations even after disabling the policy

**Root Cause**: Disabling a policy suspends enforcement (no new checks are performed), but existing violation records are preserved for audit purposes

**Solution**: This is expected behavior. Violation records from previous enforcement periods are retained. To remove them:
1. Fix the violations in the cluster
2. Re-enable the policy to trigger a fresh enforcement job
3. If no violations remain, the job status will show `Success`

## Pitfall 8: Policy Instance Quota Exceeded

**Symptom**: `CreateClusterPolicyInstance` returns `403 Quota limit exceeded`

**Root Cause**: UCS has limits on the number of policy instances that can be created

**Solution**: Check quotas (using `huawei-cloud-ucs-cluster-onboarding-manager` skill):

```bash
hcloud UCS ShowQuota --cli-region=cn-north-4
```

If quota is exceeded:
1. Delete unused or obsolete policy instances
2. Request a quota increase through Huawei Cloud support

## Pitfall 9: Compliance Check Data Appears Stale

**Symptom**: Enforcement job data shows old timestamps or violation data that seems outdated

**Root Cause**: Enforcement jobs are performed periodically, not continuously. The data may be from the last job execution cycle.

**Solution**: Trigger a fresh enforcement check by:

```bash
# Re-trigger enforcement
hcloud UCS DisableClusterPolicy --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
hcloud UCS EnableClusterPolicy --clusterid=<ucs-cluster-id> --retry=true --cli-region=cn-north-4

# Check new job status
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4
```

## Pitfall 10: Policy Instance ID vs Definition ID Confusion

**Symptom**: Using wrong ID type for operations (e.g., using definition ID where instance ID is expected)

**Root Cause**: Policy instances and policy definitions have different UUIDs. Using one type of ID for operations that expect the other type causes errors.

**Solution**: Keep track of both IDs separately:
- `constraintTemplateID`: Used in `CreateClusterPolicyInstance`, `CreateClusterGroupPolicyInstance`, and `UpdatePolicyInstance`
- `policyinstanceid`: Used in `ShowPolicyInstance`, `UpdatePolicyInstance`, `DeletePolicyInstance`
- `policydefinitionid`: Used in `ShowPolicyDefinition`

```bash
# ✅ CORRECT - Use policyinstanceid for instance operations
hcloud UCS ShowPolicyInstance --policyinstanceid=<instance-id> --cli-region=cn-north-4

# ✅ CORRECT - Use policydefinitionid for definition operations
hcloud UCS ShowPolicyDefinition --policydefinitionid=<definition-id> --cli-region=cn-north-4

# ❌ WRONG - Using definition ID for instance operation
hcloud UCS ShowPolicyInstance --policyinstanceid=<definition-id> --cli-region=cn-north-4
```

## Pitfall 11: CreatePolicyInstance vs Scope-Specific Operations

**Symptom**: Command fails with "operation not found" or unexpected parameter errors when using `CreatePolicyInstance`

**Root Cause**: `CreatePolicyInstance` is NOT a single UCS API operation. It is TWO separate operations: `CreateClusterPolicyInstance` (for cluster-level) and `CreateClusterGroupPolicyInstance` (for fleet group-level). Using `CreatePolicyInstance` directly will fail.

**Solution**: Always use the scope-specific operation:

```bash
# ✅ CORRECT - Cluster-level
hcloud UCS CreateClusterPolicyInstance --clusterid=<ucs-cluster-id> --constraintTemplateID=<template-id> --cli-region=cn-north-4

# ✅ CORRECT - Fleet group-level
hcloud UCS CreateClusterGroupPolicyInstance --clustergroupid=<fleet-group-id> --constraintTemplateID=<template-id> --cli-region=cn-north-4

# ❌ WRONG - This operation does not exist
hcloud UCS CreatePolicyInstance --name=my-policy --policy_definition_id=<def-id> --cluster_id=<ucs-id> --cli-region=cn-north-4
```

## Pitfall 12: --policyinstanceid vs --instance_id (Naming Convention)

**Symptom**: Command fails with "parameter not found" error when using `--instance_id`

**Root Cause**: UCS API uses concatenated camelCase parameter names without underscores. The correct parameter is `--policyinstanceid`, not `--instance_id`.

**Solution**: Use UCS parameter naming convention:

```bash
# ✅ CORRECT - UCS uses no underscore, concatenated
hcloud UCS ShowPolicyInstance --policyinstanceid=<instance-id> --cli-region=cn-north-4
hcloud UCS UpdatePolicyInstance --policyinstanceid=<instance-id> --cli-region=cn-north-4
hcloud UCS DeletePolicyInstance --policyinstanceid=<instance-id> --cli-region=cn-north-4

# ❌ WRONG - Underscore style is not used by UCS
hcloud UCS ShowPolicyInstance --instance_id=<instance-id> --cli-region=cn-north-4
```

Same rule applies to other parameters:
- `--policydefinitionid` (not `--definition_id`)
- `--clusterid` (not `--cluster_id`)
- `--clustergroupid` (not `--cluster_group_id`)
- `--constraintTemplateID` (not `--policy_definition_id`)

## Pitfall 13: --constraintTemplateID vs --policy_definition_id

**Symptom**: Command fails with "parameter not found" when using `--policy_definition_id`

**Root Cause**: The UCS API uses `--constraintTemplateID` as the parameter name for referencing constraint templates, not `--policy_definition_id`.

**Solution**: Always use `--constraintTemplateID`:

```bash
# ✅ CORRECT - Use constraintTemplateID
hcloud UCS CreateClusterPolicyInstance --clusterid=<ucs-cluster-id> --constraintTemplateID=<template-id> --enforcementAction=deny --cli-region=cn-north-4

# ❌ WRONG - policy_definition_id is not a UCS parameter
hcloud UCS CreateClusterPolicyInstance --clusterid=<ucs-cluster-id> --policy_definition_id=<def-id> --cli-region=cn-north-4
```

## Pitfall 14: GetPolicyAssignment Does Not Exist

**Symptom**: Command fails with "operation not found" when using `GetPolicyAssignment`

**Root Cause**: `GetPolicyAssignment` is NOT a UCS API operation. It does not exist in the hcloud UCS command set.

**Solution**: Use `ListPolicyJobs` and `ShowPolicyJob` to check policy enforcement status:

```bash
# ✅ CORRECT - List enforcement jobs
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4

# ✅ CORRECT - Show specific job details
hcloud UCS ShowPolicyJob --jobid=<job-id> --cli-region=cn-north-4

# ❌ WRONG - This operation does not exist
hcloud UCS GetPolicyAssignment --instance_id=<instance-id> --cli-region=cn-north-4
```

## Pitfall 15: ListPolicyInstances/ListPolicyDefinitions Filter Parameters Don't Exist

**Symptom**: Command runs but filter parameters like `--name`, `--cluster_id`, `--category`, `--limit`, `--offset` have no effect or cause unexpected behavior

**Root Cause**: `ListPolicyInstances` and `ListPolicyDefinitions` only accept `--cli-region`. They do NOT support any filter parameters.

**Solution**: List all instances/definitions and filter from the response manually:

```bash
# ✅ CORRECT - Only --cli-region is available
hcloud UCS ListPolicyInstances --cli-region=cn-north-4
hcloud UCS ListPolicyDefinitions --cli-region=cn-north-4

# ❌ WRONG - These filter parameters do not exist
hcloud UCS ListPolicyInstances --name=security --cluster_id=<id> --limit=20 --offset=0 --cli-region=cn-north-4
hcloud UCS ListPolicyDefinitions --category=security --limit=50 --offset=0 --cli-region=cn-north-4
```

## Pitfall 16: Enable/Disable Must Use Scope-Specific Operations

**Symptom**: `EnablePolicy` or `DisablePolicy` fails with "operation not found" error

**Root Cause**: Enable and Disable are TWO separate scope-specific operations each: `EnableClusterPolicy`/`EnableClusterGroupPolicy` and `DisableClusterPolicy`/`DisableClusterGroupPolicy`.

**Solution**: Use the correct scope-specific operation:

```bash
# ✅ CORRECT - Enable on cluster
hcloud UCS EnableClusterPolicy --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

# ✅ CORRECT - Enable on fleet group
hcloud UCS EnableClusterGroupPolicy --clustergroupid=<fleet-group-id> --cli-region=cn-north-4

# ✅ CORRECT - Disable on cluster
hcloud UCS DisableClusterPolicy --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

# ✅ CORRECT - Disable on fleet group
hcloud UCS DisableClusterGroupPolicy --clustergroupid=<fleet-group-id> --cli-region=cn-north-4

# ❌ WRONG - These single operations do not exist
hcloud UCS EnablePolicy --instance_id=<id> --cluster_id=<id> --cli-region=cn-north-4
hcloud UCS DisablePolicy --instance_id=<id> --cli-region=cn-north-4
```

## Common Error Response Reference

| Error Code          | HTTP Status | Description                  | Recommended Action                    |
| ------------------- | ----------- | ---------------------------- | ------------------------------------- |
| `UCS.001`           | 400         | Invalid parameter            | Check parameter format and naming     |
| `UCS.002`           | 404         | Resource not found           | Verify resource ID exists             |
| `UCS.003`           | 409         | Resource already exists      | Use Show operation to check           |
| `UCS.004`           | 403         | Permission denied            | Check IAM policies                    |
| `UCS.005`           | 403         | Quota exceeded               | Delete unused instances or request    |
| `UCS.006`           | 401         | Authentication failed        | Regenerate or check credentials       |
| `UCS.007`           | 429         | Too many requests            | Add delay, reduce request rate        |
| `UCS.010`           | 400         | Cluster not registered       | Register cluster first                |
| `UCS.011`           | 400         | Group has no members         | Add clusters to fleet group first     |