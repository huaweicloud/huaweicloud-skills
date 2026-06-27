# IAM Policies — huawei-cloud-ecs-passwordless-login

IAM configuration required for COC (Cloud Operations Center) script operations.

## Account-Level Setup (One-Time)

COC requires a cross-service agency named `ServiceAgencyForCOC` that trusts the COC service (`op_svc_coc`). This is a one-time setup per account.

### Required Agency Roles

| Role Name | Purpose |
|-----------|---------|
| `IAM ReadOnlyAccess` | Read IAM configuration (required by COC to enumerate users/projects) |
| `RMS ReadOnlyAccess` | Read RMS resource data (required by COC to discover ECS instances) |
| `DCS UserAccess` | DCS user access (required by COC for distributed cache integration) |
| `COCServiceAgencyPolicy` | Core COC service permissions for script execution |

### Agency Trust Policy

The agency `ServiceAgencyForCOC` must trust the service account `op_svc_coc`, allowing COC to act on behalf of the user account.

## COC Script Operations (Runtime)

These are the permissions COC uses at script execution time (via the agency):

| Operation | Purpose |
|-----------|---------|
| `coc:document:list` | Check if deploy script already exists |
| `coc:document:create` | Create parameterized SSH key deploy script |
| `coc:document:delete` | Remove script during cleanup |
| `coc:instance:executeDocument` | Execute key deployment on target ECS |
| `coc:job:get` | Poll execution status |

## ECS Read-only (for IP-to-ID Resolution)

| Operation | Purpose |
|-----------|---------|
| `ecs:servers:list` | Resolve ECS IP to instance ID |

## Authorization Commands

### 1. Get Domain ID

```bash
hcloud IAM KeystoneListAuthDomains/v3
# Extract the "id" field from the first domain in the response
```

### 2. Create Agency

```bash
hcloud IAM CreateAgency/v3 \
  --agency.domain_id="<domain_id>" \
  --agency.name="ServiceAgencyForCOC" \
  --agency.trust_domain_name="op_svc_coc" \
  --agency.description="Agency for COC script execution" \
  --agency.duration="FOREVER"
```

**HTTP 409**: Agency already exists — skip creation, proceed to role binding.

### 3. Find Role IDs

```bash
hcloud IAM KeystoneListPermissions/v3 \
  --display_name="IAM ReadOnlyAccess"

hcloud IAM KeystoneListPermissions/v3 \
  --display_name="RMS ReadOnlyAccess"

hcloud IAM KeystoneListPermissions/v3 \
  --display_name="DCS UserAccess"

hcloud IAM KeystoneListPermissions/v3 \
  --display_name="COCServiceAgencyPolicy"
```

Extract the `id` field from each response.

### 4. Bind Roles to Agency

Run for each of the 4 role IDs:

```bash
hcloud IAM AssociateAgencyWithAllProjectsPermission/v3 \
  --agency_id="<agency_id>" \
  --domain_id="<domain_id>" \
  --role_id="<role_id>"
```

**HTTP 409**: Role already bound — skip and continue to the next role.

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| 401 Unauthorized | Invalid/expired AK/SK | Re-run `hcloud configure init` |
| 403 Forbidden | Insufficient IAM permissions | User must have admin or `iam:agencies:createAgency` |
| 409 Conflict (CreateAgency) | Agency already exists | Expected on repeat runs; skip creation |
| 409 Conflict (Associate) | Role already bound | Expected on repeat runs; skip binding |
| Role not found | Permission name misspelled or not available | Verify the role name against the IAM console |
