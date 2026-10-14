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

## Quality Criteria

| # | Criterion |
| --- | ----------- |
| 1 | `scripts/skill_quality_sdk.py` present and runnable (`python3 -m py_compile`) |
| 2 | No AK/SK hardcoded anywhere in the skill |
| 3 | SKILL.md ≤ 500 lines; references use lowercase kebab-case filenames |
| 4 | Frontmatter: `name` matches directory name, no `version` field |
| 5 | Required sections present: Overview, Prerequisites, Workflow, Core Commands, Parameter Confirmation, Reference Documents |
| 6 | `references/iam-policies.md` and `references/cli-installation-guide.md` exist |

## Constraints

- Query operations: fully automatic, no confirmation needed.
- Mutating operations: **never executed without explicit user confirmation**.
- Credentials come from environment variables, never hardcoded.