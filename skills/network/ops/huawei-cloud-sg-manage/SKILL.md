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
tags: [huawei-cloud, vpc, security-group, network, firewall]
---

# Huawei Cloud Security Group Management (安全组管理)

**STOP - Do not answer from general knowledge.** Follow the procedure below.
Always run `hcloud VPC <Operation> --help` before constructing commands to discover exact
parameter names and requirements.

<!-- cli-install-version: 3.9.0 -->
## Step 0: Install skill-quality-cli (idempotent, skip if already installed)

The CLI installs into `~/.local/bin/`, which is **not always in `$PATH`** (bare
`skill-quality-cli` can fail with exit 127). Export it first, then run the installer:

```bash
export PATH="$HOME/.local/bin:$PATH"
bash scripts/ensure_cli.sh
```

> The script detects whether `skill-quality-cli` is available; if not, it installs a
> pinned release (fixed version + SHA256 whitelist verification, see the script header) into
> `~/.local/bin/` (idempotent, silently skipped on failure — never blocks the business flow).
> Upgrade manually via `skill-quality-cli upgrade`.

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
  ├─ Query (R3)      → hcloud VPC ListSecurityGroups/ListSecurityGroupRules/ShowSecurityGroup
  ├─ Analyze (R3)    → hcloud VPC ListSecurityGroupRules + deterministic rule engine
  │                     (priority-ordered matching, CIDR/port/protocol semantics)
  └─ Manage (R2/R1)  → preview → hcloud VPC Create/Update/Delete (confirmed only after user approval)
```

**All cloud operations execute through the local `hcloud` (KooCLI) CLI — no Python SDK, no
raw HTTP API calls.** The bundled dispatcher builds and runs the hcloud commands.

**Dependency**: Quality telemetry is collected automatically via `skill-quality-cli`
(installed by `scripts/ensure_cli.sh` if absent).

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
| Never run a Manage action without preview | All R2/R1 actions must be previewed and explicitly confirmed by the user — see confirmation gates |

## Prerequisites

1. **hcloud CLI** (KooCLI 7.2.x or later) installed and authenticated.
   - Installation and configuration guide: see `references/cli-installation-guide.md`
   - Two supported authentication modes:
     - **AK/SK credentials**: environment variables `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK`
       (or `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY` / `HW_ACCESS_KEY` / `HW_SECRET_KEY`)
     - **Local hcloud profile**: "hcloud configure list" must show a valid AKSK profile
   - Verify with "hcloud configure list"
2. **Region**: always pass `--cli-region={region}` (e.g. `cn-north-4`). `--project_id` is
   auto-filled from the authenticated profile when available; pass an explicit
   `project_id=` if the profile cannot resolve it.
3. **IAM permissions**: least-privilege policies in `references/iam-policies.md`
   (`vpc:securityGroups:*`, `vpc:securityGroupRules:*`).
4. **`skill-quality-cli`** — ensured by `bash scripts/ensure_cli.sh` (idempotent, skips if present)
   - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade)
   - Disable telemetry report: set `SKILL_QUALITY_REPORT=0`

## Workflow

```
1. Identify target → region, security_group_id / security_group_rule_id, filters
2. Classify intent →
   - Query/Analyze (R3): list / get / diagnose / conflict / audit — execute automatically
   - Manage (R2/R1): create / update / delete — ALWAYS preview first, then ask for
     explicit user confirmation before confirmed execution
3. Execute → dispatcher or the wrapped hcloud commands below
4. Output → structured JSON + readable summary
```

**Confirmation gates (MUST NOT be skipped):**

- **R2 actions** (`huawei_create_security_group`, `huawei_create_sg_rule`,
  `huawei_update_security_group`): show the full command and the resource to be
  created/updated, then ask "confirm?" before running. Execution requires
  `confirmed=true`.
- **R1 actions** (`huawei_delete_security_group`, `huawei_delete_sg_rule`): show the full
  command and side effects, print the connectivity-impact warning, and require explicit
  confirmation. Execution requires `confirmed=true`.
- The dispatcher enforces this at the tool level: without `confirmed=true` it only
  **previews** (prints the exact command + impact, no API call).

## Core Commands

> All direct `hcloud` commands below are shown in **dual form**: the bare executable
> command and the identical command wrapped with
> `skill-quality-cli run --skill-name huawei-cloud-sg-manage -- ...` for quality reporting.
> The bundled dispatcher (`python3 scripts/huawei-cloud.py <action> key=value ...`) is the
> recommended entry — it routes the 11 actions, builds the hcloud commands and prints JSON.
> No Python SDK package is needed for any business command.

> **⚠️ Mandatory: every `hcloud` command in this skill MUST be wrapped with
> `skill-quality-cli run --skill-name huawei-cloud-sg-manage -- <command>` — bare `hcloud`
> calls are strictly forbidden.** (Once installed, quality reporting is automatic for the
> wrapped form; set `SKILL_QUALITY_REPORT=0` to opt out without changing the command.)

### 1. Query (R3 — read-only, auto execute)

**`huawei_list_security_groups`** — list security groups:

```bash
python3 scripts/huawei-cloud.py huawei_list_security_groups region=cn-north-4
python3 scripts/huawei-cloud.py huawei_list_security_groups region=cn-north-4 name=my-sg
# Direct CLI (optional filters: --name.1=, --id.1=, --enterprise_project_id=, --limit=)
skill-quality-cli run --skill-name huawei-cloud-sg-manage -- hcloud VPC ListSecurityGroups/v3 --cli-region={region}
```

**`huawei_list_security_group_rules`** — list security group rules (optionally filtered by SG):

```bash
python3 scripts/huawei-cloud.py huawei_list_security_group_rules region=cn-north-4
python3 scripts/huawei-cloud.py huawei_list_security_group_rules region=cn-north-4 security_group_id={sg_id}
# Direct CLI (optional filters: --security_group_id.1=, --direction=, --protocol.=, --action=, --enabled=)
skill-quality-cli run --skill-name huawei-cloud-sg-manage -- hcloud VPC ListSecurityGroupRules/v3 --cli-region={region}
```

**`huawei_get_security_group`** — show a security group's detail:

```bash
python3 scripts/huawei-cloud.py huawei_get_security_group security_group_id={sg_id} region=cn-north-4
# Direct CLI:
skill-quality-cli run --skill-name huawei-cloud-sg-manage -- hcloud VPC ShowSecurityGroup/v3 --cli-region={region} --security_group_id={sg_id}
```

### 2. Analyze (R3 — read-only, auto execute)

**`huawei_diagnose_sg_port_connectivity`** — port connectivity diagnosis. Evaluates the
ingress/egress rules of one security group in priority order against a
(direction, protocol, port, remote) probe and reports the effective verdict
(ALLOW / DENY / INDETERMINATE) with the deciding rule:

```bash
# Is TCP/22 from 10.0.0.0/8 allowed inbound to this SG?
python3 scripts/huawei-cloud.py huawei_diagnose_sg_port_connectivity \
  security_group_id={sg_id} direction=ingress protocol=tcp port=22 remote=10.0.0.0/8 \
  region=cn-north-4
# Is outbound HTTPS allowed?
python3 scripts/huawei-cloud.py huawei_diagnose_sg_port_connectivity \
  security_group_id={sg_id} direction=egress protocol=tcp port=443 \
  region=cn-north-4
```

**`huawei_analyze_sg_rule_conflict`** — rule conflict detection (duplicates, allow/deny
contradictions, shadowed rules). Runs against one SG, or all SGs when no SG is given:

```bash
python3 scripts/huawei-cloud.py huawei_analyze_sg_rule_conflict security_group_id={sg_id} region=cn-north-4
python3 scripts/huawei-cloud.py huawei_analyze_sg_rule_conflict region=cn-north-4
```

**`huawei_audit_sg_overexposed_rules`** — security audit identifying over-exposed rules
(world-open `0.0.0.0/0` / `::/0` allows, wide port ranges, ineffective denies):

```bash
python3 scripts/huawei-cloud.py huawei_audit_sg_overexposed_rules security_group_id={sg_id} region=cn-north-4
python3 scripts/huawei-cloud.py huawei_audit_sg_overexposed_rules region=cn-north-4
```

### 3. Manage (R2 — preview + confirm)

**`huawei_create_security_group`** — create a security group:

```bash
# [W] 写操作 (WRITE): creates a security group — R2: preview + explicit confirmation required
# Step 1 — preview (no resource is changed):
python3 scripts/huawei-cloud.py huawei_create_security_group name={name} description={desc} region=cn-north-4
# Step 2 — execute ONLY after user approval:
python3 scripts/huawei-cloud.py huawei_create_security_group name={name} description={desc} region=cn-north-4 confirmed=true
# Direct CLI equivalent:
skill-quality-cli run --skill-name huawei-cloud-sg-manage -- hcloud VPC CreateSecurityGroup/v3 --cli-region={region} --security_group.name={name} --security_group.description={desc}
```

**`huawei_create_sg_rule`** — add a security group rule (direction is required; protocol,
ports, ethertype and one of remote_ip_prefix / remote_group_id / remote_address_group_id
are the key selectors):

```bash
# [W] 写操作 (WRITE): adds a security group rule — R2: preview + explicit confirmation required
# Step 1 — preview:
python3 scripts/huawei-cloud.py huawei_create_sg_rule \
  security_group_id={sg_id} direction=ingress protocol=tcp multiport=22 \
  ethertype=IPv4 remote_ip_prefix=10.0.0.0/8 action=allow priority=1 \
  region=cn-north-4
# Step 2 — execute ONLY after user approval:
python3 scripts/huawei-cloud.py huawei_create_sg_rule \
  security_group_id={sg_id} direction=ingress protocol=tcp multiport=22 \
  ethertype=IPv4 remote_ip_prefix=10.0.0.0/8 action=allow priority=1 \
  region=cn-north-4 confirmed=true
# Direct CLI equivalent:
skill-quality-cli run --skill-name huawei-cloud-sg-manage -- hcloud VPC CreateSecurityGroupRule/v3 --cli-region={region} --security_group_rule.security_group_id={sg_id} --security_group_rule.direction=ingress --security_group_rule.protocol=tcp --security_group_rule.multiport=22 --security_group_rule.remote_ip_prefix=10.0.0.0/8
```

**`huawei_update_security_group`** — update a security group's name/description:

```bash
# [W] 写操作 (WRITE): updates a security group — R2: preview + explicit confirmation required
python3 scripts/huawei-cloud.py huawei_update_security_group \
  security_group_id={sg_id} name={new_name} description={new_desc} region=cn-north-4
# ... then re-run with confirmed=true after user approval:
python3 scripts/huawei-cloud.py huawei_update_security_group \
  security_group_id={sg_id} name={new_name} description={new_desc} region=cn-north-4 confirmed=true
# Direct CLI equivalent:
skill-quality-cli run --skill-name huawei-cloud-sg-manage -- hcloud VPC UpdateSecurityGroup --cli-region={region} --security_group_id={sg_id} --security_group.name={new_name}
```

### 4. Manage (R1 — preview + confirm)

**`huawei_delete_security_group`** — delete a security group. **IRREVERSIBLE — it removes
the SG and ALL of its rules; instances/ports still associated will lose connectivity:**

```bash
# [W] 写操作 (WRITE) — IRREVERSIBLE: deletes a security group and its rules — R1: explicit confirmation required
python3 scripts/huawei-cloud.py huawei_delete_security_group security_group_id={sg_id} region=cn-north-4
# ... then re-run with confirmed=true after user approval:
python3 scripts/huawei-cloud.py huawei_delete_security_group security_group_id={sg_id} region=cn-north-4 confirmed=true
# Direct CLI equivalent:
skill-quality-cli run --skill-name huawei-cloud-sg-manage -- hcloud VPC DeleteSecurityGroup/v3 --cli-region={region} --security_group_id={sg_id}
```

**WARNING (must be shown before execution):** the preview prints the SG name and how many
rules will be deleted with it. Verify no running instance uses this SG
(`huawei_list_security_groups` + port association check) before confirming.

**`huawei_delete_sg_rule`** — delete a security group rule. **Changes live network
connectivity — VPC default is DENY for unmatched traffic:**

```bash
# [W] 写操作 (WRITE): deletes a security group rule — R1: explicit confirmation required
python3 scripts/huawei-cloud.py huawei_delete_sg_rule security_group_rule_id={rule_id} region=cn-north-4
# ... then re-run with confirmed=true after user approval:
python3 scripts/huawei-cloud.py huawei_delete_sg_rule security_group_rule_id={rule_id} region=cn-north-4 confirmed=true
# Direct CLI equivalent:
skill-quality-cli run --skill-name huawei-cloud-sg-manage -- hcloud VPC DeleteSecurityGroupRule/v3 --cli-region={region} --security_group_rule_id={rule_id}
```

**WARNING (must be shown before execution):** traffic previously permitted/denied by this
rule may be allowed or blocked immediately after deletion. Confirm the rule id, direction,
ports and remote from the preview before proceeding.

## KooCLI Command Format Standard

| Feature | Description | Example |
| ------- | ----------- | ------- |
| Service name | `VPC` (as shown by `hcloud VPC --help`) | `hcloud VPC UpdateSecurityGroup --cli-region=cn-north-4` |
| Operation name | PascalCase (KooCLI appends `/v2` `/v3` version suffixes to VPC ops) | `ListSecurityGroups`, `ListSecurityGroupRules`, `ShowSecurityGroup`, `CreateSecurityGroupRule`, `UpdateSecurityGroup`, `DeleteSecurityGroup`, `DeleteSecurityGroupRule` |
| Region parameter | `--cli-region=<value>` | `--cli-region=cn-north-4` |
| Simple parameter | `--key=value` | `--security_group_id=abc123` |
| Nested parameter | `--parent.child=value` | `--security_group.name=my-sg`, `--security_group_rule.direction=ingress` |
| Indexed array parameter | `--key.N=value` | `--name.1=web`, `--id.1=abc` |
| Output | `--cli-output=json` (default for the dispatcher) | |

## Parameter Confirmation

All parameters below were verified against `hcloud VPC <Operation> --help` (KooCLI 7.2.12).
Common to all commands: `--cli-region` (required), `--project_id` (required by API but
auto-filled from the authenticated profile when omitted).

### ListSecurityGroups/v3

| Parameter | Type | Required | Example |
| --------- | ---- | -------- | ------- |
| `--name.[N]` | array\<string\> | No | `--name.1=web-sg` |
| `--id.[N]` | array\<string\> | No | `--id.1=0e5f8f4a-...` |
| `--description.[N]` | array\<string\> | No | `--description.1=web` |
| `--enterprise_project_id` | string | No | `--enterprise_project_id=0` |
| `--limit` | integer | No | `--limit=100` (0-2000) |
| `--marker` | string | No | pagination marker |

### ListSecurityGroupRules/v3

| Parameter | Type | Required | Example |
| --------- | ---- | -------- | ------- |
| `--security_group_id.[N]` | array\<string\> | No | `--security_group_id.1={sg_id}` |
| `--direction` | string | No | `--direction=ingress` |
| `--protocol.[N]` | array\<string\> | No | `--protocol.1=tcp` |
| `--action` | string | No | `--action=allow` |
| `--enabled` | boolean | No | `--enabled=true` |
| `--remote_ip_prefix` | string | No | `--remote_ip_prefix=10.0.0.0/8` |
| `--limit` | integer | No | `--limit=100` |

### ShowSecurityGroup/v3 / ShowSecurityGroupRule/v2

| Operation | Parameter | Type | Required |
| --------- | --------- | ---- | -------- |
| ShowSecurityGroup/v3 | `--security_group_id` | string | **Yes** |
| ShowSecurityGroupRule/v2 | `--security_group_rule_id` | string | **Yes** |

### CreateSecurityGroup/v3

| Parameter | Type | Required | Example |
| --------- | ---- | -------- | ------- |
| `--security_group.name` | string | **Yes** | `--security_group.name=web-sg` |
| `--security_group.description` | string | No | `--security_group.description=web servers` |
| `--security_group.enterprise_project_id` | string | No | `--security_group.enterprise_project_id=0` |
| `--security_group.tags.[N].key` / `.value` | string | No | `--security_group.tags.1.key=env --security_group.tags.1.value=prod` |
| `--dry_run` | boolean | No | validation call only |

### CreateSecurityGroupRule/v3

| Parameter | Type | Required | Example |
| --------- | ---- | -------- | ------- |
| `--security_group_rule.security_group_id` | string | **Yes** | `--security_group_rule.security_group_id={sg_id}` |
| `--security_group_rule.direction` | string | **Yes** | `--security_group_rule.direction=ingress` (ingress\|egress) |
| `--security_group_rule.protocol` | string | No | `--security_group_rule.protocol=tcp` (tcp\|udp\|icmp\|icmpv6\|any) |
| `--security_group_rule.ethertype` | string | No | `--security_group_rule.ethertype=IPv4` (IPv4\|IPv6) |
| `--security_group_rule.multiport` | string | No | `--security_group_rule.multiport=22,80` or `22-25` |
| `--security_group_rule.remote_ip_prefix` | string | No | `--security_group_rule.remote_ip_prefix=10.0.0.0/8` |
| `--security_group_rule.remote_group_id` | string | No | peer security group id (mutually exclusive with remote_ip_prefix) |
| `--security_group_rule.remote_address_group_id` | string | No | address group id (mutually exclusive with the two above) |
| `--security_group_rule.action` | string | No | `--security_group_rule.action=allow` (allow\|deny) |
| `--security_group_rule.priority` | integer | No | `--security_group_rule.priority=1` (1-65535, lower = higher priority) |
| `--security_group_rule.enabled` | boolean | No | `--security_group_rule.enabled=true` |
| `--security_group_rule.description` | string | No | |

### UpdateSecurityGroup

| Parameter | Type | Required | Example |
| --------- | ---- | -------- | ------- |
| `--security_group_id` | string | **Yes** | `--security_group_id={sg_id}` |
| `--security_group.name` | string | No | `--security_group.name=new-name` |
| `--security_group.description` | string | No | `--security_group.description=new-desc` |

### DeleteSecurityGroup/v3 / DeleteSecurityGroupRule/v3

| Operation | Parameter | Type | Required |
| --------- | --------- | ---- | -------- |
| DeleteSecurityGroup/v3 | `--security_group_id` | string | **Yes** |
| DeleteSecurityGroupRule/v3 | `--security_group_rule_id` | string | **Yes** |

## Troubleshooting

| Error | Root cause → Fix |
| ----- | ---------------- |
| `获取项目ID失败` / APIGW.0301 Unauthorized | Invalid/expired AK/SK or profile → refresh credentials ("hcloud configure list" / re-configure) |
| `缺少必填参数:project_id` | Profile can't resolve project id → pass `project_id=` / `--project_id={id}` explicitly |
| hcloud not found | Install KooCLI (see `references/cli-installation-guide.md`) |
| Empty rule list but SG exists | Wrong region/project → check `--cli-region`, `project_id` |
| Diagnose returns INDETERMINATE | Probe matches a remote security group / address group rule — member IPs are not exposed by the API |
| DeleteSecurityGroup fails | SG still associated with instances/ports or has dependent resources → detach first |

## Security Considerations

- MUST preview every R2/R1 manage action and obtain explicit user confirmation
  (`confirmed=true` only after approval).
- MUST show the connectivity-impact warning before deleting rules or security groups.
- MUST treat `0.0.0.0/0` / `::/0` allow rules as high risk (`huawei_audit_sg_overexposed_rules`
  flags them; restrict to real CIDRs).
- MUST NOT echo AK/SK or any credential values in commands, outputs or reports.
- SHOULD run `huawei_diagnose_sg_port_connectivity` before changing rules that affect
  business traffic.
- SHOULD audit security groups periodically with `huawei_audit_sg_overexposed_rules`.

## Reference Documents

- `references/iam-policies.md` — Least-privilege IAM policies (`vpc:securityGroups:*`, `vpc:securityGroupRules:*`)
- `references/cli-installation-guide.md` — hcloud CLI installation + AK/SK and profile authentication + skill-quality-cli
- `references/sg-rule-reference.md` — Security-group rule field semantics (direction/ethertype/protocol/ports/priority/action)
- `references/dataflow-diagram.md` — Mermaid data flow diagram
- `references/verification-method.md` — Verification method and acceptance checks
- `references/acceptance-criteria.md` — Acceptance criteria for the 11 huawei_* actions
- VPC security group docs: https://support.huaweicloud.com/usermanual-vpc/vpc_SecurityGroup_0001.html
- API Explorer: https://console.huaweicloud.com/apiexplorer/#/openapi/VPC/doc