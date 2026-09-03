# API Reference — Cloud Connect (CC) Query Endpoints

All endpoints verified from SDK source `_http_info` `resource_path` or hcloud CLI `--debug` output.

## Base Information

- **Service**: CC (Cloud Connect)
- **API Version**: v3
- **Auth**: AK/SK + domain_id (account ID)
- **All operations**: GET (read-only)

## Endpoints

### 1. Cloud Connections

| Operation | Method | URI |
|-----------|--------|-----|
| List | GET | `/v3/{domain_id}/ccaas/cloud-connections` |
| Show | GET | `/v3/{domain_id}/ccaas/cloud-connections/{id}` |

### 2. Bandwidth Packages

| Operation | Method | URI |
|-----------|--------|-----|
| List | GET | `/v3/{domain_id}/ccaas/bandwidth-packages` |
| Show | GET | `/v3/{domain_id}/ccaas/bandwidth-packages/{id}` |

### 3. Inter-Region Bandwidths

| Operation | Method | URI |
|-----------|--------|-----|
| List | GET | `/v3/{domain_id}/ccaas/inter-region-bandwidths` |
| Show | GET | `/v3/{domain_id}/ccaas/inter-region-bandwidths/{id}` |

### 4. Network Instances

| Operation | Method | URI |
|-----------|--------|-----|
| List | GET | `/v3/{domain_id}/ccaas/network-instances` |
| Show | GET | `/v3/{domain_id}/ccaas/network-instances/{id}` |

### 5. Cloud Connection Routes

| Operation | Method | URI |
|-----------|--------|-----|
| List | GET | `/v3/{domain_id}/ccaas/cloud-connection-routes` |
| Show | GET | `/v3/{domain_id}/ccaas/cloud-connection-routes/{id}` |

### 6. Authorisations (Granted — Grantor's View)

Returns authorisations where the calling account (identified by `domain_id`) is the **grantor** — it owns the network instances and has authorised other accounts to load them.

| Operation | Method | URI |
|-----------|--------|-----|
| List | GET | `/v3/{domain_id}/ccaas/authorisations` |

### 7. Permissions (Received — Grantee's View)

Returns permissions where the calling account (identified by `domain_id`) is the **grantee** — other accounts have authorised it to load their network instances into the calling account's cloud connections.

| Operation | Method | URI |
|-----------|--------|-----|
| List | GET | `/v3/{domain_id}/ccaas/permissions` |

## Path Parameters

| Parameter | Description |
|-----------|-------------|
| `{domain_id}` | Account ID (obtain from IAM → My Credentials → Account ID) |
| `{id}` | Resource instance ID |

## Common Query Parameters (List Operations)

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | integer | Page size (1–2000) |
| `marker` | string | Pagination token from previous response |
| `enterprise_project_id` | array<string> | Filter by enterprise project |
| `id` | array<string> | Filter by resource ID |
| `name` | array<string> | Filter by resource name |
| `status` | array<string> | Filter by status (e.g., ACTIVE) |
