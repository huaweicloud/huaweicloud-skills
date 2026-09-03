# Acceptance Criteria

## Success Criteria for Each Query Type

### Cloud Connection Queries

| Criteria | Expected Behavior |
|----------|-------------------|
| List returns valid JSON | `ListCloudConnections` returns a JSON array of cloud connections |
| Show returns matching ID | `ShowCloudConnection --id=X` returns a resource where `id == X` |
| Status filter works | `--status.1=ACTIVE` returns only connections with `status=ACTIVE` |
| Pagination works | `--limit=1` returns at most 1 entry with a valid `marker` for next page |

### Bandwidth Package Queries

| Criteria | Expected Behavior |
|----------|-------------------|
| List returns valid JSON | `ListBandwidthPackages` returns a JSON array of bandwidth packages |
| Show returns matching ID | `ShowBandwidthPackage --id=X` returns a resource where `id == X` |
| Cloud connection filter works | `--cloud_connection_id.1=Y` returns only packages bound to connection Y |

### Inter-Region Bandwidth Queries

| Criteria | Expected Behavior |
|----------|-------------------|
| List returns valid JSON | `ListInterRegionBandwidths` returns a JSON array |
| Show returns matching ID | `ShowInterRegionBandwidth --id=X` returns a resource where `id == X` |
| Bandwidth package filter works | `--bandwidth_package_id.1=Y` returns only bandwidths under package Y |

### Network Instance Queries

| Criteria | Expected Behavior |
|----------|-------------------|
| List returns valid JSON | `ListNetworkInstances` returns a JSON array |
| Show returns matching ID | `ShowNetworkInstance --id=X` returns a resource where `id == X` |
| Region filter works | `--region_id.1=cn-north-4` returns only instances in that region |

### Cloud Connection Route Queries

| Criteria | Expected Behavior |
|----------|-------------------|
| List returns valid JSON | `ListCloudConnectionRoutes` returns a JSON array |
| Show returns matching ID | `ShowCloudConnectionRoutes --id=X` returns a resource where `id == X` |
| Cloud connection filter works | `--cloud_connection_id.1=Y` returns only routes for connection Y |

### Authorisation Queries (Granted — Grantor's View)

| Criteria | Expected Behavior |
|----------|-------------------|
| List returns valid JSON | `ListAuthorisations` returns a JSON `authorisations` array |
| Each entry has `cloud_connection_domain_id` | Non-empty string identifying the grantee account |
| `domain_id` matches caller | Each entry's `domain_id` equals the calling account's domain ID |
| Instance filter works | `--instance_id.1=Y` returns only authorisations for network instance Y |
| Cloud connection filter works | `--cloud_connection_id.1=Z` returns only authorisations for cloud connection Z |
| `is_loaded_by_cloud_connection` field present | Boolean indicating whether the grantee has loaded the instance |

### Permission Queries (Received — Grantee's View)

| Criteria | Expected Behavior |
|----------|-------------------|
| List returns valid JSON | `ListPermissions` returns a JSON `permissions` array |
| Each entry has `instance_domain_id` | Non-empty string identifying the grantor account (the foreign account that owns the network instance) |
| `domain_id` matches caller | Each entry's `domain_id` equals the calling account's domain ID |
| Instance filter works | `--instance_id.1=Y` returns only permissions for network instance Y |
| Cloud connection filter works | `--cloud_connection_id.1=Z` returns only permissions for cloud connection Z |

## Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| Invalid `--domain_id` | API returns 403/404 error, CLI displays error message |
| Invalid `--id` | API returns 404, CLI displays "resource not found" |
| No resources found | API returns empty array, CLI displays empty result |
| Missing `--domain_id` | CLI uses default domain_id from auth config and returns results for the default account (no error). Always specify `--domain_id` explicitly to avoid querying the wrong account. |
