# Verification Method

## 1. Prerequisites Verification

```bash
hcloud version                   # >= 3.2.0
obsutil version                  # >= 5.5.0
python3 --version                # >= 3.8
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs ls -limit=1   # credentials + endpoint OK
```

## 2. Read-only Verification (R3 actions, live)

```bash
# TC-01: bucket stat (ACL, versioning, metadata)
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs stat obs://{bucket}
# expect: bucket metadata including ACL, versioning status, storage class

# TC-02: bucket policy (HTTPS enforcement check)
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs bucketpolicy obs://{bucket} -method=get
# expect: bucket policy JSON or "no policy" message

# TC-03: CORS rules
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs cors obs://{bucket} -method=get
# expect: CORS configuration JSON or "no CORS" message

# TC-04: object listing (naming pattern)
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs ls obs://{bucket} -limit=100 -s
# expect: object keys + LastModified + size

# TC-05: encryption configuration
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud OBS GetBucketEncryption --bucket={bucket}
# expect: encryption config JSON or 404 (not configured)

# TC-06: replication configuration
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud OBS GetBucketReplication --bucket={bucket}
# expect: replication config JSON or 404 (not configured)

# TC-07: logging configuration
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud OBS GetBucketLogging --bucket={bucket}
# expect: logging config JSON or 404 (not configured)

# TC-08: Referer anti-hotlinking
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud OBS GetBucketReferer --bucket={bucket}
# expect: Referer config JSON or 404 (not configured)

# TC-09: BPA status
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud OBS GetBucketBlockPublicAccess --bucket={bucket}
# expect: BPA status JSON or 404 (not configured)
```

## 3. Full Audit Verification

```bash
# TC-10: full audit (text format)
python3 scripts/obs_security_auditor.py audit --bucket {bucket}
# expect: security score report with all 10 checks, grade, risk items, remediation

# TC-11: full audit (JSON format)
python3 scripts/obs_security_auditor.py audit --bucket {bucket} --format json --output /tmp/report.json
# expect: JSON report saved to /tmp/report.json, exit code 0 (no critical) or 1 (critical found)
```

## 4. Error Handling Verification

```bash
# TC-12: non-existent bucket
python3 scripts/obs_security_auditor.py audit --bucket non-existent-bucket-12345
# expect: report with ERROR status on all checks, graceful exit

# TC-13: bucket with no encryption (404 handling)
# (run against a bucket known to have no encryption configured)
# expect: encryption check shows CRITICAL "No encryption configured", not a script crash
```

## 5. Security Verification

```bash
# No hardcoded credentials in the skill
grep -rniE "access[_-]?key[[:space:]]*=[[:space:]]*['\"]?[A-Z0-9]{8,}" skills/storage/obs/huawei-cloud-obs-security-audit/ || echo "clean"

# No AK/SK in scripts
grep -rniE "(AK|SK|secret[_-]?key)[[:space:]]*=[[:space:]]*['\"]" skills/storage/obs/huawei-cloud-obs-security-audit/scripts/ || echo "clean"
```

## 6. Structure Compliance

```bash
bash scripts/validate-skill.sh skills/storage/obs/huawei-cloud-obs-security-audit
```

Expected: no FAIL on Critical checks (SKILL.md exists, frontmatter, name match, description + triggers, no version, required sections, iam-policies.md, no hardcoded credentials, no cross-skill references).

## 7. Acceptance Test Cases (from acceptance-criteria.md)

| Case | Action | Expected |
|------|--------|----------|
| TC-01 | bucket stat | metadata with ACL, versioning |
| TC-02 | bucket policy | policy JSON or no-policy message |
| TC-03 | CORS | CORS config or no-CORS message |
| TC-04 | list objects | keys/sizes returned |
| TC-05 | encryption | config JSON or 404 handled |
| TC-06 | replication | config JSON or 404 handled |
| TC-07 | logging | config JSON or 404 handled |
| TC-08 | Referer | config JSON or 404 handled |
| TC-09 | BPA | status JSON or 404 handled |
| TC-10 | full audit (text) | score report with all 10 checks |
| TC-11 | full audit (JSON) | JSON report saved to file |
| TC-12 | non-existent bucket | graceful error handling |
| TC-13 | 404 handling | "not configured" not crash |
