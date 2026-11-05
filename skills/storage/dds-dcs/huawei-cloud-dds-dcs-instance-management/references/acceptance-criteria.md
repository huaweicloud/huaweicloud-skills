# Acceptance Criteria

## Query Operations (R3)

| # | Criteria | Verification Method |
|---|----------|--------------------|
| 1 | `huawei_list_dds_instances` returns DDS instance list with pagination support | Execute CLI command and verify JSON output |
| 2 | `huawei_get_dds_instance` returns single DDS instance details by ID | Execute CLI with `--id` filter |
| 3 | `huawei_list_dcs_instances` returns DCS instance list with filtering | Execute CLI command with various filters |
| 4 | `huawei_get_dcs_nodes_information` returns node topology for DCS instance | CLI primary: `hcloud DCS ShowNodesInformation --cli-region={region} --instance_id={id}`; SDK fallback (`show_nodes_information`) only when the CLI is unavailable; verify the returned node list |
| 5 | `huawei_list_dcs_custom_templates` returns list of custom config templates | CLI primary: `hcloud DCS ListConfigTemplates --cli-region={region} --type={sys\|user}`; SDK fallback (`list_config_templates`); verify the returned template list |

## Analysis Operations (R3)

| # | Criteria | Verification Method |
|---|----------|--------------------|
| 6 | `huawei_analyze_dds_deployment` combines all DDS queries into deployment assessment | Run analysis workflow and validate output structure |
| 7 | `huawei_analyze_dcs_security` checks whitelist, SSL, ACL, and password policies | Run security analysis workflow |

## Management Operations (R2)

| # | Criteria | Verification Method |
|---|----------|--------------------|
| 8 | `huawei_create_dds_instance` accepts valid parameters and creates instance | Confirm user, then execute with test params (including `--flavor.{N}.size` as a multiple of 10 and `--flavor.{N}.storage=ULTRAHIGH`) |
| 9 | `huawei_add_dds_readonly_node` adds nodes to replica set | Confirm user, then query `hcloud DDS ListFlavors --engine_name=DDS-Community` for a `.rr` spec code, execute `AddReadonlyNode --spec_code={spec_code_rr}`; if the region exposes no `.rr` spec, report the capability as unavailable instead of retrying |
| 10 | `huawei_add_dds_sharding_node` adds shard/mongos to cluster | Confirm user, then execute; `--volume.size` (10–2000 GB) is supplied for `--type=shard` |
| 11 | `huawei_create_dds_backup` creates manual backup | Execute and verify backup list |
| 12 | `huawei_create_dcs_instance` creates new cache instance — CLI primary (`hcloud DCS CreateInstance`), SDK fallback | Confirm user, then execute the CLI command with the required params (`--name`, `--engine`, `--capacity`, `--spec_code`, `--vpc_id`, `--subnet_id`, `--az_codes.1`, and `--password` unless `--no_password_access=true`); fall back to the SDK script only when the CLI is unavailable |
| 13 | `huawei_create_dcs_custom_template` creates custom template — CLI primary (`hcloud DCS CreateCustomTemplate`), SDK fallback | Execute the CLI command with `--name`, `--template_id`, `--type` matching the source template (`sys`/`user`) and `--params.{*}`; verify against the template list; SDK fallback only when the CLI is unavailable |

## Management Operations (R1)

| # | Criteria | Verification Method |
|---|----------|--------------------|
| 14 | `huawei_delete_dds_instance` permanently deletes DDS instance | Double-confirm user, then execute |
| 15 | `huawei_delete_dcs_instance` permanently deletes DCS instance | Double-confirm user, then execute |
| 16 | `huawei_restart_dcs_instance` restarts DCS instance(s) | Confirm user, then execute with `restart` action |

## Non-Functional Requirements

| # | Criteria | Verification Method |
|---|----------|--------------------|
| 17 | All CLI commands execute without error | Execute each command with `--help` against live KooCLI |
| 18 | SDK fallback scripts import and initialize without exception | Run Python import test |
| 19 | No hardcoded credentials in any file | Grep for AK/SK patterns |
| 20 | Mutating operations always prompt for user confirmation | Code review of workflow section |

## Quality Reporting (CLI)

| # | Criteria | Verification Method |
|---|----------|--------------------|
| 21 | `scripts/ensure_cli.sh` exists and is executable (idempotent `skill-quality-cli` installer) | `test -x scripts/ensure_cli.sh && bash scripts/ensure_cli.sh` |
| 22 | `scripts/cli/cli_entry.py` + `scripts/cli/cli_reporting.py` are bundled (zero-dependency in-skill carrier) | `ls scripts/cli/` |
| 23 | `SKILL.md` contains the "Quality Reporting (Unified CLI)" section with Mode 1 (`run` wrap) / Mode 2 (`report`) and the quality-reporting wrapping rule (wrapper is a reporting bypass; native `hcloud ...` stays directly executable) | Review `SKILL.md` |
| 24 | Every CLI action in `SKILL.md` is documented in its native `hcloud <Service> <Operation> ...` form (directly executable by hcloud), with the `skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- ...` quality-reporting wrapper shown alongside as a comment/bypass | `grep` hcloud lines in SKILL.md bash blocks; run `hcloud <Operation> --help` |
| 25 | No runtime dependency on, or `import` of, the legacy `skill_quality_sdk` module in `scripts/`, `SKILL.md` or `references/` — and no `quality_context` remnant. One historical docstring mention of `skill_quality_sdk.py` is allowed in `scripts/cli/cli_reporting.py` (it declares that the bundled reporting module replaces the old SDK) | `grep -rn "import skill_quality_sdk\|from skill_quality_sdk\|quality_context" <skill dir> --exclude=acceptance-criteria.md` returns nothing (the exclusion is needed only because this criterion quotes the search patterns itself) |

## Pre-flight Validation (issue #496 / #659 fixes)

| # | Criteria | Verification Method |
|---|----------|--------------------|
| 26 | Existence pre-check before mutating or querying DDS/DCS resources (issue #496-6): `huawei_delete_dds_instance`, `huawei_delete_dcs_instance` and the DCS node query first confirm the resource exists via `ListInstances --id`/`--instance_id` (or `ShowInstance`); an empty result stops the workflow with "instance {id} does not exist", and `DBS.01010023` / `DCS.002` are mapped to that same message | Review the workflow steps and run a live call with a non-existent instance ID |
| 27 | Parameter completeness and enum validation before execution (issues #496-3, #496-7): `huawei_create_dds_instance` checks the required-parameter list including `--flavor.{N}.size` (multiple of 10) and `--flavor.{N}.storage=ULTRAHIGH`; `huawei_restart_dcs_instance` rejects any `action` outside `restart` / `soft_restart` / `flush` and shows those legal values | Inspect the documented checklists; run `hcloud DDS CreateInstance --help` / `hcloud DCS RestartOrFlushInstances --help` and compare |
| 28 | DCS parameter rules corrected (issues #496-2, #659-3, #659-4): `list_config_templates` uses `type` = `sys`/`user` and never `system`; `create_instance` requires `spec_code` and `password` (unless `no_password_access=true`); `create_custom_template` `type` matches the source template; the DDS `AddReadonlyNode` `.rr` read-only spec is documented, and a region with no `.rr` flavor is reported as unavailable (`DBS.280434`; DDS-Enhanced `DBS.02000024`) | `grep -n "system\|spec_code\|password\|\.rr" references/related-commands.md` and inspect the documented examples |
