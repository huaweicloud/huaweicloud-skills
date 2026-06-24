# Huawei Cloud DNS Configuration for OBS Static Website

Use this reference when you need to configure DNS records for an OBS static website custom domain via Huawei Cloud DNS (hcloud CLI).

## Prerequisites

- `hcloud` CLI installed and configured with AK/SK credentials (see `references/hcloud-install-config.md`)
- The DNS zone for your domain already exists in Huawei Cloud DNS

## Workflow

### 1. Find the DNS Zone ID

List all public zones and locate the one matching your domain:

```bash
hcloud DNS ListPublicZones --cli-region=<region>
```

Look for the zone whose `name` matches your domain (e.g., `example.com.`). Note its `id`.

### 2. Check Existing Record Sets

Verify there is no conflicting record for your subdomain:

```bash
hcloud DNS ListRecordSets --zone_type=public --cli-region=<region>
```

Look for records with the name `<subdomain>.<domain>.` (e.g., `www.example.com.`).

### 3. Create a CNAME Record

Create a CNAME record pointing your custom domain to the OBS website endpoint:

```bash
hcloud DNS CreateRecordSet \
  --zone_id="<zone_id>" \
  --name="<custom_domain>." \
  --type="CNAME" \
  --records.1="<bucket_name>.obs.<region>.myhuaweicloud.com." \
  --cli-region=<region> \
  --ttl=300
```

**Parameters:**
| Parameter | Value | Description |
|-----------|-------|-------------|
| `--zone_id` | Zone UUID | The ID of your DNS zone from step 1 |
| `--name` | `custom_domain.` | Full domain name **with trailing dot** |
| `--type` | `CNAME` | Record type for domain alias |
| `--records.1` | OBS website endpoint | Target URL **with trailing dot**, e.g. `my-bucket.obs.cn-north-4.myhuaweicloud.com.` |
| `--cli-region` | Region | Region where the DNS API is called |
| `--ttl` | `300` (recommended) | Time-to-live in seconds |

**Example:**

```bash
hcloud DNS CreateRecordSet \
  --zone_id="ff8080828fb6d17b018fbd5a2fac1d7f" \
  --name="www.example.com." \
  --type="CNAME" \
  --records.1="my-bucket.obs.cn-north-4.myhuaweicloud.com." \
  --cli-region=cn-north-4 \
  --ttl=300
```

### 4. Verify DNS Resolution

Check that the CNAME record resolves correctly:

```bash
dig +short <custom_domain> CNAME
```

Expected output:
```
<bucket_name>.obs.<region>.myhuaweicloud.com.
```

## Important Notes

- **Trailing dot**: Both the `--name` and `--records.1` values must end with a `.` (period) — this is the fully qualified domain name (FQDN) format required by Huawei Cloud DNS API.
- **DNS propagation**: After creation, the record status may show `PENDING_CREATE`. Propagation typically completes within minutes.
- **OBS custom domain registration**: Creating a DNS CNAME record alone is NOT sufficient. You must also register the custom domain on the OBS bucket via `setBucketCustomDomain` (see `references/obs-python-sdk-website.md`). Use the `--custom-domain` flag of `scripts/set_obs_website_sdk.py`.
- **HTTPS**: The OBS website endpoint serves HTTP by default. For HTTPS, consider using CDN (Content Delivery Network) with an SSL certificate.
- **Bucket name with dots**: If the bucket name contains dots, HTTPS access may be problematic. A custom domain with CDN+SSL is recommended.

## Troubleshooting

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| `dig` returns no result | DNS not propagated or record not created | Check `hcloud DNS ListRecordSets` to confirm record exists |
| Custom domain not reachable | Missing `setBucketCustomDomain` on OBS bucket | Re-run `set_obs_website_sdk.py` with `--custom-domain` flag |
