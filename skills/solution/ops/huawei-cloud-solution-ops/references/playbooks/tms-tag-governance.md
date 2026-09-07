# TMS Tag Governance

Use this playbook when the user asks for tag readiness, tag coverage, or governance/cost-allocation cleanup.

## Inputs

- Target region and resource type list.
- Required tag keys, allowed values, and owner/cost-center taxonomy if available.
- Optional target resource IDs for resource tag readback.

## Read-Only Flow

1. Run TMS `ListProviders` to confirm which cloud services and resource types are supported by TMS.
2. Run TMS `ListPredefineTags`, `ListTagKeys`, and `ListTagValues` to inspect the current taxonomy.
3. Run TMS `ListResource` with explicit `resource_types` and `tags` when finding resources by tag.
4. Run TMS `ShowResourceTag` for specific resources before recommending any tag change.
5. Run `ShowTagQuota` when failures may be caused by quota or per-resource tag limits.

## Guardrails

- Tag create/update/delete operations can affect automation, access policy, reporting, and cost allocation.
- Do not write tags from this playbook; prepare a separate guarded change plan after owner confirmation.
- Avoid assuming that every service supports every TMS query shape.

## Promotion Gaps

- Collect live read-only smoke evidence for `ListProviders`, `ListPredefineTags`, and one target-scoped tag query.
- Add service-specific resource type examples after live validation.
