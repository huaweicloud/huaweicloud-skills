# Acceptance Criteria

## 1. Structural compliance (GitCode Skill registration)

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-01 | SKILL.md exists with YAML frontmatter (`name`, `description`, `tags`; no `version`) | `bash scripts/validate-skill.sh skills/storage/obs/huawei-cloud-obs-lifecycle-management` | |
| AC-02 | `name` matches directory name | `grep '^name:' SKILL.md` == `huawei-cloud-obs-lifecycle-management` | |
| AC-03 | description contains feature summary + trigger words | `Triggers include:` present in frontmatter description | |
| AC-04 | All 9 `huawei_*` actions documented with commands | Capability Matrix in SKILL.md = 9 rows | |
| AC-05 | Required sections present: Overview, Prerequisites, Workflow, Core Commands, Parameter Confirmation, Reference Documents | validate-skill.sh High checks | |
| AC-06 | `references/iam-policies.md` present (least privilege) | file exists | |
| AC-07 | `references/cli-installation-guide.md` present (CLI-based skill) | file exists | |
| AC-08 | No hardcoded AK/SK anywhere | `grep -rniE 'access.?key=.{8,}' skill dir` → clean | |
| AC-09 | No cross-skill named references | validate-skill.sh cross-skill check | |
| AC-10 | File count ≤ 30; SKILL.md ≤ 500 lines; all extensions in allowlist | validate-skill.sh Low checks | |

## 2. Registration & routing (9 actions)

| # | Action | Registers | Routes to |
|---|--------|-----------|-----------|
| AC-11 | `huawei_list_obs_lifecycle_rules` | Query R3 | `hcloud obs lifecycle obs://{bucket} -method=get` |
| AC-12 | `huawei_get_obs_lifecycle_rule` | Query R3 | get + JSON filter by ID |
| AC-13 | `huawei_list_obs_objects` | Query R3 | `hcloud obs ls obs://{bucket} -limit={n} -s` |
| AC-14 | `huawei_diagnose_obs_lifecycle` | Analyze R3 | `scripts/obs_lifecycle_analyzer.py diagnose` |
| AC-15 | `huawei_analyze_obs_lifecycle_cost` | Analyze R3 | `scripts/obs_lifecycle_analyzer.py cost` |
| AC-16 | `huawei_preview_obs_lifecycle` | Analyze R3 | `scripts/obs_lifecycle_analyzer.py preview` |
| AC-17 | `huawei_create_obs_lifecycle_rule` | Manage R2 | preview + confirm → `-method=put` |
| AC-18 | `huawei_update_obs_lifecycle_rule` | Manage R2 | get → modify → preview + confirm → `-method=put` |
| AC-19 | `huawei_delete_obs_lifecycle_rule` | Manage R1 | get → remove → preview + confirm → `-method=put` |

## 3. Functional criteria

| # | Criterion | Status |
|---|-----------|--------|
| AC-20 | Read-only actions execute without mutation and return structured output | |
| AC-21 | Diagnose distinguishes: disabled rule / prefix mismatch / age not elapsed / overlapping rules / versioning / object already transitioned | |
| AC-22 | Cost analysis compares standard vs IA vs Archive/Deep Archive for the scanned object set | |
| AC-23 | Preview (dry-run) returns affected object count + total size and never mutates | |
| AC-24 | Manage actions refuse to run without preview + explicit user confirmation (`--apply` only for pre-confirmed automation) | |
| AC-25 | Create/update enforce merge-with-existing-rules (PUT semantics documented + implemented) | |
| AC-26 | Delete single rule preserves all other rules; full-config delete is clearly marked destructive | |

## 4. Results (filled during Phase 4/5 testing)

| Test case | Result |
|-----------|--------|
| TC-01 list rules (live) | |
| TC-02 get rule (live) | |
| TC-03 list objects (live) | |
| TC-04 stat bucket (live) | |
| TC-05 diagnose (live) | |
| TC-06 cost (live) | |
| TC-07 preview (live) | |
| TC-08 create rule (preview+confirm) | |
| TC-09 update rule (preview+confirm) | |
| TC-10 delete rule (preview+confirm) | |