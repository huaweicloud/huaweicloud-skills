---
name: huawei-cloud-sg-manage
description: |
  Use when managing or diagnosing Huawei Cloud security groups (安全组) — VPC subnet-level
  firewalls. Covers listing/querying security groups and rules, port connectivity diagnosis
  (ingress/egress rule matching), rule conflict detection, over-exposure security audit
  (e.g. 0.0.0.0/0 world-open rules), and full CRUD (create/update/delete security groups and
  rules). Managed actions run with preview + explicit confirmation (R2/R1); query and diagnose
  actions are read-only and auto-execute (R3). Uses the local hcloud (KooCLI) VPC CLI with
  AK/SK environment variables or a local hcloud profile.
  Provides 11 huawei_* actions: huawei_list_security_groups, huawei_list_security_group_rules,
  huawei_get_security_group, huawei_diagnose_sg_port_connectivity, huawei_analyze_sg_rule_conflict,
  huawei_audit_sg_overexposed_rules, huawei_create_security_group, huawei_create_sg_rule,
  huawei_update_security_group, huawei_delete_security_group, huawei_delete_sg_rule.
  Triggers include: "安全组", "安全组规则", "防火墙规则", "端口连通性", "端口诊断", "规则冲突",
  "过度开放", "全开放", "0.0.0.0/0", "security group", "security group rule", "SG rule",
  "ingress", "egress", "inbound", "outbound", "port connectivity", "port diagnosis",
  "rule conflict", "over-exposed", "world-open", "VPC", "安全审计", "防火墙".
triggers: ["安全组", "安全组规则", "防火墙规则", "端口连通性", "端口诊断", "规则冲突",
  "过度开放", "全开放", "0.0.0.0/0", "security group", "security group rule", "SG rule",
  "ingress", "egress", "inbound", "outbound", "port connectivity", "port diagnosis",
  "rule conflict", "over-exposed", "world-open", "VPC", "安全审计", "防火墙"]
tags: [huawei-cloud, vpc, security-group, network, firewall]
---

# Huawei Cloud Security Group Management (安全组管理)

**STOP - Do not answer from general knowledge.** Every command below is spelled with the
operation name and parameters verified against KooCLI 7.3.12. Copy a command as-is, replace
only the `<...>` placeholders, and run it. Do not invent parameter names.

## Overview

This skill manages **Huawei Cloud security groups (安全组)** — the VPC subnet-level
stateful firewall (security group is a VPC sub-resource). It provides 11 `huawei_*` actions:

| # | Capability | Risk | Action |
|---|-----------|------|--------|
| 1 | Query (read-only) | R3 — auto execute | `huawei_list_security_groups` |
| 2 | Query (read-only) | R3 — auto execute | `huawei_list_security_group_rules` |
| 3 | Query (read-only) | R3 — auto execute | `huawei_get_security_group` |
| 4 | Analyze (read-only) | R3 — auto execute | `huawei_diagnose_sg_port_connectivity` |
| 5 | Analyze (read-only) | R3 — auto execute | `huawei_analyze_sg_rule_conflict` |
| 6 | Analyze (read-only) | R3 — auto execute | `huawei_audit_sg_overexposed_rules` |
| 7 | Manage | R2 — preview + confirm | `huawei_create_security_group` |
| 8 | Manage | R2 — preview + confirm | `huawei_create_sg_rule` |
| 9 | Manage | R2 — preview + confirm | `huawei_update_security_group` |
| 10 | Manage | R1 — preview + confirm | `huawei_delete_security_group` |
| 11 | Manage | R1 — preview + confirm | `huawei_delete_sg_rule` |

### Architecture

```
User request → Action Router (scripts/huawei-cloud.py dispatcher)
  ├─ Query (R3)      → hcloud VPC ListSecurityGroups/v3 | ListSecurityGroupRules/v3 | ShowSecurityGroup/v3
  ├─ Analyze (R3)    → hcloud VPC ListSecurityGroupRules/v3 + deterministic rule engine
  │                     (priority-ordered matching, CIDR/port/protocol semantics)
  └─ Manage (R2/R1)  → preview → hcloud VPC Create/Update/Delete (confirmed only after user approval)
```

**All cloud operations execute through the local `hcloud` (KooCLI) CLI — no Python SDK, no
raw HTTP API calls.** The bundled dispatcher builds and runs the hcloud commands; its
list/SG results are cached per process, so one intent issues one query per resource no
matter how many analyses reuse it.

### Scope boundaries

- ✅ List/query security groups and their rules
- ✅ Port connectivity diagnosis (ingress/egress rule matching, priority-ordered)
- ✅ Rule conflict detection (duplicates, allow/deny contradictions, shadowed rules)
- ✅ Over-exposure audit (world-open 0.0.0.0/0 / ::/0, wide port ranges, ineffective denies)
- ✅ Create/update/delete security groups and rules (with preview + confirmation)
- ❌ Doesn't manage other VPC resources (VPCs, subnets, routers, firewalls, network
  queries) — those are out of scope for this skill
- ❌ Doesn't resolve remote-security-group / address-group member IPs (not exposed by the API)

## Critical Warnings

| Trap | Why |
| ---- | --- |
| Deleting a security group is irreversible | Removes the SG and ALL its rules at once; instances/ports still associated lose connectivity |
| Deleting a rule changes live connectivity | VPC default is DENY for unmatched traffic — a rule deletion can expose or block traffic immediately |
| `0.0.0.0/0` / `::/0` allow rules mean world-open | Any internet host can reach those ports; audit first, restrict to real CIDRs |
| Rule priority matters | Lower numerical priority wins; a broad allow with priority 1 makes every lower-priority deny ineffective |
| Never run a Manage action without preview | All R2/R1 actions must be previewed and explicitly confirmed by the user — see confirmation gates and the per-operation 前置确认 / 影响范围 / 回滚 sections |

## Prerequisites

1. **hcloud CLI** (KooCLI 7.2.x or later) installed and authenticated.
   - Verify with `hcloud version` (prints `Current KooCLI version: 7.x.y`).
   - Installation and configuration: `references/cli-installation-guide.md`.
   - Two supported authentication modes:
     - **AK/SK credentials**: environment variables `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK`
       (or `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY` / `HW_ACCESS_KEY` / `HW_SECRET_KEY`)
     - **Local KooCLI profile**: the KooCLI `configure list` subcommand shows a valid AKSK profile
   - No CLI or no credentials → the dispatcher fails in under 2 seconds with
     `{"success": false, "error_code": "cli_missing" | "credentials_missing", "hint": ...}`
     instead of returning an empty list.
2. **Region**: always pass `--cli-region=cn-north-4` (replace with your region). `--project_id`
   is auto-filled from the authenticated profile when available; pass `--project_id=<id>` if
   the profile cannot resolve it.
3. **IAM permissions**: least-privilege policies in `references/iam-policies.md`
   (`vpc:securityGroups:*`, `vpc:securityGroupRules:*`).
4. **Timeouts**: every hcloud call is hard-capped at 30s (`HCLOUD_TIMEOUT` overrides, 1-300s)
   and fails with `error_code=timeout` + a remediation hint.

## Workflow

```
1. Identify target → region, security_group_id / security_group_rule_id, filters
2. Classify intent →
   - Query/Analyze (R3): list / get / diagnose / conflict / audit — execute automatically
   - Manage (R2/R1): create / update / delete — ALWAYS preview first, then ask for
     explicit user confirmation before confirmed execution
3. Execute → dispatcher or the bare hcloud commands below (one query per resource)
4. Output → structured JSON + readable summary
```

**Confirmation gates (MUST NOT be skipped):**

- **R2 actions** (`huawei_create_security_group`, `huawei_create_sg_rule`,
  `huawei_update_security_group`): show 前置确认 / 影响范围 / 回滚, then ask "confirm?"
  before running. Execution requires `confirmed=true`.
- **R1 actions** (`huawei_delete_security_group`, `huawei_delete_sg_rule`): show the same three
  sections plus the connectivity-impact warning, then require explicit confirmation.
  Execution requires `confirmed=true`.
- The dispatcher enforces this at the tool level: without `confirmed=true` it only
  **previews** (prints the exact command, preconditions, impact, rollback, no API call).

## Core Commands

All examples below are **bare `hcloud` commands** that can be copied and run as-is
(only `<...>` placeholders need replacing). `cn-north-4` is the default region used
throughout — substitute your own. When `skill-quality-cli` is installed and you want
quality reporting, prefix a direct CLI call with
`skill-quality-cli run --skill-name huawei-cloud-sg-manage -- `; the dispatcher attaches
reporting itself. Bare commands are always the fallback and require no wrapper.

### 0. Connectivity check (no cloud mutation)

```bash
hcloud version
```

### 1. Query (R3 — read-only, auto execute)

**`huawei_list_security_groups`** — list security groups (optionally filter by name/id):

```bash
hcloud VPC ListSecurityGroups/v3 --cli-region=cn-north-4 --limit=100
hcloud VPC ListSecurityGroups/v3 --cli-region=cn-north-4 --name.1=default
```

**`huawei_list_security_group_rules`** — list security group rules (optionally one SG):

```bash
hcloud VPC ListSecurityGroupRules/v3 --cli-region=cn-north-4 --limit=100
hcloud VPC ListSecurityGroupRules/v3 --cli-region=cn-north-4 --security_group_id.1=<sg-id>
```

**`huawei_get_security_group`** — show one security group:

```bash
hcloud VPC ShowSecurityGroup/v3 --cli-region=cn-north-4 --security_group_id=<sg-id>
```

Get a real `<sg-id>` from `hcloud VPC ListSecurityGroups/v3 --cli-region=cn-north-4 --limit=1`
(the `id` field of the first group) before calling the id-based commands.

### 2. Analyze (R3 — read-only, auto execute)

**`huawei_diagnose_sg_port_connectivity`** — port connectivity diagnosis. Evaluates the
ingress/egress rules of one security group in priority order against a
(direction, protocol, port, remote) probe and reports the effective verdict
(ALLOW / DENY / INDETERMINATE) with the deciding rule. One SG + one rule list are fetched:

```bash
python3 scripts/huawei-cloud.py huawei_diagnose_sg_port_connectivity \
  security_group_id=<sg-id> direction=ingress protocol=tcp port=22 remote=10.0.0.0/8
python3 scripts/huawei-cloud.py huawei_diagnose_sg_port_connectivity \
  security_group_id=<sg-id> direction=egress protocol=tcp port=443
```

**`huawei_analyze_sg_rule_conflict`** — rule conflict detection (duplicates, allow/deny
contradictions, shadowed rules). Runs against one SG, or all SGs when no SG is given:

```bash
python3 scripts/huawei-cloud.py huawei_analyze_sg_rule_conflict security_group_id=<sg-id>
python3 scripts/huawei-cloud.py huawei_analyze_sg_rule_conflict
```

**`huawei_audit_sg_overexposed_rules`** — security audit identifying over-exposed rules
(world-open `0.0.0.0/0` / `::/0` allows, wide port ranges, ineffective denies):

```bash
python3 scripts/huawei-cloud.py huawei_audit_sg_overexposed_rules security_group_id=<sg-id>
python3 scripts/huawei-cloud.py huawei_audit_sg_overexposed_rules
```

The three analyze actions are one-shot: they reuse the process cache, so a single analysis
never re-queries the API for the same security group.

### 3. Manage (R2 — preview + confirm)

Each write operation documents the three items required by the CLI-write-operation rule
(审查编码 L5): **前置确认 → 影响范围 → 回滚**. The preview prints all three; read them out
loud to the user before asking for confirmation.

**`huawei_create_security_group`** — create a security group:

```bash
python3 scripts/huawei-cloud.py huawei_create_security_group name=<name> description=<desc>
python3 scripts/huawei-cloud.py huawei_create_security_group name=<name> description=<desc> confirmed=true
```

Direct CLI equivalent (the second line runs only after approval; `--dry_run=true` validates
without creating):

```bash
hcloud VPC CreateSecurityGroup/v3 --cli-region=cn-north-4 --security_group.name=<name> --security_group.description=<desc> --dry_run=true
hcloud VPC CreateSecurityGroup/v3 --cli-region=cn-north-4 --security_group.name=<name> --security_group.description=<desc>
```

- **前置确认**: user approved name / description / enterprise project; the name does not
  duplicate an existing group in this region+project (`hcloud VPC ListSecurityGroups/v3
  --cli-region=cn-north-4 --name.1=<name>` returns an empty list).
- **影响范围**: adds one security group with the platform default rules; nothing is bound to
  it, so no live traffic changes until a NIC is associated.
- **回滚**: `hcloud VPC DeleteSecurityGroup/v3 --cli-region=cn-north-4 --security_group_id=<created id>`
  (the executor returns `created.security_group.id`).

**`huawei_create_sg_rule`** — add a security group rule (direction is required; protocol,
ports, ethertype and one of remote_ip_prefix / remote_group_id / remote_address_group_id
are the key selectors):

```bash
python3 scripts/huawei-cloud.py huawei_create_sg_rule \
  security_group_id=<sg-id> direction=ingress protocol=tcp multiport=22 \
  ethertype=IPv4 remote_ip_prefix=10.0.0.0/8 action=allow priority=1
python3 scripts/huawei-cloud.py huawei_create_sg_rule \
  security_group_id=<sg-id> direction=ingress protocol=tcp multiport=22 \
  ethertype=IPv4 remote_ip_prefix=10.0.0.0/8 action=allow priority=1 confirmed=true
```

- **前置确认**: the target SG id came from a list call in the same region/project; user
  approved direction/protocol/ports/remote/action/priority.
- **影响范围**: the rule applies immediately to **every NIC bound to this security group**;
  a world-open (`0.0.0.0/0`) allow exposes the ports to the internet.
- **回滚**: `hcloud VPC DeleteSecurityGroupRule/v3 --cli-region=cn-north-4 --security_group_rule_id=<created id>`
  (returned as `created.security_group_rule.id`).

**`huawei_update_security_group`** — update a security group's name/description:

```bash
python3 scripts/huawei-cloud.py huawei_update_security_group \
  security_group_id=<sg-id> name=<new-name> description=<new-desc>
python3 scripts/huawei-cloud.py huawei_update_security_group \
  security_group_id=<sg-id> name=<new-name> description=<new-desc> confirmed=true
```

Direct CLI equivalent:

```bash
hcloud VPC UpdateSecurityGroup/v3 --cli-region=cn-north-4 --security_group_id=<sg-id> --security_group.name=<new-name> --dry_run=true
hcloud VPC UpdateSecurityGroup/v3 --cli-region=cn-north-4 --security_group_id=<sg-id> --security_group.name=<new-name>
```

- **前置确认**: the preview captures the current name/description via
  `hcloud VPC ShowSecurityGroup/v3 --cli-region=cn-north-4 --security_group_id=<sg-id>`;
  user approved the new values.
- **影响范围**: renames/relabels only — rules and bindings are unchanged; automation or
  runbooks that address the group **by name** break until updated.
- **回滚**: re-run `UpdateSecurityGroup/v3` with the captured `current_values`
  (`--security_group.name=<old> --security_group.description=<old>`).

### 4. Manage (R1 — preview + confirm)

**`huawei_delete_security_group`** — delete a security group. **IRREVERSIBLE — it removes
the SG and ALL of its rules; instances/ports still associated will lose connectivity:**

```bash
python3 scripts/huawei-cloud.py huawei_delete_security_group security_group_id=<sg-id>
python3 scripts/huawei-cloud.py huawei_delete_security_group security_group_id=<sg-id> confirmed=true
```

Direct CLI equivalent (no `--dry_run` on delete: preview with `ShowSecurityGroup/v3`, then
delete only after approval):

```bash
hcloud VPC ShowSecurityGroup/v3 --cli-region=cn-north-4 --security_group_id=<sg-id>
hcloud VPC ListSecurityGroupRules/v3 --cli-region=cn-north-4 --security_group_id.1=<sg-id>
hcloud VPC DeleteSecurityGroup/v3 --cli-region=cn-north-4 --security_group_id=<sg-id>
```

- **前置确认**: the SG is not bound to any instance/NIC (detach first); the rule list above
  was exported (`rules_snapshot`) and stored; user explicitly confirmed the irreversible
  deletion.
- **影响范围**: the group and every rule in it disappear at once; every associated
  instance/port falls back to the VPC default (DENY for unmatched traffic).
- **回滚**: deletion cannot be undone. Restore service by recreating the group
  (`CreateSecurityGroup/v3` with the saved name/description), recreating each rule from
  `rules_snapshot`, then rebinding the instances/NICs.

**`huawei_delete_sg_rule`** — delete a security group rule. **Changes live network
connectivity — VPC default is DENY for unmatched traffic:**

```bash
python3 scripts/huawei-cloud.py huawei_delete_sg_rule security_group_rule_id=<rule-id>
python3 scripts/huawei-cloud.py huawei_delete_sg_rule security_group_rule_id=<rule-id> confirmed=true
```

Direct CLI equivalent:

```bash
hcloud VPC ShowSecurityGroupRule/v2 --cli-region=cn-north-4 --security_group_rule_id=<rule-id>
hcloud VPC DeleteSecurityGroupRule/v3 --cli-region=cn-north-4 --security_group_rule_id=<rule-id>
```

- **前置确认**: the rule id came from `ListSecurityGroupRules/v3` of the intended SG; user
  confirmed direction/protocol/ports/remote shown by the preview (`captured_rule`).
- **影响范围**: traffic previously permitted/denied by this rule flips immediately on every
  NIC bound to the group; an allow removal can cut off access, a deny removal can expose ports.
- **回滚**: recreate the rule from `captured_rule` with `hcloud VPC CreateSecurityGroupRule/v3
  --cli-region=cn-north-4 --security_group_rule.security_group_id=<sg> --security_group_rule.direction=<dir>
  --security_group_rule.protocol=<proto> --security_group_rule.multiport=<ports>
  --security_group_rule.remote_ip_prefix=<cidr>`.

## KooCLI Command Format Standard

| Feature | Description | Example |
| ------- | ----------- | ------- |
| Service name | `VPC` (as listed in the KooCLI VPC service help) | `hcloud VPC UpdateSecurityGroup/v3 --cli-region=cn-north-4` |
| Operation name | PascalCase **plus the explicit version suffix** — security-group operations use `/v3`, except `ShowSecurityGroupRule/v2` | `ListSecurityGroups/v3`, `ListSecurityGroupRules/v3`, `ShowSecurityGroup/v3`, `CreateSecurityGroupRule/v3`, `UpdateSecurityGroup/v3`, `DeleteSecurityGroup/v3`, `DeleteSecurityGroupRule/v3` |
| Region parameter | `--cli-region=<value>` | `--cli-region=cn-north-4` |
| Simple parameter | `--key=value` | `--security_group_id=<id>` |
| Nested parameter | `--parent.child=value` | `--security_group.name=<name>`, `--security_group_rule.direction=ingress` |
| Indexed array parameter | `--key.N=value` | `--name.1=web`, `--id.1=<id>` |
| Output | `--cli-output=json` (default for the dispatcher) | |

## Parameter Confirmation

All parameters below were verified against the KooCLI VPC operation help (KooCLI 7.2.12 / 7.3.12).

| Operation | Required parameters | Optional (main) |
| --------- | ------------------- | --------------- |
| `ListSecurityGroups/v3` | — | `--name.[N]`, `--id.[N]`, `--description.[N]`, `--enterprise_project_id`, `--limit`, `--marker` |
| `ListSecurityGroupRules/v3` | — | `--security_group_id.[N]`, `--direction`, `--protocol.[N]`, `--action`, `--enabled`, `--remote_ip_prefix`, `--limit` |
| `ShowSecurityGroup/v3` | `--security_group_id` | — |
| `ShowSecurityGroupRule/v2` | `--security_group_rule_id` | — |
| `CreateSecurityGroup/v3` | `--security_group.name` | `--security_group.description`, `--security_group.enterprise_project_id`, `--security_group.tags.[N].key\|value`, `--dry_run` |
| `CreateSecurityGroupRule/v3` | `--security_group_rule.security_group_id`, `--security_group_rule.direction` | `protocol`, `ethertype`, `multiport`, `remote_ip_prefix` / `remote_group_id` / `remote_address_group_id` (pick one), `action`, `priority`, `enabled`, `description`, `--dry_run` |
| `UpdateSecurityGroup/v3` | `--security_group_id` | `--security_group.name`, `--security_group.description`, `--dry_run` |
| `DeleteSecurityGroup/v3` | `--security_group_id` | — |
| `DeleteSecurityGroupRule/v3` | `--security_group_rule_id` | — |

Full per-operation parameter tables (types, ranges, examples): `references/cli-parameters.md`.

## Error Contract

Every action prints JSON; a failed call returns a structured envelope instead of an empty
result:

```json
{"success": false, "error": "...", "error_code": "timeout", "hint": "...", "command": "hcloud VPC ..."}
```

| `error_code` | Meaning → Fix |
| ------------ | ------------- |
| `cli_missing` | `hcloud` not on PATH → install KooCLI and re-run `hcloud version` |
| `credentials_missing` | no profile and no AK/SK env vars → run the KooCLI `configure init` subcommand or export `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY` |
| `timeout` | call exceeded `HCLOUD_TIMEOUT` (default 30s) → raise it or check network/region |
| `cli_error` | KooCLI rejected the command (`[USE_ERROR]`, rc=0) → fix operation name / parameters |
| `project_id_missing` | profile cannot resolve a project → pass `--project_id=<id>` |
| `auth_error` / `permission_denied` | AK/SK rejected or IAM denies → `references/iam-policies.md` |
| `missing_parameter` | required parameter absent → the `hint` names it |
| `api_error` / `SYS.xxxx` | cloud API rejected the request → check id/region |

## Troubleshooting

| Symptom | Root cause → Fix |
| ------- | ---------------- |
| `获取项目ID失败` / APIGW.0301 Unauthorized | Invalid/expired AK/SK or profile → refresh the KooCLI profile (re-configure) |
| `缺少必填参数:project_id` | Profile can't resolve project id → pass `--project_id=<id>` explicitly |
| Empty rule list but SG exists | Wrong region/project → check `--cli-region`, `--project_id` |
| Diagnose returns INDETERMINATE | Probe matches a remote-security-group / address-group rule — member IPs are not exposed by the API |
| DeleteSecurityGroup fails | SG still associated with instances/ports or has dependent resources → detach first |
| `install_cli.sh` exits 1 in an offline network | Network/proxy unreachable (reported within 30s) → use the offline package or skip the optional quality wrapper; business commands do not need it |

## Security Considerations

- MUST preview every R2/R1 manage action and obtain explicit user confirmation
  (`confirmed=true` only after approval), stating 前置确认 / 影响范围 / 回滚.
- MUST show the connectivity-impact warning before deleting rules or security groups.
- MUST treat `0.0.0.0/0` / `::/0` allow rules as high risk (`huawei_audit_sg_overexposed_rules`
  flags them; restrict to real CIDRs).
- MUST NOT echo AK/SK or any credential values in commands, outputs or reports; the
  dispatcher redacts `--cli-access-key` / `--cli-secret-key` / `--cli-security-token`.
- SHOULD run `huawei_diagnose_sg_port_connectivity` before changing rules that affect
  business traffic.
- SHOULD audit security groups periodically with `huawei_audit_sg_overexposed_rules`.

## Reference Documents

- `references/iam-policies.md` — Least-privilege IAM policies (`vpc:securityGroups:*`, `vpc:securityGroupRules:*`)
- `references/sg-rule-reference.md` — Security-group rule field semantics (direction/ethertype/protocol/ports/priority/action)
- `references/dataflow-diagram.md` — Mermaid data flow diagram
- `references/verification-method.md` — Verification method and acceptance checks
- `references/acceptance-criteria.md` — Acceptance criteria for the 11 huawei_* actions
- `references/cli-installation-guide.md` — KooCLI install/verify and offline behaviour
- `references/cli-parameters.md` — Full per-operation parameter tables
- VPC security group docs: https://support.huaweicloud.com/usermanual-vpc/vpc_SecurityGroup_0001.html
- API Explorer: https://console.huaweicloud.com/apiexplorer/#/openapi/VPC/doc