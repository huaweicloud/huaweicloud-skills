# Security Check Catalog

Detailed description of all 10 security audit items, including the check logic, scoring rules, and remediation guidance for each.

## Check 1: Bucket ACL Permissions

| Attribute | Value |
|-----------|-------|
| **Action** | `huawei_audit_obs_acl` |
| **Command** | `hcloud obs stat obs://{bucket}` |
| **Max Score** | 15 |
| **Weight** | High |

**Check Logic:** The `hcloud obs stat` command returns bucket metadata including the ACL setting. The auditor extracts the ACL value and classifies it.

**Scoring:**
- `private` → 15/15 (PASS) — only the owner can read/write
- `public-read` → 5/15 (WARN) — anyone can read; risk of data exposure
- `public-read-write` → 0/15 (CRITICAL) — anyone can read/write; severe security risk

**Remediation:** Set ACL to private unless public access is intentionally required. Use pre-signed URLs for temporary sharing instead.

---

## Check 2: Block Public Access (BPA)

| Attribute | Value |
|-----------|-------|
| **Action** | `huawei_audit_obs_bpa` |
| **Command** | `hcloud OBS GetBucketBlockPublicAccess --bucket={bucket}` |
| **Max Score** | 15 |
| **Weight** | High |

**Check Logic:** Queries the BPA configuration via hcloud OpenAPI mode. BPA, when enabled, ignores existing public access permissions (ACL, bucket policy) and prevents creating new public access configurations.

**Scoring:**
- BPA enabled → 15/15 (PASS)
- BPA disabled / not configured → 0/15 (CRITICAL)

**Remediation:** Enable BPA to prevent unintended public access. This is the strongest safeguard against accidental data exposure.

---

## Check 3: Bucket Encryption

| Attribute | Value |
|-----------|-------|
| **Action** | `huawei_audit_obs_encryption` |
| **Command** | `hcloud OBS GetBucketEncryption --bucket={bucket}` |
| **Max Score** | 15 |
| **Weight** | High |

**Check Logic:** Queries the server-side encryption configuration. OBS supports three encryption modes.

**Scoring:**
- `SSE-KMS` → 15/15 (PASS) — uses KMS-managed keys, best practice
- `SSE-OBS` → 12/15 (PASS) — uses OBS-managed keys, acceptable
- `SSE-C` → 10/15 (PASS) — uses customer-provided keys, requires key management
- No encryption → 0/15 (CRITICAL)

**Remediation:** Enable SSE-KMS encryption for sensitive data. SSE-KMS provides centralized key management via KMS and supports key rotation.

---

## Check 4: Multi-Version Control

| Attribute | Value |
|-----------|-------|
| **Action** | `huawei_audit_obs_versioning` |
| **Command** | `hcloud obs stat obs://{bucket}` (includes versioning status) |
| **Max Score** | 10 |
| **Weight** | Medium |

**Check Logic:** The `hcloud obs stat` output includes the versioning status of the bucket.

**Scoring:**
- Versioning enabled → 10/10 (PASS)
- Versioning suspended → 0/10 (WARN)
- Versioning not enabled → 0/10 (WARN)

**Remediation:** Enable versioning to retain multiple versions of objects, providing quick recovery from accidental deletion or overwrite.

---

## Check 5: Cross-Region Replication

| Attribute | Value |
|-----------|-------|
| **Action** | `huawei_audit_obs_replication` |
| **Command** | `hcloud OBS GetBucketReplication --bucket={bucket}` |
| **Max Score** | 10 |
| **Weight** | Medium |

**Check Logic:** Queries the cross-region replication configuration. Replication provides disaster recovery by copying objects to a different region.

**Scoring:**
- Replication configured → 10/10 (PASS)
- No replication → 0/10 (WARN)

**Remediation:** Configure cross-region replication for critical data to ensure disaster recovery capability.

---

## Check 6: HTTPS Enforcement

| Attribute | Value |
|-----------|-------|
| **Action** | `huawei_audit_obs_https` |
| **Command** | `hcloud obs bucketpolicy obs://{bucket} -method=get` |
| **Max Score** | 15 |
| **Weight** | High |

**Check Logic:** Retrieves the bucket policy JSON and checks for a `SecureTransport=true` condition. This condition enforces that all requests must use HTTPS.

**Scoring:**
- Policy contains `SecureTransport=true` → 15/15 (PASS)
- No such condition / no policy → 0/15 (CRITICAL)

**Remediation:** Add a bucket policy with a `SecureTransport=true` condition to enforce HTTPS-only access. Example policy snippet:

```json
{
  "Statement": [{
    "Effect": "Deny",
    "Action": "*",
    "Principal": "*",
    "Condition": {"Bool": {"SecureTransport": "false"}}
  }]
}
```

---

## Check 7: Bucket Logging

| Attribute | Value |
|-----------|-------|
| **Action** | `huawei_audit_obs_logging` |
| **Command** | `hcloud OBS GetBucketLogging --bucket={bucket}` |
| **Max Score** | 10 |
| **Weight** | Medium |

**Check Logic:** Queries the bucket logging configuration. When enabled, OBS records all access requests to a target bucket.

**Scoring:**
- Logging enabled → 10/10 (PASS)
- Logging not configured → 0/10 (WARN)

**Remediation:** Enable bucket logging to record all access requests. Configure a target bucket to receive the log files. Use the logs to detect malicious access via Remote IP analysis.

---

## Check 8: Referer Anti-Hotlinking

| Attribute | Value |
|-----------|-------|
| **Action** | `huawei_audit_obs_referer` |
| **Command** | `hcloud OBS GetBucketReferer --bucket={bucket}` |
| **Max Score** | 5 |
| **Weight** | Medium |

**Check Logic:** Queries the Referer anti-hotlinking configuration. This feature checks the `Referer` header of incoming requests against a whitelist or blacklist.

**Scoring:**
- Referer rules configured → 5/5 (PASS)
- Not configured → 0/5 (WARN)

**Remediation:** Configure Referer rules to prevent unauthorized hotlinking, especially for buckets hosting public content.

---

## Check 9: CORS Rules

| Attribute | Value |
|-----------|-------|
| **Action** | `huawei_audit_obs_cors` |
| **Command** | `hcloud obs cors obs://{bucket} -method=get` |
| **Max Score** | 5 |
| **Weight** | Low |

**Check Logic:** Queries the CORS (Cross-Origin Resource Sharing) configuration and checks for wildcard (`*`) origins.

**Scoring:**
- CORS rules with specific origins (no wildcard) → 5/5 (PASS)
- CORS rules with wildcard (`*`) origin → 2/5 (WARN)
- No CORS configured → 5/5 (PASS, acceptable if no cross-domain access needed)

**Remediation:** If CORS is required, restrict origins to specific domains instead of using wildcard `*`.

---

## Check 10: Object Naming Pattern

| Attribute | Value |
|-----------|-------|
| **Action** | `huawei_audit_obs_naming` |
| **Command** | `hcloud obs ls obs://{bucket} -limit={limit} -s` |
| **Max Score** | 10 |
| **Weight** | Low |

**Check Logic:** Lists objects in the bucket and analyzes the key prefixes for sequential naming patterns (dates, timestamps, sequential numeric IDs, alphabetic sequences). Sequential prefixes cause uneven key distribution in OBS's hash-based partitioning, leading to performance bottlenecks and potential security enumeration risks.

**Scoring:**
- Random prefixes (hex hash, UUID) → 10/10 (PASS)
- Partial sequential prefixes (30-70% of objects) → 5/10 (WARN)
- Fully sequential prefixes (>70% of objects) → 0/10 (CRITICAL)

**Sequential patterns detected:**
- Date prefixes: `2024-01-15/`, `20240115/`
- Timestamp prefixes: `1699836400_file.txt`
- Sequential numeric IDs: `000001/`, `000002/`
- Alphabetic sequences: `a/`, `b/`, `c/`

**Remediation:** Use hex hash prefixes (e.g., first 4-8 characters of a SHA-256 hash) instead of sequential naming. This ensures even distribution across OBS partitions and prevents enumeration attacks.
