# Workflow 5: Diagnose Domain Issues

> Use this workflow when you need to diagnose DNS, certificate, origin, or ownership issues.

## Prerequisites

- hcloud CLI installed and authenticated
- Target domain name (e.g., `<your-domain>`)
- Optional: client IP addresses seen at origin (for `ShowIpInfo/v2`)

## Steps

### Step 1: Get domain_id

Most diagnostic APIs require `domain_id`. Obtain it first:

```bash
hcloud CDN ShowDomainDetailByName --cli-region=cn-north-1 --domain_name=<your-domain>
```

**Extract:** `domain.id` from the response.

### Step 2: Check domain ownership and CNAME status

Verify the domain ownership and CNAME configuration:

```bash
# Domain ownership verification
hcloud CDN ShowVerifyDomainOwnerInfo --cli-region=cn-north-1 --domain_name=<your-domain>

# CNAME status (and other config items, --item=<item>, enum: cname_status, etc.)
hcloud CDN ListDomainConfigs --cli-region=cn-north-1 --item=<item> --domain_names=<your-domain>
```

**Returns:**
- `ShowVerifyDomainOwnerInfo`: TXT record verification status, verification time
- `ListDomainConfigs` with `--item=<item>` (enum: cname_status, etc.): CNAME resolution status (whether the domain CNAME points to the CDN endpoint)

### Step 3: Check DNS (if IPs belong to Huawei Cloud CDN)

If you have client IPs hitting the origin and want to verify if they're CDN edge nodes:

```bash
hcloud CDN ShowIpInfo/v2 --cli-region=cn-north-1 --ips=<ip1>,<ip2>
```

**Parameters:** `--ips` (required): Comma-separated IP list (max 20 IPs per call)

**Returns:** For each IP: whether it belongs to Huawei Cloud CDN, and if so, which edge node/region.

**Use case:** If the origin server sees non-CDN IPs, it may indicate:
- DNS misconfiguration (client bypassing CDN)
- Origin pull from non-CDN source
- Potential unauthorized access

### Step 4: Check HTTPS certificate

Verify the certificate binding and expiry:

```bash
# Cert binding info (uses domain_name)
hcloud CDN ShowCertificatesHttpsInfo/v2 --cli-region=cn-north-1 --domain_name=<your-domain>

# Cert details (uses domain_id)
hcloud CDN ShowHttpInfo --cli-region=cn-north-1 --domain_id=<domain_id>
```

**Returns:**
- `ShowCertificatesHttpsInfo/v2`: Cert binding info, cert ID, domain association
- `ShowHttpInfo`: Certificate details (expiry date, content, cert type)

**Common issues:**
- Certificate expired → users see browser warnings
- Certificate not properly bound → HTTPS fails
- Domain mismatch (SAN does not include the domain) → browser errors

### Step 5: Check origin configuration

Verify origin host and IP filtering:

```bash
# Origin host configuration
hcloud CDN ShowOriginHost --cli-region=cn-north-1 --domain_id=<domain_id>

# IP black/white list (origin pull filtering)
hcloud CDN ShowBlackWhiteList --cli-region=cn-north-1 --domain_id=<domain_id>
```

**Returns:**
- `ShowOriginHost`: `origin_host_type`, `customize_domain` (the Host header sent to origin)
- `ShowBlackWhiteList`: IP filter configuration (which IPs can/cannot access)

**Common issues:**
- `origin_host_type` mismatch → origin server rejects the Host header
- IP blacklist too restrictive → legitimate CDN edge nodes blocked
- IP whitelist missing CDN edge IP ranges → CDN cannot pull from origin

### Step 6: Check cache and other configs (optional)

```bash
# Cache rules (TTL configuration)
hcloud CDN ShowCacheRules --cli-region=cn-north-1 --domain_id=<domain_id>

# Response headers
hcloud CDN ShowResponseHeader --cli-region=cn-north-1 --domain_id=<domain_id>

# Referer validation
hcloud CDN ShowRefer --cli-region=cn-north-1 --domain_id=<domain_id>
```

## Diagnosis Matrix

| Symptom | Check | Likely Cause |
|---------|-------|---------------|
| 502 errors at edge | `ShowIpInfo/v2`, `ShowOriginHost` | Origin unreachable, IP blocked, wrong Host header |
| HTTPS fails | `ShowHttpInfo`, `ShowCertificatesHttpsInfo/v2` | Cert expired, not bound, domain mismatch |
| Origin pull failures | `ShowBlackWhiteList`, `ShowOriginHost` | CDN edge IP blocked, wrong origin host |
| CNAME not working | `ListDomainConfigs --item=<item>` (enum: cname_status, etc.) | DNS not pointing to CDN endpoint |
| Ownership not verified | `ShowVerifyDomainOwnerInfo` | TXT record missing or incorrect |
| Cache miss high | `ShowCacheRules` | Cache TTL too short, rules misconfigured |
| Hotlinking | `ShowRefer` | Referer whitelist not configured |

## Common Issues

- **Missing `domain_id`**: Always call `ShowDomainDetailByName` first. APIs like `ShowOriginHost`, `ShowHttpInfo`, `ShowBlackWhiteList` require `domain_id`, not `domain_name`.
- **ShowTags/v2 missing `resource_id`**: `ShowTags/v2` requires `--resource_id=<domain_id>`, not a standalone list-all-tags call. See Pitfall #13.
- **ShowIpInfo/v2 IP limit**: Max 20 IPs per call. For more IPs, split into multiple queries.
