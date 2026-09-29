# Step 5: Generate Diagnosis Report

Aggregate the query and probe results to generate a structured text diagnosis report.

## Report Format

```
==================== CDN Certificate Diagnosis Report ====================
Analysis Time: <ISO 8601 time>
Target Domain: <domain>

--- Certificate Summary (Common Info) ---
Certificate Name: <cert_name> / N/A
Certificate Status: <not configured | configuring | configured>
Issuer: <data.tls.issuer_cn from cert_probe.py>
CN: <data.tls.subject_cn from cert_probe.py>
SAN: <data.tls.san_list from cert_probe.py, joined with ", ">
Valid From: <data.tls.not_before from cert_probe.py, ISO 8601 UTC>
Expires On: <data.tls.not_after from cert_probe.py, ISO 8601 UTC> (API expiration_time: <readable date>)
Days Remaining: <data.days_remaining> (<data.status>)

--- Diagnosis Items ---
[Domain Permission Validation]: ✅ Pass / ❌ Fail / ⚠️ Warning
  Detail: <detail>
[Certificate Configuration Status]: ✅ Pass / ❌ Fail / ⚠️ Warning
  Detail: <https_status / cert_name / expiration_time>
[Actual Certificate Probe]: Pass / Fail / Warning / N/A
  Detail: <probe result>
  Expire Date: <data.tls.not_after from cert_probe.py, ISO 8601 UTC>
  Issuer: <data.tls.issuer_cn from cert_probe.py>
  CN: <data.tls.subject_cn from cert_probe.py>
  SAN: <data.tls.san_list from cert_probe.py, joined with ", ">
[Days Remaining Calculation]: ✅ Pass / ❌ Fail / ⚠️ Warning / N/A
  Detail: data.days_remaining=<int>, data.status=<normal|warning|expired|unknown>

--- Conclusion ---
Status: <overall status>
Suggestion: <fix recommendation>
```

> **⚠️ Certificate Summary is mandatory.** The `Certificate Summary (Common Info)` block MUST always be printed at the top of the report (below the header), explicitly showing the certificate's common information to the user: certificate name, status, issuer, CN, SAN, validity period (Valid From / Expires On), and days remaining. These fields are the certificate's commonly used information and must be fed back to the user explicitly, not buried in prose. When a field is unavailable (e.g., probe skipped because https_status=0), print `N/A` for that field.

## Status Marker Rules

| Marker | Meaning | Usage Scenario |
|--------|---------|----------------|
| ✅ Pass | Passed | Probe/calculation result normal |
| ❌ Fail | Failed | Probe failed or certificate already expired |
| ⚠️ Warning | Warning | Certificate about to expire, configuring, probe timed out, or partial result |
| N/A | Not applicable | Step not involved (e.g., probe skipped when https_status=0) |

## Report Generation Rules

1. **Analysis time**: use ISO 8601 format (e.g., `2026-08-12T10:00:00+08:00`)
2. **Target domain**: the domain_name entered by the user
3. **Certificate Summary block**: always print the mandatory `Certificate Summary (Common Info)` block with certificate name, status, issuer, CN, SAN, Valid From / Expires On (from probe) and API `expiration_time` converted to a readable date; use `N/A` for unavailable fields
4. **Timestamp formatting**: API `expiration_time` is a millisecond timestamp — convert it to a readable UTC/UTC+8 date (e.g., `2026-09-12 08:00:00 +08:00`) before printing; never print the raw millisecond value as the primary display
5. **Diagnosis item list**: list all diagnosis items in step order
6. **Detail**: each item contains probe results and key information
7. **Days remaining**: fill in `data.days_remaining` and `data.status` based on the Python script output (inside the `{result, data, error_msg}` envelope)
8. **expiration_time empty**: report "Certificate expiration time unknown; API did not return a valid expiration time" in the detail, and attach the raw API response
9. **Conclusion**: overall status (Normal / About to Expire / Expired / Not Configured / Configuring / Cannot Diagnose)
10. **Fix recommendation**: provide specific fix recommendations based on the status

## Conclusion Status Decision

| Scenario | Overall Status | Fix Recommendation |
|----------|----------------|---------------------|
| status=normal (`data.days_remaining>30`) | ✅ Certificate status normal | Certificate has sufficient remaining validity; no action needed |
| status=warning (`0 < data.days_remaining ≤ 30`) | ⚠️ Certificate about to expire | Certificate will expire in <data.days_remaining> days; recommend updating the certificate in advance and redeploying it to CDN |
| status=expired (`data.days_remaining ≤ 0`) | ❌ Certificate expired | Certificate has expired; HTTPS service may be affected; update the certificate immediately and deploy it to CDN |
| status=unknown (expiration_time empty) | Expiration time unknown | API did not return a valid expiration time; please judge manually based on the raw API response or the `data.tls.not_after` field probed by `cert_probe.py` |
| https_status=0 (not configured) | ❌ Certificate not configured | This domain has no HTTPS certificate configured; please configure a certificate in the CDN console or via hcloud CLI |
| https_status=2 (configuring) | ⚠️ Certificate configuring | Certificate is configuring; please wait for configuration to complete before diagnosing |
| Certificate probe timed out | Certificate probe timed out | Recommend running `python scripts/cert_probe.py --domain <domain> --timeout 10` manually to confirm the actual certificate status; check the network connection and CNAME effectiveness |
| Insufficient permission | ❌ Cannot diagnose | Contact the administrator to grant CDN domain query and configuration query permissions |
| Domain does not exist | ❌ Cannot diagnose | Please confirm domain ownership; the domain is not under the current account |

## Example Reports

### Normal Certificate (status=normal)

```
==================== CDN Certificate Diagnosis Report ====================
Analysis Time: 2026-08-12T10:00:00+08:00
Target Domain: www.example.com

--- Certificate Summary (Common Info) ---
Certificate Name: example-cert
Certificate Status: configured
Issuer: TrustAsia TLS RSA CA
CN: www.example.com
SAN: www.example.com, example.com
Valid From: 2025-09-12T00:00:00Z
Expires On: 2026-09-12T00:00:00Z (API expiration_time: 2026-09-12 08:00:00 +08:00)
Days Remaining: 31 (normal)

--- Diagnosis Items ---
[Domain Permission Validation]: ✅ Pass
  Detail: Domain belongs to current account, domain_id=xxxxxxxxxx, domain_status=online
[Certificate Configuration Status]: ✅ Pass
  Detail: https_status=3, cert_name=example-cert, expiration_time=1789824000000
[Actual Certificate Probe]: ✅ Pass
  Detail: HTTPS probe succeeded; certificate chain valid
  Expire Date: 2026-09-12T00:00:00Z
  Issuer: TrustAsia TLS RSA CA
  CN: www.example.com
  SAN: www.example.com, example.com
[Days Remaining Calculation]: ✅ Pass
  Detail: data.days_remaining=31, data.status=normal

--- Conclusion ---
Status: Certificate status normal
Suggestion: Certificate has sufficient remaining validity; no action needed
```

### Certificate About to Expire (status=warning)

```
==================== CDN Certificate Diagnosis Report ====================
Analysis Time: 2026-08-12T10:00:00+08:00
Target Domain: www.example.com

--- Certificate Summary (Common Info) ---
Certificate Name: example-cert
Certificate Status: configured
Issuer: TrustAsia TLS RSA CA
CN: www.example.com
SAN: www.example.com, example.com
Valid From: 2025-08-27T00:00:00Z
Expires On: 2026-08-27T00:00:00Z (API expiration_time: 2026-08-27 08:00:00 +08:00)
Days Remaining: 15 (warning)

--- Diagnosis Items ---
[Domain Permission Validation]: ✅ Pass
  Detail: Domain belongs to current account, domain_id=xxxxxxxxxx
[Certificate Configuration Status]: ✅ Pass
  Detail: https_status=3, cert_name=example-cert, expiration_time=1723852800000
[Actual Certificate Probe]: ✅ Pass
  Detail: HTTPS probe succeeded; certificate chain valid
  Expire Date: 2026-08-27T00:00:00Z
  Issuer: TrustAsia TLS RSA CA
  CN: www.example.com
[Days Remaining Calculation]: ⚠️ Warning
  Detail: data.days_remaining=15, data.status=warning

--- Conclusion ---
Status: Certificate about to expire
Suggestion: Certificate will expire in 15 days; recommend updating the certificate in advance and redeploying it to CDN
```

### Certificate Not Configured (https_status=0)

```
==================== CDN Certificate Diagnosis Report ====================
Analysis Time: 2026-08-12T10:00:00+08:00
Target Domain: www.example.com

--- Certificate Summary (Common Info) ---
Certificate Name: N/A
Certificate Status: not configured
Issuer: N/A
CN: N/A
SAN: N/A
Valid From: N/A
Expires On: N/A
Days Remaining: N/A

--- Diagnosis Items ---
[Domain Permission Validation]: ✅ Pass
  Detail: Domain belongs to current account, domain_id=xxxxxxxxxx
[Certificate Configuration Status]: ❌ Fail
  Detail: https_status=0, HTTPS certificate not configured
[Actual Certificate Probe]: N/A
  Detail: Certificate not configured; probe skipped
[Days Remaining Calculation]: N/A
  Detail: Certificate not configured; calculation skipped

--- Conclusion ---
Status: Certificate not configured
Suggestion: This domain has no HTTPS certificate configured; please configure a certificate in the CDN console or via hcloud CLI
```

### Expiration Time Unknown (expiration_time empty)

```
==================== CDN Certificate Diagnosis Report ====================
Analysis Time: 2026-08-12T10:00:00+08:00
Target Domain: www.example.com

--- Certificate Summary (Common Info) ---
Certificate Name: example-cert
Certificate Status: configured
Issuer: TrustAsia TLS RSA CA
CN: www.example.com
SAN: www.example.com, example.com
Valid From: 2025-09-12T00:00:00Z
Expires On: 2026-09-12T00:00:00Z (API expiration_time: N/A)
Days Remaining: unknown (API expiration_time missing; probed not_after: 2026-09-12T00:00:00Z)

--- Diagnosis Items ---
[Domain Permission Validation]: ✅ Pass
  Detail: Domain belongs to current account, domain_id=xxxxxxxxxx
[Certificate Configuration Status]: ✅ Pass
  Detail: https_status=3, cert_name=example-cert, expiration_time=(empty)
[Actual Certificate Probe]: ✅ Pass
  Detail: HTTPS probe succeeded
  Expire Date: 2026-09-12T00:00:00Z
  Issuer: TrustAsia TLS RSA CA
  CN: www.example.com
[Days Remaining Calculation]: ⚠️ Warning
  Detail: Certificate expiration time unknown; API did not return a valid expiration time
  Raw API Response: {"total": 1, "https": [{"domain_name": "www.example.com", "https_status": 3, "cert_name": "example-cert", "expiration_time": null}]}

--- Conclusion ---
Status: Expiration time unknown
Suggestion: API did not return a valid expiration time; please judge manually based on the raw API response or the data.tls.not_after value probed by cert_probe.py (2026-09-12T00:00:00Z)
```
