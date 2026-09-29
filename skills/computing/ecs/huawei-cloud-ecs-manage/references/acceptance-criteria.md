# Acceptance Criteria

Checklist that must pass before `huawei-cloud-ecs-manage` is accepted.

## A. Structure & compliance (华为云Skill检查规范)

- [ ] `SKILL.md` exists at `skills/computing/ecs/huawei-cloud-ecs-manage/SKILL.md`
- [ ] Frontmatter: valid YAML (`yaml.safe_load`), `name` == directory name, `description`
      contains feature summary + trigger words, `tags` ≤ 5, no `version` field
- [ ] SKILL.md ≤ 500 lines; total files ≤ 30; every file extension in the allowlist;
      no `__pycache__`, no `.pyc`, no `.markdownlint.json` inside the skill
- [ ] Required sections present: Overview, Prerequisites, Workflow, Core Commands,
      Parameter Confirmation, Reference Documents, KooCLI Command Format Standard
- [ ] `references/iam-policies.md`, `references/cli-installation-guide.md`,
      `references/verification-method.md`, `references/dataflow-diagram.md`,
      `references/acceptance-criteria.md` exist and use kebab-case filenames
- [ ] No hardcoded credentials anywhere; no cross-skill direct calls
- [ ] Every `hcloud` command includes `--cli-region`; service names title-case
      (`ECS`, `IMS`, `VPC`, `EVS`, `EIP`, `KPS`); operation names PascalCase

## B. Functional (per capability)

| Action | Required behavior | Pass |
| ------ | ----------------- | ---- |
| `huawei_list_ecs_instances` | lists instances with status; supports `--status`/`--limit` |  |
| `huawei_get_ecs_instance` | returns one instance detail incl. status/addresses/fault |  |
| `huawei_list_ecs_flavors` | lists flavors; `--availability_zone`/`--flavor_id` filters honored |  |
| `huawei_list_ecs_images` | lists images; `--__os_type`/`--architecture`/`--status=active` filters honored |  |
| `huawei_list_ecs_quotas` | returns `ShowServerLimits` absolute limits + usage |  |
| `huawei_diagnose_ecs_create_failure` | runs the 6 ordered checks (quota→flavor→image→network→keypair→disk), stops at first failure, outputs root cause + fix |  |
| `huawei_analyze_ecs_health` | reports status/disk/network verdict from ShowServer + volume + EIP checks |  |
| `huawei_create_ecs_instance` | R2: dry-run first, preview + confirm, then create; returns created server id |  |
| `huawei_start_ecs_instance` | R2: preview + confirm; instance reaches `ACTIVE` |  |
| `huawei_stop_ecs_instance` | R2: preview + confirm; instance reaches `SHUTOFF` |  |
| `huawei_restart_ecs_instance` | R2: preview + confirm; instance reboots |  |
| `huawei_delete_ecs_instance` | R1: verify + irreversible warning + confirm; instance deleted (or in recycle bin) |  |

## C. Confirmation gates

- [ ] No write command ever auto-executes without user confirmation
- [ ] `huawei_delete_ecs_instance` always warns about `--delete_volume` / `--delete_publicip` data loss
- [ ] `huawei_create_ecs_instance` always offers `--dry_run=true` validation before the real create

## D. Test evidence

- [ ] All syntax cases (`--help`) pass against KooCLI 7.2.12
- [ ] All read-only cases return clean JSON (no `error_code`/`error_msg`) with valid credentials
- [ ] Write cases verified via dry-run and, where a test instance exists, full lifecycle
      create → query → stop → start → restart → delete with resource release confirmed

## E. Quality telemetry

- [ ] `scripts/ensure_cli.sh` present; `skill-quality-cli` runnable; `SKILL_QUALITY_REPORT=0` honored