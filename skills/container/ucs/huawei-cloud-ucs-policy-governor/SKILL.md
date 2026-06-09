---
id: huawei-cloud-ucs-policy-governor
name: huawei-cloud-ucs-policy-governor
description: |
  Huawei Cloud UCS (Universal Cloud Service) policy governance and compliance management skill using hcloud CLI.
  Use this skill when the user wants to: (1) manage UCS policy instances - create/update/query/delete, (2) manage UCS policy definitions - query/list, (3) enable/disable policies on clusters or fleet groups, (4) check policy enforcement job status, (5) audit fleet compliance and review policy enforcement status.
  Trigger: user mentions "UCS policy", "UCS 策略", "UCS governance", "UCS 治理", "UCS compliance", "UCS 合规", "policy instance", "策略实例", "policy definition", "策略定义", "enable policy", "启用策略", "disable policy", "禁用策略", "fleet compliance", "舰队合规", "policy audit", "策略审计", "UCS 策略管理", "UCS 合规治理", "policy governance", "策略治理"
tags: [ucs, policy-governance, compliance, policy-instance, fleet]
---

# Huawei Cloud UCS Policy Governor

## Overview

This skill provides policy governance and compliance management capabilities for Huawei Cloud UCS (Universal Cloud Service) using the `hcloud` CLI, covering policy instance lifecycle, policy definitions, policy enforcement, and compliance auditing.

**Architecture**: hcloud CLI → UCS Service API → PolicyInstance/PolicyDefinition/PolicyJob resources

**Related Skills**:
- `huawei-cloud-ucs-cluster-onboarding-manager` - Cluster registration, lifecycle, fleet grouping, and access management

**Capabilities**:
- Create policy instances for clusters or fleet groups
- Update, query, and delete policy instances
- List and query policy definitions (templates)
- Enable and disable policies on clusters or fleet groups
- Check policy enforcement job status via ListPolicyJobs/ShowPolicyJob
- Audit fleet compliance and review policy enforcement results

**Typical Use Cases**:

- "Create a security policy instance for my production cluster"
- "Create a compliance policy for my fleet group"
- "List all available policy definitions"
- "Enable a policy on cluster 'prod-backend'"
- "Enable a policy on fleet group 'production-fleet'"
- "Disable a policy temporarily for maintenance"
- "Check policy enforcement job status"
- "Audit policy enforcement across all clusters"
- "Update a policy instance configuration"
- "Delete an obsolete policy instance"
- "Query policy definition details before applying"

## Prerequisites

### 1. hcloud CLI Requirements (MANDATORY)

- hcloud CLI installed (version >= 7.2.2)
- Run `hcloud version` to verify installation
- First-time usage: `printf "y\n" | hcloud version` to accept privacy statement

### 2. Credential Configuration

hcloud CLI supports two credential modes via environment variables, automatically detected at runtime:

**Mode A — Long-term AK/SK** (permanent access):
```bash
export HUAWEI_CLOUD_AK=<your-ak>
export HUAWEI_CLOUD_SK=<your-sk>
export HUAWEI_CLOUD_REGION=cn-north-4
```

**Mode B — Temporary AK/SK + SecurityToken** (recommended for temporary or delegated access):
```bash
export HUAWEI_CLOUD_AK=<your-temp-ak>
export HUAWEI_CLOUD_SK=<your-temp-sk>
export HUAWEI_CLOUD_SECURITY_TOKEN=<your-security-token>
export HUAWEI_CLOUD_REGION=cn-north-4
```

> When `HUAWEI_CLOUD_SECURITY_TOKEN` is present, hcloud CLI automatically uses temporary credential authentication. When only AK/SK are set, it uses long-term credential authentication.

- **Security Rules**:
  - 🚫 Never expose AK/SK/SecurityToken values in code, conversation, or commands
  - 🚫 Never use `echo $HUAWEI_CLOUD_AK` or `echo $HUAWEI_CLOUD_SK` to check credentials
  - ✅ Use environment variables: `HUAWEI_CLOUD_AK`, `HUAWEI_CLOUD_SK`, `HUAWEI_CLOUD_REGION`, `HUAWEI_CLOUD_SECURITY_TOKEN`
  - ✅ Prefer IAM users over root account for cloud operations
  - ✅ Enable MFA for sensitive operations

**⚠️ Important Security Notes**:

- Never commit credentials to version control
- Use IAM users with minimal required permissions
- Enable MFA for sensitive operations
- Rotate AK/SK regularly

### 3. IAM Permission Requirements

| API Action                                  | Permission        | Purpose                                |
| ------------------------------------------- | ----------------- | -------------------------------------- |
| `ucs:clusterPolicyInstance:create`           | Create policy     | Create cluster-level policy instances  |
| `ucs:clusterGroupPolicyInstance:create`      | Create policy     | Create fleet group-level policy instances |
| `ucs:policyInstance:update`                  | Update policy     | Modify policy instances                |
| `ucs:policyInstance:get`                     | Get policy        | View policy instance details           |
| `ucs:policyInstance:delete`                  | Delete policy     | Remove policy instances                |
| `ucs:policyInstance:list`                    | List policies     | List all policy instances              |
| `ucs:policyDefinition:list`                  | List definitions  | List available policy definitions      |
| `ucs:policyDefinition:get`                   | Get definition    | View policy definition details         |
| `ucs:clusterPolicy:enable`                   | Enable policy     | Enable cluster-level policy enforcement |
| `ucs:clusterPolicy:disable`                  | Disable policy    | Disable cluster-level policy enforcement |
| `ucs:clusterGroupPolicy:enable`              | Enable policy     | Enable fleet group-level policy enforcement |
| `ucs:clusterGroupPolicy:disable`             | Disable policy    | Disable fleet group-level policy enforcement |
| `ucs:policyJob:list`                         | List jobs         | List policy enforcement jobs           |
| `ucs:policyJob:get`                          | Get job           | View policy enforcement job details    |

See [IAM Permission Policies](references/iam-policies.md) for complete policy JSON.

**Permission Failure Handling**:

1. When any command fails due to permission errors, read `references/iam-policies.md`
2. Display the required permission list and policy JSON to the user
3. Guide the user to create a custom policy in the IAM console and grant authorization
4. Pause execution and wait for user confirmation that permissions have been granted

## Core Commands

### 1. Policy Instance Management

See [Task: Policy Management](references/task-policy-management.md) for detailed workflows.

```bash
# Create a cluster-level policy instance
hcloud UCS CreateClusterPolicyInstance --clusterid=<ucs-cluster-id> --constraintTemplateID=<template-id> --enforcementAction=deny --namespaces.1=default --namespaces.2=production --parameters='{"maxReplicas":"3"}' --cli-region=cn-north-4

# Create a fleet group-level policy instance
hcloud UCS CreateClusterGroupPolicyInstance --clustergroupid=<fleet-group-id> --constraintTemplateID=<template-id> --enforcementAction=warn --parameters='{"cpuLimit":"2"}' --cli-region=cn-north-4

# Update a policy instance
hcloud UCS UpdatePolicyInstance --policyinstanceid=<instance-id> --constraintTemplateID=<new-template-id> --enforcementAction=warn --parameters='{"cpuLimit":"4"}' --cli-region=cn-north-4

# Show policy instance details
hcloud UCS ShowPolicyInstance --policyinstanceid=<instance-id> --cli-region=cn-north-4

# Delete a policy instance
hcloud UCS DeletePolicyInstance --policyinstanceid=<instance-id> --cli-region=cn-north-4

# List all policy instances (no filter parameters available)
hcloud UCS ListPolicyInstances --cli-region=cn-north-4
```

### 2. Policy Definition Management

```bash
# List all available policy definitions (no filter parameters available)
hcloud UCS ListPolicyDefinitions --cli-region=cn-north-4

# Show policy definition details
hcloud UCS ShowPolicyDefinition --policydefinitionid=<definition-id> --cli-region=cn-north-4
```

### 3. Policy Enforcement (Enable/Disable)

```bash
# Enable a policy on a cluster
hcloud UCS EnableClusterPolicy --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

# Enable a policy on a fleet group
hcloud UCS EnableClusterGroupPolicy --clustergroupid=<fleet-group-id> --cli-region=cn-north-4

# Enable a policy on a cluster with retry
hcloud UCS EnableClusterPolicy --clusterid=<ucs-cluster-id> --retry=true --cli-region=cn-north-4

# Disable a policy on a cluster
hcloud UCS DisableClusterPolicy --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

# Disable a policy on a fleet group
hcloud UCS DisableClusterGroupPolicy --clustergroupid=<fleet-group-id> --cli-region=cn-north-4
```

### 4. Policy Enforcement Job Status

See [Task: Compliance Audit](references/task-compliance-audit.md) for detailed workflows.

```bash
# List policy enforcement jobs
hcloud UCS ListPolicyJobs --cli-region=cn-north-4

# List policy enforcement jobs filtered by kind
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4

# Show a specific policy enforcement job
hcloud UCS ShowPolicyJob --jobid=<job-id> --cli-region=cn-north-4
```

## Parameter Reference

### Common Parameters

| Parameter       | Required/Optional | Description                   | Default                              |
| --------------- | ----------------- | ----------------------------- | ------------------------------------ |
| `--cli-region`  | Required          | Huawei Cloud region ID        | Config value or `HUAWEI_CLOUD_REGION` |

### Policy Instance Parameters

| Parameter               | Required | Description              | Constraints                                  |
| ----------------------- | -------- | ------------------------ | -------------------------------------------- |
| `--clusterid`           | Yes*     | Target UCS cluster ID    | Required for CreateClusterPolicyInstance     |
| `--clustergroupid`      | Yes*     | Target fleet group ID    | Required for CreateClusterGroupPolicyInstance |
| `--constraintTemplateID`| No       | Constraint template ID   | References existing constraint template      |
| `--enforcementAction`   | No       | Enforcement action       | `warn` or `deny`                             |
| `--namespaces.[N]`      | No       | Target namespaces array  | Array index starting from 1                  |
| `--parameters`          | No       | Policy parameters object | JSON object string                           |
| `--policyinstanceid`    | Yes      | Instance ID (for get/update/delete) | Used in Show/Update/Delete operations |
| `--retry`               | No       | Retry flag for enable    | Query param for EnableClusterPolicy/EnableClusterGroupPolicy |

*Note: `--clusterid` is required for cluster-level operations (CreateClusterPolicyInstance, EnableClusterPolicy, DisableClusterPolicy). `--clustergroupid` is required for fleet group-level operations (CreateClusterGroupPolicyInstance, EnableClusterGroupPolicy, DisableClusterGroupPolicy).

### Policy Definition Parameters

| Parameter               | Required | Description              | Constraints                                  |
| ----------------------- | -------- | ------------------------ | -------------------------------------------- |
| `--policydefinitionid`  | Yes      | Definition ID            | Used in ShowPolicyDefinition                 |

### Policy Job Parameters

| Parameter               | Required | Description              | Constraints                                  |
| ----------------------- | -------- | ------------------------ | -------------------------------------------- |
| `--jobid`               | Yes      | Policy job ID            | Used in ShowPolicyJob                        |
| `--kind`                | No       | Job type filter          | Default `EnablePolicy`, used in ListPolicyJobs |

## Output Format

### CreateClusterPolicyInstance / CreateClusterGroupPolicyInstance

[to be verified — UCS responses follow k8s-style format based on verified ShowClusterList/ListPolicyDefinitions patterns]

UCS API returns Kubernetes-style objects, not flat JSON. Based on verified `ShowClusterList` and `ListPolicyDefinitions` responses, policy instance responses likely use a k8s-style object structure with `kind`, `apiVersion`, `metadata`, `spec`, and `status` fields rather than flat fields like `id`, `constraintTemplateID`, `enforcementAction`.

**Key Fields** (expected, format to be verified):
- Instance UUID: Likely in `metadata.uid` (not flat `id`)
- Constraint template reference: Likely in `spec.constraintTemplateID`
- Enforcement action: Likely in `spec.enforcementAction` (`warn` or `deny`)
- Status: Likely in `status.phase` (`Enabled`, `Disabled`, `Pending`)

### ListPolicyDefinitions

**Response Example** (verified):

```json
{
  "items": [
    {
      "kind": "ConstraintTemplate",
      "apiVersion": "templates.gatekeeper.sh/v1beta1",
      "metadata": {
        "name": "k8srequiredresources",
        "uid": "3b900254-0086-11ee-924e-0255ac1000d3",
        "creationTimestamp": "2023-06-01T14:11:41Z",
        "annotations": {
          "name-chinese": "K8sRequiredResources",
          "tag-chinese": "集群安全策略",
          "description-chinese": "..."
        }
      },
      "spec": {
        "type": "general",
        "officialTag": "ClusterSecurityPolicies",
        "level": "1",
        "targetKind": "Pod",
        "official": true,
        "description": "Requires containers to have defined resources set...",
        "constraintTemplate": {
          "kind": "ConstraintTemplate",
          "apiVersion": "templates.gatekeeper.sh/v1",
          "metadata": { "name": "k8srequiredresources" },
          "spec": {
            "crd": {
              "spec": {
                "names": { "kind": "K8sRequiredResources" },
                "validation": { "openAPIV3Schema": { "properties": {} } }
              }
            },
            "targets": [
              {
                "target": "admission.k8s.gatekeeper.sh",
                "rego": "...",
                "libs": []
              }
            ]
          }
        }
      }
    }
  ]
}
```

**Key Fields**:
- `metadata.name`: Constraint template name (used as `constraintTemplateID` in CreateClusterPolicyInstance, not flat `id`)
- `metadata.uid`: Definition UUID
- `spec.officialTag`: Policy category/tag (not flat `category`)
- `spec.level`: Severity level (not flat `severity`)
- `spec.targetKind`: Target resource type (e.g., `Pod`)
- `spec.description`: Policy description
- `spec.constraintTemplate.spec.crd.spec.validation.openAPIV3Schema.properties`: Parameter definitions (not flat `parameters` array)
- `spec.type`: Policy type (e.g., `general`)
- `spec.official`: Whether this is an official (built-in) policy

### ListPolicyJobs

**Response Example** (verified for empty result):

When no jobs exist, returns `{ "items": null }`. When populated, likely k8s-style objects based on verified UCS pattern:

```json
{
  "items": null
}
```

[to be verified for populated response — likely k8s-style objects with `kind`, `apiVersion`, `metadata`, `spec`, `status` fields]

**Key Fields** (expected, format to be verified):
- Job UUID: Likely in `metadata.uid` (not flat `jobid`)
- Job type: Likely in `spec.kind` (`EnablePolicy`, etc.)
- Job status: Likely in `status.phase` (`Success`, `Failed`, `InProgress`)

## Verification

See [Verification Method](references/verification-method.md) for step-by-step verification.

## Common Region IDs

| Region Name                    | Region ID        |
| ------------------------------ | ---------------- |
| North China - Beijing 4        | `cn-north-4`     |
| North China - Beijing 1        | `cn-north-1`     |
| East China - Shanghai 1        | `cn-east-3`      |
| East China - Shanghai 2        | `cn-east-2`      |
| South China - Guangzhou        | `cn-south-1`     |
| South China - Shenzhen         | `cn-south-4`     |
| Southwest China - Guiyang 1    | `cn-southwest-2` |
| Asia Pacific - Bangkok         | `ap-southeast-2` |
| Asia Pacific - Singapore       | `ap-southeast-1` |
| Asia Pacific - Hong Kong       | `ap-southeast-3` |
| Europe - Paris                 | `eu-west-0`      |

## Best Practices

1. **Policy Parameters**: Use `--constraintTemplateID` to reference constraint templates, not `--policy_definition_id`
2. **Fleet-Level Policies**: Apply policies to fleet groups using `CreateClusterGroupPolicyInstance` for consistent enforcement
3. **Gradual Rollout**: Enable policies on staging clusters first using `EnableClusterPolicy`, then roll out to production fleet groups using `EnableClusterGroupPolicy`
4. **Compliance Monitoring**: Use `ListPolicyJobs` and `ShowPolicyJob` to monitor enforcement task status
5. **Enforcement Action**: Choose `warn` for initial rollout (violations reported but not blocked), then switch to `deny` for strict enforcement
6. **Disable Before Delete**: Disable a policy using `DisableClusterPolicy`/`DisableClusterGroupPolicy` before deleting to prevent sudden enforcement gaps
7. **Namespace Scoping**: Use `--namespaces.[N]` to scope policy enforcement to specific namespaces

## Reference Documents

| Document                                               | Description                              |
| ------------------------------------------------------ | ---------------------------------------- |
| [UCS Policy API Guide](references/ucs-policy-api-guide.md) | hcloud UCS policy API reference     |
| [IAM Permission Policies](references/iam-policies.md)  | Required permissions and policy JSON     |
| [Verification Method](references/verification-method.md) | Step-by-step verification              |
| [Common Pitfalls](references/common-pitfalls.md)       | Troubleshooting guides                   |
| [Task: Policy Management](references/task-policy-management.md) | Policy instance CRUD workflows |
| [Task: Compliance Audit](references/task-compliance-audit.md) | Compliance and audit workflows |

## Notes

- **Policy deletion is irreversible** — the enforcement configuration is permanently removed
- **Disabling a policy suspends enforcement** — violations are not checked while the policy is disabled
- **Fleet group policies apply to all member clusters** — ensure group membership is correct before applying
- **AK/SK must never be hardcoded** — credentials should only be obtained via environment variables
- **hcloud CLI is the only supported method** — all operations use `hcloud UCS <Operation>` format
- **CreatePolicyInstance is TWO separate operations** — use `CreateClusterPolicyInstance` for cluster-level and `CreateClusterGroupPolicyInstance` for fleet group-level policies
- **Enable/Disable are scope-specific** — use `EnableClusterPolicy`/`DisableClusterPolicy` for clusters and `EnableClusterGroupPolicy`/`DisableClusterGroupPolicy` for fleet groups
- **GetPolicyAssignment does not exist** — use `ListPolicyJobs` and `ShowPolicyJob` to check enforcement task status
- **ListPolicyInstances and ListPolicyDefinitions have no filter parameters** — only `--cli-region` is available

## Common Pitfalls

See [Common Pitfalls & Solutions](references/common-pitfalls.md) for detailed troubleshooting guides.

**Quick Reference**:

| Pitfall                     | Symptom                         | Quick Fix                                    |
| --------------------------- | ------------------------------- | -------------------------------------------- |
| Wrong create operation      | Create fails with wrong scope   | Use CreateClusterPolicyInstance for clusters, CreateClusterGroupPolicyInstance for fleet groups |
| Constraint template not found | Create fails                  | Use `ListPolicyDefinitions` to find valid template ID |
| Cluster not registered      | EnableClusterPolicy fails       | Register cluster with `huawei-cloud-ucs-cluster-onboarding-manager` |
| Fleet group empty           | Policy not enforced anywhere    | Add clusters to fleet group first            |
| Wrong param names           | Command fails (underscore vs camelCase) | Use `--policyinstanceid` not `--instance_id`, `--clusterid` not `--cluster_id` |
| GetPolicyAssignment used    | Operation not found             | Use `ListPolicyJobs`/`ShowPolicyJob` instead |
| List filter params used     | Unexpected behavior             | ListPolicyInstances/ListPolicyDefinitions have no filter params, only --cli-region |