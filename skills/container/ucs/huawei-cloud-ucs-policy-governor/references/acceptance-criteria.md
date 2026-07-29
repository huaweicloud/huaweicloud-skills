# Acceptance Criteria

Acceptance standards and test checklist for this skill.

## 1. Environment Preparation

- [ ] hcloud CLI is installed (`hcloud --version` returns a version number)
- [ ] AK/SK credentials are configured (`hcloud UCS ListPolicyDefinitions --cli-region=cn-north-4` succeeds)
- [ ] Target cluster is registered in UCS and status is `Available`

## 2. Policy Definition Query

- [ ] `ListPolicyDefinitions --cli-region=cn-north-4` returns policy definition list
- [ ] Each definition includes `metadata.name`, `spec.type`, `spec.description`

## 3. Policy Instance Management

- [ ] `CreateClusterPolicyInstance --clusterid=<id> --constraintTemplateID=<template> --enforcementAction=warn` succeeds (requires policy center enabled)
- [ ] `ListPolicyInstances --cli-region=cn-north-4` returns created instance
- [ ] `ShowPolicyInstance --policyinstanceid=<id>` returns instance details
- [ ] `UpdatePolicyInstance --policyinstanceid=<id> --enforcementAction=deny` updates enforcement action (requires user confirmation)
- [ ] `DeletePolicyInstance --policyinstanceid=<id>` removes instance (⚠️ irreversible, requires user confirmation)

## 4. Policy Center Management

- [ ] `EnableClusterPolicy --clusterid=<id>` enables policy center on cluster
- [ ] `DisableClusterPolicy --clusterid=<id>` disables policy center (requires user confirmation)
- [ ] `EnableClusterGroupPolicy --clustergroupid=<id>` enables fleet-level policy
- [ ] `DisableClusterGroupPolicy --clustergroupid=<id>` disables fleet-level policy (requires user confirmation)

## 5. Compliance Audit

- [ ] `ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4` returns job list
- [ ] `ShowPolicyJob --jobid=<id>` returns job details

## 6. Error Handling

- [ ] Operations on cluster with `Failed` status return `UCS.00150001` error
- [ ] `ShowPolicyInstance` with invalid ID returns `UCS.00000016` error
- [ ] `DisableClusterPolicy` on cluster without policy center returns `UCS.00150005` error

## 7. Parameter Confirmation

- [ ] SKILL.md includes `## 参数确认` section with risk levels for all write operations
- [ ] DeletePolicyInstance marked as High risk
- [ ] UpdatePolicyInstance, DisableClusterPolicy, DisableClusterGroupPolicy marked as Medium risk
