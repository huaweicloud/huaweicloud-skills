# Acceptance Criteria

## Functional Criteria

| # | Criterion | Verification |
| --- | ----------- | -------------- |
| 1 | Skill lists ECS instances with filters and pagination | `hcloud ECS ListServersDetails --cli-region={region} --limit=5` returns valid JSON |
| 2 | Skill shows ECS instance detail | `hcloud ECS ShowServer --cli-region={region} --server_id={id}` returns the instance object |
| 3 | Skill prompts user confirmation before every mutating operation | Workflow text for Create/Delete/Start/Stop/Reboot/Rename includes explicit confirmation step |
| 4 | Skill creates an ECS instance | `CreateServers` returns server id / job and instance reaches `ACTIVE` |
| 5 | Skill starts/stops/reboots instances | `BatchStartServers`/`BatchStopServers`/`BatchRebootServers` change the instance status as expected |
| 6 | Skill renames instances | `BatchUpdateServersName` changes `name` (verified via `ShowServer`) |
| 7 | Skill deletes instances | `DeleteServers` removes the instance (verified via `ListServersDetails`) |
| 8 | Skill answers basic ECS knowledge questions | FAQ section covers flavors, billing, login, status |
| 9 | All CLI parameter names match the corresponding KooCLI `--help` output | Grep each command's params against --help output |
| 10 | Every concrete CLI command includes `--cli-region` | Visual / grep check |
| 11 | Skill validates the environment at the entry point (Workflow Step 0) | `bash scripts/preflight_check.sh --region={region}` exits 0 when the environment is ready, and exits non-zero with installation/authentication guidance when `hcloud` is absent from `PATH`, credentials are missing, or no region is resolvable |
| 12 | Skill reinstalls the operating system | `ReinstallServerWithCloudInit` / `ReinstallServerWithoutCloudInit` accepted with `--server_id`; instance returns to `ACTIVE` (or stays `SHUTOFF` when it was stopped beforehand), verified via `ShowServer` |
| 13 | Skill switches the operating system image | `ChangeServerOsWithCloudInit` / `ChangeServerOsWithoutCloudInit` accepted with `--server_id` and `--os-change.imageid` |
| 14 | Skill resizes an instance (change flavor) | `ListResizeFlavors` returns candidate flavors; `ResizeServer --dry_run=true` validates without changing anything; `ResizeServer` applies and `ShowServer` reports the new `flavor.id` |
| 15 | OS-change and resize operations warn about disruption and require confirmation | Command sections carry explicit confirmation + system-disk-reset / restart warnings |
| 16 | Documented operation names exist in KooCLI | `hcloud ECS <Operation> --help` succeeds for every documented operation; the nonexistent `ReinstallOs` / `ChangeServerFleet` are documented only as a correction mapping |

## Quality Criteria

| # | Criterion |
| --- | ----------- |
| 1 | `scripts/skill_quality_sdk.py` present and runnable (`python3 -m py_compile`) |
| 2 | No AK/SK hardcoded anywhere in the skill |
| 3 | SKILL.md ≤ 500 lines; references use lowercase kebab-case filenames |
| 4 | Frontmatter: `name` matches directory name, no `version` field |
| 5 | Required sections present: Overview, Prerequisites, Workflow, Core Commands, Parameter Confirmation, Reference Documents |
| 6 | `references/iam-policies.md` and `references/cli-installation-guide.md` exist |
| 7 | `scripts/preflight_check.sh` exists, passes `bash -n`, and is referenced by both SKILL.md Step 0 and `references/cli-installation-guide.md` |
| 8 | `references/lifecycle-change-operations.md` exists and every operation/parameter it documents was verified against `hcloud ECS <Operation> --help` |
| 9 | No fabricated operation or parameter name anywhere in the skill (notably `ReinstallOs` / `ChangeServerFleet` appear only as an explicitly-labelled correction) |

## Constraints

- Query operations: fully automatic, no confirmation needed.
- Mutating operations: **never executed without explicit user confirmation**.
- OS reinstall / OS change **reinitialize the system disk** (data loss) and resize **restarts the
  instance** — both must be presented as disruptive changes and confirmed before execution, and
  resize must be preceded by a `--dry_run=true` pre-check.
- The Step 0 preflight must run before any ECS command; a preflight failure aborts the run rather
  than degrading into a mid-workflow `command not found`.
- Credentials come from environment variables, never hardcoded.