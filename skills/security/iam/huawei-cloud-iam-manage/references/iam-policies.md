# IAM Policies — Least Privilege for huawei-cloud-iam-manage

This skill manages Huawei Cloud IAM identity configuration. IAM is a **global/account-level** service
managed at the domain (account) level, so IAM permissions are granted to the **calling principal**
(the account administrator or an IAM user/agency that itself holds IAM-admin grants). The permission
action names follow the `iam:...` convention (service prefix `iam`).

Grant the **minimum** permission set per capability group to the calling principal.

## 1. Query (R3, read-only)

Covers: `huawei_list_iam_users`, `huawei_list_iam_groups`, `huawei_list_iam_policies`,
`huawei_list_iam_agencies`, `huawei_list_iam_custom_policies`.

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:users:listUsers",
        "iam:users:getUser",
        "iam:groups:listGroups",
        "iam:groups:getGroup",
        "iam:permissions:listPolicies",
        "iam:permissions:getPolicy",
        "iam:agencies:listAgencies",
        "iam:agencies:getAgency",
        "iam:credentials:listAccessKeys"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## 2. Diagnose / Analyze (R3, read-only)

Covers: `huawei_analyze_iam_least_privilege`, `huawei_analyze_iam_password_compliance`.

Needs everything in section 1 plus the ability to read attached policies and MFA device state:

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:permissions:listPoliciesForUser",
        "iam:permissions:listPoliciesForGroup",
        "iam:users:listUserMfaDevices",
        "iam:organizations:getAccountSummary",
        "iam:users:getPasswordPolicy"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## 3. Manage — Create / Configure (R2)

Covers: `huawei_create_iam_user`, `huawei_create_iam_group`, `huawei_create_iam_agency`,
`huawei_create_iam_ak_sk`, `huawei_create_iam_custom_policy`, `huawei_attach_iam_policy`,
`huawei_detach_iam_policy`, `huawei_config_iam_login`.

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:users:createUser",
        "iam:users:updateUser",
        "iam:groups:createGroup",
        "iam:groups:updateGroup",
        "iam:agencies:createAgency",
        "iam:agencies:updateAgency",
        "iam:credentials:createAccessKey",
        "iam:permissions:grantRoleToUserOnProject",
        "iam:permissions:revokeRoleFromUserOnProject",
        "iam:permissions:grantRoleToGroupOnProject",
        "iam:permissions:revokeRoleFromGroupOnProject",
        "iam:permissions:createPolicy",
        "iam:permissions:updatePolicy",
        "iam:permissions:attachPolicy",
        "iam:permissions:detachPolicy",
        "iam:users:updateUserLoginProtect",
        "iam:users:createUserLoginProfile",
        "iam:users:updateUserPassword"
      ],
      "Resource": ["*"]
    }
  ]
}
```

> **Caution**: granting any of the above to an IAM user makes them an IAM administrator for the domain.
> In practice the account administrator (root) or a dedicated "iam-administrators" group holds these.
> For a managed IAM user, prefer granting the managed role `IAMFullAccess` / `Security Administrator`
> for production use, or scope `Resource` to specific users/policies.

## 4. Manage — Delete (R1)

Covers: `huawei_delete_iam_user`, `huawei_delete_iam_group`, `huawei_delete_iam_agency`,
`huawei_delete_iam_ak_sk`, `huawei_delete_iam_custom_policy`.

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:users:deleteUser",
        "iam:groups:deleteGroup",
        "iam:agencies:deleteAgency",
        "iam:credentials:deleteAccessKey",
        "iam:permissions:deletePolicy"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## 5. Managed system roles shortcut

Instead of custom policies, the caller may be granted one of these managed (predefined) roles:

| Role | Effective grants |
| ---- | ---------------- |
| `IAMFullAccess` (系统策略) | Full IAM management incl. users/groups/policies/agencies/AK-SK/login configuration |
| `Security Administrator` (系统策略) | IAM policies/roles management (attach/detach), agency management |
| `IAMReadOnlyAccess` (系统策略) | All IAM read/list queries (section 1) |

Using a **custom** policy scoped from sections 1-4 is the least-privilege profile; using the managed
roles is the pragmatic alternative.

> **Never use `AdministratorAccess`** for this skill's calling principal just to enable IAM management —
> instead grant `IAMFullAccess` (+ credentials permissions) or the scoped custom policies above.