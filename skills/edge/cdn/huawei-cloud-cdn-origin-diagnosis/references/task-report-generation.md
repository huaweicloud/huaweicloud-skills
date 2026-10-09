# Step 4: Generate Diagnosis Report

Aggregate probe results and generate a structured text diagnosis report with IP whitelist prompts and remediation suggestions.

## Report Format

```
==================== CDN Origin Server Diagnosis Report ====================
Analysis Time: <ISO 8601 time>
Target Domain: <domain>

--- Origin Configuration ---
origin_addr: <origin address>
origin_type: <origin type>
http_port: <HTTP port>
https_port: <HTTPS port>
origin_protocol: <back-to-source protocol>

--- Diagnosis Items ---
[Domain Permission Validation]: ✅ Pass / ❌ Fail / ⚠️ Warning
  Detail: <details>
[Origin Configuration Query]: ✅ Pass / ❌ Fail / ⚠️ Warning / N/A
  Detail: <details>
[Origin Connectivity Probe]: ✅ Pass / ❌ Fail / ⚠️ Warning / N/A
  Detail: <HTTP status code + probe result>

--- Conclusion ---
Status: <overall status>
Suggestion: <remediation suggestion>
```

## Status Marker Rules

| Marker | Meaning | Usage Scenario |
|--------|---------|----------------|
| ✅ Pass | Passed | Probe result meets expectations |
| ❌ Fail | Failed | Probe result does not meet expectations (origin unreachable) |
| ⚠️ Warning | Warning | Probe timeout or partial result |
| N/A | Not applicable | Origin not configured or a preceding step already aborted |

## Report Generation Rules

1. **Analysis time**: Use ISO 8601 format (e.g., `2026-08-12T10:00:00+08:00`)
2. **Target domain**: The domain_name entered by the user
3. **Origin configuration info**: origin_addr, origin_type, http_port, https_port, origin_protocol parsed in Step 2
4. **Diagnosis item list**: List all diagnosis items in step order
5. **Detail**: Each item includes the probe result and key information
6. **Conclusion**: Overall status (Pass / Fail / Partial Pass / Cannot Diagnose)
7. **Remediation suggestion**: Provide specific remediation suggestions based on failed items, including IP whitelist prompts

## Probe Field Sources

The "Origin Connectivity Probe" diagnosis item is populated from the JSON
output of `scripts/origin_probe.py`:

| Report Field | JSON Source Field | Notes |
|--------------|-------------------|-------|
| HTTP status code | `origin_probe.py` → `data.http_status` | `null` when no response was received (e.g. timeout, connection refused) |
| Connectivity | `origin_probe.py` → `data.connected` | `true` when a response was received; `false` otherwise |
| Private address marker | `origin_probe.py` → `data.is_private_address` | When `true`, append a note that the origin is a private IP and CDN back-to-source cannot reach it directly |
| Probe duration | `origin_probe.py` → `data.duration_ms` | Optional supplementary detail |
| Probe failure reason | `origin_probe.py` → `data.error.reason` | `connect_timeout`, `connect_failed`, `tls_handshake_failed`, `missing_library`; surfaced in the detail line when `data.error` is non-null |

## Conclusion Status Judgment

| Scenario | Overall Status | Remediation Suggestion |
|----------|----------------|------------------------|
| Origin reachable | ✅ Origin diagnosis passed | Origin connectivity is normal. If back-to-source failures persist, check the back-to-source configuration consistency in the CDN console. |
| Origin unreachable | ❌ Origin unreachable | The origin may have a whitelist configured. Please confirm that the CDN back-to-source IP ranges have been added to the origin whitelist. |
| Probe timeout | ⚠️ Origin probe timeout | Manual verification of origin connectivity is recommended; confirm network and firewall configuration and retry. |
| Origin not configured | ❌ Origin not configured | Please configure the origin address and port in the CDN console. |
| Origin partially reachable (follow protocol, only one of HTTP/HTTPS reachable) | ⚠️ Origin partially reachable | The HTTP/HTTPS back-to-source protocol is abnormal. Please check the service status on the corresponding port of the origin. |
| Insufficient permissions | ❌ Cannot diagnose | Please contact the administrator to grant the CDN query permission (`cdn:*:query*`). |
| Domain does not exist | ❌ Cannot diagnose | Please confirm the domain ownership; the domain is not under the current account. |

## IP Whitelist Prompt Rule

When the origin is unreachable (5xx or connection failed), the remediation suggestion **must include**:

> "The origin may have a whitelist configured. Please confirm that the CDN back-to-source IP ranges have been added to the origin whitelist."

Additional recommendations (optional supplements):
- Check the origin firewall, security group, and WAF configuration
- Obtain CDN back-to-source IP ranges via the Huawei Cloud CDN console or technical support
- Temporarily allow the CDN back-to-source IP ranges on the origin, then re-probe

## Example Reports

### Origin Reachable

```
==================== CDN Origin Server Diagnosis Report ====================
Analysis Time: 2026-08-12T10:00:00+08:00
Target Domain: www.example.com

--- Origin Configuration ---
origin_addr: 192.168.1.100
origin_type: ipaddr
http_port: 80
https_port: 443
origin_protocol: http

--- Diagnosis Items ---
[Domain Permission Validation]: ✅ Pass
  Detail: Domain belongs to the current account, domain_id=xxxxxxxxxx
[Origin Configuration Query]: ✅ Pass
  Detail: Origin configuration found, origin_addr=192.168.1.100, origin_type=ipaddr
[Origin Connectivity Probe]: ✅ Pass
  Detail: HTTP 200, origin reachable

--- Conclusion ---
Status: Origin diagnosis passed
Suggestion: Origin connectivity is normal. If back-to-source failures persist, check the back-to-source configuration consistency in the CDN console.
```

### Origin Unreachable (with IP whitelist prompt)

```
==================== CDN Origin Server Diagnosis Report ====================
Analysis Time: 2026-08-12T10:05:00+08:00
Target Domain: www.example.com

--- Origin Configuration ---
origin_addr: 192.168.1.100
origin_type: ipaddr
http_port: 80
https_port: 443
origin_protocol: http

--- Diagnosis Items ---
[Domain Permission Validation]: ✅ Pass
  Detail: Domain belongs to the current account, domain_id=xxxxxxxxxx
[Origin Configuration Query]: ✅ Pass
  Detail: Origin configuration found, origin_addr=192.168.1.100, origin_type=ipaddr
[Origin Connectivity Probe]: ❌ Fail
  Detail: HTTP 502, origin unreachable

--- Conclusion ---
Status: Origin unreachable
Suggestion: The origin may have a whitelist configured. Please confirm that the CDN back-to-source IP ranges have been added to the origin whitelist.
```

### Origin Not Configured

```
==================== CDN Origin Server Diagnosis Report ====================
Analysis Time: 2026-08-12T10:10:00+08:00
Target Domain: www.example.com

--- Origin Configuration ---
origin_addr: (not configured)
origin_type: (not configured)
http_port: (not configured)
https_port: (not configured)
origin_protocol: (not configured)

--- Diagnosis Items ---
[Domain Permission Validation]: ✅ Pass
  Detail: Domain belongs to the current account, domain_id=xxxxxxxxxx
[Origin Configuration Query]: ❌ Fail
  Detail: configs.sources is empty; origin not configured
[Origin Connectivity Probe]: N/A
  Detail: Origin not configured; probe step skipped

--- Conclusion ---
Status: Origin not configured
Suggestion: Please configure the origin address and port in the CDN console.
```

### Probe Timeout

```
==================== CDN Origin Server Diagnosis Report ====================
Analysis Time: 2026-08-12T10:15:00+08:00
Target Domain: www.example.com

--- Origin Configuration ---
origin_addr: 192.168.1.100
origin_type: ipaddr
http_port: 80
https_port: 443
origin_protocol: http

--- Diagnosis Items ---
[Domain Permission Validation]: ✅ Pass
  Detail: Domain belongs to the current account, domain_id=xxxxxxxxxx
[Origin Configuration Query]: ✅ Pass
  Detail: Origin configuration found, origin_addr=192.168.1.100, origin_type=ipaddr
[Origin Connectivity Probe]: ⚠️ Warning
  Detail: Probe timed out; no response within 10 seconds

--- Conclusion ---
Status: Origin probe timeout
Suggestion: Manual verification of origin connectivity is recommended; confirm network and firewall configuration and retry.
```
