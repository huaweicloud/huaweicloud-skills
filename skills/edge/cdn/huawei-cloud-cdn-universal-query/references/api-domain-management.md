# Category 1: Domain Management APIs (14 APIs)

> All commands should use `--cli-region=cn-north-1`. All operations are read-only (GET).

## API List

### 1. ListDomains/v2 — List all CDN domains

```bash
hcloud CDN ListDomains/v2 --cli-region=cn-north-1 --page_size=<page_size> --domain_status=<domain_status>
```

**Parameters:**
- `--page_size` (optional): Number of results per page (default 100, max 100). User-provided integer.
- `--domain_status` (optional): Filter by domain status. Valid values: `online`, `offline`, `configuring`, `configuring_failed`.
- `--service_area` (optional): Filter by service area. Valid values: `mainland_china`, `outside_mainland_china`, `global`.
- `--business_type` (optional): ⚠ Avoid using `web` — may cause timeout (see Pitfall #10)

**Pitfall:** Do NOT use `--business_type=web` filter — it causes performance issues. Use `--domain_status` or `--service_area` instead.

**Returns:** `total` (count), `domains` array with `id`, `domain_name`, `domain_status`, `service_area`, `business_type`.

---

### 2. ShowDomainDetail — Get domain details by ID

```bash
hcloud CDN ShowDomainDetail --cli-region=cn-north-1 --domain_id=<domain_id>
```

**Parameters:** `--domain_id` (required)

**Returns:** Domain configuration including origins, HTTPS, cache, etc.

---

### 3. ShowDomainDetailByName — Get domain details by name

```bash
hcloud CDN ShowDomainDetailByName --cli-region=cn-north-1 --domain_name=<your-domain>
```

**Parameters:** `--domain_name` (required)

**Returns:** Domain details including `domain.id` — use this to obtain `domain_id` for other APIs.

**Common use:** First step before calling `ShowOriginHost`, `ShowCacheRules`, `ShowHttpInfo`, etc.

---

### 4. ShowDomainFullConfig/v2 — Get full domain configuration

```bash
hcloud CDN ShowDomainFullConfig/v2 --cli-region=cn-north-1 --domain_name=<your-domain>
```

**Parameters:** `--domain_name` (required)

**Returns:** Complete domain config (HTTPS/TLS, origin, cache, filters, etc.).

---

### 5. ShowOriginHost — Get origin host configuration

```bash
hcloud CDN ShowOriginHost --cli-region=cn-north-1 --domain_id=<domain_id>
```

**Parameters:** `--domain_id` (required)

**Returns:** `origin_host_type`, `customize_domain`.

---

### 6. ShowCacheRules — Get cache rules

```bash
hcloud CDN ShowCacheRules --cli-region=cn-north-1 --domain_id=<domain_id>
```

**Parameters:** `--domain_id` (required)

**Returns:** `cache_config` with `rules` array (match type, TTL, priority).

---

### 7. ShowResponseHeader — Get response header rules

```bash
hcloud CDN ShowResponseHeader --cli-region=cn-north-1 --domain_id=<domain_id>
```

**Parameters:** `--domain_id` (required)

**Returns:** Custom HTTP response headers configured for the domain.

---

### 8. ShowRefer — Get referer validation config

```bash
hcloud CDN ShowRefer --cli-region=cn-north-1 --domain_id=<domain_id>
```

**Parameters:** `--domain_id` (required)

**Returns:** Referer whitelist/blacklist configuration.

---

### 9. ShowHttpInfo — Get HTTPS certificate details

```bash
hcloud CDN ShowHttpInfo --cli-region=cn-north-1 --domain_id=<domain_id>
```

**Parameters:** `--domain_id` (required)

**Returns:** Certificate details (expiry date, content, domain binding).

---

### 10. ShowCertificatesHttpsInfo/v2 — Get HTTPS cert binding info

```bash
hcloud CDN ShowCertificatesHttpsInfo/v2 --cli-region=cn-north-1 --domain_name=<your-domain>
```

**Parameters:** `--domain_name` (required)

**Returns:** HTTPS certificate binding info for the domain.

---

### 11. ShowBlackWhiteList — Get IP black/white list

```bash
hcloud CDN ShowBlackWhiteList --cli-region=cn-north-1 --domain_id=<domain_id>
```

**Parameters:** `--domain_id` (required)

**Returns:** IP blacklist/whitelist configuration.

---

### 12. ShowVerifyDomainOwnerInfo — Get domain ownership verification

```bash
hcloud CDN ShowVerifyDomainOwnerInfo --cli-region=cn-north-1 --domain_name=<your-domain>
```

**Parameters:** `--domain_name` (required)

**Returns:** Domain ownership verification status (TXT record, verification time).

---

### 13. ListDomainConfigs — Get specific config items

```bash
hcloud CDN ListDomainConfigs --cli-region=cn-north-1 --item=<item> --domain_names=<your-domain>
```

**Parameters:**
- `--item` (required): Config item to query. Valid values include: `cname_status`, `origin_host`, `https_status`, `cache_settings`, `compression`, `ip_filter`, `redirect`, `request_limit`, `response_header`, `websocket`.
- `--domain_names` (required): Comma-separated domain names

**Returns:** Specific config items for one or more domains.

---

### 14. ShowTags/v2 — Get domain tags

```bash
hcloud CDN ShowTags/v2 --cli-region=cn-north-1 --resource_id=<domain_id>
```

**Parameters:** `--resource_id` (required, must be `domain_id` not domain name)

**Pitfall:** `ShowTags/v2` is NOT a list-all-tags API. It requires `--resource_id` (domain_id). See Pitfall #13.

**Returns:** Tags associated with the specified domain.

---

## Common Prerequisite Pattern

Most domain config APIs require `domain_id` (not `domain_name`). Always obtain it first:

```bash
# Step 1: Get domain_id from domain name
hcloud CDN ShowDomainDetailByName --cli-region=cn-north-1 --domain_name=<your-domain>
# Extract: domain.id

# Step 2: Use domain_id for config APIs
hcloud CDN ShowOriginHost --cli-region=cn-north-1 --domain_id=<id>
hcloud CDN ShowCacheRules --cli-region=cn-north-1 --domain_id=<id>
hcloud CDN ShowResponseHeader --cli-region=cn-north-1 --domain_id=<id>
hcloud CDN ShowRefer --cli-region=cn-north-1 --domain_id=<id>
hcloud CDN ShowHttpInfo --cli-region=cn-north-1 --domain_id=<id>
hcloud CDN ShowBlackWhiteList --cli-region=cn-north-1 --domain_id=<id>
hcloud CDN ShowTags/v2 --cli-region=cn-north-1 --resource_id=<id>
```
