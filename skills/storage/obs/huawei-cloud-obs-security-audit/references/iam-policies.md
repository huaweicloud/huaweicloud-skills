# IAM Policies — Huawei Cloud OBS Security Audit

Least-privilege IAM permissions for OBS bucket security audit. This skill is **read-only (R3)** — no write permissions required.

## 1. Security Audit (R3) — read-only policy

Covers all 11 audit actions: ACL, BPA, encryption, versioning, replication, HTTPS, logging, Referer, CORS, naming pattern, and full audit.

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "obs:bucket:GetBucketAcl",
        "obs:bucket:GetBucketPolicy",
        "obs:bucket:GetBucketCors",
        "obs:bucket:GetBucketEncryption",
        "obs:bucket:GetBucketReplication",
        "obs:bucket:GetBucketLogging",
        "obs:bucket:GetBucketReferer",
        "obs:bucket:GetBucketBlockPublicAccess",
        "obs:bucket:GetBucketVersioning",
        "obs:bucket:GetBucketLocation",
        "obs:bucket:GetBucketStorage",
        "obs:bucket:ListAllMyBuckets",
        "obs:object:ListObject"
      ],
      "Resource": "*"
    }
  ]
}
```

## 2. Scoped to a single bucket (recommended production hardening)

Replace `Resource` with the specific bucket ARN to restrict all operations to one bucket:

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "obs:bucket:GetBucketAcl",
        "obs:bucket:GetBucketPolicy",
        "obs:bucket:GetBucketCors",
        "obs:bucket:GetBucketEncryption",
        "obs:bucket:GetBucketReplication",
        "obs:bucket:GetBucketLogging",
        "obs:bucket:GetBucketReferer",
        "obs:bucket:GetBucketBlockPublicAccess",
        "obs:bucket:GetBucketVersioning",
        "obs:bucket:GetBucketLocation",
        "obs:bucket:GetBucketStorage",
        "obs:object:ListObject"
      ],
      "Resource": [
        "obs:*:*:*:bucket:my-bucket",
        "obs:*:*:*:object:my-bucket/*"
      ]
    }
  ]
}
```

## Permissions Mapping

| Skill Action | IAM Action | Resource |
|--------------|-----------|----------|
| `huawei_audit_obs_acl` | `obs:bucket:GetBucketAcl` | bucket |
| `huawei_audit_obs_bpa` | `obs:bucket:GetBucketBlockPublicAccess` | bucket |
| `huawei_audit_obs_encryption` | `obs:bucket:GetBucketEncryption` | bucket |
| `huawei_audit_obs_versioning` | `obs:bucket:GetBucketVersioning` | bucket |
| `huawei_audit_obs_replication` | `obs:bucket:GetBucketReplication` | bucket |
| `huawei_audit_obs_https` | `obs:bucket:GetBucketPolicy` | bucket |
| `huawei_audit_obs_logging` | `obs:bucket:GetBucketLogging` | bucket |
| `huawei_audit_obs_referer` | `obs:bucket:GetBucketReferer` | bucket |
| `huawei_audit_obs_cors` | `obs:bucket:GetBucketCors` | bucket |
| `huawei_audit_obs_naming` | `obs:object:ListObject` | bucket + objects |
| `huawei_audit_obs_full` | All above | bucket + objects |
| List buckets (discovery) | `obs:bucket:ListAllMyBuckets` | account |
| Bucket stat (metadata) | `obs:bucket:GetBucketLocation`, `obs:bucket:GetBucketStorage` | bucket |

## Notes

- This skill requires **only read permissions** — no `Put*` or `Delete*` actions.
- IAM policy syntax follows the Huawei Cloud IAM custom policy (JSON) format; apply via the IAM console or `IAM` APIs.
- For temporary credentials (STS), the same `Action` list applies; the OBS endpoint accepts an `X-Security-Token` (obsutil `-t={token}`).
- If the caller lacks a specific permission (e.g. `GetBucketBlockPublicAccess`), the auditor script treats the item as "not configured" rather than failing the entire audit.
