# Config Governance Readiness

Use this playbook when the user asks about Config resource recorder, resource inventory, compliance packs, or advanced governance queries.

## Inputs

- Domain ID for account-wide Config queries.
- Optional provider, resource type, resource ID, conformance pack ID, and policy assignment ID.
- Whether the user cares about a single account or organization-level governance.

## Read-Only Flow

1. Run Config `ListBuiltInPolicyDefinitions` and `ListProviders` to understand supported governance coverage.
2. Run Config `ListAllResources` and `ListResources` to inspect inventory by account and type.
3. Run Config `ShowResourceById` for target-scoped readback before recommending remediation.
4. Run Config `ListPolicyStatesByDomainId` to inspect current compliance posture.
5. Run Config `ListConformancePacks` and conformance-pack compliance queries when package-level governance is in scope.
6. Run `ListConfigurationAggregators` when cross-account inventory or compliance aggregation is needed.

## Guardrails

- Do not mutate recorder, policy, remediation, conformance pack, or aggregator settings from this playbook.
- Governance output can be broad and sensitive; summarize by counts, policy names, and high-level findings unless raw details are requested.
- Mention domain, region, and organization scope for every conclusion.

## Promotion Gaps

- Collect live read-only smoke evidence for resource inventory, policy compliance, and conformance pack queries.
- Confirm overlap and naming differences between Config and RMS before any curated registry promotion.
