# Common Pitfalls & Solutions

This document contains detailed troubleshooting guides for common issues encountered when using the Huawei Cloud SWR Enterprise Instance skill.

## Pitfall 1: Instance Creation Requires Existing VPC and Subnet

**Symptom**: `CreateInstance` fails with VPC/subnet not found error

**Root Cause**: Enterprise instances must be deployed within an existing VPC and subnet. The VPC/subnet must exist before creating the instance.

**Solution**: Verify VPC and subnet exist before creating an instance:

```bash
# Verify VPC exists (use VPC CLI or console)
# Verify subnet exists within the VPC

# Then create instance with valid VPC/subnet IDs
hcloud SWR CreateInstance --name=my-instance --spec=swr.ee.basic --charge_mode=postPaid --vpc_id=<valid-vpc-id> --subnet_id=<valid-subnet-id> --enterprise_project_id=0 --cli-region=cn-north-4
```

## Pitfall 2: Instance Not Ready for Operations

**Symptom**: Instance-related operations (namespace creation, credential creation) fail with errors

**Root Cause**: Instance operations cannot be performed while the instance is in `Creating` or `Initial` status. Only `Running` instances are ready for use.

**Solution**: Wait for the instance to reach `Running` status:

```bash
# Check instance status
hcloud SWR ListInstance --cli-region=cn-north-4

# Or check specific instance
hcloud SWR ShowInstance --instance_id=<instance-id> --cli-region=cn-north-4

# Wait until status is "Running" before proceeding
```

**Instance Status Flow**: `Initial` → `Creating` → `Running` (or `Unavailable` if creation fails)

## Pitfall 3: Invalid Instance Name Format

**Symptom**: `CreateInstance` returns error `400 Bad Request` or name validation error

**Root Cause**: Instance name violates naming rules

**Naming Rules**:
- Start with lowercase letter
- Followed by lowercase letters, digits, or hyphens (`-`)
- No consecutive hyphens (`--` is invalid)
- Cannot end with hyphen (`-`)
- Length: 3-48 characters

**Common Mistakes**:
- ❌ `MyInstance` — starts with uppercase
- ❌ `my--instance` — consecutive hyphens
- ❌ `my-instance-` — ends with hyphen
- ❌ `ab` — too short (minimum 3 chars)
- ❌ Very long names > 48 chars

**Valid Examples**: `my-instance`, `prod-registry01`, `dev-team-app`

## Pitfall 4: Pagination Offset Must Be Multiple of Limit

**Symptom**: `ListInstanceNamespaces`, `ListInstanceRegistries`, `ListInstanceRepositories`, or `ListInstanceArtifacts` pagination returns errors or unexpected results

**Root Cause**: For instance-specific list operations (namespace, registry, repository, artifact), the `offset` parameter must be 0 or a multiple of `limit`. This is different from the basic SWR pagination which allows any offset value.

**Solution**: Always use offset values that are multiples of limit:

```bash
# ✅ CORRECT - offset=0, limit=20 (0 is multiple of 20)
hcloud SWR ListInstanceNamespaces --instance_id=<id> --limit=20 --offset=0 --cli-region=cn-north-4

# ✅ CORRECT - offset=20, limit=20 (20 is multiple of 20)
hcloud SWR ListInstanceNamespaces --instance_id=<id> --limit=20 --offset=20 --cli-region=cn-north-4

# ✅ CORRECT - offset=40, limit=20 (40 is multiple of 20)
hcloud SWR ListInstanceNamespaces --instance_id=<id> --limit=20 --offset=40 --cli-region=cn-north-4

# ❌ WRONG - offset=10, limit=20 (10 is NOT multiple of 20)
hcloud SWR ListInstanceNamespaces --instance_id=<id> --limit=20 --offset=10 --cli-region=cn-north-4
```

⚠️ **Note**: `ListInstance` and `ListInstanceLtCredentials` use standard offset/limit pagination (offset does not need to be multiple of limit). Only instance namespace, registry, repository, and artifact lists require the offset-to-be-multiple constraint.

## Pitfall 5: Namespace metadata.public Required for Update

**Symptom**: `UpdateInstanceNamespace` fails or only changes visibility when other settings were intended

**Root Cause**: `--metadata.public` is a required parameter for `UpdateInstanceNamespace`, even if you only want to change `auto_scan`, `prevent_vul`, or `severity` settings

**Solution**: Always include `--metadata.public` in update commands:

```bash
# ✅ CORRECT - Include metadata.public even when changing only scan settings
hcloud SWR UpdateInstanceNamespace --instance_id=<id> --namespace_name=group-dev --metadata.public=false --metadata.auto_scan=true --cli-region=cn-north-4

# ❌ WRONG - Missing metadata.public
hcloud SWR UpdateInstanceNamespace --instance_id=<id> --namespace_name=group-dev --metadata.auto_scan=true --cli-region=cn-north-4
```

## Pitfall 6: Registry Instance ID Appears Twice for swr-pro-internal

**Symptom**: `CreateInstanceRegistry` with type `swr-pro-internal` fails with missing parameters

**Root Cause**: When creating a registry of type `swr-pro-internal`, `--instance_id` appears both as a path parameter (the source instance) and a body parameter (the target instance ID). Both must be provided.

**Solution**: Provide both instance IDs when creating `swr-pro-internal` registry:

```bash
# ✅ CORRECT - Both instance_id values provided
hcloud SWR CreateInstanceRegistry --instance_id=<source-instance-id> --name=target-registry --type=swr-pro-internal --url=<target-url> --credential.type=basic --credential.access_key=<key> --credential.access_secret=<secret> --insecure=false --instance_id=<target-instance-id> --project_id=<target-project-id> --region_id=cn-east-3 --cli-region=cn-north-4

# ❌ WRONG - Missing target instance_id body parameter
hcloud SWR CreateInstanceRegistry --instance_id=<source-instance-id> --name=target-registry --type=swr-pro-internal --url=<target-url> --credential.type=basic --credential.access_key=<key> --credential.access_secret=<secret> --insecure=false --cli-region=cn-north-4
```

## Pitfall 7: Deleting Instance Removes ALL Data Permanently

**Symptom**: All namespaces, repositories, artifacts, and configurations disappear after instance deletion

**Root Cause**: `DeleteInstance` removes the entire instance and all associated data permanently

**Solution**: Before deleting an instance, always:

1. Confirm with the user that they understand ALL data will be permanently deleted
2. Consider using `--delete_obs=true` and `--delete_dns=true` for complete cleanup
3. If any data needs to be preserved, sync/migrate it to another instance first

```bash
# Delete with OBS bucket and DNS cleanup
hcloud SWR DeleteInstance --instance_id=<id> --delete_obs=true --delete_dns=true --cli-region=cn-north-4
```

## Pitfall 8: Default Domain Cannot Be Deleted

**Symptom**: `DeleteDomainName` fails when attempting to delete the default domain

**Root Cause**: The SWR-assigned default domain (e.g., `xxx.cn-north-4.myhuaweicloud.com`) cannot be deleted. Only custom domains added via `AddDomainName` can be removed.

**Solution**: Only delete custom domains. Leave the default domain intact:

```bash
# ✅ CORRECT - Delete only custom domain
hcloud SWR DeleteDomainName --instance_id=<id> --domainname_id=<custom-domain-id> --cli-region=cn-north-4

# ❌ WRONG - Attempting to delete default domain will fail
```

## Pitfall 9: Public Access Whitelist is Full Replacement

**Symptom**: Previous whitelist entries disappear after updating the whitelist

**Root Cause**: `UpdateInstanceEndpointPolicy` performs a full replacement of the IP whitelist, not an incremental add. All existing entries are replaced by the new ones provided.

**Solution**: When adding new IPs, include ALL existing IPs plus the new ones:

```bash
# ✅ CORRECT - Include all existing IPs plus new ones
hcloud SWR UpdateInstanceEndpointPolicy --instance_id=<id> --ip_list.1.ip=10.0.0.0/8 --ip_list.1.description="Existing: Internal" --ip_list.2.ip=192.168.0.0/16 --ip_list.2.description="Existing: VPN" --ip_list.3.ip=172.16.0.0/12 --ip_list.3.description="New: Docker network" --cli-region=cn-north-4

# ❌ WRONG - Only providing new entries (existing entries will be lost)
hcloud SWR UpdateInstanceEndpointPolicy --instance_id=<id> --ip_list.1.ip=172.16.0.0/12 --ip_list.1.description="New: Docker network" --cli-region=cn-north-4
```

**Best Practice**: Before updating the whitelist, check current entries with `ShowInstanceEndpointPolicy` and include all existing entries in the update command.

## Pitfall 10: Artifact Reference Uses Digest, Not Tag Name

**Symptom**: `ShowInstanceArtifact`, `DeleteInstanceArtifact`, `StartManualScanning` fail with "not found" error

**Root Cause**: These operations use `--reference` which must be the artifact's SHA256 digest (e.g., `sha256:abc123...`), NOT the tag name (e.g., `v1.0`)

**Solution**: First obtain the digest from `ListInstanceArtifacts`, then use it for operations:

```bash
# 1. List artifacts to find the digest
hcloud SWR ListInstanceArtifacts --instance_id=<id> --namespace_name=group-dev --repository_name=my-app --cli-region=cn-north-4

# 2. Use the digest value for operations
hcloud SWR ShowInstanceArtifact --instance_id=<id> --namespace_name=group-dev --repository_name=my-app --reference=sha256:abc123def456... --cli-region=cn-north-4
```

## Pitfall 11: CreateInstanceEndpointPolicy Status Constraints

**Symptom**: `CreateInstanceEndpointPolicy` fails when trying to enable or disable public access

**Root Cause**: The enable/disable operation has status constraints:
- Can only enable (`--enable=true`) when status is `Disable` or `EnableFailed`
- Can only disable (`--enable=false`) when status is `Enable` or `DisableFailed`

**Solution**: Check current status before changing:

```bash
# Check current public access status
hcloud SWR ShowInstanceEndpointPolicy --instance_id=<id> --cli-region=cn-north-4

# Then enable or disable based on current status
hcloud SWR CreateInstanceEndpointPolicy --instance_id=<id> --enable=true --cli-region=cn-north-4
```

## Pitfall 12: Registry Credential Security

**Symptom**: Registry sync fails with authentication error

**Root Cause**: Registry credentials (`--credential.access_key` and `--credential.access_secret`) must be correct and current. If the target registry changes its credentials, sync will fail.

**Solution**:
- Never expose or log credential values
- Update registry credentials when they change on the target side
- Verify credentials work by testing manually before configuring in SWR

```bash
# Update registry credentials when target credentials change
hcloud SWR UpdateInstanceRegistry --instance_id=<id> --registry_id=<reg-id> --name=target --type=swr-pro --url=<url> --credential.type=basic --credential.access_key=<new-key> --credential.access_secret=<new-secret> --insecure=false --cli-region=cn-north-4
```

## Pitfall 13: Instance VPC Project ID Confusion

**Symptom**: `CreateInstance` or `CreateInstanceInternalEndpoint` fails with project ID errors

**Root Cause**: The `--project_id` body parameter for VPC/subnet configuration may differ from the auto-filled path `--project_id`. If the VPC/subnet is in a different project, the body `--project_id` must specify the VPC/subnet project.

**Solution**: Ensure the body `--project_id` matches the project where the VPC and subnet reside:

```bash
# If VPC/subnet are in a different project, specify that project ID
hcloud SWR CreateInstance --name=my-instance --spec=swr.ee.basic --charge_mode=postPaid --vpc_id=<vpc-id> --subnet_id=<subnet-id> --enterprise_project_id=0 --project_id=<vpc-project-id> --cli-region=cn-north-4
```

## Pitfall 14: ListAllInstanceRepositories Uses Marker-Based Pagination

**Symptom**: Pagination with `--offset/--limit` returns unexpected results for `ListAllInstanceRepositories`

**Root Cause**: `ListAllInstanceRepositories` uses `--marker/--limit` pagination, not `--offset/--limit`. The `--marker` value comes from the `next_marker` field in the previous response.

**Solution**: Use marker-based pagination:

```bash
# ✅ CORRECT - First page (no marker needed)
hcloud SWR ListAllInstanceRepositories --limit=20 --cli-region=cn-north-4

# ✅ CORRECT - Next page (use next_marker from previous response)
hcloud SWR ListAllInstanceRepositories --limit=20 --marker=<next_marker> --cli-region=cn-north-4

# ❌ WRONG - Using offset for this operation
hcloud SWR ListAllInstanceRepositories --limit=20 --offset=0 --cli-region=cn-north-4
```

## Common Error Response Reference

| Error Code          | HTTP Status | Description                  | Recommended Action                    |
| ------------------- | ----------- | ---------------------------- | ------------------------------------- |
| `SVCSTG.SWR.401`    | 401         | Authentication failed        | Check AK/SK configuration            |
| `SVCSTG.SWR.403`    | 403         | Permission denied            | Check IAM policies                    |
| `SVCSTG.SWR.404`    | 404         | Resource not found           | Verify resource exists first          |
| `SVCSTG.SWR.409`    | 409         | Resource already exists      | Use Show operation to check           |
| `SVCSTG.SWR.400`    | 400         | Invalid parameter            | Check parameter format and rules      |
| `SVCSTG.SWR.500`    | 500         | Internal server error        | Retry or contact support              |
| `SVCSTG.SWR.429`    | 429         | Too many requests            | Add delay, reduce request rate        |