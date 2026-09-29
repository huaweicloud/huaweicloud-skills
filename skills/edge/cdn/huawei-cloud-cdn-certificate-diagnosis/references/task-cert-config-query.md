# Step 2: Query Certificate Configuration

Retrieve the certificate status, certificate name, and expiration time configured on CDN via ShowCertificatesHttpsInfo/v2.

## Prerequisites

- Step 1 (credential validation and domain permission validation) has passed

## Command

```bash
hcloud CDN ShowCertificatesHttpsInfo/v2 --cli-region=<region> --domain_name=<domain>
```

## Decision Logic

The API returns a `https[]` array wrapped by `total`/`https`. **Locate the element whose `domain_name` matches the queried domain first**, then branch handling based on that element's `https_status` field:

| https_status | Meaning | Next Handling |
|--------------|---------|---------------|
| 0 | HTTPS certificate not configured | Report "This domain has no HTTPS certificate configured"; skip Steps 3 and 4; go directly to Step 5 (report generation) |
| 2 | Certificate configuring | Report "Certificate is configuring; please wait for configuration to complete"; skip Steps 3 and 4; go directly to Step 5 (report generation) |
| 3 | HTTPS certificate configured | Record cert_name and expiration_time; continue to Step 3 (certificate probe) |

> **Parsing rule**: read `https_status` / `cert_name` / `expiration_time` from the `https[]` element matching `domain_name`, not from the response top level. If `https[]` is empty or no matching element is found, treat the domain as "certificate not configured".

## Output Records

When https_status=3, record the following information (from the matched `https[]` element):

| Field | Description | Notes |
|-------|-------------|-------|
| `https_status` | Certificate configuration status (fixed at 3) | Configured |
| `cert_name` | Certificate name | Used for report display |
| `expiration_time` | Certificate expiration time (ms timestamp) | May be empty; when empty, no calculation is performed and Step 4 reports "Expiration time unknown" |

## Exception Handling

| Exception Scenario | Handling |
|---------------------|----------|
| API returns non-200 | Check hcloud version and network; degrade to probe results only, annotated with "API query failed" |
| Returned fields empty | If no matching `https[]` element exists or `https_status` is empty, report "No certificate configuration information retrieved. Please confirm the domain onboarding status" |
| expiration_time empty | **Do not calculate**; Step 4 reports "Certificate expiration time unknown; API did not return a valid expiration time"; expose the raw API response to the user |
| Network timeout | Retry once; if still failing, apply degraded handling |

## Example

```bash
hcloud CDN ShowCertificatesHttpsInfo/v2 --cli-region=<region> --domain_name=www.example.com

# Certificate configured (match https[] element by domain_name)
{
  "total": 1,
  "https": [
    {
      "domain_name": "www.example.com",
      "https_status": 3,
      "cert_name": "example-cert",
      "expiration_time": 1789824000000
    }
  ]
}
# → Continue to Step 3 (certificate probe)

# Certificate not configured
{
  "total": 1,
  "https": [
    {
      "domain_name": "www.example.com",
      "https_status": 0
    }
  ]
}
# → Report "HTTPS certificate not configured"; skip Steps 3 and 4

# Configuring
{
  "total": 1,
  "https": [
    {
      "domain_name": "www.example.com",
      "https_status": 2
    }
  ]
}
# → Report "Certificate configuring"; skip Steps 3 and 4

# expiration_time empty (configured but no expiration time returned)
{
  "total": 1,
  "https": [
    {
      "domain_name": "www.example.com",
      "https_status": 3,
      "cert_name": "example-cert",
      "expiration_time": null
    }
  ]
}
# → Continue to Step 3 (probe); Step 4 reports "Expiration time unknown"
```

## Report Content

Record the following information in the diagnosis report:
- Diagnosis item name: Certificate Configuration Status
- Status: ✅ Pass (configured) / ❌ Fail (not configured) / ⚠️ Warning (configuring)
- Detail: https_status, cert_name, expiration_time
