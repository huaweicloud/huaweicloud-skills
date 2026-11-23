# Acceptance Criteria

## 1. Structural Compliance (GitCode Skill Registration)

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-01 | SKILL.md exists with YAML frontmatter (`name`, `description`, `tags`; no `version`) | `bash scripts/validate-skill.sh skills/storage/obs/huawei-cloud-obs-security-audit` | |
| AC-02 | `name` matches directory name | `grep '^name:' SKILL.md` == `huawei-cloud-obs-security-audit` | |
| AC-03 | description contains feature summary + trigger words | `Triggers include:` present in frontmatter description | |
| AC-04 | All 11 `huawei_audit_*` actions documented with commands | Capability Matrix in SKILL.md = 11 rows | |
| AC-05 | Required sections present: Overview, Prerequisites, Workflow, Core Commands, Parameter Confirmation, Reference Documents | validate-skill.sh High checks | |
| AC-06 | `references/iam-policies.md` present (least privilege) | file exists | |
| AC-07 | `references/cli-installation-guide.md` present (CLI-based skill) | file exists | |
| AC-08 | No hardcoded AK/SK anywhere | `grep -rniE 'access.?key=.{8,}' skill dir` → clean | |
| AC-09 | No cross-skill named references | validate-skill.sh cross-skill check | |
| AC-10 | File count ≤ 30; SKILL.md ≤ 500 lines; all extensions in allowlist | validate-skill.sh Low checks | |
| AC-11 | Quality-CLI integration: ensure_cli.sh + install_cli.sh exist; SKILL.md contains skill-quality-cli run mandate | validate-skill.sh High check | |

## 2. Registration & Routing (11 Actions)

| # | Action | Registers | Routes to |
|---|--------|-----------|-----------|
| AC-12 | `huawei_audit_obs_acl` | Query R3 | `hcloud obs stat obs://{bucket}` |
| AC-13 | `huawei_audit_obs_bpa` | Query R3 | `hcloud OBS GetBucketBlockPublicAccess --bucket={bucket}` |
| AC-14 | `huawei_audit_obs_encryption` | Query R3 | `hcloud OBS GetBucketEncryption --bucket={bucket}` |
| AC-15 | `huawei_audit_obs_versioning` | Query R3 | `hcloud obs stat obs://{bucket}` |
| AC-16 | `huawei_audit_obs_replication` | Query R3 | `hcloud OBS GetBucketReplication --bucket={bucket}` |
| AC-17 | `huawei_audit_obs_https` | Query R3 | `hcloud obs bucketpolicy obs://{bucket} -method=get` |
| AC-18 | `huawei_audit_obs_logging` | Query R3 | `hcloud OBS GetBucketLogging --bucket={bucket}` |
| AC-19 | `huawei_audit_obs_referer` | Query R3 | `hcloud OBS GetBucketReferer --bucket={bucket}` |
| AC-20 | `huawei_audit_obs_cors` | Query R3 | `hcloud obs cors obs://{bucket} -method=get` |
| AC-21 | `huawei_audit_obs_naming` | Query R3 | `hcloud obs ls obs://{bucket} -limit={n} -s` |
| AC-22 | `huawei_audit_obs_full` | Analysis R3 | `scripts/obs_security_auditor.py audit --bucket={bucket}` |

## 3. Functional Criteria

| # | Criterion | Status |
|---|-----------|--------|
| AC-23 | All 10 audit checks execute without mutation and return structured results | |
| AC-24 | Security score model: ACL(15) + BPA(15) + Encryption(15) + Versioning(10) + Replication(10) + HTTPS(15) + Logging(10) + Referer(5) + CORS(5) + Naming(10) = 110 | |
| AC-25 | Grade levels: Excellent (99-110) / Good (77-98) / Fair (55-76) / High Risk (0-54) | |
| AC-26 | 404 responses for encryption/replication/logging/referer/BPA are handled as "not configured" (not errors) | |
| AC-27 | Risk items list includes severity (CRITICAL/WARN) and remediation recommendations | |
| AC-28 | Remediation recommendations are sorted by priority (P0 critical → P1 warning) | |
| AC-29 | Output supports both text and JSON formats | |
| AC-30 | Script accepts --bucket (required), --endpoint, --output, --format parameters | |
| AC-31 | Script exits with code 0 if no critical risks, 1 if critical risks exist | |

## 4. Results (filled during Phase 4/5 testing)

| Test Case | Result |
|-----------|--------|
| TC-01 bucket stat (live) | |
| TC-02 bucket policy (live) | |
| TC-03 CORS (live) | |
| TC-04 list objects (live) | |
| TC-05 encryption (live) | |
| TC-06 replication (live) | |
| TC-07 logging (live) | |
| TC-08 Referer (live) | |
| TC-09 BPA (live) | |
| TC-10 full audit text (live) | |
| TC-11 full audit JSON (live) | |
| TC-12 non-existent bucket (error handling) | |
| TC-13 404 handling (not configured) | |
