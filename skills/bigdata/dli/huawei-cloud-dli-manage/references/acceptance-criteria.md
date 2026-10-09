# Acceptance Criteria

## Qualification Gates

- [ ] `skills/bigdata/dli/huawei-cloud-dli-manage/SKILL.md` exists with valid YAML frontmatter (`name`, `description`, `tags`, no `version`)
- [ ] Frontmatter `name` matches the directory name: `huawei-cloud-dli-manage`
- [ ] `description` includes feature summary + trigger words
- [ ] Required sections present: Overview, Prerequisites, Workflow, Core Commands, Parameter Confirmation, Reference Documents
- [ ] SKILL.md ≤ 500 lines
- [ ] `references/iam-policies.md` exists (least privilege)
- [ ] `references/cli-installation-guide.md` exists (CLI used)
- [ ] Every concrete CLI command includes `--cli-region` and all required parameters verified against `hcloud dli <Op> --help`
- [ ] No hardcoded credentials anywhere; AK/SK only from environment
- [ ] High-risk operations (delete/cancel/stop/scale-in) explicitly gated by double confirmation
- [ ] No cross-skill direct calls

## Functional Acceptance

| Scenario | Accept Criteria |
|----------|-----------------|
| Queue patrol | `ListQueues` + `ShowQuota` + pools return inventory with CU usage, highlight > 80% usage |
| SQL job troubleshooting | Search by `--job-status=failed`, pull status/log detail, produce root-cause report |
| Flink job stop | `BatchStopFlinkJobs` executes only after user double confirmation; savepoint flag honored |
| Connectivity check | `CreateConnectivityTask` + `ShowConnectivityTask` reports success/failure per queue-address pair |
| Idle cleanup | Proposals listed first; deletions only after explicit user confirmation; snapshot output |
| Owner change | `UpdateTableOwner`/`UpdateDatabaseOwner`/`UpdateJobResourceOwner` verified via re-query |

## Verification Evidence

- [ ] At least 3 read-only smoke commands executed successfully against a live DLI account (output `is_success: true`)
- [ ] `--help` parameter cross-check performed for every documented command
- [ ] Skill passes skillcheck / markdownlint / hwcloud-spec / gitleaks (or deviations explicitly accepted)