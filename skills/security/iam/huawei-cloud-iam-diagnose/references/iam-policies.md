# IAM Policies Required by This Skill

This skill is **read-only**. The AK/SK or hcloud profile used to run it needs read access to the
IAM service. Below are the least-privilege guidelines.

## 1. Least privilege — preset read-only roles

For most chain-expansion steps only read access is required:

- `IAMReadOnlyAccess` (preset) covers the majority of the same-domain listing endpoints this skill
  uses (users, groups, attached policies, agencies).

## 2. Interfaces that also need admin/view permission

The following interfaces are used and, depending on account policy, may additionally require the
caller to be an IAM administrator (or hold equivalent role):

| Interface | Purpose | When used |
|---|---|---|
| `keystone_list_domain_permissions_for_group` | group domain-scoped roles | diagnose / trace, group chain |
| `keystone_list_all_project_permissions_for_group` | group all-projects roles | diagnose / trace, group chain |
| `keystone_check_project/domain_permission_for_group`, `keystone_check_role_for_group` | real group check | check_group_permission |
| `list_domain_permissions_for_agency`, `list_all_projects_permissions_for_agency` | agency roles | diagnose / trace, agency chain |
| `check_project/domain/all_projects_permission_for_agency` | real agency check | check_agency_permission |
| `keystone_show_permission`, `show_custom_policy` | role policy doc | policy document parsing |
| `get_policy_version_v5` | v5 identity policy doc | policy document parsing |

If the running credential lacks one of these, the affected step reports `HTTP 403` and the script
continues with the rest of the chain — the output stays transparent about what could/could not be
read.

## 3. Custom policy example (if you must build one)

When a minimal custom policy is required on a sub-account, a rough shape follows:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:users:getUser",
        "iam:users:listUsersForGroup",
        "iam:groups:listGroups",
        "iam:groups:listRolesOnGroup",
        "iam:agencies:listAgencies",
        "iam:roles:getRole",
        "iam:roles:listRoles"
      ]
    }
  ]
}
```

> Grant the minimum that matches your environment. Do not grant `iam:*` unless strictly required,
> and never attach write actions (`create*`, `delete*`, `update*`, `associate*`, `detach*`) to a
> read-only diagnosis persona.

## 4. Notes

- This skill never writes, creates, or modifies anything; the policies above reflect *reading*
  IAM structure only.
- Keep AK/SK out of chat output. The scripts read credentials from environment variables or
  `~/.hcloud/config.json`.