# API and CLI Command Reference

## API Quick Reference

| Step | API | Method | Purpose | Key Parameters |
|------|-----|--------|---------|----------------|
| 1 | `ShowDomainDetailByName` | GET | Validate domain permission + get basic info | `--domain_name` |
| 2 | `ShowDomainFullConfig/v2` | GET | Query origin configuration | `--domain_name` |
| 3 | `scripts/origin_probe.py` | — | Origin connectivity probe (Python) | `--scheme`, `--host`, `--port`, `--timeout 10` |

## API Details

### ShowDomainDetailByName

**Purpose**: Query domain details by domain name; used to validate that the domain belongs to the current account.

**Command**:
```bash
hcloud CDN ShowDomainDetailByName --cli-region=<region> --domain_name=<domain>
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--domain_name` | string | Yes | Accelerated domain |
| `--cli-region` | string | Yes | Region; recommended `cn-north-1` |

**Return Fields** (real response wraps them under a top-level `domain` object):

| Field | Type | Description |
|-------|------|-------------|
| `domain.id` | string | Domain ID |
| `domain.domain_name` | string | Domain name |
| `domain.cname` | string | CNAME address |
| `domain.domain_status` | string | Domain status (online/offline/configuring) |

**Return Example**:
```json
{
  "domain": {
    "id": "xxxxxxxxxx",
    "domain_name": "www.example.com",
    "cname": "www.example.com.cdn.net",
    "domain_status": "online"
  }
}
```

**Error Codes**:

| Error Code | Description | Handling |
|------------|-------------|----------|
| 200 | Success | Continue to subsequent steps |
| 404 | Domain does not exist | Abort; prompt to confirm domain ownership |
| 403 | Insufficient permissions | Abort; prompt to contact the administrator for authorization |
| CDN.0171 | Domain does not belong to the current account | Abort; prompt to confirm domain ownership |

### ShowDomainFullConfig/v2

**Purpose**: Query the full configuration of a CDN domain, including origin configuration.

**Command**:
```bash
hcloud CDN ShowDomainFullConfig/v2 --cli-region=<region> --domain_name=<domain>
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--domain_name` | string | Yes | Accelerated domain |
| `--cli-region` | string | Yes | Region; recommended `cn-north-1` |

**Return Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `configs.sources` | array | Origin configuration list |
| `configs.sources[].origin_addr` | string | Origin address (IP or domain) |
| `configs.sources[].origin_type` | string | Origin type (ipaddr/domain/obs_bucket) |
| `configs.sources[].http_port` | integer | HTTP back-to-source port |
| `configs.sources[].https_port` | integer | HTTPS back-to-source port |
| `configs.origin_protocol` | string | Back-to-source protocol (http/https/follow) |

**Return Example (IP origin)**:
```json
{
  "configs": {
    "sources": [
      {
        "origin_addr": "192.168.1.100",
        "origin_type": "ipaddr",
        "http_port": 80,
        "https_port": 443
      }
    ],
    "origin_protocol": "http"
  }
}
```

**Return Example (domain origin)**:
```json
{
  "configs": {
    "sources": [
      {
        "origin_addr": "origin.example.com",
        "origin_type": "domain",
        "http_port": 80,
        "https_port": 443
      }
    ],
    "origin_protocol": "follow"
  }
}
```

**Return Example (OBS bucket origin)**:
```json
{
  "configs": {
    "sources": [
      {
        "origin_addr": "my-bucket.obs.cn-north-4.myhuaweicloud.com",
        "origin_type": "obs_bucket",
        "http_port": 80,
        "https_port": 443
      }
    ],
    "origin_protocol": "https"
  }
}
```

**Return Example (origin not configured)**:
```json
{
  "configs": {
    "sources": [],
    "origin_protocol": "http"
  }
}
```

**Decision Logic**:

| configs.sources Status | Handling |
|------------------------|----------|
| Non-empty array | Parse origin_addr, etc.; continue to Step 3 |
| Empty array `[]` | Report "origin not configured"; abort probe step |
| Field does not exist | Report "origin not configured"; abort probe step |

**Error Codes**:

| Error Code | Description | Handling |
|------------|-------------|----------|
| 200 | Success | Parse configuration |
| 404 | Domain does not exist | Abort |
| 403 | Insufficient permissions | Abort; prompt to contact the administrator for authorization |

## Probe Command Description

### scripts/origin_probe.py (Origin Connectivity Probe)

**Path** (relative to skill root): `scripts/origin_probe.py`

**Command format**:
```bash
python scripts/origin_probe.py --scheme <http|https> --host <origin_addr> --port <port> [--timeout 10]
```

**Arguments**:

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--scheme` | string | Yes | URL scheme (`http` or `https`) |
| `--host` | string | Yes | Origin host (IP literal or domain name) |
| `--port` | integer | Yes | Origin port (1-65535) |
| `--timeout` | integer | No | Request timeout in seconds (default 10, range 1-30) |

**Library requirement**: `requests >= 2.25`

**Output JSON schema**:

> **Output envelope**: the script wraps its output in `{result, data, error_msg}`; business fields are inside `data`.

```json
{
  "result": "success",
  "data": {
    "scheme": "https",
    "host": "origin.example.com",
    "port": 443,
    "connected": true,
    "http_status": 200,
    "is_private_address": false,
    "duration_ms": 210,
    "error": null
  },
  "error_msg": ""
}
```

| Field | Type | Description |
|-------|------|-------------|
| `scheme` | string | The `--scheme` argument echoed back |
| `host` | string | The `--host` argument echoed back |
| `port` | integer | The `--port` argument echoed back |
| `data.connected` | boolean | `true` when an HTTP response was received |
| `data.http_status` | integer \| null | HTTP status code, or `null` when no response |
| `data.is_private_address` | boolean | `true` when the host is a private/loopback/link-local IP literal |
| `data.duration_ms` | integer | Probe duration in milliseconds |
| `data.error` | object \| null | `null` on success; otherwise `{"reason": <code>, "message": <string>}` |

**Error reason codes**: `connect_timeout`, `connect_failed`, `tls_handshake_failed`, `missing_library`, `invalid_scheme`, `invalid_host`, `invalid_port`, `invalid_timeout`.

**Probe Strategy (based on origin_protocol)**:

| origin_protocol | Probe Command |
|-----------------|---------------|
| http | `python scripts/origin_probe.py --scheme http --host <origin_addr> --port <http_port>` |
| https | `python scripts/origin_probe.py --scheme https --host <origin_addr> --port <https_port>` |
| follow | Execute both http and https probes |

**Decision Logic (consumed by the report step)**:

| `data.connected` / `data.http_status` | Conclusion | Handling |
|------------------------------|------------|----------|
| `data.connected=true`, `data.http_status` 200 / 3xx | Origin reachable | Report pass |
| `data.connected=true`, `data.http_status` 5xx | Origin unreachable | Report failure + IP whitelist prompt |
| `connected=false` (`error.reason=connect_failed`) | Origin unreachable | Report failure + IP whitelist prompt |
| `connected=false` (`error.reason=connect_timeout`) | Probe timeout | Report timeout |

## Important Notes

- All hcloud commands should use `--cli-region=<region>`
- All hcloud parameters must use the `--key=value` format (connected with equals sign)
- `scripts/origin_probe.py` enforces a 10-second timeout via `--timeout 10` (default)
- This skill uses only query APIs and does not call any write operations
- When origin_type is obs_bucket, the origin is an OBS bucket; the probe logic is the same
- When origin_protocol is follow, CDN selects the back-to-source protocol based on the client protocol; both http and https must be probed
