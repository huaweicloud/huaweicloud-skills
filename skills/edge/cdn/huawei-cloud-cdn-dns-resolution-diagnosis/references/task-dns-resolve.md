# Step 2: DNS Resolution Probe

Resolve the domain via `python scripts/dns_resolve.py` and parse the JSON
`data.resolved_ips` field to obtain the actual IP list.

## 2.1 Execute DNS Resolution

**Command**:
```bash
python scripts/dns_resolve.py --domain <domain_name> [--timeout 10]
```

**Parameter Description**:

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--domain` | Yes | — | Domain to resolve for A records (RFC 1035 validated) |
| `--timeout` | No | `10` | Query lifetime in seconds, range `[1, 30]` |

**Timeout Control**: 10 seconds (enforced by the script via `dns.resolver.resolve(lifetime=timeout)`; `--timeout 10` is the default and matches the original probe budget).

**Output**: A single JSON object on stdout. Diagnostic logs, if any, go to stderr.

**Exit Codes**:
- `0` — Probe completed (including soft failures such as NXDOMAIN, NoAnswer, timeout)
- `2` — Argument error or missing library import (`dnspython` absent)

## 2.2 JSON Output Schema

> **Output envelope**: the script wraps its output in the platform standard `{result, data, error_msg}` envelope (`format_output()` in `dns_resolve.py`); business fields are inside `data`. Parse `data.*`, not the top level.

### Success

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

### NXDOMAIN (domain does not exist)

```json
{
  "result": "failed",
  "data": {
    "domain": "nope.example.invalid",
    "resolved_ips": [],
    "duration_ms": 27,
    "error": { "reason": "dns_nxdomain", "message": "Domain 'nope.example.invalid' does not exist" }
  },
  "error_msg": "dns_nxdomain"
}
```

### NoAnswer (no A records)

```json
{
  "result": "failed",
  "data": {
    "domain": "txt-only.example.com",
    "resolved_ips": [],
    "duration_ms": 31,
    "error": { "reason": "dns_no_answer", "message": "No A records found for 'txt-only.example.com'" }
  },
  "error_msg": "dns_no_answer"
}
```

### Timeout

```json
{
  "result": "failed",
  "data": {
    "domain": "timeout.example.com",
    "resolved_ips": [],
    "duration_ms": 10012,
    "error": { "reason": "dns_timeout", "message": "DNS query for 'timeout.example.com' timed out after 10s" }
  },
  "error_msg": "dns_timeout"
}
```

### Missing library (prerequisite failure, exit code 2)

```json
{
  "result": "failed",
  "data": {
    "domain": "www.example.com",
    "resolved_ips": [],
    "duration_ms": 0,
    "error": { "reason": "missing_library", "message": "Missing Python library: dnspython. Install with: pip install dnspython>=2.1" }
  },
  "error_msg": "missing_library"
}
```

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `data.domain` | string | The domain passed via `--domain` |
| `data.resolved_ips` | array of strings | Resolved IPv4 addresses (one string per IP); empty on failure |
| `data.duration_ms` | integer | Probe duration in milliseconds |
| `data.error` | object or null | `null` on success; `{reason, message}` on soft failure or prereq failure |

`data.error.reason` values produced by this script: `dns_nxdomain`, `dns_no_answer`, `dns_timeout`, `missing_library`, `invalid_domain`, `invalid_timeout`, `unexpected_probe_error`.

## 2.3 Resolution Result Decision

| Probe Result (JSON) | Handling |
|---------------------|----------|
| `data.error == null` and `data.resolved_ips` non-empty | Record IP count and address list, continue to Step 3 (IP attribution check) |
| `data.error == null` and `data.resolved_ips` empty | Domain not resolved, skip Step 3, generate report directly with conclusion "Domain not resolved" |
| `data.error.reason == "dns_timeout"` | Skip Step 3, generate report directly, mark "DNS probe timeout" |
| `data.error.reason == "dns_nxdomain"` | Skip Step 3, generate report directly, mark "Domain does not exist (NXDOMAIN)" |
| `data.error.reason == "dns_no_answer"` | Skip Step 3, generate report directly, mark "No A records found" |
| `data.error.reason == "missing_library"` (exit code 2) | Abort skill, prompt to install `dnspython` (see cli-installation-guide.md) |

## 2.4 IP List Processing

### IP Count Statistics

- Read the length of the `data.resolved_ips` array as `N`
- If `N > 20`, only take the first 20 IPs for Step 3 query
- Note in the report "Actually resolved to N IPs; due to API limit, only the first 20 are verified"

### IP Format Validation

- `data.resolved_ips` already contains only IPv4 address strings (the script extracts A records and stringifies each RR)
- Deduplicate (if duplicate IPs exist, which is rare for A records)

### IP List Joining

Join the IP list with English commas for the `--ips` parameter of ShowIpInfo/v2:
```
--ips=1.2.3.4,5.6.7.8,9.10.11.12
```

## Exception Handling

| Exception Scenario | Handling |
|--------------------|----------|
| `data.error.reason == "missing_library"` (exit code 2) | Prompt to install `dnspython>=2.1`, see cli-installation-guide.md |
| `data.error.reason == "invalid_domain"` (exit code 2) | Abort; the `--domain` argument failed RFC 1035 validation |
| `data.error.reason == "invalid_timeout"` (exit code 2) | Abort; `--timeout` is outside `[1, 30]` |
| `data.error.reason == "dns_timeout"` | DNS server unreachable within lifetime; check local network and DNS configuration |
| `data.error.reason == "dns_nxdomain"` | Domain does not exist; check the domain spelling and authoritative DNS |
| `data.error.reason == "dns_no_answer"` | No A records returned; the domain may only have other record types (e.g., CNAME, TXT) |
| `data.error.reason == "unexpected_probe_error"` | Unexpected failure; the detailed traceback is on stderr for debugging |

## Example

### Normal Resolution

```bash
$ python scripts/dns_resolve.py --domain www.example.com --timeout 10
{"result": "success", "data": {"domain": "www.example.com", "resolved_ips": ["1.2.3.4", "5.6.7.8"], "duration_ms": 38, "error": null}, "error_msg": ""}
```

→ `data.resolved_ips = ["1.2.3.4", "5.6.7.8"]`, count=2, continue to Step 3

### Returns Empty (NXDOMAIN)

```bash
$ python scripts/dns_resolve.py --domain unresolved.example.com --timeout 10
{"result": "failed", "data": {"domain": "unresolved.example.com", "resolved_ips": [], "duration_ms": 27, "error": {"reason": "dns_nxdomain", "message": "..."}}, "error_msg": "dns_nxdomain"}
```

→ Domain not resolved, skip Step 3, generate report

### Timeout

```bash
$ python scripts/dns_resolve.py --domain timeout.example.com --timeout 10
{"result": "failed", "data": {"domain": "timeout.example.com", "resolved_ips": [], "duration_ms": 10012, "error": {"reason": "dns_timeout", "message": "..."}}, "error_msg": "dns_timeout"}
```

→ DNS probe timeout, skip Step 3, generate report and mark timeout

### More Than 20 IPs

```bash
$ python scripts/dns_resolve.py --domain hightraffic.example.com --timeout 10
{"result": "success", "data": {"domain": "hightraffic.example.com", "resolved_ips": ["1.1.1.1", "2.2.2.2", ... "25.25.25.25"], "duration_ms": 55, "error": null}, "error_msg": ""}
```

→ `data.resolved_ips` has 25 entries, only take the first 20 for query, note the limit in the report

## Output Forwarding

After this step is complete, the following information is forwarded to Step 3 and report generation:
- `resolved_ips`: IP address list (up to 20, derived from the JSON `data.resolved_ips` field)
- `ip_count`: Total number of IPs actually resolved (length of `data.resolved_ips` before truncation)
- `truncated`: Whether truncated (true/false)
- `probe_status`: success/empty/timeout/nxdomain/no_answer (derived from `data.error.reason` and `data.resolved_ips`)
- `duration_ms`: Probe duration (from the JSON `data.duration_ms` field)
