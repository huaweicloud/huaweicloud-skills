# API and CLI Command Reference

## API Quick Reference

| Step | API/Command | Method | Purpose | Key Parameters |
|------|-------------|--------|---------|----------------|
| 1 | `ShowDomainDetailByName` | GET | Validate domain permission + obtain CNAME | `--domain_name` |
| 2 | `python scripts/dns_resolve.py` | — | DNS resolution probe; emits JSON in `{result, data, error_msg}` envelope with `data.resolved_ips` | `--domain`, `--timeout` |
| 3 | `ShowIpInfo/v2` | GET | Query IP attribution (up to 20 IPs) | `--ips` |

## API Details

### ShowDomainDetailByName

**Purpose**: Query domain details by domain name, used to validate the domain belongs to the current account and obtain the expected CNAME.

**Command**:
```bash
hcloud CDN ShowDomainDetailByName --cli-region=<region> --domain_name=<domain>
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--domain_name` | string | Yes | Accelerated domain |
| `--cli-region` | string | Yes | Region, recommended `cn-north-1` |

**Return Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Domain ID |
| `domain_name` | string | Domain name |
| `cname` | string | CNAME address (expected resolution target) |
| `domain_status` | string | Domain status (online/offline/configuring) |

**Return Example**:
```json
{
  "id": "xxxxxxxxxx",
  "domain_name": "www.example.com",
  "cname": "www.example.com.cdn.net",
  "domain_status": "online"
}
```

**Error Codes**:

| Error Code | Description | Handling |
|------------|-------------|----------|
| 200 | Success | Continue to subsequent steps |
| 404 | Domain not found | Abort, prompt to confirm domain ownership |
| 403 | Permission denied | Abort, prompt to contact administrator for authorization |
| CDN.0171 | Domain not under current account | Abort, prompt to confirm domain ownership |

### ShowIpInfo/v2

**Purpose**: Query IP attribution information to determine whether an IP belongs to a Huawei Cloud CDN node.

**Command**:
```bash
hcloud CDN ShowIpInfo/v2 --cli-region=<region> --ips=<IP1,IP2,...>
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--ips` | string | Yes | IP list, multiple IPs separated by English commas, **up to 20** |
| `--cli-region` | string | Yes | Region, recommended `cn-north-1` |

**Return Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `cdn_ips` | array | Top-level list of `CdnIps` objects — the response wraps results under this key (not `ips`) |
| `cdn_ips[].ip` | string | Queried IP address |
| `cdn_ips[].belongs` | boolean | Whether it belongs to Huawei Cloud CDN (true/false) |
| `cdn_ips[].region` | string | Province/region of the IP (attribution location, e.g. `四川`/`北京`; empty if not Huawei Cloud) |
| `cdn_ips[].isp` | string | ISP of the IP (if not Huawei Cloud) |
| `cdn_ips[].platform` | string | Platform the IP belongs to (e.g. `华为云`; empty if not Huawei Cloud) |

**Return Example**:
```json
{
  "cdn_ips": [
    {
      "ip": "1.2.3.4",
      "belongs": true,
      "region": "四川",
      "isp": "华为云",
      "platform": "华为云"
    },
    {
      "ip": "5.6.7.8",
      "belongs": true,
      "region": "广东",
      "isp": "华为云",
      "platform": "华为云"
    }
  ]
}
```

**IP Count Limit**:

| Scenario | Handling |
|----------|----------|
| IP count ≤ 20 | Query all |
| IP count > 20 | Take only the first 20, note in the report "Actually resolved to N IPs; due to API limit, only the first 20 are verified" |

## Python Probe Scripts

This skill performs DNS resolution via the Python probe script
`scripts/dns_resolve.py` instead of a `dig` binary. The script emits a single
JSON object on stdout and enforces a 10-second probe timeout.

### dns_resolve.py

**Path**: `scripts/dns_resolve.py` (relative to the skill root)

**Library**: `dnspython >= 2.1`

**Command**:
```bash
python scripts/dns_resolve.py --domain <domain_name> [--timeout 10]
```

**CLI Arguments**:

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--domain` | Yes | — | Domain to resolve for A records (RFC 1035 validated, length ≤ 253) |
| `--timeout` | No | `10` | Query lifetime in seconds, range `[1, 30]` |

**Output JSON Schema**:

| Field | Type | Description |
|-------|------|-------------|
| `domain` | string | The domain passed via `--domain` |
| `data.resolved_ips` | array of strings | Resolved IPv4 addresses; empty on failure |
| `data.duration_ms` | integer | Probe duration in milliseconds |
| `error` | object or null | `null` on success; `{reason, message}` on failure |

`data.error.reason` values: `dns_nxdomain`, `dns_no_answer`, `dns_timeout`, `missing_library`, `invalid_domain`, `invalid_timeout`, `unexpected_probe_error`.

**Exit Codes**:
- `0` — Probe ran to completion (including soft failures: NXDOMAIN, NoAnswer, timeout)
- `2` — Argument error or missing `dnspython` import

**Success Example**:
```json
{
  "result": "success",
  "data": {
    "domain": "www.example.com",
    "resolved_ips": ["1.2.3.4", "5.6.7.8"],
    "duration_ms": 38,
    "error": null
  },
  "error_msg": ""
}
```

**NXDOMAIN Failure Example**:
```json
{
  "result": "failed",
  "data": {
    "domain": "nope.example.invalid",
    "resolved_ips": [],
    "duration_ms": 27,
    "error": { "reason": "dns_nxdomain", "message": "..." }
  },
  "error_msg": "dns_nxdomain"
}
```

**Decision Logic** (consumed by Step 3 and report generation):
- `data.error == null` and `data.resolved_ips` non-empty → Record IP count and addresses, continue to Step 3
- `data.error == null` and `data.resolved_ips` empty → Domain not resolved, report "not resolved", prompt to configure DNS CNAME
- `data.error.reason == "dns_timeout"` → Probe timeout, return partial result, mark "DNS probe timeout"
- `data.error.reason == "dns_nxdomain"` → Domain does not exist
- `data.error.reason == "dns_no_answer"` → No A records found

## IP Attribution Decision Logic

| Scenario | Condition | Conclusion | Report Status |
|----------|-----------|------------|---------------|
| Resolved | All IPs belongs=true | Domain correctly resolved to Huawei Cloud CDN | ✅ Pass |
| Not resolved | All IPs belongs=false | Domain not resolved to Huawei Cloud CDN; CNAME needs to be configured | ❌ Fail |
| Partial resolution | Some belongs=true, some false | Partial regions switched, suspected false positive | ⚠️ Warning |

## Important Notes

- All hcloud commands should use `--cli-region=<region>`
- All hcloud parameters must use the `--key=value` format (connected with equals sign)
- `dns_resolve.py` enforces a 10-second timeout via `--timeout 10` (default)
- ShowIpInfo/v2 queries at most 20 IPs
- This skill only uses query APIs and read-only DNS probes; no write operations are called
- No `curl` or `dig` binary is required; DNS probing is performed entirely through `dnspython`
