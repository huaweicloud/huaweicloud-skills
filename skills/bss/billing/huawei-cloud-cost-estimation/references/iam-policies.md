# IAM least privilege

IAM actions vary by account type, site, and service version; before relying on them, confirm against API Explorer
and runtime `hcloud <Service> <Operation> --help`. On insufficient permission, report back so the user can grant
the missing permission: never work around a failed query with a write permission, and never retry with self-granted privileges.

## Price inquiry (read-only)

| Level | Operation | Purpose |
| --- | --- | --- |
| BSS price inquiry | `ListRateOnPeriodDetail`, `ListOnDemandResourceRatings` | Obtain a period or on-demand quote |
| BSS dictionary | `ListServiceTypes`, `ListResourceTypes`, `ListServiceResources`, `ListResourceSpecs`, `ListMeasureUnits`, `ListConversions` | Resolve service, resource, spec, and measure |
| Product helper | `ECS/NovaListAvailabilityZones` | When the user specifies an AZ |
| Identity scope | `IAM/KeystoneListAuthProjects`, `IAM/KeystoneListProjects` | Resolve accessible projects |

The usual price-inquiry policy is `bss:order:view` plus the corresponding read-only BSS/IAM actions.

## Provisioning (write)

Write permission follows the service that owns the allowlisted operation (for example `ECS/CreateServers` needs an ECS
write action), while dependency lookups need only the read-only actions of the corresponding service. This file does not enumerate
write actions per service: take the action named in the current 403 error message and API Explorer as authoritative, and report back so an administrator can grant it.

## Partner price inquiry on behalf of a customer

Use the token obtained from the customer's authorization to call `KeystoneListAuthProjects`, resolve the customer
`project_id` for the target region, then run the price inquiry. Stop if authorization fails; do not widen the scope.

## Permission and throttling failure handling

| Symptom | Handling |
| --- | --- |
| `403 Forbidden` / `CBC.0151` | Record the operation and account scope, then recommend granting the corresponding action (for price inquiry, read-only only) |
| `429` | Wait 2 seconds and retry once; stop if it still fails |

Parameter errors (such as `CBC.0100` / `CBC.99006006` / `CBC.99006055`) are covered in the trap section of
`pricing/commands.md`. Historical bills, balance, and reconciliation are out of scope for this skill; use
Cost Center or a dedicated read-only billing skill.
