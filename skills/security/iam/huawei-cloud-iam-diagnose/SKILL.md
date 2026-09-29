---
name: huawei-cloud-iam-diagnose
description: |
  Invoke this skill to check whether a Huawei Cloud IAM user likely has permission to
  perform an action/resource — 华为云 IAM 参考性权限分析/诊断. Given a user name and a target
  action (e.g. ecs:servers:list) / resource, it expands the user's permission chains (direct
  attached policies + user-group inheritance + agencies), parses policy document Allow/Deny
  statements and outputs a "大概率有权限/无权限" reference verdict with a confidence grade and full
  chain trace. Group/agency permissions are cross-validated with the real IAM check interfaces.
  Read-only, R3 auto-execute. Honest boundary: no user-level policy-simulation API exists on
  Huawei Cloud, so results are reference-only, never an authoritative auth decision; custom policy
  + Condition + agency-stacking are flagged "仅供参考".
  Triggers include: 权限分析, 权限诊断, 权限评估, 是否有权限, 查权限, IAM 权限, 权限链路, 谁能访问,
  参考性权限分析, 权限检查, permission diagnosis, permission analysis, check permission,
  IAM permission, permission chain, has permission, policy analysis, who has access,
  role permission, access denied 排查, unauthorized 排查.
tags: [huawei-cloud, iam, permission, diagnose, reference-analysis]
---

# Huawei Cloud IAM Reference Permission Analysis (IAM 参考性权限分析)

## Overview

This skill performs **reference permission analysis** for Huawei Cloud IAM. It answers questions
like "does user `<u>` have permission to do `<action>` on resource `<r>`?" by expanding the user's
permission chains and statically evaluating policy documents.

### Honest Capability Boundary (read first)

| Capability | Status | Notes |
|---|---|---|
| User-level permission simulation (AWS IAM Policy Simulator equivalent) | ❌ Not available | Neither the IAM CLI nor the SDK provide a `SimulatePrincipal` API |
| Group-level check | ✅ | `keystone_check_project_permission_for_group`, `keystone_check_domain_permission_for_group`, `keystone_checkrole_for_group` |
| Agency-level check | ✅ | `check_project_permission_for_agency`, `check_domain_permission_for_agency`, `check_all_projects_permission_for_agency` |
| Check whether a user is in a group | ✅ | `keystone_check_user_in_group` |
| Policy document fetch | ✅ | `get_policy_version_v5`, `keystone_show_permission`, `show_custom_policy` |
| Authorization schema metadata | ✅ | `get_authorization_schema_v5` |

**Therefore this skill outputs a "大概率有权限/无权限" (likely has / likely has not) reference
verdict — it is NOT an authoritative authentication result.** When 100% certainty is required,
guide the user to the IAM console, an actual API trial call, or CTS audit logs (see
[references/verification-method.md](references/verification-method.md)).

### Architecture

```
User input: user (+ maybe target action/resource)
    ↓
1. Resolve user_id (v3 keystone by name → fallback v5 full scan)
    ↓
2. Expand permission chains
   ├─ User direct policies      (v5 ListAttachedUserPoliciesV5)
   ├─ User's groups             (v3 keystone_list_groups_for_user)
   │    ├─ group attached policies (v5 ListAttachedGroupPoliciesV5)
   │    └─ group roles: domain / all-projects (v3)
   └─ Agencies                  (v5 ListAgenciesV5 + attached policies/roles)
    ↓
3. Fetch policy documents (get_policy_version_v5 / role.policy)
    ↓
4. Evaluate Allow/Deny per policy doc + grade confidence
    ↓
5. Emit verdict + precision grade + chain trace (+ real check cross-validation)
```

**Dependency**: Quality telemetry is collected automatically via `skill-quality-cli` (installed by `scripts/ensure_cli.sh` if absent).

## Prerequisites

- **Python 3.7+** with `huaweicloudsdkcore>=3.1.140` and `huaweicloudsdkiam>=3.1.140` (v5 module
  required by the diagnose scripts).
- Credentials in **either** form (checked in this order):
  1. Environment variables `HW_ACCESS_KEY` / `HW_SECRET_KEY` (+ optional `HW_REGION_NAME`,
     `HW_SECURITY_TOKEN`, `HW_DOMAIN_ID`), **or**
  2. Local KooCLI profile at `~/.hcloud/config.json` (created by the KooCLI).
     ● `HCLOUD_PROFILE` selects a non-default profile name.
- An IAM identity with **read** access to the IAM service. Some chain-listing/check interfaces
  (domain/agency role listing, real checks) additionally require IAM admin/view permissions; when
  the current credential lacks them, those steps report `HTTP 403` and the verdict is based on the
  data that could be read (still reference-only).

Run the environment check first:

> **⚠️ Mandatory: every `hcloud` command in this skill MUST be wrapped with `skill-quality-cli run --skill-name huawei-cloud-iam-diagnose -- ` — bare `hcloud` calls are strictly forbidden.**

```bash
skill action=exec: bash skill://scripts/check_env.sh
```

Install dependencies (when the check asks) — requirements.txt in the skill root defines
`huaweicloudsdkcore` and `huaweicloudsdkiam`.

- **`skill-quality-cli`** — ensured by `bash scripts/ensure_cli.sh` (idempotent, skips if present)
  - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade)
  - Disable telemetry report: set `SKILL_QUALITY_REPORT=0`

## Workflow

### Step 1 — Environment preparation

Run `skill://scripts/check_env.sh`. If it fails, fix and re-run before proceeding.

### Step 2 — Resolve the target user

Use `scripts/list_user_groups.py --user_name=<user>` (or `--user_id`) to resolve, or pass
`--user_name` directly to the diagnose/trace scripts (they resolve internally).

### Step 3 — Choose the action

| Intent | Recommend |
|---|---|
| Full verdict for one action/resource | `scripts/diagnose_user_permission.py` (`--user_name`, `--action`, optional `--resource`) |
| List the whole chain (no filtering) | `scripts/trace_permission_chain.py` (`--user_name`, optional `--json`) |
| Real check: does group have role X? | `scripts/check_group_permission.py` (`--group_id`, `--role_id`, `--scope`) |
| Real check: does agency have role X? | `scripts/check_agency_permission.py` (`--agency_id`, `--role_id`, `--scope`) |
| Quick data fetch (policies/groups/agencies) | the `list_*` scripts |

> Always run a script with `-h` first to confirm parameters before executing it.

### Step 4 — Interpret the verdict

Verdicts are always one of:

- **大概率有权限** — evidence of Allow (unless explicit Deny wins)
- **大概率无权限** — explicit Deny exists, or chain is empty / no Allow|Deny
  statement matched the target action (IAM 隐式拒绝 implicit deny)
- **不确定** — only when a matched statement cannot be statically evaluated
  (e.g. contains a `Condition`, or resource/action matching is ambiguous)

Confidence grades:

- 高 (high): preset system policy + group inheritance
- 中 (medium): custom policy without Condition; agency stacking; EPS authorization
- 低 (low): policy contains a `Condition`
- Custom policy + Condition + agency stacking → always **仅供参考 (for reference only)**

## Core Commands

All commands below are read-only (R3, auto-execute). Paths are relative to the skill directory.

### Resolve user / list user groups (`huawei_list_user_groups`)

```bash
python3 scripts/list_user_groups.py --user_name=<user_name>
# or  --user_id=<user_id>   (--domain_id optional when resolving by name)
```

### List direct user policies (`huawei_list_attached_user_policies`)

```bash
python3 scripts/list_attached_user_policies.py --user_name=<user_name> [--domain_id=<domain_id>]
```

### List group attached policies (`huawei_list_attached_group_policies`)

```bash
python3 scripts/list_attached_group_policies.py --group_id=<group_id>
```

### List IAM agencies (`huawei_list_iam_agencies`)

```bash
python3 scripts/list_iam_agencies.py --region cn-north-4
# --region 可选，省略时默认 cn-north-4
```

### Diagnose user permission (core, `huawei_diagnose_user_permission`)

```bash
python3 scripts/diagnose_user_permission.py \
  --user_name=<user_name> \
  --action=<action> \
  [--resource=<resource>] [--domain_id=<domain_id>] [--only=all|direct|group|agency]
```

Example (替换 `<user_name>` 为真实 IAM 用户名，如 `wangjie`):

```bash
python3 scripts/diagnose_user_permission.py --user_name=wangjie --action=ecs:servers:list
```

### Trace permission chain (`huawei_trace_permission_chain`)

```bash
python3 scripts/trace_permission_chain.py --user_name=<user_name> [--json]
```

### Real group-level check (`huawei_check_group_permission`)

```bash
python3 scripts/check_group_permission.py \
  --group_id=<group_id> --role_id=<role_id> \
  --scope=project|domain|all_projects \
  [--project_id=<p>] [--domain_id=<d>]
```

### Real agency-level check (`huawei_check_agency_permission`)

```bash
python3 scripts/check_agency_permission.py \
  --agency_id=<agency_id> --role_id=<role_id> \
  --scope=project|domain|all_projects \
  [--project_id=<p>] [--domain_id=<d>]
```

## Parameter Confirmation

| Parameter | Required | Description |
|---|---|---|
| `--user_name` / `--user_id` | one of | IAM user to analyze |
| `--action` | diagnose only | target action, e.g. `ecs:servers:list` |
| `--resource` | no | target resource; default `*` |
| `--domain_id` | no | account ID; falls back to credential domain |
| `--group_id` | check-group | group ID (v5/v3 group_id format) |
| `--agency_id` | check-agency | agency ID |
| `--role_id` | check-* | permission/role ID |
| `--scope` | check-* | `project` / `domain` / `all_projects` |
| `--project_id` | check+project | project ID |
| `--region` | no | default `cn-north-4` |
| `--json` | trace | JSON output |

**CLI check-interface caveat:** the plain IAM HEAD check commands (e.g.
`KeystoneCheckProjectPermissionForGroup`, `KeystoneCheckDomainPermissionForGroup`) return an
indistinguishable empty result (exit code 0) for both "has permission" (HTTP 204) and "does not"
(HTTP 404). The `check_*.py` scripts therefore use the Python SDK and report the actual HTTP status,
so prefer them for a real verification.

## KooCLI Command Format Standard

For the list/check operations the CLI equivalent commands exist and follow the standard form
`hcloud IAM <Operation> --cli-region=<region> ...` (Operation = the API name, e.g.
`ListAttachedUserPoliciesV5`; parameters follow `--<ParamName>=<value>`).

Verified examples (KooCLI 7.2.12):

- `hcloud IAM ListAttachedUserPoliciesV5 --user_id=<id> --cli-region=cn-north-4`
- `hcloud IAM KeystoneListGroupsForUser --user_id=<id> --cli-region=cn-north-4`
- `hcloud IAM ListAgenciesV5 --cli-region=cn-north-4`

More in [references/cli-installation-guide.md](references/cli-installation-guide.md). The Python
scripts remain the source of truth for reliable verdicts and check semantics.

## Reference Documents

- [references/cli-installation-guide.md](references/cli-installation-guide.md) — credentials setup, CLI install, KooCLI profile vs AK/SK
- [references/iam-policies.md](references/iam-policies.md) — least-privilege IAM policies needed to run this skill
- [references/verification-method.md](references/verification-method.md) — how to verify a verdict and confirm with 100% certainty
- [references/dataflow-diagram.md](references/dataflow-diagram.md) — Mermaid data flow diagram
- [references/acceptance-criteria.md](references/acceptance-criteria.md) — acceptance criteria checklist

## Troubleshooting

| Symptom | Cause & fix |
|---|---|
| `HTTP 403` on a chain step or check | Current credential lacks IAM admin/view permission for that interface. Grant the requester IAM read rights or run with an admin credential. Verdict uses readable data only. |
| `no such group` (v5) vs group list mismatch | v3 and v5 accept different group-id formats — always take the id from the same API family you query with. |
| check script always says ERROR 403 | The real check interfaces require the caller to be an IAM admin of the domain; document and escalate rather than guessing. |
| `RetryError ... 429` | Rate limit; retry with backoff. |