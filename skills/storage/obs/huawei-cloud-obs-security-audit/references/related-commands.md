# Related Commands — Quick Reference

## Command Map (skill action → CLI → OBS REST API)

| # | Skill Action | hcloud Command | OBS REST API | Risk |
|---|-------------|----------------|--------------|------|
| 1 | `huawei_audit_obs_acl` | `hcloud obs stat obs://{bucket} -acl` | `GET /{bucket}` (metadata) | R3 |
| 2 | `huawei_audit_obs_bpa` | `hcloud obs get-public-access-block obs://{bucket}` (fallback: `hcloud obs bucketpolicy obs://{bucket} -method=get`) | `GET /{bucket}?public-access-block` | R3 |
| 3 | `huawei_audit_obs_encryption` | `hcloud obs encryption obs://{bucket} -method=get` | `GET /{bucket}?encryption` | R3 |
| 4 | `huawei_audit_obs_versioning` | `hcloud obs stat obs://{bucket}` (includes versioning) | `GET /{bucket}` (metadata) | R3 |
| 5 | `huawei_audit_obs_replication` | `hcloud obs bucketpolicy obs://{bucket} -method=get` (parse replication from policy) | `GET /{bucket}?policy` | R3 |
| 6 | `huawei_audit_obs_https` | `hcloud obs bucketpolicy obs://{bucket} -method=get` | `GET /{bucket}?policy` | R3 |
| 7 | `huawei_audit_obs_logging` | `hcloud obs bucketpolicy obs://{bucket} -method=get` (parse logging from policy) | `GET /{bucket}?policy` | R3 |
| 8 | `huawei_audit_obs_referer` | `hcloud obs bucketpolicy obs://{bucket} -method=get` (parse referer from policy) | `GET /{bucket}?policy` | R3 |
| 9 | `huawei_audit_obs_cors` | `hcloud obs cors obs://{bucket} -method=get` | `GET /{bucket}?cors` | R3 |
| 10 | `huawei_audit_obs_naming` | `hcloud obs ls obs://{bucket} -limit={n} -s` | `GET /{bucket}?list-type=2` (ListObjectsV2) | R3 |
| 11 | `huawei_audit_obs_full` | `python3 scripts/obs_security_auditor.py audit --bucket={bucket}` | All above | R3 |

> Official OBS API reference: `https://support.huaweicloud.com/api-obs/obs_04_0006.html`. Endpoints come from the official OBS endpoint list — never inferred.

## Read-only Snippets

```bash
# List buckets (verify credentials)
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs ls -limit=1

# Bucket metadata (ACL, versioning, storage class, location)
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs stat obs://{bucket} -acl

# Bucket policy (for HTTPS SecureTransport analysis, replication, logging, referer, and BPA fallback)
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs bucketpolicy obs://{bucket} -method=get

# CORS configuration
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs cors obs://{bucket} -method=get

# Object listing (naming pattern analysis)
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs ls obs://{bucket} -limit=1000 -s

# Bucket encryption
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs encryption obs://{bucket} -method=get

# Block Public Access (BPA) — dedicated obsutil subcommand
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs get-public-access-block obs://{bucket}
# BPA fallback: analyze bucket policy for explicit public-access deny statements
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs bucketpolicy obs://{bucket} -method=get

# Cross-region replication — parsed from bucket policy JSON (no dedicated obsutil subcommand)
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs bucketpolicy obs://{bucket} -method=get

# Bucket logging — parsed from bucket policy JSON (no dedicated obsutil subcommand)
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs bucketpolicy obs://{bucket} -method=get

# Referer anti-hotlinking — parsed from bucket policy JSON (no dedicated obsutil subcommand)
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs bucketpolicy obs://{bucket} -method=get
```

## Full Audit Script

```bash
# Run comprehensive security audit — all 10 dimensions
python3 scripts/obs_security_auditor.py audit --bucket {bucket}

# With JSON output and file save
python3 scripts/obs_security_auditor.py audit --bucket {bucket} --format json --output /tmp/report.json

# With custom endpoint
python3 scripts/obs_security_auditor.py audit --bucket {bucket} --endpoint obs.cn-north-4.myhuaweicloud.com
```

## Common Pitfalls

| Pitfall | Truth |
|---------|-------|
| `hcloud obs` takes `--cli-region` | No — region lives in the endpoint (`obs.{region}.myhuaweicloud.com`), configured via `hcloud obs config` |
| 404 response means an error | No — for encryption/replication/logging/referer/BPA, a 404 means the feature is **not configured**, which is a valid audit finding |
| BPA and ACL are the same | No — BPA blocks all public access (overrides ACL/policy); ACL is the per-bucket access control list. BPA is checked via dedicated `get-public-access-block` subcommand with bucket policy fallback |
| `hcloud obs replication` / `logging` / `referer` exist | No — these subcommands do not exist in obsutil. Replication, logging, and referer configurations are parsed from the bucket policy JSON (`bucketpolicy -method=get`) |
| `SecureTransport` is a bucket setting | No — it's a **condition** inside a bucket policy statement, not a standalone configuration |
| Sequential naming is only a performance issue | No — it also creates a security enumeration risk (attackers can guess object keys) |
| CORS `*` is always bad | Not always — for truly public buckets it may be acceptable, but for private data it should be restricted |

## Best Practice References

- [OBS Security Configuration](https://support.huaweicloud.com/intl/zh-cn/bestpractice-obs/obs_05_2100.html)
- [Malicious Access Protection](https://support.huaweicloud.com/intl/zh-cn/bestpractice-obs/obs_05_2321.html)
- [Misoperation Protection](https://support.huaweicloud.com/intl/zh-cn/bestpractice-obs/obs_05_2120.html)
