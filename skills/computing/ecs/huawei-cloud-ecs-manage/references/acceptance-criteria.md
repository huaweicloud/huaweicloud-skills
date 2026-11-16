# Acceptance Criteria

Checklist that must pass before `huawei-cloud-ecs-manage` is accepted.

## A. Structure & compliance (华为云Skill检查规范)

- [ ] `SKILL.md` exists at `skills/computing/ecs/huawei-cloud-ecs-manage/SKILL.md`
- [ ] Frontmatter: valid YAML (`yaml.safe_load`), `name` == directory name, `description`
      contains feature summary + trigger words, `tags` ≤ 5, no `version` field
- [ ] SKILL.md ≤ 500 lines; total files ≤ 30; every file extension in the allowlist;
      no `__pycache__`, no `.pyc`, no `.markdownlint.json`, no `tests/` directory inside the skill
- [ ] Required sections present: Overview, Prerequisites, Workflow, Core Commands,
      Parameter Confirmation, Reference Documents, KooCLI Command Format Standard
- [ ] `references/iam-policies.md`, `references/cli-installation-guide.md`,
      `references/verification-method.md`, `references/dataflow-diagram.md`,
      `references/acceptance-criteria.md`, `references/manage-operations.md`,
      `references/sdk-examples.md`, `references/related-skills.md` exist and use kebab-case filenames
- [ ] No hardcoded credentials anywhere; no cross-skill direct calls (out-of-scope requests are
      handed back to the user, never invoked by this skill)
- [ ] Every executable `hcloud` command block includes `--cli-region` (inline prose/table mentions
      rely on the "append `--cli-region` to every command" instruction instead); service names
      title-case (`ECS`, `IMS`, `VPC`, `EVS`, `EIP`, `KPS`); operation names PascalCase

## B. Functional (per capability)

### B1. Query & diagnose (R3, read-only)

| Action | Required behavior | Pass |
| ------ | ----------------- | ---- |
| `huawei_list_ecs_instances` | lists instances with status; supports `--status`/`--limit` |  |
| `huawei_get_ecs_instance` | returns one instance detail incl. status/addresses/fault |  |
| `huawei_list_ecs_flavors` | lists flavors; `--availability_zone`/`--flavor_id` filters honored |  |
| `huawei_list_ecs_images` | lists images; `--__os_type`/`--architecture`/`--status=active` filters honored |  |
| `huawei_list_ecs_quotas` | returns `ShowServerLimits` absolute limits + usage |  |
| `huawei_diagnose_ecs_create_failure` | runs the 8 ordered checks (IAM→balance→quota→flavor→image→network→keypair→disk), distinguishes IAM 403 from balance/arrears, stops at first failure, outputs root cause + fix |  |
| `huawei_analyze_ecs_health` | reports status/disk/network verdict from ShowServer + volume + EIP checks |  |

### B2. Lifecycle management (R2/R1)

| Action | Required behavior | Pass |
| ------ | ----------------- | ---- |
| `huawei_create_ecs_instance` | R2: dry-run first, preview + confirm, then create; returns created server id |  |
| `huawei_start_ecs_instance` | R2: preview + confirm; instance reaches `ACTIVE` |  |
| `huawei_stop_ecs_instance` | R2: preview + confirm; instance reaches `SHUTOFF` |  |
| `huawei_restart_ecs_instance` | R2: preview + confirm; instance reboots |  |
| `huawei_delete_ecs_instance` | R1: verify + irreversible warning + confirm; instance deleted (or in recycle bin) |  |

### B3. Change operations (R2/R1)

| Action | Required behavior | Pass |
| ------ | ----------------- | ---- |
| `huawei_resize_ecs_instance` | R2: `ResizeServer` with `--dry_run=true` first; job polled to terminal state |  |
| `huawei_reinstall_ecs_os` | R2: `ReinstallServerWithCloudInit`; keeps the current image; password xor keypair |  |
| `huawei_reset_ecs_password` | R2: `ResetServerPassword`; new password never echoed back |  |
| `huawei_replace_ecs_keypair` | R2 create (`NovaCreateKeypair`) / R1 retire (`NovaDeleteKeypair`); documentation states a running instance cannot be re-bound and gives the install-public-key alternative |  |
| `huawei_bind_ecs_eip` | R2: `EIP AssociatePublicips` with `associate_instance_type=PORT` |  |
| `huawei_unbind_ecs_eip` | R1: `EIP DisassociatePublicips`; public-access loss warned |  |
| `huawei_change_ecs_security_group` | R2 attach and detach; SG UUID passed via `--addSecurityGroup.name` (accepts UUID or name), name inputs resolved via `VPC ListSecurityGroups/v2`; duplicate name rejected; access loss warned |  |
| `huawei_add_ecs_nic` | R2: `BatchAddServerNics` on an existing subnet |  |
| `huawei_remove_ecs_nic` | R1: `BatchDeleteServerNics`; primary NIC rejected (403) surfaced clearly |  |
| `huawei_attach_ecs_volume` | R2: `AttachServerVolume` with `--dry_run=true` first |  |
| `huawei_detach_ecs_volume` | R2: `DetachServerVolume`; unmount in-guest first; `--delete_flag=1` impact warned |  |

### B3b. Batch, tags, ops assist (issue #1105)

| Action | Required behavior | Pass |
| ------ | ----------------- | ---- |
| `huawei_batch_start_ecs_by_tag` / `_stop_` / `_reboot_` | R2: resolve tag with paginated `ListServersDetails --tags`, preview id/name/status list + count, > 50 → second confirmation, execute per id, return `success` + `failed[{id,error_code}]`, one failure does not abort |  |
| `huawei_batch_tag_ecs` / `huawei_batch_untag_ecs` | R2: target by instance-id list or query condition, preview target list + tag changes, loop per id, aggregate results; tag key/value limits honored |  |
| `huawei_get_ecs_vnc_console` | R3: `ShowServerRemoteConsole` with `protocol=vnc`/`type=novnc`, returns URL + short-validity note, URL never logged/persisted |  |
| `huawei_change_ecs_enterprise_project` | R2: `EPS MigrateResource` with real `resource_type` from `ListResourceMapping`; current/target EP + billing impact previewed and confirmed |  |
| `huawei_create_ecs_instance` (billing modes) | R2: `prePaid` needs `period_type`+`period_num`; spot needs `chargingMode=postPaid`+`marketType=spot`; `--dry_run=true` + cost warning before create |  |
| `huawei_batch_create_ecs_instances` | R2: per-group plan `{flavor,image,subnet,count}`, total count preview, group-by-group execution, per-server aggregation |  |
| CES metric entry | R3: documented `CES ListMetrics` / `ShowMetricData` entry plus hand-off to `huawei-cloud-ces-ecs-monitoring` |  |

### B4. Async job contract (applies to every write action above)

| Requirement | Pass |
| ----------- | ---- |
| The returned `job_id` is extracted and polled with `hcloud ECS ShowJob` until `SUCCESS`/`FAIL` |  |
| `create` additionally polls `hcloud ECS ShowServer` until `status=ACTIVE` |  |
| `SUCCESS` → final state reported; `FAIL` → `fail_reason` + failed sub-job reported, no blind retry |  |
| A polling timeout is reported as "still running (job_id=…)", never as success |  |

## C. Confirmation gates

- [ ] No write command ever auto-executes without user confirmation
- [ ] `huawei_delete_ecs_instance` always warns about `--delete_volume` / `--delete_publicip` data loss
- [ ] `huawei_create_ecs_instance` always offers `--dry_run=true` validation before the real create
- [ ] `prePaid` / `spot` creation states billing mode, period and cost before confirmation
- [ ] Batch actions print the resolved target list + count and require a second confirmation above 50
- [ ] Every change operation shows the current state before the preview; the two R1 actions
      (`huawei_unbind_ecs_eip`, `huawei_remove_ecs_nic`) state the connectivity / private-IP impact
      explicitly, and `huawei_detach_ecs_volume` (R2) warns about `--delete_flag=1`

## D. Documentation completeness

- [ ] `references/manage-operations.md` documents all 11 change actions plus batch-by-tag / tags / VNC / enterprise-project / billing-mode sections with verified parameters
- [ ] `references/sdk-examples.md` provides Python **and** Java examples for create / start / stop /
      restart / delete, plus batch / tag / prePaid / spot / VNC examples and a worked create-failure
      troubleshooting example
- [ ] `references/related-skills.md` states the capability boundary, lists monitoring/VPC/subnet/
      security-group/EVS/RDS entries, and contains one executable cross-skill orchestration path

## E. Test evidence

- [ ] All syntax cases (`--help`) pass against KooCLI 7.3.12, including the 11 change operations,
      `CreateServers`, `BatchCreateServerTags`/`BatchDeleteServerTags`, `ShowServerRemoteConsole`,
      `UpdateServer` and `EPS MigrateResource` (`ReinstallServerWithCloudInit`, not
      `ReinstallServer`; `EIP` service for EIP bind/unbind)
- [ ] All read-only cases return clean JSON (no `error_code`/`error_msg`) with valid credentials
- [ ] Write cases verified via dry-run and, where a test instance exists, full lifecycle
      create → query → stop → start → restart → delete with resource release confirmed
- [ ] `templates/test-vars.json` parses as JSON and marks every write case (lifecycle / change /
      batch / tag / enterprise-project) `write` (never auto-executed)

## F. Quality telemetry

- [ ] `scripts/ensure_cli.sh` present; `skill-quality-cli` runnable; `SKILL_QUALITY_REPORT=0` honored
