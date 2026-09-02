# Step 4: Generate Diagnosis Report

Aggregate probe results and generate a structured text diagnosis report.

## Report Format

```
==================== CDN DNS Resolution Diagnosis Report ====================
Analysis Time: <ISO 8601 time>
Target Domain: <domain>
Expected CNAME: <CDN expected CNAME>

--- DNS Resolution ---
Resolved IPs: <IP1, IP2, ...>
IP Count: <count>

--- Diagnosis Items ---
[Domain Permission Check]: ✅ Pass / ❌ Fail / ⚠️ Warning
  Detail: <detail>
[DNS Resolution Probe]: ✅ Pass / ❌ Fail / ⚠️ Warning
  Detail: <number and list of resolved IPs>
  Resolved IPs: <IP list>
[IP Attribution Check]: ✅ Pass / ❌ Fail / ⚠️ Warning / N/A
  Detail: <X/Y IPs belong to Huawei Cloud CDN>
  Huawei IPs: <IPs belonging to Huawei Cloud>
  Non-Huawei IPs: <IPs not belonging to Huawei Cloud>

--- Conclusion ---
Status: <overall status>
Suggestion: <remediation suggestion>
```

## Status Mark Rules

| Mark | Meaning | Usage Scenario |
|------|---------|----------------|
| ✅ Pass | Passed | Probe result meets expectation |
| ❌ Fail | Failed | Probe result does not meet expectation |
| ⚠️ Warning | Warning | Probe timeout, partial result, or false positive scenario |
| N/A | Not applicable | Step not executed (e.g., IP attribution check is N/A when the domain is not resolved) |

## Report Generation Rules

1. **Analysis Time**: Use ISO 8601 format (e.g., `2026-08-12T10:00:00+08:00`)
2. **Target Domain**: The domain_name entered by the user
3. **Expected CNAME**: CDN expected CNAME obtained in Step 1
4. **DNS Resolution**: List the IPs and count resolved by `dns_resolve.py` (source: the JSON `data.resolved_ips` field)
5. **Diagnosis Items List**: List all diagnosis items in step order
6. **Detail**: Each item contains the probe result and key information
7. **IP Attribution Detail**: List IPs that belong and do not belong to Huawei Cloud
8. **Conclusion**: Overall status
9. **Remediation Suggestion**: Provide specific remediation suggestions based on the status

**Probe output field mapping** (from Step 2 `dns_resolve.py` JSON to report sections):

| Report Section | JSON Field | Notes |
|----------------|------------|-------|
| Resolved IPs | `data.resolved_ips` | Joined with `, ` for display; empty shown as `(none)` |
| IP Count | `len(data.resolved_ips)` | Before 20-IP truncation |
| DNS Resolution Probe status | `data.error.reason` + `data.resolved_ips` | `null` + non-empty → Pass; `dns_timeout` → Warning; empty → Fail |
| Probe duration (optional) | `data.duration_ms` | For diagnostics if needed |

## Conclusion Status Decision

| Scenario | Overall Status | Remediation Suggestion |
|----------|----------------|------------------------|
| Resolved to Huawei Cloud | ✅ Resolved to Huawei Cloud CDN | DNS configuration is correct, no remediation needed |
| Not resolved (`dns_resolve.py` returns empty `data.resolved_ips`) | ❌ Domain not resolved | Check DNS configuration: add a CNAME record pointing the domain to `<cname>`, wait for DNS to take effect, then retry |
| Not resolved to Huawei Cloud (all IP attribution false) | ❌ Not resolved to Huawei Cloud CDN | Configure the DNS CNAME record to `<cname>`, wait for DNS to take effect, then retry |
| Partial resolution (false positive) | ⚠️ Partially resolved to Huawei Cloud CDN | Some regions may have switched; multi-region probing is recommended to confirm the global resolution status |
| DNS probe timeout (`data.error.reason == "dns_timeout"`) | ⚠️ DNS probe timeout | Manually run `python scripts/dns_resolve.py --domain <domain>` to verify, check local network and DNS configuration, then retry |
| Permission denied | ❌ Unable to diagnose | Contact the administrator to grant CDN domain query permission |
| Domain does not exist | ❌ Unable to diagnose | Confirm the domain ownership; the domain is not under the current account |

## False Positive Prompt Rules

When the IP attribution is **partial resolution** (mixed belongs), the report must include the following prompt:

> **⚠️ False Positive Prompt:** Some regions may have switched; multi-region probing is recommended

Specific prompt text (written into Suggestion):
- "Some regions may have switched; multi-region probing is recommended to confirm the global resolution status"
- Optional additional suggestion: Re-run `dns_resolve.py` after switching the host's system DNS resolver (e.g., to `8.8.8.8` or `114.114.114.114`) for verification

## Example Reports

### Scenario 1: Resolved to Huawei Cloud

```
==================== CDN DNS Resolution Diagnosis Report ====================
Analysis Time: 2026-08-12T10:00:00+08:00
Target Domain: www.example.com
Expected CNAME: www.example.com.cdn.net

--- DNS Resolution ---
Resolved IPs: 1.2.3.4, 5.6.7.8
IP Count: 2

--- Diagnosis Items ---
[Domain Permission Check]: ✅ Pass
  Detail: Domain belongs to the current account, domain_id=xxxxxxxxxx
[DNS Resolution Probe]: ✅ Pass
  Detail: Resolved to 2 IPs
  Resolved IPs: 1.2.3.4, 5.6.7.8
[IP Attribution Check]: ✅ Pass
  Detail: 2/2 IPs belong to Huawei Cloud CDN
  Huawei IPs: 1.2.3.4, 5.6.7.8
  Non-Huawei IPs: (none)

--- Conclusion ---
Status: Resolved to Huawei Cloud CDN
Suggestion: DNS configuration is correct, no remediation needed
```

### Scenario 2: Not Resolved (dns_resolve.py returns empty data.resolved_ips)

```
==================== CDN DNS Resolution Diagnosis Report ====================
Analysis Time: 2026-08-12T10:00:00+08:00
Target Domain: unresolved.example.com
Expected CNAME: unresolved.example.com.cdn.net

--- DNS Resolution ---
Resolved IPs: (none)
IP Count: 0

--- Diagnosis Items ---
[Domain Permission Check]: ✅ Pass
  Detail: Domain belongs to the current account, domain_id=xxxxxxxxxx
[DNS Resolution Probe]: ❌ Fail
  Detail: Domain not resolved, dns_resolve.py returned empty data.resolved_ips
  Resolved IPs: (none)
[IP Attribution Check]: N/A
  Detail: Domain not resolved, skip IP attribution check

--- Conclusion ---
Status: Domain not resolved
Suggestion: Check DNS configuration: add a CNAME record pointing the domain to unresolved.example.com.cdn.net, wait for DNS to take effect, then retry
```

### Scenario 3: Partial Resolution (false positive)

```
==================== CDN DNS Resolution Diagnosis Report ====================
Analysis Time: 2026-08-12T10:00:00+08:00
Target Domain: partial.example.com
Expected CNAME: partial.example.com.cdn.net

--- DNS Resolution ---
Resolved IPs: 1.2.3.4, 10.0.0.1
IP Count: 2

--- Diagnosis Items ---
[Domain Permission Check]: ✅ Pass
  Detail: Domain belongs to the current account, domain_id=xxxxxxxxxx
[DNS Resolution Probe]: ✅ Pass
  Detail: Resolved to 2 IPs
  Resolved IPs: 1.2.3.4, 10.0.0.1
[IP Attribution Check]: ⚠️ Warning
  Detail: 1/2 IPs belong to Huawei Cloud CDN
  Huawei IPs: 1.2.3.4
  Non-Huawei IPs: 10.0.0.1

--- Conclusion ---
Status: Partially resolved to Huawei Cloud CDN
Suggestion: Some regions may have switched; multi-region probing is recommended to confirm the global resolution status
```

### Scenario 4: DNS Probe Timeout

```
==================== CDN DNS Resolution Diagnosis Report ====================
Analysis Time: 2026-08-12T10:00:00+08:00
Target Domain: timeout.example.com
Expected CNAME: timeout.example.com.cdn.net

--- DNS Resolution ---
Resolved IPs: (timeout)
IP Count: N/A

--- Diagnosis Items ---
[Domain Permission Check]: ✅ Pass
  Detail: Domain belongs to the current account, domain_id=xxxxxxxxxx
[DNS Resolution Probe]: ⚠️ Warning
  Detail: DNS probe timeout, no return in 10 seconds
  Resolved IPs: (timeout)
[IP Attribution Check]: N/A
  Detail: DNS probe timeout, skip IP attribution check

--- Conclusion ---
Status: DNS probe timeout
Suggestion: Manually run `python scripts/dns_resolve.py --domain <domain>` to verify, check local network and DNS configuration, then retry
```
