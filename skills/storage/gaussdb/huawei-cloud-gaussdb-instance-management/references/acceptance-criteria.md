# Acceptance Criteria

## Skill-level criteria

| # | Criteria | Verification |
|---|----------|--------------|
| AC-01 | SKILL.md frontmatter contains `name: huawei-cloud-gaussdb-instance-management`, description with trigger words, ≤5 tags, no `version` field | `grep` frontmatter |
| AC-02 | All 12 `huawei_*` actions are documented with level (R1/R2/R3) and routing to real CLI operations | Section "Action Routing Table" |
| AC-03 | Query + Analyze actions are read-only (R3) and marked auto-execute | SKILL.md tables |
| AC-04 | Manage actions (R2/R1) require preview + user confirmation before execution | Workflow section; preview step in dataflow diagram |
| AC-05 | 3 Critical Warnings preserved: shard key permanent / ≥3 nodes / engine version pinned | "Critical Warnings" section |
| AC-06 | `hcloud GaussDB` CLI dependency declared; both AK/SK env and local hcloud profile authentication documented | Prerequisites + cli-installation-guide.md |
| AC-07 | SKILL.md has a Quality Reporting section documenting skill_quality_sdk.py integration (SDK fetched from skillsopr when a Python wrapper is added) | section exists in SKILL.md |
| AC-08 | `references/iam-policies.md` exists with least-privilege policies | file exists |
| AC-09 | Every CLI command in SKILL.md uses parameters verified via `hcloud ... --help` | spot-check against help output |
| AC-10 | No hardcoded credentials; no secrets in the skill directory | gitleaks / grep for AK/SK patterns |

## Functional criteria

| # | Criteria | Verification |
|---|----------|--------------|
| AC-11 | `huawei_list_gaussdb_instances` returns live instance list (HTTP 200) | executed with real AK/SK profile |
| AC-12 | `huawei_list_gaussdb_flavors` and `huawei_list_gaussdb_databases` command syntax validated via `--help` | executed (no-instance account → empty list OK) |
| AC-13 | openGauss service (`gaussdbforopengauss`) smoke-tested read-only | executed with real AK/SK profile |
| AC-14 | Mutating commands present exact required params (create instance, backup, readonly node, sharding node, permission, delete) | compared with `--help` required list |

## Compliance criteria

| # | Criteria |
|---|----------|
| AC-15 | Skill directory `skills/storage/gaussdb/huawei-cloud-gaussdb-instance-management/` under `skills/` |
| AC-16 | SKILL.md ≤ 500 lines; total files ≤ 30; total size ≤ 40 MB |
| AC-17 | All files use allowlisted extensions (`.md`, `.py`) |
| AC-18 | PR changes only this one skill directory |