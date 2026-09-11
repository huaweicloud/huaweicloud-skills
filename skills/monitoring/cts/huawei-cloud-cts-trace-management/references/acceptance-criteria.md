# Acceptance Criteria — huawei-cloud-cts-trace-management

## 1. Registration & Structure

- [ ] `SKILL.md` exists under `skills/{category}/{subcategory}/huawei-cloud-cts-trace-management/` with:
  - [ ] YAML frontmatter: `name: huawei-cloud-cts-trace-management` matches directory name; `description` contains feature
        summary and trigger words; `tags` ≤ 5; **no** `version` field
  - [ ] Required sections: Overview, Prerequisites, Workflow, Core Commands, Parameter Confirmation,
        Quality Reporting, Reference Documents, KooCLI Command Format Standard
  - [ ] SKILL.md ≤ 500 lines; total files ≤ 30; total size ≤ 40 MB; all file extensions allowed
- [ ] `references/iam-policies.md`, `references/cli-installation-guide.md`,
      `references/verification-method.md`, `references/dataflow-diagram.md`,
      `references/acceptance-criteria.md` exist and use kebab-case filenames
- [ ] `scripts/skill_quality_sdk.py` exists (vendored from skillsopr repo)
- [ ] No hardcoded credentials; no literal AK/SK or `hcloud configure set` with real values

## 2. Action Coverage (10 huawei_* actions)

| Action | Risk | Execution | Acceptance |
|--------|------|-----------|------------|
| `huawei_list_cts_trackers` | R3 | auto | `ListTrackers` returns tracker list JSON |
| `huawei_list_cts_traces` | R3 | auto | `ListTraces` returns traces filterable by from/to/user/service |
| `huawei_list_cts_operations` | R3 | auto | `ListOperations` returns operation list JSON |
| `huawei_list_cts_notifications` | R3 | auto | `ListNotifications` returns notification list JSON |
| `huawei_list_cts_trace_resources` | R3 | auto | `ListTraceResources` returns resource list JSON (uses `--domain_id`) |
| `huawei_analyze_cts_traces` | R3 | auto | Aggregates traces by user/time/operation dimensions |
| `huawei_analyze_cts_retention` | R3 | auto | Evaluates 7-day default vs LTS vs OBS retention |
| `huawei_create_cts_tracker` | R2 | preview+confirm | Validates OBS bucket first; creates tracker only after confirmation |
| `huawei_create_cts_notification` | R2 | preview+confirm | Creates notification only after confirmation |
| `huawei_delete_cts_tracker` | R1 | preview+confirm | Deletes data tracker only after confirmation; system tracker not deletable |

## 3. Critical Warnings (must be preserved)

- [ ] 无追踪器无事件 — skill checks/advises creating a tracker when traces are empty
- [ ] 追踪器需 OBS bucket 前置 — OBS bucket verified before tracker creation
- [ ] 审计事件默认仅保留 7 天 — retention trap surfaced; LTS recommended for long retention
- [ ] 组织级跨账号需组织追踪器 — `--is_organization_tracker=true` guidance present

## 4. CLI Correctness

- [ ] Every `hcloud CTS <Operation>` uses PascalCase operation names and includes `--cli-region`
- [ ] All required parameters from `--help` (KooCLI 7.2.12) are present in command examples
- [ ] Parameter names match `--help` output verbatim (e.g. `--obs_info.bucket_name`,
      `--operations.1.service_type`, indexed `--key.N=value` syntax)
- [ ] `ListTraceResources` uses `--domain_id` (not `--project_id`)

## 5. Security

- [ ] No credentials in files; output masking of AK/SK-like values
- [ ] No cross-skill direct calls (no named references to other skill directories)
- [ ] Write actions require explicit user confirmation
- [ ] Security audit (gitleaks/markdownlint/spec check) passes with no ERROR/CRITICAL findings