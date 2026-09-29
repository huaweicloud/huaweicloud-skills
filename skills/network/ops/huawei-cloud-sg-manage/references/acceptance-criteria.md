# Acceptance Criteria — huawei-cloud-sg-manage

## Functional criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| 1 | 11 `huawei_*` actions can be registered and routed | `python3 scripts/huawei-cloud.py list_actions` lists exactly the 11 actions; each dispatches to its handler |
| 2 | `hcloud VPC` CLI dependency correctly declared | `skill-profile.yaml` declares `dependencies[].cli.name=hcloud` + `required: true`; every business command runs through hcloud VPC operations |
| 3 | Query/diagnose actions (R3) auto-execute read-only | `huawei_list_*`, `huawei_get_*`, `huawei_diagnose_*`, `huawei_analyze_*`, `huawei_audit_*` run without confirmation |
| 4 | Manage actions (R2/R1) require preview + confirmation | Without `confirmed=true` the dispatcher returns `"preview": true` with the exact command + impact and changes nothing |
| 5 | Rule deletion shows network-connectivity impact warning | `huawei_delete_sg_rule` / `huawei_delete_security_group` previews include explicit connectivity-impact warnings |
| 6 | Dual authentication supported | AK/SK env vars (HUAWEICLOUD_SDK_AK/SK and aliases) and local hcloud profile both documented and honored by the dispatcher |
| 7 | Port connectivity diagnosis is priority-ordered | Engine evaluates matching rules by priority; lowest number wins; default DENY when nothing matches |
| 8 | Over-exposure audit flags world-open rules | `0.0.0.0/0` / `::/0` allow rules (esp. ingress with wide ports) reported CRITICAL/HIGH |
| 9 | Conflict detection finds duplicates and allow/deny contradictions | Verified by offline smoke tests (duplicate, contradiction, shadowed rule cases) |

## Specification-compliance criteria

| # | Criterion |
|---|-----------|
| 1 | SKILL.md conforms to the GitCode Skill registration spec (valid YAML frontmatter, name == directory name, description with triggers, ≤5 tags, no version field) |
| 2 | SKILL.md ≤ 500 lines; total files ≤ 30; extensions on the allowlist |
| 3 | Required sections present: Overview, Prerequisites, Workflow, Core Commands, Parameter Confirmation, Reference Documents, KooCLI Command Format Standard |
| 4 | No hardcoded credentials; no cross-skill direct calls |
| 5 | Every hcloud command wrapped with `skill-quality-cli run --skill-name huawei-cloud-sg-manage --` in documented examples |

## Validation commands

```bash
bash scripts/validate-skill.sh -s skills/network/ops/huawei-cloud-sg-manage
python3 scripts/huawei-cloud.py list_actions
```