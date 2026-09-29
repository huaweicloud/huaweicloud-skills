# Verification Method

Verify that the skill's certificate diagnosis results are correct and complete.

## Verification Steps

### 1. Verify Credential Configuration

```bash
hcloud configure list
```

Check that the output contains a valid AK/SK configuration (mode=AKSK).

### 2. Verify Domain Permission Validation

```bash
hcloud CDN ShowDomainDetailByName --cli-region=<region> --domain_name=<test-domain>
```

Check that the response returns 200 and contains domain_id, confirming the domain belongs to the current account.

### 3. Verify Certificate Configuration Query

```bash
hcloud CDN ShowCertificatesHttpsInfo/v2 --cli-region=<region> --domain_name=<test-domain>
```

Check that the response contains the https_status field:
- `https_status=0`: HTTPS certificate not configured
- `https_status=2`: certificate configuring
- `https_status=3`: HTTPS certificate configured; should return `cert_name` and `expiration_time` (ms timestamp)

### 4. Verify Actual Certificate Status Probe

```bash
python scripts/cert_probe.py --domain <test-domain> --timeout 10
```

Check that the output is a single JSON object on stdout (wrapped in the `{result, data, error_msg}` envelope; business fields are inside `data`):
- `result == "success"` and `data.connected == true` (TLS handshake succeeded)
- `data.tls.subject_cn` non-empty (subject Common Name)
- `data.tls.issuer_cn` non-empty (issuer Common Name)
- `data.tls.not_before` non-empty (start date, ISO 8601 UTC, e.g., `2025-09-12T00:00:00Z`)
- `data.tls.not_after` non-empty (expiration date, ISO 8601 UTC)
- `data.tls.san_list` present (may be an empty array)
- `data.duration_ms` integer
- `data.error == null` on success

Example expected JSON shape on success:
```json
{
  "result": "success",
  "data": {
    "domain": "<test-domain>",
    "connected": true,
    "tls": {
      "subject_cn": "<test-domain>",
      "issuer_cn": "TrustAsia TLS RSA CA",
      "not_before": "2025-09-12T00:00:00Z",
      "not_after": "2026-09-12T00:00:00Z",
      "san_list": ["<test-domain>"]
    },
    "duration_ms": 312,
    "error": null
  },
  "error_msg": ""
}
```

For failure-path verification (e.g., a malformed/expired-cert domain), the JSON still includes `result="failed"` and `data` with `domain`, `connected=false`, `tls=null`, `duration_ms`, and a non-null `data.error` with `reason` in `{connect_timeout, connect_failed, tls_handshake_failed, unexpected_probe_error}`.

A blank `--domain` or out-of-range `--timeout` should exit with code 2 and emit an `error.reason` of `invalid_domain` / `invalid_timeout`.

### 5. Verify Days Remaining Calculation

```bash
python scripts/cert_expiry_check.py --expiration_time <ms-timestamp>
```

Check that the output is in JSON format (wrapped in `{result, data, error_msg}`; read `data.days_remaining` / `data.status`):
- `data.days_remaining > 30` → `{"result": "success", "data": {"days_remaining": <int>, "status": "normal"}, "error_msg": ""}`
- `0 < data.days_remaining ≤ 30` → `{"result": "success", "data": {"days_remaining": <int>, "status": "warning"}, "error_msg": ""}`
- `data.days_remaining ≤ 0` → `{"result": "success", "data": {"days_remaining": <int>, "status": "expired"}, "error_msg": ""}`
- `expiration_time` empty → `{"result": "success", "data": {"days_remaining": null, "status": "unknown"}, "error_msg": ""}`

### 6. Verify Report Format

Check that the output report contains:
- Separator line `==================== CDN Certificate Diagnosis Report ====================`
- Analysis time and target domain
- **Mandatory `--- Certificate Summary (Common Info) ---` block** that explicitly prints the certificate's common info: Certificate Name, Certificate Status, Issuer, CN, SAN, Valid From / Expires On (with API `expiration_time` shown as a readable date), Days Remaining — `N/A` for unavailable fields
- Diagnosis item list (each item with name, status ✅/❌/⚠️, detail)
- Conclusion and fix recommendation

## Expected Output

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
  Detail: Domain belongs to current account, domain_id=xxx
[Certificate Configuration Status]: ✅ Pass
  Detail: Certificate configured, cert_name=example-cert, expiration_time=1789824000000
[Actual Certificate Probe]: ✅ Pass
  Detail: HTTPS probe succeeded; certificate chain valid
  Expire Date: 2026-09-12 00:00:00 UTC
  Issuer: CN=TrustAsia TLS RSA CA, O=TrustAsia Technologies Limited
  CN: www.example.com
  SAN: www.example.com, example.com
[Days Remaining Calculation]: ✅ Pass
  Detail: days_remaining=31, status=normal

--- Conclusion ---
Status: Certificate status normal
Suggestion: Certificate has sufficient remaining validity; no action needed
```
