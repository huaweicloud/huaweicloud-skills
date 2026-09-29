# Step 2: Query Ownership Verification Info

Obtain the ownership verification method and verification content required by CDN via ShowVerifyDomainOwnerInfo. A successful query also confirms the domain belongs to the current account.

## Command

```bash
hcloud CDN ShowVerifyDomainOwnerInfo --cli-region=<region> --domain_name=<domain>
```

## Decision Logic

| Return Field | Verification Method | Next Step |
|--------------|---------------------|-----------|
| `dns_verify_type=TXT` + `dns_verify_name` + `verify_domain_name` + `verify_content` | DNS TXT record verification | Join name (`dns_query_name = f"{dns_verify_name}.{verify_domain_name}"`), then go to Step 4 (DNS TXT verification) |
| `file_verify_url` + `file_verify_filename` + `verify_content` | File verification | Go to Step 3 (file verification probe) |
| Verification status=passed | Verification already passed | Report "Ownership verification has passed, may be cache latency, recommend refreshing and retrying" |

## Domain Permission Check (implicit)

A successful `ShowVerifyDomainOwnerInfo` query confirms the domain exists and belongs to the current account. Handle the following error responses as a permission/ownership check:

| Return Code | Action |
|-------------|--------|
| 200 | Domain check passed, continue per the decision logic above |
| 404 / CDN.0171 | Abort, return "Domain not under current account. Please confirm domain ownership." |
| 403 | Abort, return "No permission to diagnose this domain. Contact the administrator to grant CDN domain query permission." |
| Other error | Abort, return "Domain query failed: <error message>" |

## Output Records

Record the following information based on the verification method:

### DNS TXT Verification
- `dns_verify_type`: verification type (TXT)
- `dns_verify_name`: DNS TXT record **bare label** (e.g., `cdn_verification`; no dot) — must be joined with the domain before probing
- `verify_domain_name`: the domain the verification applies to (join input; e.g., `example.com`)
- `domain_name` / `file_verify_domains`: additional domain fields returned by the API (may be needed for other verification paths)
- `verify_content`: verification content (expected TXT record value; compared against entries in `dns_txt_probe.py`'s `data.txt_records`)
- **Join rule**: `dns_query_name = f"{dns_verify_name}.{verify_domain_name}"` (e.g., `cdn_verification.example.com`) — this joined name is what `scripts/dns_txt_probe.py --name` receives

### File Verification
- `file_verify_url`: verification file URL (passed to `scripts/file_probe.py --url`)
- `file_verify_filename`: verification file name
- `verify_content`: verification content (expected file content; compared against `file_probe.py`'s `data.content_preview`)

## Exception Handling

| Exception Scenario | Handling |
|--------------------|----------|
| API returns non-200 | Degrade to probe-only results, mark "API query failed, only probe results provided" |
| Return fields are empty | Report "No verification info obtained. Please confirm the domain access status." |
| Network timeout | Retry once; if still failing, degrade handling |

## Example

```bash
hcloud CDN ShowVerifyDomainOwnerInfo --cli-region=<region> --domain_name=www.example.com

# DNS TXT verification return (real shape: dns_verify_name is a bare label)
{
  "dns_verify_type": "TXT",
  "dns_verify_name": "cdn_verification",
  "verify_domain_name": "example.com",
  "verify_content": "verify_xxxxxxx"
}
# → Join: dns_query_name = "cdn_verification.example.com"
# → Go to Step 4 (DNS TXT verification) with --name cdn_verification.example.com

# File verification return
{
  "file_verify_url": "http://www.example.com/verify.txt",
  "file_verify_filename": "verify.txt",
  "verify_content": "verify_xxxxxxx"
}
# → Go to Step 3 (file verification probe)
```
