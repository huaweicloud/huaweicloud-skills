# Step 3: Origin Connectivity Probe

Select the probe protocol based on origin_protocol, and probe origin server connectivity via `scripts/origin_probe.py`, parsing the JSON output to obtain the HTTP status code and connectivity result.

## 3.1 Select Probe Protocol

Select the probe protocol and port based on the `origin_protocol` parsed in Step 2:

| origin_protocol | Probe Protocol | Probe Command |
|-----------------|----------------|---------------|
| http | HTTP | `python scripts/origin_probe.py --scheme http --host <origin_addr> --port <http_port>` |
| https | HTTPS | `python scripts/origin_probe.py --scheme https --host <origin_addr> --port <https_port>` |
| follow | HTTP + HTTPS | Execute both of the above commands |

**If Step 2 determined that sources is empty, skip this step.**

## 3.2 Execute Probe

### HTTP Probe

**Command**:
```bash
python scripts/origin_probe.py --scheme http --host <origin_addr> --port <http_port>
```

### HTTPS Probe

**Command**:
```bash
python scripts/origin_probe.py --scheme https --host <origin_addr> --port <https_port>
```

### Input Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--scheme` | string | Yes | URL scheme (`http` or `https`) |
| `--host` | string | Yes | Origin host (IP literal or domain name) |
| `--port` | integer | Yes | Origin port (1-65535) |
| `--timeout` | integer | No | Request timeout in seconds (default 10, range 1-30) |

### Output JSON Schema

> **Output envelope**: the script wraps its output in the platform standard `{result, data, error_msg}` envelope (`format_output()` in `origin_probe.py`); business fields are inside `data`. Parse `data.*`, not the top level.

The script emits a single JSON object on stdout:

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
| `data.scheme` | string | The `--scheme` argument echoed back (`http` / `https`) |
| `data.host` | string | The `--host` argument echoed back |
| `data.port` | integer | The `--port` argument echoed back |
| `data.connected` | boolean | `true` when a TCP/HTTP connection was established and an HTTP response received; `false` otherwise |
| `data.http_status` | integer \| null | HTTP status code returned by the origin (e.g. `200`, `502`); `null` when no response was received |
| `data.is_private_address` | boolean | `true` when `--host` is an IP literal in a private/loopback/link-local/reserved range; surfaced for topology context (accepted residual risk R-SEC-1). `false` for domain-name hosts. |
| `data.duration_ms` | integer | Probe duration in milliseconds |
| `data.error` | object \| null | `null` on success; otherwise `{ "reason": <code>, "message": <string> }` |

### Error Reason Codes

| `data.error.reason` | Library Exception | Meaning |
|----------------|-------------------|---------|
| `connect_timeout` | `requests.ConnectTimeout` / `TimeoutError` | TCP connect exceeded the timeout |
| `connect_failed` | `requests.ConnectionError` (non-TLS) | Connection refused / network unreachable / DNS resolution failure |
| `tls_handshake_failed` | `requests.exceptions.SSLError` | TLS handshake failed (invalid cert, protocol mismatch) |
| `missing_library` | `ImportError` | `requests` not importable; prerequisite failure |
| `invalid_scheme` / `invalid_host` / `invalid_port` / `invalid_timeout` | — | Argument validation failure (exit code 2) |

### HEAD-First, GET Fallback Behavior

The script issues `requests.head(url, timeout=10, allow_redirects=False)` by default (matching the original `curl -o /dev/null` behavior of not fetching the body). When the origin returns HTTP 405 (Method Not Allowed), the script falls back to `requests.get(url, timeout=10, allow_redirects=False, stream=True)` and closes the stream immediately. Redirects are never followed in either path.

### Timeout Enforcement

The 10-second timeout is enforced by the script via `requests` `timeout` parameter. The default is `--timeout 10`; the value is constrained to the range `[1, 30]`.

## 3.3 Determine Probe Result

### JSON Field Judgment

| `data.connected` | `data.http_status` | Conclusion | Status Marker | Handling |
|-------------|---------------|------------|---------------|----------|
| `true` | 200 / 2xx | Origin reachable | ✅ Pass | Report pass |
| `true` | 3xx | Origin reachable (redirect) | ✅ Pass | Report pass; note redirect |
| `true` | 4xx | Origin reachable but request abnormal | ⚠️ Warning | Report warning; origin service may be abnormal |
| `true` | 5xx | Origin unreachable | ❌ Fail | Report failure + IP whitelist prompt |
| `false` | `null` | Origin unreachable | ❌ Fail | Report failure + IP whitelist prompt |
| `false` | `null` + `data.error.reason=connect_timeout` | Probe timeout | ⚠️ Warning | Report timeout |

### IP Whitelist Prompt Rule

**Trigger condition**: Origin unreachable (`data.connected=false`, or `data.http_status` is 5xx)

**Prompt content**:
> "The origin may have a whitelist configured. Please confirm that the CDN back-to-source IP ranges have been added to the origin whitelist."

**Additional recommendations**:
1. Check whether the origin firewall allows CDN back-to-source IP ranges
2. Check the origin security group configuration
3. Check the origin WAF or other security policies
4. Obtain the CDN back-to-source IP ranges via the Huawei Cloud CDN console or technical support
5. Temporarily allow the CDN back-to-source IP ranges on the origin, then re-probe

### Timeout Handling

**Trigger condition**: `data.error.reason == "connect_timeout"` (the script could not establish a TCP connection within the 10-second budget)

**Handling**:
1. Return partial results; note "Origin probe timed out. Manual verification recommended."
2. Check local network connectivity
3. Confirm that the origin address and port are correct
4. Confirm the origin firewall configuration
5. Recommend that the user manually run the probe command to confirm

### Private Address Flag Handling

When `data.is_private_address == true`, the report should note: "The origin address is a private/loopback/link-local IP. CDN back-to-source traffic cannot reach private addresses directly; ensure the origin is reachable from the CDN back-to-source IP ranges." This is informational and does not change the pass/fail verdict (the `data.connected` and `data.http_status` fields remain authoritative).

## 3.4 Merge Multiple Probe Results (follow protocol)

When origin_protocol=follow, both http and https must be probed, and the results merged:

| HTTP Probe (`data.connected`/`data.http_status`) | HTTPS Probe (`data.connected`/`data.http_status`) | Overall Conclusion | Status Marker |
|----------------------------------------|-----------------------------------------|--------------------|--------------|
| Reachable | Reachable | Origin reachable | ✅ Pass |
| Reachable | Unreachable | Partially reachable (HTTPS abnormal) | ⚠️ Warning |
| Unreachable | Reachable | Partially reachable (HTTP abnormal) | ⚠️ Warning |
| Unreachable | Unreachable | Origin unreachable | ❌ Fail + IP whitelist prompt |
| Timeout | Any | Probe timeout | ⚠️ Warning |
| Any | Timeout | Probe timeout | ⚠️ Warning |

## 3.5 Output Records

After probing is complete, record the following information for the report:
- Probe protocol (http / https / follow)
- Probe URL (e.g., http://192.168.1.100:80)
- `data.http_status` (from `origin_probe.py`)
- `data.connected` (from `origin_probe.py`)
- `data.is_private_address` (from `origin_probe.py`, surfaced when `true`)
- Probe result (reachable / unreachable / timeout)
- Whether an IP whitelist prompt is attached

## Exception Handling

| Exception Scenario | Handling |
|--------------------|----------|
| `requests` library not installed | Script emits `data.error.reason=missing_library`; prompt to install via `pip install requests>=2.25`; see cli-installation-guide.md |
| Origin address is a domain that cannot be resolved | Script emits `data.error.reason=connect_failed`; report "Origin domain resolution failed"; mark ❌ Fail |
| HTTPS certificate validation failed | Script emits `data.error.reason=tls_handshake_failed`; report warning; origin may be reachable but certificate is abnormal (do not bypass verification) |
| Invalid scheme/host/port/timeout argument | Script emits `data.error.reason=invalid_*` and exits with code 2; correct the argument and retry |
| sources is empty (Step 2 already aborted) | Skip this step |

## Example

```bash
# HTTP probe
python scripts/origin_probe.py --scheme http --host 192.168.1.100 --port 80
# {"result":"success","data":{"scheme":"http","host":"192.168.1.100","port":80,"connected":true,"http_status":200,"is_private_address":true,"duration_ms":12,"error":null},"error_msg":""}
# → origin reachable ✅ (note: data.is_private_address=true; CDN cannot back-to-source a private IP directly)

# HTTPS probe returning 502
python scripts/origin_probe.py --scheme https --host 192.168.1.100 --port 443
# {"result":"success","data":{"scheme":"https","host":"192.168.1.100","port":443,"connected":true,"http_status":502,"is_private_address":true,"duration_ms":18,"error":null},"error_msg":""}
# → origin unreachable ❌ + IP whitelist prompt

# Timeout failure
python scripts/origin_probe.py --scheme http --host 10.0.0.255 --port 80
# {"scheme":"http","host":"10.0.0.255","port":80,"connected":false,"http_status":null,"is_private_address":true,"duration_ms":10023,"error":{"reason":"connect_timeout","message":"..."}}
# → probe timeout ⚠️
```
