# Troubleshooting

## Common Issues

### Issue: Credentials Not Configured

**Symptom**: `hcloud configure list` output has no AK/SK, or hcloud command returns an authentication error

**Resolution**:
1. Run `hcloud configure` to interactively configure AK/SK
2. Or configure via environment variables:
   ```bash
   export HUAWEICLOUD_SDK_AK=<your-access-key-id>
   export HUAWEICLOUD_SDK_SK=<your-secret-key>
   ```
3. After configuration, re-run `hcloud configure list` to verify

### Issue: Domain Not Found (404)

**Symptom**: `ShowDomainDetailByName` returns `error_code: CDN.0171` or 404

**Resolution**:
1. Verify the domain name spelling
2. Confirm the domain has been onboarded to CDN under the current account
3. Confirm you are using the correct account
4. Run `hcloud CDN ListDomains/v2 --cli-region=<region> --page_size=100` to view all onboarded domains

### Issue: Insufficient Permission (403)

**Symptom**: `ShowDomainDetailByName` or `ShowCertificatesHttpsInfo/v2` returns 403 or a permission-denied error

**Resolution**:
1. Check whether the IAM user has the CDN query permission (`cdn:*:query*`, plus `cdn:configuration:queryDomains` for the domain list)
2. Confirm the AK/SK belongs to the correct account
3. Contact the primary account administrator to grant CDN domain query and configuration query permissions
4. See [iam-policies.md](iam-policies.md) for details

### Issue: API Call Failed

**Symptom**: `ShowCertificatesHttpsInfo/v2` returns a non-200 response or an abnormal error

**Resolution**:
1. Check whether the hcloud version >= 3.2.0
2. Check whether the network connection is normal
3. Degrade to probe results only (if `cert_probe.py` is still runnable, output only the probe JSON)
4. Annotate in the report: "API query failed; only probe results provided; recommend manual confirmation"

### Issue: `cert_probe.py` returned `error.reason == "connect_timeout"`

**Symptom**: `python scripts/cert_probe.py --domain <domain> --timeout 10` returns no `tls` within 10 seconds; the JSON `error.reason` is `connect_timeout`.

**Resolution**:
1. Return partial results; annotate "Certificate probe timed out; recommend manual verification"
2. Check the local network connection (egress to TCP 443)
3. Confirm the domain has HTTPS configured and CNAME is in effect
4. Try running `python scripts/cert_probe.py --domain <domain> --timeout 10` manually to confirm
5. If the domain does not have HTTPS enabled yet (https_status=0), skip the probe and report "Certificate not configured"

### Issue: `cert_probe.py` returned `error.reason == "connect_failed"`

**Symptom**: The JSON `error.reason` is `connect_failed` (TCP connection refused / network unreachable).

**Resolution**:
1. Confirm the domain resolves to a CDN edge IP (the CNAME must be in effect)
2. Confirm TCP 443 egress from the execution host is allowed
3. If the domain uses a non-standard port or only HTTP, certificate probing is not applicable; report "Cannot reach <domain>:443 (TCP refused)"
4. Re-run `python scripts/cert_probe.py --domain <domain> --timeout 10` after resolving the path issue

### Issue: `cert_probe.py` returned `error.reason == "tls_handshake_failed"`

**Symptom**: The JSON `error.reason` is `tls_handshake_failed` (SSL error during the handshake — e.g., expired, revoked, or untrusted certificate).

**Resolution**:
1. Do NOT relax verification — the failure reflects the real deployment state of the certificate served by the CDN edge
2. Cross-check the failure against the API-returned `expiration_time`: if `data.error.reason == "tls_handshake_failed"` is due to `certificate has expired` and the API confirms `expiration_time` is in the past, report "Certificate already expired"
3. If the issuer is untrusted by the host trust store, report "Issuer not trusted by host trust store; recommend verifying the certificate chain manually"
4. If a self-signed certificate is served, report "Self-signed / untrusted certificate served by the edge"

### Issue: `cert_probe.py` returned exit code 2 (`invalid_domain` / `invalid_timeout`)

**Symptom**: The script exits with code 2 and the JSON `error.reason` is `invalid_domain` or `invalid_timeout`; no probe was attempted.

**Resolution**:
1. For `invalid_domain`: confirm the `--domain` value passes RFC 1035 (length <= 253, labels <= 63, alphanumeric + hyphen, no leading/trailing hyphen)
2. For `invalid_timeout`: ensure `--timeout` is in the range `[1, 30]`
3. Re-run with a corrected argument

### Issue: `cert_probe.py` returned `error.reason == "unexpected_probe_error"`

**Symptom**: The JSON `error.reason` is `unexpected_probe_error`; a traceback was written to stderr.

**Resolution**:
1. Capture the stderr traceback for diagnostic context (it is NOT included in stdout JSON)
2. Re-run the probe; if the failure persists, report "Probe failed with an unexpected error; please forward the stderr traceback to the skill maintainer"
3. If the host's Python interpreter is missing the stdlib `ssl`/`socket` modules, reinstall a complete Python >= 3.8 build (see cli-installation-guide.md)

### Issue: Python stdlib `ssl` / `socket` Not Importable

**Symptom**: `python -c "import ssl, socket; print('ok')"` raises `ImportError`; `cert_probe.py` cannot perform the TLS probe.

**Resolution**:
1. The host's Python interpreter is missing the standard library (typical of stripped/minimal builds)
2. Reinstall a complete Python >= 3.8 build (see cli-installation-guide.md); no `pip install` will recover from this state because `ssl` and `socket` ship with the interpreter itself

### Issue: Certificate Not Configured (https_status=0)

**Symptom**: `ShowCertificatesHttpsInfo/v2` returns `https_status=0`

**Resolution**:
1. Report "This domain has no HTTPS certificate configured"
2. Skip the certificate probe and expiration calculation steps
3. Recommendation: configure an HTTPS certificate in the CDN console or via hcloud CLI
4. If the business does not require HTTPS, this prompt can be ignored

### Issue: Python Environment Unavailable

**Symptom**: `python --version` errors or version is below 3.8; `cert_expiry_check.py` cannot execute

**Resolution**:
1. Check whether Python is installed: `python --version` or `python3 --version`
2. If not installed, see [cli-installation-guide.md](cli-installation-guide.md) to install Python >= 3.8
3. If `python` points to Python 2, use `python3 scripts/cert_expiry_check.py` instead
4. If the environment is temporarily unavailable, calculate manually based on `expiration_time` (ms timestamp):
   - Current timestamp (ms) = `date +%s` * 1000 (Linux/macOS)
   - Days remaining ≈ (expiration_time - current timestamp) / 86400000

## Best Practices

### 1. Always Verify Credentials First

Before performing diagnosis, run `hcloud configure list` to confirm credentials are valid.

### 2. Use Recommended Region

CDN APIs should use `--cli-region=<region>` to avoid confusion.

### 3. Set Timeout

`cert_probe.py` enforces a 10-second timeout by default via `--timeout` (default 10, range 1-30). TCP connect and the TLS handshake share this budget.

### 4. Do Not Enter Credentials in the Conversation

If the user attempts to provide AK/SK in the conversation, refuse immediately and guide them to use `hcloud configure`.

### 5. Do Not Speculate When expiration_time Is Empty

When `ShowCertificatesHttpsInfo/v2` does not return `expiration_time`, directly report "Certificate expiration time unknown; API did not return a valid expiration time", expose the raw API response to the user, and do not perform calculation.

## Error Handling Summary

| Scenario | Handling |
|----------|----------|
| Credentials not configured | Stop; prompt to configure credentials |
| Domain not found (404) | Stop; prompt to confirm domain ownership |
| Insufficient permission (403) | Stop; prompt to contact the administrator for authorization |
| API call failed | Degrade to probe results only |
| `cert_probe.py` `error.reason=connect_timeout` | Return partial results; annotate timeout |
| `cert_probe.py` `error.reason=connect_failed` | Report connection failed; check CNAME and TCP 443 egress |
| `cert_probe.py` `error.reason=tls_handshake_failed` | Report TLS handshake failed — do NOT relax verification; cross-check API `expiration_time` |
| `cert_probe.py` exit code 2 (`invalid_domain`/`invalid_timeout`) | Re-run with corrected argument; no probe was attempted |
| `cert_probe.py` `error.reason=unexpected_probe_error` | Capture stderr traceback; re-run; contact skill maintainer if persistent |
| stdlib `ssl` / `socket` not importable | Reinstall a complete Python >= 3.8 build (no pip install will help) |
| Certificate not configured (https_status=0) | Report not configured; skip probe and calculation |
| Python environment unavailable | Prompt to install Python >= 3.8 or calculate manually |
| expiration_time empty | Report "Expiration time unknown"; no calculation performed |
