# Acceptance Criteria — huawei-cloud-dew-key-management

## Skill registration & routing

| # | Criterion | Verification |
|---|-----------|--------------|
| AC-01 | SKILL.md conforms to the GitCode Skill registration spec (frontmatter `name`/`description`/`tags`, no `version` field) | Spec/config check passes |
| AC-02 | All 10 `huawei_*` actions are documented and route to executable commands | `grep -c "huawei_" SKILL.md` ≥ 10 action definitions; each maps to a verified `hcloud` command |
| AC-03 | Skill directory `skills/security/dew/huawei-cloud-dew-key-management/` contains SKILL.md, scripts/, references/ | File existence check |

## Action coverage

| # | Action | Requirement | Level |
|---|--------|-------------|-------|
| AC-10 | huawei_list_csms_secrets | Lists all secrets (names + metadata, no values) | R3 auto |
| AC-11 | huawei_describe_csms_secret | Secret metadata: rotation config, KMS key, status | R3 auto |
| AC-12 | huawei_list_csms_secret_versions | Version IDs and stages, no values | R3 auto |
| AC-13 | huawei_list_kms_keys | Lists KMS keys | R3 auto |
| AC-14 | huawei_analyze_dew_rotation | Automatic rotation status analysis (CSMS + optional KMS rotation status) | R3 auto |
| AC-15 | huawei_analyze_dew_key_usage | KMS key usage audit via CTS (ListTraces, service_type=KMS) | R3 auto |
| AC-16 | huawei_create_kms_key | Creates a KMS key | R2 preview + confirm |
| AC-17 | huawei_enable_csms_secret_rotation | Enables automatic secret rotation | R2 preview + confirm |
| AC-18 | huawei_update_csms_secret_version | Manual rotation (immediate new version, value generated in background) | R1 preview + confirm |
| AC-19 | huawei_delete_kms_key | Schedules key deletion with pending window; irreversible warning shown | R1 preview + confirm |

## Security acceptance

| # | Criterion | Verification |
|---|-----------|--------------|
| AC-20 | Secret value reads blocked end-to-end (DownloadSecretBlob / ShowSecretVersion value / DecryptData) | BLOCKED operations table present; policy blocks these calls |
| AC-21 | MCP proxy resolve pattern `{{resolve:csms:...}}` documented for runtime injection | Mentioned in SKILL.md + references |
| AC-22 | Secret values never appear in agent context/output | No value-returning command in Core Commands; masked reporting |
| AC-23 | KMS deletion irreversible warning (7-30 day window, cancellable, then unrecoverable) | Present in SKILL.md + kms-usage.md |
| AC-24 | No hardcoded AK/SK or credentials anywhere | gitleaks / credential grep clean |
| AC-25 | Supports AK/SK env vars AND local hcloud profile auth | cli-installation-guide.md documents both |
| AC-26 | Write operations (R1/R2) require preview + confirmation | Confirmation gates documented in Workflow + per action |

## CLI dependency declaration

| # | Criterion | Verification |
|---|-----------|--------------|
| AC-30 | `hcloud DEW/CSMS/KMS/CTS` CLI dependency declared correctly | hcloud CLI in Prerequisites; service names match `hcloud <svc> --help` usage |
| AC-31 | Every concrete command includes `--cli-region` | grep check |
| AC-32 | Parameter names match `hcloud --help` exactly (KooCLI 7.2.12) | Verified during Phase 2 research |

## Quality & compliance

| # | Criterion | Verification |
|---|-----------|--------------|
| AC-40 | scripts/skill_quality_sdk.py present | File existence |
| AC-41 | SKILL.md Quality Reporting section + SKILL_QUALITY_* env vars | Section and table present |
| AC-42 | references/iam-policies.md (least privilege), cli-installation-guide.md exist | File existence |
| AC-43 | SKILL.md ≤ 500 lines; total files ≤ 30; extensions in allowlist | Spec check |

## Test evidence

All R3 read-only commands were executed against a real project and returned metadata
(see phase-4/phase-5 summaries). R2/R1 mutating commands were validated via `--help`
parameter verification and gated by the confirmation policy — they must only run in a
sandbox project with explicit user confirmation.