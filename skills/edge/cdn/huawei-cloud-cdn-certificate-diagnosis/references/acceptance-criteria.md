# Acceptance Criteria

## Functional Requirements

- [ ] Skill can check credential availability via `hcloud configure list`
- [ ] Skill can validate via `ShowDomainDetailByName` that the domain belongs to the current account
- [ ] When credentials are invalid, stop and return "Credentials not configured. Run `hcloud configure` first to configure AK/SK"
- [ ] When the domain returns 404, stop and return "Domain not found under current account. Please confirm domain ownership"
- [ ] When the domain returns 403, stop and return "No permission to diagnose this domain. Contact the administrator to grant CDN domain query permission"
- [ ] Skill can retrieve certificate configuration via `ShowCertificatesHttpsInfo/v2`
- [ ] Can identify https_status=0 (certificate not configured), report "This domain has no HTTPS certificate configured", and skip probing
- [ ] Can identify https_status=2 (certificate configuring), report "Certificate is configuring; please wait for configuration to complete"
- [ ] Can identify https_status=3 (certificate configured), and continue with `cert_probe.py` probe and expiration calculation
- [ ] When https_status=3, can parse cert_name and expiration_time (ms timestamp) from the API response
- [ ] Probe actual certificate status via `python scripts/cert_probe.py --domain <domain_name> --timeout 10`
- [ ] Probe JSON `result == "success"` and `data.connected` is `true` and `data.tls` is non-null on success
- [ ] Probe JSON `data.tls.subject_cn` is non-empty on success
- [ ] Probe JSON `data.tls.issuer_cn` is non-empty on success
- [ ] Probe JSON `data.tls.not_before` is non-empty on success
- [ ] Probe JSON `data.tls.not_after` is non-empty on success; cert_probe.py `data.tls.not_after` is in ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`)
- [ ] Probe JSON `data.tls.san_list` is present (may be an empty array)
- [ ] Probe JSON `result == "success"` and `data.error` is `null` on success; `data.error.reason` is set on failure (`connect_timeout`, `connect_failed`, `tls_handshake_failed`, etc.)
- [ ] Can call `python scripts/cert_expiry_check.py --expiration_time <ms-timestamp>`
- [ ] When expiration_time is empty, report "Certificate expiration time unknown; API did not return a valid expiration time", and perform no calculation
- [ ] Python script outputs valid JSON in the `{result, data, error_msg}` envelope: `data` contains `{"days_remaining": <int|null>, "status": "..."}`
- [ ] `data.days_remaining > 30` → `data.status=normal`
- [ ] `0 < data.days_remaining ≤ 30` → `data.status=warning`
- [ ] `data.days_remaining ≤ 0` → `data.status=expired`
- [ ] expiration_time empty → `data.days_remaining=null`, `data.status=unknown`
- [ ] cert_probe.py `data.error.reason == connect_timeout` → return partial results, annotated with "Certificate probe timed out"

## Security Constraints

- [ ] Skill is read-only; it must not call Create/Update/Delete type commands
- [ ] When the user requests certificate configuration changes, refuse and return "This skill supports diagnosis only; it does not perform configuration change operations"
- [ ] Prohibited from reading/echoing/printing AK/SK values
- [ ] Prohibited from asking the user to input credentials directly in the conversation
- [ ] When the user provides AK/SK in the conversation, stop immediately and guide secure configuration
- [ ] iam-policies.md contains `cdn:*:query*` and `cdn:configuration:queryDomains` permission declarations
- [ ] The permission declaration does not include any write-operation permissions
- [ ] references/prohibited-operations.md lists all 55 prohibited non-GET operations (24 POST + 25 PUT + 6 DELETE)

## Output Format

- [ ] The report contains the separator line `==================== CDN Certificate Diagnosis Report ====================`
- [ ] The report contains analysis time and target domain
- [ ] The report contains the mandatory `--- Certificate Summary (Common Info) ---` block explicitly printing the certificate's common info: Certificate Name, Certificate Status, Issuer, CN, SAN, Valid From / Expires On (API `expiration_time` shown as a readable date, not raw milliseconds), Days Remaining — `N/A` for unavailable fields
- [ ] The report contains a diagnosis item list (each item with name, status ✅/❌/⚠️, detail)
- [ ] The report contains conclusion and fix recommendation

## Timeout Control

- [ ] cert_probe.py enforces a 10-second timeout by default via `--timeout` (range 1-30)
- [ ] All network probe commands have a 10-second timeout (TCP connect and TLS handshake share this budget)

## Command Format

- [ ] All hcloud commands use `--cli-region=<region>`
- [ ] All hcloud commands use the `--key=value` format
- [ ] Command examples follow the `hcloud CDN <Operation> --cli-region=<region> --key=value` format

## Python Script Constraints

- [ ] `scripts/cert_probe.py` uses argparse to parse `--domain` (required, RFC 1035) and `--timeout` (default 10, range 1-30)
- [ ] `scripts/cert_probe.py` enforces a 10-second timeout by default (`--timeout`)
- [ ] `scripts/cert_probe.py` emits a single JSON object on stdout wrapped in `{result, data, error_msg}`, where `data` contains (`domain`, `connected`, `tls`, `duration_ms`, `error`) and `data.tls` contains `subject_cn`/`issuer_cn`/`not_before`/`not_after`/`san_list`
- [ ] `scripts/cert_probe.py` constructs the SSL context via `ssl.create_default_context()` only; verification (`CERT_REQUIRED`) is never relaxed under any code path, including the failure path
- [ ] `scripts/cert_probe.py` does NOT modify the trust store (no `load_verify_locations`, no custom CA bundles)
- [ ] `scripts/cert_probe.py` does NOT emit raw DER/PEM bytes or private key material; only the parsed peer certificate fields (`subject_cn`, `issuer_cn`, `not_before`, `not_after`, `san_list`) are surfaced
- [ ] `scripts/cert_probe.py` does NOT call `subprocess`, `os.system`, `os.popen`, or `shell=True`; it passes input only to `socket.create_connection`, `ssl.wrap_socket`, `ssl.getpeercert`
- [ ] `scripts/cert_probe.py` does NOT accept credentials (AK/SK, tokens, cookies); credential handling remains within the hcloud flow
- [ ] `scripts/cert_probe.py` does NOT write to disk; the only side effects are the read-only network request and the stdout JSON
- [ ] `scripts/cert_probe.py` exit codes: 0 for probe completed (including soft failures encoded in `error.reason`); 2 for argument validation errors
- [ ] `scripts/cert_expiry_check.py` uses argparse to parse `--expiration_time`
- [ ] The calculation script handles only calculation logic; it does not handle business flow (API calls, report generation, etc.)
- [ ] The calculation script outputs JSON format
- [ ] When expiration_time is empty or missing, the calculation script outputs `{"result": "success", "data": {"days_remaining": null, "status": "unknown"}, "error_msg": ""}` and performs no calculation
- [ ] Both scripts use only the Python standard library (`ssl`, `socket`, `argparse`, `json`, `sys`, `time`, `datetime`, `re`, `ipaddress`); no additional dependencies
- [ ] Both scripts are compatible with Python >= 3.8

## File Constraints

- [ ] The directory contains SKILL.md + references/ + scripts/
- [ ] references/ contains iam-policies.md and cli-installation-guide.md
- [ ] The total number of files in references/ matches the checklist (iam-policies, cli-installation-guide, troubleshooting, verification-method, acceptance-criteria, dataflow-diagram, related-apis, prohibited-operations, task-permission-check, task-cert-config-query, task-cert-probe, task-expiry-check, task-report-generation)
- [ ] The SKILL.md frontmatter name is `huawei-cloud-cdn-certificate-diagnosis`, matching the directory name
- [ ] The SKILL.md description contains "Triggers include:"
- [ ] SKILL.md contains the sections: Overview, Prohibited Operations, Architecture, KooCLI Command Format Standard, Prerequisites, Authentication, IAM Permission Policies, Core Commands, Parameter Confirmation, Core Workflows, References

## Migration Compatibility (Python Probe)

- [ ] `hcloud` CLI command set, arguments, and captured output formats are byte-for-byte unchanged across this migration
- [ ] `scripts/cert_expiry_check.py` is byte-for-byte unchanged
- [ ] `scripts/cert_probe.py` is added as a sibling script; the two scripts are invoked independently
- [ ] No new IAM permission is required (the probe is an unauthenticated TLS read; the iam-policies.md scope is unchanged)
- [ ] No new write or mutating operation is introduced (the probe uses TLS handshake only)
- [ ] No new credential handling is introduced
