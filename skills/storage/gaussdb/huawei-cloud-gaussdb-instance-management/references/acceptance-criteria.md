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
| AC-07 | SKILL.md has a Quality Reporting section documenting the unified CLI reporting scheme (`skill-quality-cli`, installed by `scripts/ensure_cli.sh`) | section exists in SKILL.md |
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

## Quality reporting (CLI)

- [ ] `scripts/ensure_cli.sh` exists and is executable (idempotent `skill-quality-cli` local-deploy installer; deploys the **bundled** v1.1.8 source, no external download — SC2).
- [ ] `scripts/cli/cli_entry.py` + `scripts/cli/cli_reporting.py` are bundled v1.1.8 (zero-dependency in-skill carrier).
- [ ] `SKILL.md` contains the "Quality Reporting (Unified CLI)" section with Mode 1 (`run` wrap) /
  Mode 2 (`report`), the mandatory `skill-quality-cli run` wrapping rule for hcloud commands, and the TM1 tool-parameter whitelist (hcloud only).
- [ ] Every executable `hcloud` command in `SKILL.md` is wrapped with
  `skill-quality-cli run --skill-name huawei-cloud-gaussdb-instance-management -- ...`.
- [ ] `scripts/gaussdb_cli.sh` hard-binds reporting: success → `success`; usage error / cancelled → `biz_fail` (U01); hcloud API error → `biz_fail` (U03); hcloud missing / non-zero system failure → `sys_fail` (B01/C02).
- [ ] Reporting is fire-and-forget: never blocks, never changes business output or the exit code; skips when `SKILL_TRACE_ID` is set (wrapper already reported) or `SKILL_QUALITY_DISABLE=1` / `SKILL_QUALITY_REPORT=0`.
- [ ] E2E verified: `python3 scripts/cli/cli_entry.py --no-auto-upgrade report --skill-name huawei-cloud-gaussdb-instance-management --status success --json <cfg>` returns `[quality-report] OK trace_id=...`.
- [ ] No `skill_quality_sdk` remnants in the skill directory (scripts, SKILL.md, references).