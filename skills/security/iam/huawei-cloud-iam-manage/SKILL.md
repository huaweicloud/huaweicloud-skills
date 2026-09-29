---
name: huawei-cloud-iam-manage
description: >-
  Manages Huawei Cloud IAM identity configuration (write-capable companion to the read-only IAM query
  capability). Covers full lifecycle of IAM users, groups, policies, agencies, permanent AK/SK — with
  every write action (R2/R1) preview + explicit confirmation; deletes enumerate impacted resources first;
  high-authority grants and external-account agencies show explicit warnings; the Secret Access Key is
  returned once and never persisted or logged; includes read-only queries (R3) as pre-checks and analysis.
  Provides 20 huawei_* actions: huawei_list_iam_users, huawei_list_iam_groups,
  huawei_list_iam_policies, huawei_list_iam_agencies, huawei_list_iam_custom_policies,
  huawei_analyze_iam_least_privilege, huawei_analyze_iam_password_compliance,
  huawei_create_iam_user, huawei_create_iam_group, huawei_attach_iam_policy,
  huawei_detach_iam_policy, huawei_create_iam_agency, huawei_create_iam_ak_sk,
  huawei_create_iam_custom_policy, huawei_config_iam_login, huawei_delete_iam_user,
  huawei_delete_iam_group, huawei_delete_iam_agency, huawei_delete_iam_ak_sk,
  huawei_delete_iam_custom_policy. Triggers include: IAM, 用户, 用户组, 策略, 委托, 权限, AK/SK, MFA,
  登录保护, 创建用户, 删除用户, identity, policy, agency, access key, create user, create group, delete.
---

# Huawei Cloud IAM Management

**STOP - Do not answer from general knowledge.** Follow the procedure below.

## Overview

This skill provides write-capable management of Huawei Cloud IAM identity configuration through the
IAM service of the hcloud CLI (advanced operation reference: `IAM --help`). It is the **manage**
companion to the read-only IAM query capability and forms a **query+manage pair** under
`skills/security/iam/`.

It covers 20 `huawei_*` actions in three capability groups:

| Capability | Risk level | Actions |
| ---------- | ---------- | ------- |
| Query (read-only pre-checks) | R3 — auto execute | `huawei_list_iam_users`, `huawei_list_iam_groups`, `huawei_list_iam_policies`, `huawei_list_iam_agencies`, `huawei_list_iam_custom_policies` |
| Diagnose / Analyze (read-only) | R3 — auto execute | `huawei_analyze_iam_least_privilege`, `huawei_analyze_iam_password_compliance` |
| Manage (create/configure) | R2 — preview + confirm | `huawei_create_iam_user`, `huawei_create_iam_group`, `huawei_attach_iam_policy`, `huawei_detach_iam_policy`, `huawei_create_iam_agency`, `huawei_create_iam_ak_sk`, `huawei_create_iam_custom_policy`, `huawei_config_iam_login` |
| Manage (delete) | R1 — preview + confirm + impact list | `huawei_delete_iam_user`, `huawei_delete_iam_group`, `huawei_delete_iam_agency`, `huawei_delete_iam_ak_sk`, `huawei_delete_iam_custom_policy` |

**Scope boundaries:**

- ✅ List users/groups/policies/agencies/custom policies (R3, read-only, auto execute)
- ✅ Analyze least-privilege and domain password policy compliance (R3, read-only)
- ✅ Create users, groups, agencies, custom policies, permanent AK/SK; attach/detach policies; configure
  login profile / password / login protection (R2, preview + confirm)
- ✅ Delete users, groups, agencies, permanent AK/SK, custom policies (R1, preview + confirm)
- ❌ NEVER modify a **system** (predefined) policy — only **custom** policies are manageable
- ❌ NEVER disable the root/enterprise administrator account, or take any irreversible action without
  explicit confirmation
- ❌ NEVER write the **Secret Access Key** (SK), passwords, or any credential value to logs, files,
  persistent storage, tool intermediates, or any later conversation turn — the SK may only appear in the
  final reply, shown once to the user

**Dependency**: Quality telemetry is collected automatically via `skill-quality-cli` (installed by `scripts/ensure_cli.sh` if absent).

## Critical Warnings

| Trap | Why |
| ---- | --- |
| **SK 仅返回一次** — The Secret Access Key is returned exactly once by `CreatePermanentAccessKey`. Show it to the user exactly once, in the **final reply**. It must **not** be written to logs, files, persistent storage, tool-call inputs/outputs, or any later conversation turn. | A lost SK cannot be retrieved; the key must be deleted and re-created. |
| **Passwords are Sensitive** — `--password` in login-profile operations must never be echoed, logged, or stored. | Credential leakage. |
| **Granting high-authority policies** (e.g. `AdministratorAccess`, `SysAdm*`, `FullAccess`) requires an explicit warning before confirmation. | Least-privilege principle. |
| **Creating an agency for an external account** authorizes that account to assume the rights granted by the agency — show the trusted account (`trust_domain_name`) and warn before confirmation. | Cross-account risk. |
| **Delete is irreversible** — deleting a user permanently removes the IAM user and its access keys; deleting an agency revokes delegated access; deleting a custom policy breaks any attachments. | Data/access loss. |
| **Verifying by name first** — always run the read-only pre-check (`list_users`, `list_groups`, `list_policies`, `list_agencies`) before creating to avoid duplicates, and re-read after write to confirm. | Idempotency + accuracy. |

## Prerequisites

1. **hcloud CLI** (KooCLI 7.2.x or later) installed and authenticated.
   - **Recommended authentication — Mode B: local hcloud profile via the configure wizard**: run
     `hcloud configure set` (interactive; credentials are prompted and never passed on the command
     line), then `hcloud configure list` must show a valid profile with mode `AKSK` and a real
     `accessKeyId`.
   - **AK/SK environment variables are NOT a supported credential path for KooCLI** — KooCLI reads
     `~/.hcloud/config.json` (resolved from the OS user home, not `$HOME`), and does **not** read
     `HUAWEICLOUD_SDK_AK`/`HUAWEICLOUD_SDK_SK`, `HUAWEI_ACCESS_KEY`/`HUAWEI_SECRET_KEY`, or
     `HW_ACCESS_KEY`/`HW_SECRET_KEY` (verified against KooCLI 7.2.12: no such env names are
     consulted — those names belong to the Huawei Cloud SDKs, not KooCLI). Do not rely on environment
     variables for authentication; always configure a profile with `hcloud configure set`.
   - Verify authentication with the `configure list` subcommand.
   - See `references/cli-installation-guide.md`.
2. **Region**: always pass `--cli-region={region}` (e.g. `cn-north-4`).
3. **IAM permissions** on the calling identity: least-privilege policies are provided in
   `references/iam-policies.md`. The calling user/agency must hold the corresponding
   `iam:users:createUser` / `iam:users:deleteUser` / `iam:groups:createGroup` / `iam:agencies:createAgency`
   / `iam:credentials:createAKSK` / `iam:permissions:grantRoleToUserOnProject` style permissions, or be
   the account administrator.
4. Read-only pre-checks (`list_*`, `GetAccountSummaryV5`) require at least
   `iam:users:listUsers` / `iam:groups:listGroups` / `iam:permissions:listPolicies` /
   `iam:agencies:listAgencies` permissions.
5. **Placeholders are illustrative** — every `{user_id}` / `{group_id}` / `{policy_id}` /
   `{agency_id}` / `{access_key}` must be replaced with the **real value from the read-only list
   commands** (see "Resolving resource IDs" in Core Commands); never run with literal `{...}`.

> **Account SCP restriction (environment, not skill logic)**: under an org **SCP**, user/login/AK-SK
> writes (`CreateUserV5`, login-profile/protect, `CreatePermanentAccessKey`) may be denied
> (`PAP5.0001`-style) even with the IAM permissions above; groups/policies/agencies/attach/detach/list
> are unaffected — report the deny, suggest checking the org SCP, then proceed with permitted actions.

- **`skill-quality-cli`** — ensured by `bash scripts/ensure_cli.sh` (idempotent, skips if present)
  - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade)
  - Disable telemetry report: set `SKILL_QUALITY_REPORT=0`

## Workflow

```
1. Identify target → region, user/group/policy/agency name or id, action intent
2. Classify intent →
     - Query / Diagnose (R3): list / analyze — execute automatically
     - Manage (R2): create / attach / detach / configure — show preview, DO-NOT-WARN advice, ask confirmation
     - Manage (R1): delete — enumerate impacted resources, show irreversible warning, require confirmation
3. Pre-check (write actions) → run the relevant read-only list command and confirm no duplicate / correct targets
4. Execute → build the hcloud command from the verified templates below
5. Verify → re-read the resource with the corresponding query command
6. Output → structured JSON summary (never credentials)
7. Report quality → `skill-quality-cli run` (wrapping every hcloud command) reports status/error code automatically
```

**Confirmation gates (MUST NOT be skipped):**

- **R3 actions**: execute automatically without confirmation.
- **R2 actions** (`create_user`, `create_group`, `attach_iam_policy`, `detach_iam_policy`,
  `create_iam_agency`, `create_iam_ak_sk`, `create_iam_custom_policy`, `config_iam_login`): show the full
  command, the resource to be created/changed, and ask "confirm?" before running.
  - `attach_iam_policy` with a high-authority policy (AdministratorAccess / *FullAccess / *Admin* /
    `iam:permissions:grantRoleToUserOnProject` on a system policy): additionally print a warning:
    *"This grants broad authority. Confirm you intend to grant this permission."*
  - `create_iam_agency` targeting an external account (`--agency.trust_domain_name` set to a
    **different** account than the current one): print the trusted account name and warn:
    *"This authorizes an external account to assume this agency — confirm."*
  - `create_iam_ak_sk`: warn that **the SK will be shown only once** and must not be committed or logged.
  - `config_iam_login` with a `--password`: treat the value as Sensitive — obtain it via
    `read -s`/env, never echo it in the conversation; never include it in the printed command.
- **R1 actions** (`delete_user`, `delete_group`, `delete_agency`, `delete_ak_sk`, `delete_custom_policy`):
  first list the target's dependencies (user's attached policies / AK-SK / group memberships; agency's
  attached policies; custom policy's attachments via `ListEntitiesForPolicyV5`), print the impact list,
  then require explicit confirmation.

## Core Commands

> All commands below are shown in **dual form**: the bare executable `hcloud IAM <Operation>`
> command and the identical payload wrapped with
> `skill-quality-cli run --skill-name huawei-cloud-iam-manage -- ...` for quality reporting.
> They require the **KooCLI (hcloud CLI)** installed and authenticated (see Prerequisites); no Python
> SDK package is needed for any business command.
>
> **⚠️ Mandatory: every `hcloud` command in this skill MUST be wrapped with
> `skill-quality-cli run --skill-name huawei-cloud-iam-manage -- <command>` — bare
> `hcloud` calls are strictly forbidden.**

### 1. Query (R3 — read-only, auto execute)

List IAM users:

```bash
# Optional: --group_id={group_id} --limit={n} --marker={marker}
hcloud IAM ListUsersV5 --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM ListUsersV5 --cli-region={region}
```

List IAM groups:

```bash
# Optional: --limit={n} --marker={marker} --user_id={user_id}
hcloud IAM ListGroupsV5 --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM ListGroupsV5 --cli-region={region}
```

List all policies (system + custom):

```bash
# Optional: --policy_type={system|custom} --only_attached={true|false} --X-Language={zh-cn|en-us} --limit={n}
hcloud IAM ListPoliciesV5 --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM ListPoliciesV5 --cli-region={region}
```

List agencies (trust agencies):

```bash
# Optional: --limit={n} --marker={marker}
hcloud IAM ListAgenciesV5 --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM ListAgenciesV5 --cli-region={region}
```

List custom policies (page and per_page must be used together):

```bash
# --page={page} --per_page={per_page} are both required (1..300)
hcloud IAM ListCustomPolicies --cli-region={region} --page=1 --per_page=100
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM ListCustomPolicies --cli-region={region} --page=1 --per_page=100
```

**Resolving resource IDs** — every write/delete operation below takes ID-type parameters. Do not guess
them: resolve from the corresponding list command output and use the real value. All name matching is
done **client-side** against the full list output — none of these list commands support a `--name` /
`--scope` filter (verified against KooCLI 7.2.12):

```bash
# {user_id}    → hcloud IAM ListUsersV5        --cli-region={region}            → users[].user_id      (filter by user_name)
# {group_id}   → hcloud IAM ListGroupsV5       --cli-region={region}            → groups[].group_id     (filter by group_name)
# {policy_id}  → hcloud IAM ListPoliciesV5     --cli-region={region} --policy_type={custom|system} --only_attached=true → policies[].policy_id (filter by policy_name)
# {agency_id}  → hcloud IAM ListAgenciesV5     --cli-region={region}            → agencies[].agency_id  (filter by agency_name)
# {access_key} → hcloud IAM ListPermanentAccessKeys --cli-region={region} --user_id={user_id} → credentials[].access
# {domain_id}  → hcloud IAM KeystoneListAuthDomains --cli-region={region}       → domains[].id
```

> Example (agency id by name): `hcloud IAM ListAgenciesV5 --cli-region=cn-north-4` → output JSON
> `agencies[]` → pick the record whose `name` equals the target agency name → use its `agency_id`.
> The same list-then-filter pattern applies to `user_name`→`user_id`, `group_name`→`group_id`, and
> `policy_name`→`policy_id`.

### 2. Diagnose / Analyze (R3 — read-only, auto execute)

**`huawei_analyze_iam_least_privilege`** — find over-privileged users/groups (those holding system
admin policies or many policies):

```bash
# Step 1: list users
hcloud IAM ListUsersV5 --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM ListUsersV5 --cli-region={region}

# Step 2: for each user, list attached user policies
hcloud IAM ListAttachedUserPoliciesV5 --cli-region={region} --user_id={user_id}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM ListAttachedUserPoliciesV5 --cli-region={region} --user_id={user_id}

# Step 3: additionally list groups with policies
hcloud IAM ListGroupsV5 --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM ListGroupsV5 --cli-region={region}
hcloud IAM ListAttachedGroupPoliciesV5 --cli-region={region} --group_id={group_id}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM ListAttachedGroupPoliciesV5 --cli-region={region} --group_id={group_id}
```

Flag accounts attached to any **system admin policy** (`AdministratorAccess`, `SysAdm*`, any
`*FullAccess`, `*Admin`) or to more than a threshold (default 8) policies. Report them in a table with
user_id, attached policy names, and the risk reason.

**`huawei_analyze_iam_password_compliance`** — compare the domain password policy against the
Huawei Cloud security baseline:

```bash
# Step 1: show domain password policy (v5)
hcloud IAM ShowPasswordPolicyV5 --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM ShowPasswordPolicyV5 --cli-region={region}

# Step 2 (recommended): list users and their MFA devices
hcloud IAM ListUsersV5 --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM ListUsersV5 --cli-region={region}
hcloud IAM ListUserMfaDevices --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM ListUserMfaDevices --cli-region={region}
```

Check: minimum password length ≥ 8, password valid days ≤ 90, minimum password age ≥ 0, at least 3
character classes, disallowed recent passwords ≥ 1, users without MFA. Output a pass/fail table per check
and a remediation hint per failed check.

> Note: `ShowDomainPasswordPolicy` (v3) requires `--domain_id`; `ShowPasswordPolicyV5` (v5) reads the
> calling account's policy and is the preferred default.

### 3. Manage (R2 — preview + confirm)

**`huawei_create_iam_user`** — create an IAM user:

```bash
# Optional: --description={description}
hcloud IAM CreateUserV5 --cli-region={region} --name={user_name} --enabled=true
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM CreateUserV5 --cli-region={region} --name={user_name} --enabled=true
```

> Pre-check: run `ListUsersV5` with the same name to avoid duplicates.

**`huawei_create_iam_group`** — create an IAM group:

```bash
# Optional: --description={description}
hcloud IAM CreateGroupV5 --cli-region={region} --group_name={group_name}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM CreateGroupV5 --cli-region={region} --group_name={group_name}
```

**`huawei_attach_iam_policy`** — attach a policy to a user or group:

```bash
# Attach to a user
hcloud IAM AttachUserPolicyV5 --cli-region={region} --user_id={user_id} --policy_id={policy_id}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM AttachUserPolicyV5 --cli-region={region} --user_id={user_id} --policy_id={policy_id}
# Attach to a group
hcloud IAM AttachGroupPolicyV5 --cli-region={region} --group_id={group_id} --policy_id={policy_id}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM AttachGroupPolicyV5 --cli-region={region} --group_id={group_id} --policy_id={policy_id}
# Attach to an agency
hcloud IAM AttachAgencyPolicyV5 --cli-region={region} --agency_id={agency_id} --policy_id={policy_id}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM AttachAgencyPolicyV5 --cli-region={region} --agency_id={agency_id} --policy_id={policy_id}
```

> Pre-check: resolve the policy id/name with `ListPoliciesV5`. If the policy name contains
> `AdministratorAccess`, `Admin`, or `FullAccess`, print the high-authority warning before confirmation.

**`huawei_detach_iam_policy`** — detach a policy from a user or group:

```bash
hcloud IAM DetachUserPolicyV5 --cli-region={region} --user_id={user_id} --policy_id={policy_id}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM DetachUserPolicyV5 --cli-region={region} --user_id={user_id} --policy_id={policy_id}
hcloud IAM DetachGroupPolicyV5 --cli-region={region} --group_id={group_id} --policy_id={policy_id}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM DetachGroupPolicyV5 --cli-region={region} --group_id={group_id} --policy_id={policy_id}
hcloud IAM DetachAgencyPolicyV5 --cli-region={region} --agency_id={agency_id} --policy_id={policy_id}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM DetachAgencyPolicyV5 --cli-region={region} --agency_id={agency_id} --policy_id={policy_id}
```

**`huawei_create_iam_agency`** — create a trust agency. Use the **legacy `CreateAgency`** (v3)
interface (verified working) — the V5 `CreateAgencyV5 --trust_policy` form is rejected by the
platform (`PAP5.0011 malformed policy document`) and must not be used.

```bash
# --agency.domain_id        委托方账号ID（先经 KeystoneListAuthDomains 获取 domains[].id）
# --agency.name             委托名
# --agency.trust_domain_name 被委托方账号名（允许扮演该委托的账号；与 trust_domain_id 至少填一个）
# 通过 --agency.trust_domain_name / --agency.trust_domain_id 指定被委托方，平台自动生成信任策略，无需手写 trust_policy JSON
# Optional: --agency.description --agency.duration={FOREVER|ONEDAY|<days>}
hcloud IAM CreateAgency --cli-region={region} --agency.domain_id={domain_id} --agency.name={agency_name} --agency.trust_domain_name={trusted_domain_name}
# 质量上报包装（推荐执行方式）:
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM CreateAgency --cli-region={region} --agency.domain_id={domain_id} \
  --agency.name={agency_name} --agency.trust_domain_name={trusted_domain_name}
```

> The `trust_domain_name` is the account allowed to assume this agency; if it is **not** the current
> account (external/delegated account), print the account id and the cross-account warning before
> confirmation. Verify with `ListAgenciesV5` (match by `agency_name`).

**`huawei_create_iam_ak_sk`** — create a permanent AK/SK for an IAM user:

```bash
# Optional: --credential.description={description}
hcloud IAM CreatePermanentAccessKey --cli-region={region} --credential.user_id={user_id}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM CreatePermanentAccessKey --cli-region={region} --credential.user_id={user_id}
```

**⚠️ SK handling (MANDATORY):**

- The response contains `credential.secret_access_key`. **Show it once** in the summary, then instruct
  the user to save it.
- **Do NOT** store it in a file, do NOT pipe it to logs, do NOT paste it again on request ("SK 只显示一次").
- If lost, the key must be deleted (`huawei_delete_iam_ak_sk`) and re-created.

**`huawei_create_iam_custom_policy`** — create a custom identity policy:

```bash
# Optional: --description={description} --path={path}
hcloud IAM CreatePolicyV5 --cli-region={region} --policy_name={policy_name} --policy_document='{"Version":"5.0","Statement":[{"Effect":"Allow","Action":["ecs:servers:list"],"Resource":["*"]}]}'
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM CreatePolicyV5 --cli-region={region} --policy_name={policy_name} --policy_document='{"Version":"5.0","Statement":[{"Effect":"Allow","Action":["ecs:servers:list"],"Resource":["*"]}]}'
```

**`huawei_config_iam_login`** — configure login: enable/disable user, set/reset password, set login
protection / MFA basis:

```bash
# Enable or disable a user (启停用)
hcloud IAM UpdateUserV5 --cli-region={region} --user_id={user_id} --enabled={true|false}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM UpdateUserV5 --cli-region={region} --user_id={user_id} --enabled={true|false}

# Create login profile (sets initial password). --password is Sensitive.
# Because --password collides with a KooCLI system parameter, pass it via --cli-jsonInput:
cat > /tmp/login_profile.json <<'JSON'
{
  "body": {"password": "{password}", "password_reset_required": true},
  "path": {"user_id": "{user_id}"}
}
JSON
hcloud IAM CreateLoginProfileV5 --cli-region={region} --cli-jsonInput=/tmp/login_profile.json
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM CreateLoginProfileV5 --cli-region={region} --cli-jsonInput=/tmp/login_profile.json

# Update login profile (reset password) — same jsonInput workaround
cat > /tmp/update_login_profile.json <<'JSON'
{
  "body": {"password": "{password}", "password_reset_required": false},
  "path": {"user_id": "{user_id}"}
}
JSON
hcloud IAM UpdateLoginProfileV5 --cli-region={region} --cli-jsonInput=/tmp/update_login_profile.json
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM UpdateLoginProfileV5 --cli-region={region} --cli-jsonInput=/tmp/update_login_profile.json

# Configure login protection (登录保护 / MFA)
hcloud IAM UpdateLoginProtect --cli-region={region} --user_id={user_id} --login_protect.enabled={true|false} --login_protect.verification_method={sms|email|vmfa}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM UpdateLoginProtect --cli-region={region} --user_id={user_id} --login_protect.enabled={true|false} --login_protect.verification_method={sms|email|vmfa}
```

> For the login-profile jsonInput files: the `.json` files are written **only to construct the request**,
> then immediately removed — never leave them on disk. The password value comes from the user's secure
> channel (env/`read -s`), is never echoed in the preview, and is never printed after execution.

### 4. Manage Delete (R1 — preview + confirm + impact list)

**`huawei_delete_iam_user`** — delete an IAM user. **Impact pre-check (MUST run):**

```bash
# List the user's attached policies, groups, AK/SK to enumerate impact
hcloud IAM ListAttachedUserPoliciesV5 --cli-region={region} --user_id={user_id}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM ListAttachedUserPoliciesV5 --cli-region={region} --user_id={user_id}
hcloud IAM ListGroupsV5 --cli-region={region} --user_id={user_id}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM ListGroupsV5 --cli-region={region} --user_id={user_id}
hcloud IAM ListPermanentAccessKeys --cli-region={region} --user_id={user_id}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM ListPermanentAccessKeys --cli-region={region} --user_id={user_id}

# Then delete (after user confirms the impact list)
hcloud IAM DeleteUserV5 --cli-region={region} --user_id={user_id}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM DeleteUserV5 --cli-region={region} --user_id={user_id}
```

**`huawei_delete_iam_group`** — delete an IAM group:

```bash
hcloud IAM DeleteGroupV5 --cli-region={region} --group_id={group_id}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM DeleteGroupV5 --cli-region={region} --group_id={group_id}
```

**`huawei_delete_iam_agency`** — delete an agency. Use the **legacy `DeleteAgency`** (v3) interface
(verified effective) — the V5 `DeleteAgencyV5` returns `rc=0` but silently leaves the agency in
place and must not be used.

> ⚠️ `ListAgenciesV5` has **no `--name` filter** (verified: only `--limit` / `--marker` /
> `--path_prefix` are accepted). Matching by agency name must be done **client-side** against the full
> list output — never pass `--name` to `ListAgenciesV5`.

```bash
# 1) Read back to confirm the agency exists and resolve its agency_id (match by agency_name)
hcloud IAM ListAgenciesV5 --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM ListAgenciesV5 --cli-region={region}
#    → client-side filter: agencies[].name == {agency_name} → agencies[].agency_id

# 2) Delete with the legacy interface (DeleteAgencyV5 was observed to silently no-op)
hcloud IAM DeleteAgency --cli-region={region} --agency_id={agency_id}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM DeleteAgency --cli-region={region} --agency_id={agency_id}

# 3) MUST re-read after deletion (full list + client-side filter by agency_name):
#    if the agency still shows up, deletion did not take effect — retry and report;
#    do not end silently on rc=0 alone.
hcloud IAM ListAgenciesV5 --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM ListAgenciesV5 --cli-region={region}
#    → client-side filter again: 0 matches by {agency_name} ⇒ deletion confirmed
```

> Re-read `ListAgenciesV5` after deletion, filter the result **on the client side** by `agency_name`
> (`ListAgenciesV5 --name` is NOT supported), and confirm the agency is gone; report the read-back
> (do not assume success from the delete `rc=0` alone).

**`huawei_delete_iam_ak_sk`** — delete a permanent AK/SK:

```bash
hcloud IAM DeletePermanentAccessKey --cli-region={region} --access_key={access_key}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM DeletePermanentAccessKey --cli-region={region} --access_key={access_key}
```

**`huawei_delete_iam_custom_policy`** — delete a custom policy:

```bash
# Optional pre-check: list entities attached to the policy
hcloud IAM ListEntitiesForPolicyV5 --cli-region={region} --policy_id={policy_id}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM ListEntitiesForPolicyV5 --cli-region={region} --policy_id={policy_id}

hcloud IAM DeletePolicyV5 --cli-region={region} --policy_id={policy_id}
skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud IAM DeletePolicyV5 --cli-region={region} --policy_id={policy_id}
```

## KooCLI Command Format Standard

| Feature | Description | Example |
| ------- | ----------- | ------- |
| Service name | `IAM` (as shown by the IAM service `--help`; metadata dir `iam`) | `hcloud IAM ListUsersV5 --cli-region=cn-north-4` |
| Operation name | PascalCase | `ListUsersV5`, `CreateUserV5`, `DeletePolicyV5` |
| Region parameter | `--cli-region=<value>` | `--cli-region=cn-north-4` |
| Simple parameter | `--key=value` | `--user_id=xxx` |
| Indexed / dotted body | `--parent.child=value` | `--credential.user_id=xxx`, `--login_protect.enabled=true` |

> Always run `hcloud IAM <Operation> --help` before constructing a command to confirm exact parameter
> names. Operation+param tables below were verified against KooCLI 7.2.12.

## Parameter Confirmation

### Query (R3)

| Operation | Parameter | Type | Required | Example |
| --------- | --------- | ---- | -------- | ------- |
| ListUsersV5 | `--group_id` | string | No | `--group_id=G-001` |
| ListUsersV5 | `--limit` | int | No | `--limit=100` |
| ListUsersV5 | `--marker` | string | No | `--marker=next_token` |
| ListGroupsV5 | `--user_id` | string | No | `--user_id=U-001` |
| ListGroupsV5 | `--limit` `/` `--marker` | - | No | `--limit=100` |
| ListPoliciesV5 | `--policy_type` | string | No | `--policy_type=custom` |
| ListPoliciesV5 | `--only_attached` | bool | No | `--only_attached=true` |
| ListPoliciesV5 | `--X-Language` | string | No | `--X-Language=en-us` |
| ListAgenciesV5 | `--limit` `/` `--marker` | - | No | `--limit=100` |
| ListCustomPolicies | `--page` `/` `--per_page` | int | No | `--page=1 --per_page=100` |

### Analyze (R3)

| Operation | Parameter | Type | Required | Example |
| --------- | --------- | ---- | -------- | ------- |
| ShowPasswordPolicyV5 | — | - | — | `hcloud IAM ShowPasswordPolicyV5 --cli-region={region}` |
| ListAttachedUserPoliciesV5 | `--user_id` | string | **Yes** | `--user_id=U-001` |
| ListAttachedGroupPoliciesV5 | `--group_id` | string | **Yes** | `--group_id=G-001` |
| ListUserMfaDevices | — | - | — | `hcloud IAM ListUserMfaDevices --cli-region={region}` |

### Manage Create (R2)

| Operation | Parameter | Type | Required | Example |
| --------- | --------- | ---- | -------- | ------- |
| CreateUserV5 | `--name` | string | **Yes** | `--name=dev-user` |
| CreateUserV5 | `--enabled` | bool | **Yes** | `--enabled=true` |
| CreateUserV5 | `--description` | string | No | `--description="dev account"` |
| CreateGroupV5 | `--group_name` | string | **Yes** | `--group_name=dev` |
| CreateGroupV5 | `--description` | string | No | `--description="dev group"` |
| CreateAgency | `--agency.domain_id` | string | **Yes** | `--agency.domain_id=<account-domain-id>` (from `KeystoneListAuthDomains`) |
| CreateAgency | `--agency.name` | string | **Yes** | `--agency.name=cce-agency` |
| CreateAgency | `--agency.trust_domain_name` | string | **Yes** (与 `trust_domain_id` 至少其一) | `--agency.trust_domain_name=<trusted-account-name>` |
| CreateAgency | `--agency.trust_domain_id` | string | Yes (与 `trust_domain_name` 至少其一) | `--agency.trust_domain_id=<trusted-account-id>` |
| CreateAgency | `--agency.description` / `--agency.duration` | string | No | `--agency.description="for cce"` |
| CreatePermanentAccessKey | `--credential.user_id` | string | **Yes** | `--credential.user_id=U-001` |
| CreatePermanentAccessKey | `--credential.description` | string | No | `--credential.description="prod key"` |
| CreatePolicyV5 | `--policy_name` | string | **Yes** | `--policy_name=read-vpc` |
| CreatePolicyV5 | `--policy_document` | string(JSON) | **Yes** | `--policy_document='{"Version":"5.0",...}'` |
| CreatePolicyV5 | `--description` | string | No | `--description="read vpc"` |

### Manage Attach/Detach (R2)

| Operation | Parameter | Type | Required |
| --------- | --------- | ---- | -------- |
| AttachUserPolicyV5 / DetachUserPolicyV5 | `--user_id` | string | **Yes** |
| AttachUserPolicyV5 / DetachUserPolicyV5 | `--policy_id` | string | **Yes** |
| AttachGroupPolicyV5 / DetachGroupPolicyV5 | `--group_id` | string | **Yes** |
| AttachGroupPolicyV5 / DetachGroupPolicyV5 | `--policy_id` | string | **Yes** |
| AttachAgencyPolicyV5 / DetachAgencyPolicyV5 | `--agency_id` | string | **Yes** |
| AttachAgencyPolicyV5 / DetachAgencyPolicyV5 | `--policy_id` | string | **Yes** |

### Manage Configure Login (R2)

| Operation | Parameter | Type | Required |
| --------- | --------- | ---- | -------- |
| UpdateUserV5 | `--user_id` | string | **Yes** |
| UpdateUserV5 | `--enabled` | bool | No |
| UpdateUserV5 | `--new_user_name` | string | No |
| CreateLoginProfileV5 | `--user_id` | string | **Yes** |
| CreateLoginProfileV5 | `--password` | string | **Yes (Sensitive)** |
| CreateLoginProfileV5 | `--password_reset_required` | bool | **Yes** |
| UpdateLoginProfileV5 | `--user_id` | string | **Yes** |
| UpdateLoginProfileV5 | `--password` | string | No (Sensitive) |
| UpdateLoginProfileV5 | `--password_reset_required` | bool | No |
| UpdateLoginProtect | `--user_id` | string | **Yes** |
| UpdateLoginProtect | `--login_protect.enabled` | bool | **Yes** |
| UpdateLoginProtect | `--login_protect.verification_method` | string | **Yes** |

> ⚠️ **`--password` disambiguation**: `CreateLoginProfileV5` / `UpdateLoginProfileV5` declare a body
> parameter named `password`, colliding with the KooCLI system parameter of the same name. When passed on
> the command line, KooCLI prompts "系统参数(a)/目标API参数(b)/兼为两者(c)" — answer `b`, or (preferred,
> non-interactive) pass the body+path via `--cli-jsonInput=<file>` as shown in Core Commands. Delete the
> jsonInput file immediately after the call.

### Manage Delete (R1)

| Operation | Parameter | Type | Required |
| --------- | --------- | ---- | -------- |
| DeleteUserV5 | `--user_id` | string | **Yes** |
| DeleteGroupV5 | `--group_id` | string | **Yes** |
| DeleteAgency | `--agency_id` | string | **Yes** |
| DeletePermanentAccessKey | `--access_key` | string | **Yes** |
| DeletePolicyV5 | `--policy_id` | string | **Yes** |

Common to all operations: `--cli-region` (required).

## Troubleshooting

Common errors and fixes are documented in `references/troubleshooting.md`.

## Security Considerations

- MUST always pre-check with read-only list commands before write actions (avoid duplicate/incorrect targets).
- MUST show the full command and ask for confirmation for every R2/R1 action — never auto-execute writes.
- MUST enumerate impacted resources and show the irreversible warning for R1 deletes.
- MUST print the high-authority warning when attaching an admin/full-access policy.
- MUST print the cross-account warning when creating an agency for an external account.
- MUST show the SK once only, never persist/log it; passwords are Sensitive and never echoed.
- MUST delete any temporary jsonInput file containing a password immediately after the login-profile call.
- MUST NOT modify system policies; only custom policies are manageable.
- SHOULD tie policies to **groups** and attach users to groups (coarse-grained) rather than attaching
  policies directly to many users.

## Quality Reporting

Quality telemetry is collected automatically via `skill-quality-cli` (see the **Dependency** note in
Overview): every `hcloud` command in this skill is wrapped with
`skill-quality-cli run --skill-name huawei-cloud-iam-manage -- ...`, which reports trace_id, status,
error code, cost, and masked input/output to the operations console. The CLI is ensured idempotently by
`scripts/ensure_cli.sh` (installs only if absent; no auto-upgrade — run `skill-quality-cli upgrade` to
update manually). Reporting is non-blocking, fails silently, and can be disabled for local testing by
setting `SKILL_QUALITY_REPORT=0`.

### Error Code Convention

| Prefix | Category | Examples |
|--------|----------|---------|
| U | User input | U01 missing param, U03 no data found |
| C | Configuration | C01 missing AK/SK/env, C02 hcloud not authenticated |
| N | Network | N01 timeout, N02 connection refused |
| B | Code bug | B01 null pointer, B04 version mismatch |
| P | Platform | P01 scheduler error, P02 resource insufficient |

## Reference Documents

- `references/cli-installation-guide.md` — hcloud CLI installation and AK/SK + profile authentication
- `references/iam-policies.md` — Least-privilege IAM policies required for each action
- `references/dataflow-diagram.md` — Mermaid data flow diagram
- `references/verification-method.md` — Verification method and acceptance checks
- `references/acceptance-criteria.md` — Acceptance criteria for the 20 huawei_* actions
- `references/troubleshooting.md` — Common errors and fixes
- IAM API reference: https://support.huaweicloud.com/api-iam/iam_18_0001.html
- API Explorer: https://console.huaweicloud.com/apiexplorer/#/openapi/IAM/doc
