# Acceptance Criteria — huawei-cloud-deployment-task-management

## 1. Registration & Structure

- [ ] `SKILL.md` exists under `skills/{category}/{subcategory}/huawei-cloud-deployment-task-management/` with:
  - [ ] YAML frontmatter: `name: huawei-cloud-deployment-task-management` matches directory name; `description` contains
        feature summary and trigger words; `tags` ≤ 5; **no** `version` field
  - [ ] Required sections: Overview, Prerequisites, Workflow, Core Commands, Parameter Confirmation,
        Quality Reporting, Reference Documents, KooCLI Command Format Standard
  - [ ] SKILL.md ≤ 500 lines; total files ≤ 30; total size ≤ 40 MB; all file extensions allowed
- [ ] `references/iam-policies.md`, `references/cli-installation-guide.md`,
      `references/verification-method.md`, `references/dataflow-diagram.md`,
      `references/acceptance-criteria.md` exist and use kebab-case filenames
- [ ] `scripts/skill_quality_sdk.py` exists (vendored from skillsopr repo)
- [ ] No hardcoded credentials; no literal AK/SK or `hcloud configure set` with real values

## 2. Action Coverage (9 huawei_* actions)

| Action | Risk | Execution | Acceptance |
|--------|------|-----------|------------|
| `huawei_list_clouddeploy_apps` | R3 | auto | `ListAllApp` returns application list JSON |
| `huawei_list_clouddeploy_tasks` | R3 | auto | `ListDeployTasks` returns task list JSON |
| `huawei_get_clouddeploy_task` | R3 | auto | `ShowDeployTaskDetail` returns task detail JSON |
| `huawei_analyze_clouddeploy_failure` | R3 | auto | `ListDeployTaskHistoryByDate` history evaluated for agent/timeout/artifact/permission causes |
| `huawei_analyze_clouddeploy_artifact` | R3 | auto | Task artifact config verified against the OBS object (`hcloud obs ls`) |
| `huawei_create_clouddeploy_app` | R2 | preview+confirm | Name uniqueness pre-checked; app created only after confirmation |
| `huawei_create_clouddeploy_task` | R2 | preview+confirm | Task created referencing an existing app only after confirmation |
| `huawei_start_clouddeploy_task` | R2 | preview+confirm | Task started only after confirmation; host agent online |
| `huawei_delete_clouddeploy_task` | R1 | preview+explicit confirm | Task deleted only after explicit second confirmation |

## 3. Critical Warnings (must be preserved)

- [ ] Flyway SQL dialect mismatch (H2 → MySQL) — migration audit guidance present
- [ ] Service name is `CodeArtsDeploy` (verify with `hcloud --help`; `CloudDeploy` unsupported)
- [ ] Deployment hosts need the agent installed before tasks can run
- [ ] Task must reference an application (app created before task)
- [ ] Artifact source defaults to OBS — bucket/object verified before start
- [ ] Parallel deployments may conflict — running-task check / serialization guidance
- [ ] Security baseline — IAM roles, artifact integrity, no plaintext credentials

## 4. CLI Correctness

- [ ] Every `hcloud CodeArtsDeploy <Operation>` uses PascalCase operation names and includes
      `--cli-region`
- [ ] All required parameters from `--help` (KooCLI 7.2.12) are present in command examples
- [ ] Parameter names match `--help` output verbatim (e.g. `--states.1=failed`,
      `--params.1.type=encrypt`, `--configs.1.name`, `--create_type=template`)
- [ ] `CheckIsDuplicateAppName` used as pre-check for `huawei_create_clouddeploy_app`

## 5. Security

- [ ] No credentials in files; output masking of AK/SK-like values
- [ ] No cross-skill direct calls (no named references to other skill directories)
- [ ] Write actions require explicit user confirmation (R2 preview+confirm, R1 double confirm)
- [ ] Security audit (gitleaks/markdownlint/spec check) passes with no ERROR/CRITICAL findings