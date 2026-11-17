# Acceptance Criteria — huawei-cloud-sg-manage

## Functional criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| 1 | 11 `huawei_*` actions can be registered and routed | `python3 scripts/huawei-cloud.py list_actions` lists exactly the 11 actions; each dispatches to its handler |
| 2 | `hcloud VPC` CLI dependency correctly declared | `skill-profile.yaml` declares `dependencies[].cli.name=hcloud` + `required: true`; every business command runs through hcloud VPC operations |
| 3 | Query/diagnose actions (R3) auto-execute read-only | `huawei_list_*`, `huawei_get_*`, `huawei_diagnose_*`, `huawei_analyze_*`, `huawei_audit_*` run without confirmation |
| 4 | Manage actions (R2/R1) require preview + confirmation | Without `confirmed=true` the dispatcher returns `"preview": true` with the exact command + impact and changes nothing; direct CLI write examples in SKILL.md always show a preview step (`--dry_run=true`, or `ShowSecurityGroup/v3` / `ShowSecurityGroupRule/v2` for the two deletes) before the execute step, which is gated on explicit user confirmation |
| 5 | Rule deletion shows network-connectivity impact warning | `huawei_delete_sg_rule` / `huawei_delete_security_group` previews include explicit connectivity-impact warnings |
| 6 | Dual authentication supported | AK/SK env vars (HUAWEICLOUD_SDK_AK/SK and aliases) and local KooCLI profile both documented and honored by the dispatcher |
| 7 | Port connectivity diagnosis is priority-ordered | Engine evaluates matching rules by priority; lowest number wins; default DENY when nothing matches |
| 8 | Over-exposure audit flags world-open rules | `0.0.0.0/0` / `::/0` allow rules (esp. ingress with wide ports) reported CRITICAL/HIGH |
| 9 | Conflict detection finds duplicates and allow/deny contradictions | Verified by offline smoke tests (duplicate, contradiction, shadowed rule cases) |
| 10 | Every failure is a structured, non-empty result | Missing CLI/credentials, timeout, `[USE_ERROR]` rejection and API error bodies all return `{"success": false, "error", "error_code", "hint"}`; no list-returning action ever substitutes `[]` for a failed call (`tests/test_offline_contract.py`) |
| 11 | Fast, bounded failure paths | Missing prerequisites fail in <2s; any hcloud call is capped by `HCLOUD_TIMEOUT` (default 30s) and reports `error_code=timeout` |
| 12 | One intent = one query per resource | `diagnose` issues Show + Rules only; `conflict`/`audit` reuse the per-process cache (`tests/test_offline_contract.py::CacheReuseTest`) |

## CLI-write-operation criteria (审查编码 L5)

| # | Criterion | Verification |
|---|-----------|--------------|
| L5-1 | Every write operation states 前置确认 (preconditions) before execution | The preview of `huawei_create_security_group`, `huawei_create_sg_rule`, `huawei_update_security_group`, `huawei_delete_security_group`, `huawei_delete_sg_rule` returns a `preconditions` list; SKILL.md §3/§4 spells the same list per operation |
| L5-2 | Every write operation states 影响范围 (blast radius) | The preview returns `impact` (resource, affected bindings, live-connectivity effect); SKILL.md states it per operation |
| L5-3 | Every write operation states 回滚 (rollback) | The preview returns a copy-pasteable `rollback` command plus `current_values` (update), `rules_snapshot` (delete SG) or `captured_rule` (delete rule); SKILL.md states it per operation |
| L5-4 | Write examples are never executed blind | SKILL.md write examples are preview-first; the execute line is the same command with `confirmed=true` (dispatcher) or without `--dry_run=true` (direct CLI), reachable only after explicit approval |

## Specification-compliance criteria

| # | Criterion |
|---|-----------|
| 1 | SKILL.md conforms to the GitCode Skill registration spec (valid YAML frontmatter, name == directory name, description with triggers, ≤5 tags, no version field) |
| 2 | SKILL.md ≤ 450 lines; total files ≤ 30; extensions on the allowlist |
| 3 | Required sections present: Overview, Prerequisites, Workflow, Core Commands, Parameter Confirmation, Reference Documents, KooCLI Command Format Standard |
| 4 | No hardcoded credentials; no cross-skill direct calls |
| 5 | Documented examples are copy-pasteable bare `hcloud VPC <Op>/v3 --cli-region=cn-north-4 ...` commands with no `{region}` placeholders, no inline `#` comments on command lines and no invalid flags; the `skill-quality-cli run -- ` wrapper is documented only as an optional prefix |
| 6 | Installation scripts finish or fail within 30s on an offline host: `install_cli.sh` exits non-zero with a readable reason, `ensure_cli.sh` warns and exits 0 |

## Validation commands

Run from the skill root (`skills/network/ops/huawei-cloud-sg-manage`); all commands are offline and require no credentials.

```bash
python3 scripts/huawei-cloud.py list_actions
python3 -m unittest discover -s tests -v
bash -n scripts/install_cli.sh && bash -n scripts/ensure_cli.sh
```