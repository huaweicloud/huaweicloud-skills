# RMS Config Governance

Use this playbook when the user asks for resource inventory, compliance status, policy assignment, or aggregator readiness through RMS.

## Inputs

- Domain ID is required for most RMS account-wide queries.
- Optional provider, resource type, resource ID, aggregator ID, and policy assignment ID.
- Compliance reporting goal and account/organization scope.

## Read-Only Flow

1. Run RMS `ListBuiltInPolicyDefinitions` to inspect available governance rules.
2. Run RMS `ListProviders` and `ListAllResources` with explicit domain scope to establish inventory coverage.
3. Run RMS `ListResources` when narrowing to one provider/type.
4. Run RMS `ShowResourceById` for target-scoped resource readback.
5. Run RMS `ListPolicyStatesByDomainId` or assignment-scoped policy-state queries when checking compliance.
6. Run `ListConfigurationAggregators` when organization or multi-account aggregation is in scope.

## Guardrails

- Do not create, update, or delete policy assignments, aggregators, or remediation settings from this playbook.
- Compliance data can be stale or partial; always state query scope, account scope, and data timestamp when summarizing.
- Avoid broad raw dumps of full inventory unless the user confirms output scope.

## Promotion Gaps

- Collect live read-only smoke evidence for one inventory query, one policy query, and one target-scoped resource query.
- Document domain ID discovery and organization-scope prerequisites.
