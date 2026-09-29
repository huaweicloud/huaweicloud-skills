# Category 4: Template / Rule / Tag / Account APIs (10 APIs)

> All commands should use `--cli-region=cn-north-1`. All operations are read-only (GET).

## API List

### 1. ShowDomainTemplate — Get domain templates

```bash
# System templates
hcloud CDN ShowDomainTemplate --cli-region=cn-north-1 --tml_type=<tml_type>

# User templates
hcloud CDN ShowDomainTemplate --cli-region=cn-north-1 --tml_type=<tml_type>
```

**Parameters:** `--tml_type` (optional, INTEGER, enum: `1`=system templates, `2`=user templates; 不传时不按模板类型过滤)

**Pitfall:** `--tml_type` is INTEGER, not string. Do NOT use `system` or `user`. See Pitfall #8.

**Returns:** List of domain templates with configuration snapshots.

---

### 2. ShowAppliedTemplateRecord — Get applied template records

```bash
hcloud CDN ShowAppliedTemplateRecord --cli-region=cn-north-1 --limit=<limit> --offset=<offset>
```

**Parameters:** `--limit`, `--offset`, `--tml_id`, `--tml_name`, `--operator_id` (all optional)

**Returns:** Records of templates applied (template ID, apply time, status). Supports pagination and filtering by template ID/name/operator.

---

### 3. ListRuleDetails — Get rule details

```bash
hcloud CDN ListRuleDetails --cli-region=cn-north-1 --domain_name=<your-domain>
```

**Parameters:** `--domain_name` (required)

**Returns:** Rule details configured for the domain (conditions, actions, priority).

---

### 4. ListShareCacheGroups — Get shared cache groups

```bash
hcloud CDN ListShareCacheGroups --cli-region=cn-north-1
```

**Parameters:** None

**Returns:** List of shared cache groups (group ID, member domains, status).

---

### 5. ListSubscriptionTasks — Get subscription tasks

```bash
hcloud CDN ListSubscriptionTasks --cli-region=cn-north-1
```

**Parameters:** None

**Returns:** List of subscription tasks (task type, status, target resources).

---

### 6. ShowIpInfo/v2 — Check if IPs belong to Huawei Cloud CDN

```bash
hcloud CDN ShowIpInfo/v2 --cli-region=cn-north-1 --ips=<ip1>,<ip2>
```

**Parameters:** `--ips` (required): Comma-separated IP list (max 20 IPs per call)

**Returns:** For each IP: whether it belongs to Huawei Cloud CDN, and if so, which edge node/region.

**Use:** Verify if a client IP hitting the origin is a Huawei Cloud CDN edge node (useful for origin pull diagnostics).

---

### 7. ShowQuota/v2 — Get account quota

```bash
hcloud CDN ShowQuota/v2 --cli-region=cn-north-1
```

**Parameters:** None

**Returns:** Account quota info (max domains, max refresh tasks, etc.).

---

### 8. ShowSpecialUser — Get special user config

```bash
hcloud CDN ShowSpecialUser --cli-region=cn-north-1
```

**Parameters:** None

**Returns:** Special user configuration (custom rate limits, special features enabled).

---

### 9. ListSpecialConfiguration — Get special configurations

```bash
hcloud CDN ListSpecialConfiguration --cli-region=cn-north-1 --domain_name=<your-domain>
```

**Parameters:** `--domain_name` (required); `--page_number`, `--page_size` (optional)

**Returns:** List of special configurations applied to the domain (custom features, overrides).

---

### 10. ShowStatsConfigs — Get statistics config

```bash
hcloud CDN ShowStatsConfigs --cli-region=cn-north-1 --config_type=<config_type>
```

**Parameters:** `--config_type` (required, INTEGER, enum: `0`=热点统计, `1`=ces上报); `--limit`, `--offset` (optional)

**Returns:** Statistics collection configuration (which metrics are enabled, retention period).

---

## Common Use Cases

### Verify if an IP is a Huawei Cloud CDN edge node

```bash
hcloud CDN ShowIpInfo/v2 --cli-region=cn-north-1 --ips=<ip1>,<ip2>
```

Useful when debugging origin pull issues — if the client IP at origin is a Huawei Cloud CDN edge node, the request is a legitimate CDN origin pull.

### Check account-level limits before bulk operations

```bash
hcloud CDN ShowQuota/v2 --cli-region=cn-north-1
```

Verify domain count quota before adding new domains.

### Review special configurations

```bash
hcloud CDN ShowSpecialUser --cli-region=cn-north-1
hcloud CDN ListSpecialConfiguration --cli-region=cn-north-1 --domain_name=<your-domain>
hcloud CDN ShowStatsConfigs --cli-region=cn-north-1 --config_type=<config_type>
```

These three APIs together give a complete picture of account-level special configurations.
