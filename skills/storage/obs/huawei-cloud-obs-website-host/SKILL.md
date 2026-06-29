---
name: huawei-cloud-obs-website-host
description: Configure Huawei Cloud OBS static website hosting with Python SDK and a custom domain. Use when the user needs to enable or repair OBS website hosting, set index or error pages, expose an existing bucket for public website access through a custom domain, or connect that domain through Huawei Cloud DNS when Huawei manages the zone. Triggers include OBS static website hosting, website endpoint, index page, error page, public-read bucket website access, custom domain CNAME, Huawei Cloud DNS, setBucketWebsite. 中文触发词包括：OBS 静态网站托管、网站托管、自定义域名解析。
---

# Huawei Cloud OBS Website Host

## Overview

Configure an existing Huawei Cloud OBS bucket for static website hosting with Huawei Cloud OBS Python SDK and register a custom domain for the site.

Use this skill when the user wants to:
- enable or repair OBS static website hosting
- set an index document or error document
- make the site reachable through a custom domain backed by the OBS static website endpoint
- add or repair a custom domain, including Huawei Cloud DNS when applicable
- diagnose 403, 404, or DNS issues on a hosted OBS site

## What Good Looks Like

- The bucket has static website hosting enabled.
- The bucket can serve `index.html` from the website endpoint.
- Anonymous users can read the website content.
- A missing path returns the configured error page or a clean 404.
- A custom domain is registered and resolves to the OBS website endpoint through DNS. A custom domain is **mandatory** — the default OBS bucket domain is not permitted for online object preview per security compliance requirements.
- The setup is not considered complete until the custom domain is registered on the bucket and resolves correctly.
- The OBS website endpoint is used, not the regular bucket API endpoint.
- A 403 usually has two common causes: anonymous/public read is not enabled on the bucket or objects, or the AK/SK used for OBS operations lacks required IAM permissions.
- A 404 usually means the index document name or upload path is wrong.

## Security Compliance: Custom Domain Requirement

Based on Huawei Cloud security compliance requirements, the OBS bucket default domain name (`<bucket_name>.obs.<region>.myhuaweicloud.com`) is **prohibited** from being used for online preview of objects within the bucket. A custom domain is therefore **mandatory** for static website hosting.

If the user does not have a custom domain prepared:

1. Direct the user to register a domain through the [Huawei Cloud Domain Registration Service](https://www.huaweicloud.com/product/domain.html), or other common domain registration sites.
2. For users in mainland China, the domain must also complete **ICP filing (网站备案)** before it can be used for website hosting.
3. Only after the domain is registered (and filed, if applicable) should the static website hosting configuration continue.

> **Important:** Do not proceed with static website hosting configuration until the custom domain prerequisite is confirmed. The default OBS domain is not a valid alternative for website access even in the testing environment.

## Required Inputs

Collect these before making changes:
- `region`
- `bucket_name`
- `custom_domain` (**required** — see Security Compliance section above)
- `index_document` (optional, default: `index.html`)
- `error_document` (optional)
- `dns_zone` or DNS account context (optional; required only if the user wants Huawei Cloud DNS changes in this run)

Assume static website files are already uploaded by the user.

## Dependencies

The skill depends on the following runtime/tooling components:

- Python 3.8+ (required for `scripts/set_obs_website_sdk.py` and `scripts/verify_obs_website.py`)
- Huawei OBS Python SDK package: `esdk-obs-python`
- `obsutil` (for generating and maintaining `.obsutilconfig` credential config)
- Huawei Cloud AK/SK credentials (from `.obsutilconfig`)
- Network access to OBS endpoint and website endpoint
- `hcloud` CLI (required only when this skill manages Huawei Cloud DNS record operations)


Install command:

```bash
pip install esdk-obs-python
```

## hcloud CLI Reference

Load `references/cli-installation-guide.md` when hcloud CLI or obsutil installation and configuration is needed.
Load `references/hcloud-dns-obs-website.md` when creating or managing DNS CNAME records for OBS static website custom domains (step-by-step guide with hcloud `DNS CreateRecordSet` commands).

Security note:
- Never hardcode AK/SK in scripts or checked-in files.
- Prefer environment variables for SDK scripts and secure local profile storage for CLI use.

## obsutil Config Dependency

Load `references/cli-installation-guide.md` when you need obsutil installation or `.obsutilconfig` setup guidance.

The Python SDK helper script (`scripts/set_obs_website_sdk.py`) reads credentials by default from:
1. CLI flags (`--access-key`, `--secret-key`, `--security-token`)
2. Environment variables (`HW_ACCESS_KEY`, `HW_SECRET_KEY`, `HW_SECURITY_TOKEN`)
3. `.obsutilconfig`

If `ak`/`sk` are empty across all sources, the script must stop and ask the user to fill missing keys in `.obsutilconfig` (or provide CLI/env credentials).

Credential check rule:
- Only report presence/absence of keys (`ak`, `sk`, `securitytoken`).
- Never print credential values during checks.
- Never print full lines from `.obsutilconfig` to console.
- Treat console output as model context; any leaked value is a security incident.

Safe check examples (status only, no secret values):

Linux/macOS:

```bash
CFG="${HOME}/.obsutilconfig"
if [ ! -f "$CFG" ]; then
  echo "obsutilconfig_exists=false"
  echo "ak_configured=false"
  echo "sk_configured=false"
  echo "securitytoken_configured=false"
else
  awk -F= '
    BEGIN { ak=0; sk=0; st=0 }
    /^[[:space:]]*#/ { next }
    /^[[:space:]]*(ak|access_key_id)[[:space:]]*=/ { if ($2 ~ /[^[:space:]]/) ak=1 }
    /^[[:space:]]*(sk|secret_access_key)[[:space:]]*=/ { if ($2 ~ /[^[:space:]]/) sk=1 }
    /^[[:space:]]*(securitytoken|security_token|token)[[:space:]]*=/ { if ($2 ~ /[^[:space:]]/) st=1 }
    END {
      print "obsutilconfig_exists=true"
      print "ak_configured=" (ak ? "true" : "false")
      print "sk_configured=" (sk ? "true" : "false")
      print "securitytoken_configured=" (st ? "true" : "false")
    }
  ' "$CFG"
fi
```

Windows (PowerShell):

```powershell
$cfg = Join-Path $HOME ".obsutilconfig"
if (-not (Test-Path $cfg)) {
  "obsutilconfig_exists=false"
  "ak_configured=false"
  "sk_configured=false"
  "securitytoken_configured=false"
} else {
  $lines = Get-Content $cfg
  $ak = $false; $sk = $false; $st = $false
  foreach ($line in $lines) {
    if ($line -match '^\s*#') { continue }
    if ($line -match '^\s*(ak|access_key_id)\s*=\s*(\S.*)$') { $ak = $true }
    if ($line -match '^\s*(sk|secret_access_key)\s*=\s*(\S.*)$') { $sk = $true }
    if ($line -match '^\s*(securitytoken|security_token|token)\s*=\s*(\S.*)$') { $st = $true }
  }
  "obsutilconfig_exists=true"
  "ak_configured=$ak"
  "sk_configured=$sk"
  "securitytoken_configured=$st"
}
```

Do not use:
- `cat ~/.obsutilconfig`
- `grep -E "ak|sk|token" ~/.obsutilconfig`

## Script Usage Intent

Use the bundled scripts by default for the tasks they were built for:

- `scripts/set_obs_website_sdk.py` applies or updates the bucket website configuration and registers the required custom domain. Use it whenever the task is to enable, repair, or change OBS static website hosting settings.
- `scripts/verify_obs_website.py` validates the published website endpoint. Use it after any website configuration change, and also when the user asks whether the site is reachable or when troubleshooting 403/404 behavior.
- Do not replace these scripts with ad hoc one-off code unless the script itself is broken and must be patched.
- Use the scripts to keep credential handling, SDK object construction, and verification behavior consistent across runs.

## Workflow

1. Verify Python runtime and OBS SDK are available (`pip install esdk-obs-python` if missing).
2. Verify the custom domain prerequisite (see **Security Compliance** section):
   - Confirm `custom_domain` is provided by the user.
   - If the user does not have a domain, guide them to register one at [Huawei Cloud Domain Registration](https://www.huaweicloud.com/product/domain.html) and complete **ICP filing (网站备案)** for mainland China regions. Stop here and wait for the user to complete this step.
   - Check whether the user manages DNS in Huawei Cloud DNS or with an external provider.
   - If Huawei Cloud DNS changes are part of this run, verify `hcloud` is installed and authenticated.
   - If DNS is managed outside Huawei Cloud or outside this run, collect that constraint explicitly before proceeding.
3. Verify the bucket exists in the requested region (use **Bucket Existence and Region Check Method** below).
4. Check that the caller has permission to update bucket website settings.
5. Check that anonymous read is allowed for the website files (use the method in **Anonymous Read Check Method** below).
6. Do not upload or modify website content objects (`index.html`, assets, etc.). Assume content already exists in the bucket.
7. Configure static website hosting by running `scripts/set_obs_website_sdk.py` with `--custom-domain <domain>` (use `index.html` if `index_document` is not provided).
   - The script exists to keep SDK object construction and credential lookup consistent.
   - Use it instead of writing a one-off SDK call in the response.
8. Register the required custom domain on the bucket via the OBS SDK path used by the script:
   - `client.setBucketCustomDomain(bucket_name, custom_domain)` — required even if DNS CNAME already exists.
   - If DNS record changes are requested in this run, create a DNS CNAME record to the OBS website hostname and wait for propagation. (read `references/hcloud-dns-obs-website.md`)
   - If DNS is managed outside Huawei Cloud or outside this run, provide the required CNAME target and explicitly instruct the user to create or update the CNAME record with their external DNS provider after OBS custom-domain registration is complete.
   - For externally managed DNS, include the practical handoff details the user needs: record type `CNAME`, host/name, target/value, and a verification command such as `dig`.
9. Verify the published site by running `scripts/verify_obs_website.py --bucket-name <bucket_name> --region <region> [--domain <custom_domain>] [--index-document <name>]`.
   - If the user provided a custom domain, final verification MUST use that custom domain via `--domain <custom_domain>`.
   - Only use the default OBS hostname for interim checks or when no custom domain was provided.
10. Confirm the root path returns the homepage (HTTP 200).
11. Confirm a missing path returns the configured error behavior (HTTP 404 or configured error page).
12. Verify DNS resolution (`dig` / `nslookup`) and HTTP access through the user-provided custom domain. Do not treat the setup as complete based only on the default OBS hostname when a custom domain is part of the request.

## Bucket Existence and Region Check Method

Run a read-only SDK check with `verify_obs_website.py` before website configuration.

```bash
python scripts/verify_obs_website.py \
  --bucket-name "<bucket_name>" \
  --region "<region>" \
  --index-document "<index_document>"
```

`obs endpoint` is auto-built as `https://obs.<region>.myhuaweicloud.com`.

Pass/Fail rules:
- `PASS`: `headBucket` is `2xx` and region matches (or region cannot be returned but bucket is reachable with `2xx`).
- `FAIL`: `headBucket` non-`2xx`, `getBucketLocation` non-`2xx`, or explicit region mismatch.

## Anonymous Read Check Method

Use anonymous HTTP requests against the OBS website endpoint (no AK/SK) as the source of truth.

1. The verifier auto-builds the default website URL:
   - `http://<bucket_name>.obs.<region>.myhuaweicloud.com`
2. Run bundled verifier (preferred):

```bash
python scripts/verify_obs_website.py \
  --bucket-name "<bucket_name>" \
  --region "<region>" \
  --domain "<custom_domain>" \
  --index-document "<index_document>"
```

3. If no custom domain was provided by the user, verify the default OBS website endpoint instead:

```bash
python scripts/verify_obs_website.py \
  --bucket-name "<bucket_name>" \
  --region "<region>" \
  --index-document "<index_document>"
```

4. If you need a quick single-file check, run:

```bash
site_url="http://<custom_domain>"
curl -s -o /dev/null -w "%{http_code}\n" "$site_url/<index_document>"
```

Pass/Fail rules:
- `200` on `root_path` and `index_document`: anonymous read is working.
- `403`: treat as two possible issues that must both be reported to the user: anonymous/public read is not enabled (ACL/policy issue), or the AK/SK used for SDK verification/configuration lacks required IAM permissions.
- `404`: object path/name issue (for example, `index.html` missing or key path mismatch), not an anonymous-permission success.

When `403` appears, treat setup as failed and tell the user both common possibilities:
- bucket/object is not public-read for website access
- AK/SK lacks required IAM permissions for OBS operations

Provide remediation via `references/iam-policies.md`.

## Response Shape

Always return:
1. Input summary
2. Actions performed
3. Verification results
4. Remediation steps if anything failed

When DNS is externally managed, also include a short DNS handoff section that tells the user exactly which CNAME record to configure with their provider.

## Safety Rules

- Never print secrets, AK/SK, or tokens.
- Do not claim success until the website endpoint is verified.
- If the user provided a custom domain, final success must be based on verification through that custom domain, not only the default OBS hostname.
- If permissions are missing, stop and report the missing capability.
- If DNS provider ownership is unspecified, ask whether the zone is managed in Huawei Cloud DNS or externally before assuming `hcloud` steps.
- If Huawei Cloud DNS changes are required for completion but the zone is unknown, ask for the zone instead of guessing.
- Do not use the regular bucket endpoint as the final website result.
- If the bucket name contains dots, warn that HTTPS access can be problematic.
- `obsutil` is allowed only for managing `~/.obsutilconfig`; do not use it to configure website hosting.
- Do not perform any object upload actions in this skill.
- Especially during verification, use read-only checks only; never upload test files.
- For externally managed DNS, do not stop at “DNS is external”; provide the user-facing CNAME handoff details needed to finish the setup.

## Permission Failure Handling (MUST)

When any command fails due to IAM permission errors:

1. Read `references/iam-policies.md`.
2. Show the required permission list and policy JSON to the user.
3. Guide the user to create a custom IAM policy and grant it in Huawei Cloud IAM console.
4. Pause execution and wait for user confirmation that permissions were granted.

## References

Load `references/obs-python-sdk-website.md` for SDK method usage for website hosting **and custom domain registration** (`setBucketCustomDomain`).
Load `references/iam-policies.md` for required IAM actions and policy JSON.
Load `references/hcloud-dns-obs-website.md` for step-by-step DNS CNAME configuration for custom domains via Huawei Cloud DNS (`hcloud` CLI), including zone lookup, record creation, and verification.

> **Known Pitfall:** The `setBucketWebsite` API in esdk-obs-python >= 3.x uses `WebsiteConfiguration` model objects, **not** keyword arguments like `indexDocumentSuffix`. Always import `WebsiteConfiguration`, `IndexDocument`, and `ErrorDocument` and construct them properly.

## Scripts

Use scripts only for repeatable checks and verification. Keep command output human-readable and focused on success/failure.
- `scripts/set_obs_website_sdk.py <bucket_name> <endpoint> --custom-domain <domain> [--index-document <name>] [--error-document <name>]` applies static website hosting settings through the OBS SDK, registers the required custom domain, and reads credentials from CLI args, env vars, or `~/.obsutilconfig`.
- `scripts/verify_obs_website.py --bucket-name <name> --region <region> [--domain <custom_domain>] [--index-document <name>] [--json]` verifies endpoint DNS/HTTP behavior and also performs a read-only bucket existence + region check (`headBucket` + `getBucketLocation`). If `--domain` is provided, that custom domain is the final verification target; otherwise it auto-builds the default website URL as `http://<bucket>.obs.<region>.myhuaweicloud.com`. The OBS API endpoint remains `https://obs.<region>.myhuaweicloud.com`. It prints structured sections (`Input summary`, `Actions performed`, `Verification results`, `Remediation steps`) so agent responses can directly reuse them.

## Validation Rules

Load `references/verification-method.md` for validation rules.
