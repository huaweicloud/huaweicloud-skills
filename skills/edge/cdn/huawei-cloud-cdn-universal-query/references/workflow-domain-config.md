# Workflow 1: Query Domain Configuration

> Use this workflow when you need to inspect a domain's full configuration.

## Prerequisites

- hcloud CLI installed and authenticated
- Target domain name (e.g., `<your-domain>`)

## Steps

### Step 1: Get domain_id from domain name

Most domain config APIs require `domain_id` (not `domain_name`). Always obtain it first:

```bash
hcloud CDN ShowDomainDetailByName --cli-region=cn-north-1 --domain_name=<your-domain>
```

**Extract:** `domain.id` from the response — this is the `domain_id` used in subsequent calls.

### Step 2: Get full domain configuration (optional overview)

```bash
hcloud CDN ShowDomainFullConfig/v2 --cli-region=cn-north-1 --domain_name=<your-domain>
```

Returns the complete config snapshot (HTTPS/TLS, origin, cache, filters, etc.).

### Step 3: Get specific configurations (using domain_id from Step 1)

Call the relevant config APIs based on what you need to inspect:

| Want to inspect | Command |
|------------------|---------|
| Origin host | `hcloud CDN ShowOriginHost --cli-region=cn-north-1 --domain_id=<id>` |
| Cache rules | `hcloud CDN ShowCacheRules --cli-region=cn-north-1 --domain_id=<id>` |
| Response headers | `hcloud CDN ShowResponseHeader --cli-region=cn-north-1 --domain_id=<id>` |
| Referer validation | `hcloud CDN ShowRefer --cli-region=cn-north-1 --domain_id=<id>` |
| HTTPS certificate | `hcloud CDN ShowHttpInfo --cli-region=cn-north-1 --domain_id=<id>` |
| IP black/white list | `hcloud CDN ShowBlackWhiteList --cli-region=cn-north-1 --domain_id=<id>` |
| Domain tags | `hcloud CDN ShowTags/v2 --cli-region=cn-north-1 --resource_id=<id>` |

### Step 4: Get domain-specific info (using domain_name)

Some APIs use `domain_name` instead of `domain_id`:

```bash
# HTTPS cert binding info
hcloud CDN ShowCertificatesHttpsInfo/v2 --cli-region=cn-north-1 --domain_name=<your-domain>

# Domain ownership verification
hcloud CDN ShowVerifyDomainOwnerInfo --cli-region=cn-north-1 --domain_name=<your-domain>

# Specific config items ( --item=<item>, enum: cname_status, etc.)
hcloud CDN ListDomainConfigs --cli-region=cn-north-1 --item=<item> --domain_names=<your-domain>
```

## Common Issues

- **Missing `domain_id`**: Always call `ShowDomainDetailByName` first. APIs like `ShowOriginHost` will fail without `domain_id`.
- **ShowTags/v2 missing `resource_id`**: ShowTags/v2 is NOT a list-all-tags API — it requires `--resource_id=<domain_id>`. See Pitfall #13.
