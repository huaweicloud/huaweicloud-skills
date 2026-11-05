# IAM Policies for FunctionGraph Trigger Management

## Overview

This document specifies the IAM (Identity and Access Management) permissions required to create
and verify FunctionGraph TIMER and OBS triggers, and records exactly which statements were
verified against official sources and which were not.

## Verified Authorization Items

The FunctionGraph API reference publishes the authorization item (IAM action) behind each API.
Every action named in this section was copied from that page; nothing here is inferred.

- Source: [权限及授权项说明 — Permissions and authorization items](https://support.huaweicloud.com/api-functiongraph/functiongraph_06_1100.html), FunctionGraph API Reference (page updated 2025-05-28), fetched 2026-11-03.
- Source: [创建触发器 CreateFunctionTrigger](https://support.huaweicloud.com/api-functiongraph/functiongraph_06_0122.html) (updated 2026-10-21), whose "授权信息" section refers to the permission page above.

Rows relevant to this skill, quoted as published (the page renders the service prefix as
`FunctionGraph:`):

| Permission | API | Authorization item |
|------------|-----|--------------------|
| 创建触发器 | `POST /v2/{project_id}/fgs/triggers/{function_urn}` | `FunctionGraph:trigger:create` |
| 获取指定触发器的信息 | `GET /v2/{project_id}/fgs/triggers/{function_urn}/{trigger_type_code}/{trigger_id}` | `FunctionGraph:trigger:get` |
| 获取指定函数的所有触发器 | `GET /v2/{project_id}/fgs/triggers/{function_urn}` | `FunctionGraph:trigger: listSpecifiedFunctionTriggers` |
| 删除触发器 | `DELETE /v2/{project_id}/fgs/triggers/{function_urn}/{trigger_type_code}/{trigger_id}` | `FunctionGraph:trigger:delete` |
| 删除指定函数的所有触发器 | `DELETE /v2/{project_id}/fgs/triggers/{function_urn}` | `FunctionGraph:trigger: deleteSpecifiedFunctionTriggers` |
| 获取函数列表 | `GET /v2/{project_id}/fgs/functions` | `FunctionGraph:function:list` |
| 获取函数的metadata | `GET /v2/{project_id}/fgs/functions/{function_urn}/config` | `FunctionGraph:function:getConfig` |

The two spaces shown after `trigger:` in the "list"/"delete all" rows are present on the published
page; they are reproduced here rather than silently corrected.

The JSON policy examples below use the lowercase `functiongraph:` service namespace that this
document already used. The published page renders the same items with a capitalised
`FunctionGraph:`. This document does not assert case sensitivity in either direction — validate
the policy with IAM before production use.

### Corrections to earlier revisions of this document

- `functiongraph:function:get` was listed as required for the existence pre-check. The skill's
  pre-check calls `ShowFunctionConfig` (`GET .../fgs/functions/{function_urn}/config`), whose
  published authorization item is `FunctionGraph:function:getConfig`. The pre-check policy now
  uses `functiongraph:function:getConfig`.
- `functiongraph:trigger:list` was listed as required for verification. Listing a function's
  triggers (`GET .../fgs/triggers/{function_urn}`) is published as
  `FunctionGraph:trigger: listSpecifiedFunctionTriggers`.
- If you want to keep the old names in an existing policy as well, that is harmless, but they are
  not the actions the published table associates with these APIs.

## Required Permissions

### Minimum Policy for Trigger Creation

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "functiongraph:function:getConfig",
                "functiongraph:trigger:create",
                "functiongraph:trigger:get",
                "functiongraph:trigger:listSpecifiedFunctionTriggers"
            ],
            "Resource": [
                "urn:fss:*:*:function:*"
            ]
        }
    ]
}
```

Each action covers one API the skill can call:

| Action | API the skill calls | When |
|--------|---------------------|------|
| `functiongraph:function:getConfig` | `ShowFunctionConfig` | Existence pre-check before creating anything |
| `functiongraph:trigger:create` | `CreateFunctionTrigger` | The creation call itself |
| `functiongraph:trigger:get` | `ShowFunctionTrigger` | Verifying one trigger |
| `functiongraph:trigger:listSpecifiedFunctionTriggers` | `ListFunctionTriggers` | Verifying via the trigger list |

### Full Trigger Management Policy

For the complete trigger lifecycle (including the cleanup steps that this skill itself does not
perform), use this policy:

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "functiongraph:function:getConfig",
                "functiongraph:function:list",
                "functiongraph:trigger:create",
                "functiongraph:trigger:get",
                "functiongraph:trigger:listSpecifiedFunctionTriggers",
                "functiongraph:trigger:update",
                "functiongraph:trigger:delete",
                "functiongraph:trigger:deleteSpecifiedFunctionTriggers"
            ],
            "Resource": [
                "urn:fss:*:*:function:*"
            ]
        }
    ]
}
```

`functiongraph:trigger:update` is included because it is needed to enable or disable a trigger
through the API. It is **not** listed in the published authorization-item table fetched for this
document, so treat it as unverified; the other seven actions in this policy are verified above.

## Permission Actions Reference

| Action used here | Published authorization item | Description | Required for |
|------------------|------------------------------|-------------|--------------|
| `functiongraph:function:getConfig` | `FunctionGraph:function:getConfig` | Query function metadata | Existence pre-check |
| `functiongraph:function:list` | `FunctionGraph:function:list` | List all functions | Function discovery |
| `functiongraph:trigger:create` | `FunctionGraph:trigger:create` | Create trigger | **Core operation** |
| `functiongraph:trigger:get` | `FunctionGraph:trigger:get` | Query one trigger | Verification |
| `functiongraph:trigger:listSpecifiedFunctionTriggers` | `FunctionGraph:trigger: listSpecifiedFunctionTriggers` | List a function's triggers | Verification |
| `functiongraph:trigger:delete` | `FunctionGraph:trigger:delete` | Delete one trigger | Cleanup |
| `functiongraph:trigger:deleteSpecifiedFunctionTriggers` | `FunctionGraph:trigger: deleteSpecifiedFunctionTriggers` | Delete all triggers of a function | Cleanup |
| `functiongraph:trigger:update` | not listed in the fetched table | Update trigger | Enable/disable |
| `functiongraph:function:get` | not listed in the fetched table | Query function details | Not required (see corrections) |
| `functiongraph:trigger:list` | not listed in the fetched table | List triggers | Not required (see corrections) |

## OBS Event Triggers: Additional Permissions (NOT VERIFIED)

An OBS trigger is registered as an event notification on the OBS bucket. Whether that step
requires permissions **on the OBS side** (an `obs:*` action on the bucket) in addition to
`FunctionGraph:trigger:create` could not be verified from any source reachable in this
environment. Therefore:

- **No `obs:*` action name is stated anywhere in this document.** Naming one would be invention.
- What *is* verified: the published FunctionGraph authorization-item table associates trigger
  creation (`POST /v2/{project_id}/fgs/triggers/{function_urn}`) only with
  `FunctionGraph:trigger:create`; it does not list any OBS-side action for that API.
- What was checked and did not yield an answer: the FunctionGraph API reference (permissions
  page above and the CreateFunctionTrigger page), the KooCLI 7.2.12 `CreateFunctionTrigger`
  help output, and the official OBS and FunctionGraph documentation indexes. The
  `usermanual-functiongraph` and `productdesc-functiongraph` pages cited by earlier revisions of
  this repository returned HTTP 404, and the general web search available here did not return
  usable Huawei documentation.

**Action required before production use:** confirm with the IAM policy simulator / console
whether creating an OBS event trigger needs bucket-level OBS permissions for your principal. If
it does, add exactly the actions shown by IAM for that operation rather than guessing an action
name.

## Policy Assignment Methods

### Method 1: Through Console

1. Navigate to **IAM Console** → **Policies**
2. Click **Create Custom Policy**
3. Select **JSON** view
4. Paste the policy JSON
5. Click **OK** to create
6. Attach policy to user/group/role

### Method 2: Using KooCLI

Create the identity policy with `IAM CreatePolicyV5` (KooCLI 7.2.12: `--policy_name` and
`--policy_document` are both required; the document uses the v5 grammar whose version block is
`"Version": "5.0"`):

```bash
hcloud IAM CreatePolicyV5 \
    --cli-region=cn-north-4 \
    --policy_name "FunctionGraphTriggerManager" \
    --description "Policy for managing FunctionGraph TIMER and OBS triggers" \
    --policy_document '{
        "Version": "5.0",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "functiongraph:function:getConfig",
                    "functiongraph:trigger:create",
                    "functiongraph:trigger:get",
                    "functiongraph:trigger:listSpecifiedFunctionTriggers"
                ],
                "Resource": ["urn:fss:*:*:function:*"]
            }
        ]
    }'
```

The JSON policy examples elsewhere in this document use the classic policy format
(`"Version": "1.1"`), which is what the IAM console and the custom-policy v3 APIs expect. Convert
the version block when you move a policy between the console and `CreatePolicyV5`.

### Method 3: Assign to User

Attach the policy to the IAM user or user group in the console:

1. Navigate to **IAM Console** → **Users** (or **User Groups**)
2. Select the user or group
3. Choose **Authorize** → select the custom policy → **OK**

The IAM CLI operation that performs this attachment was not verified for this document, so no
command is shown here. Confirm the operation name and flags with
`hcloud IAM <Operation> --help` before scripting it.

## Resource Scoping

### All Functions in All Regions

```json
"Resource": ["urn:fss:*:*:function:*"]
```

### Specific Region

```json
"Resource": ["urn:fss:cn-north-4:*:function:*"]
```

### Specific Function

```json
"Resource": [
    "urn:fss:cn-north-4:project-id:function:default:my-function:*"
]
```

### Multiple Specific Functions

```json
"Resource": [
    "urn:fss:cn-north-4:project-id:function:default:backup-function:*",
    "urn:fss:cn-north-4:project-id:function:default:cleanup-function:*"
]
```

## Condition Keys

Use conditions to further restrict access:

### Time-based Restriction

```json
{
    "Effect": "Allow",
    "Action": ["functiongraph:trigger:create"],
    "Resource": ["*"],
    "Condition": {
        "DateLessThan": {
            "g:CurrentTime": "2024-12-31T23:59:59Z"
        }
    }
}
```

### Source IP Restriction

```json
{
    "Effect": "Allow",
    "Action": ["functiongraph:trigger:create"],
    "Resource": ["*"],
    "Condition": {
        "IpAddress": {
            "g:SourceIp": ["192.168.1.0/24", "10.0.0.0/8"]
        }
    }
}
```

## Role-Based Access Control (RBAC)

### Built-in Roles

| Role | Description | Includes Trigger Permissions |
|------|-------------|----------------------------|
| `Tenant Administrator` | Full access | Yes |
| `FunctionGraph Administrator` | FunctionGraph full access | Yes |
| `FunctionGraph Developer` | Create/manage functions | Yes |
| `FunctionGraph Viewer` | Read-only access | No (view only) |

The role names and their descriptions are reproduced from the FunctionGraph console; they were
not cross-checked against the official authorization-item page in this revision. Confirm the
exact role name in the IAM console before referencing it in automation. The verified, per-API
authorization items are listed under
[Verified Authorization Items](#verified-authorization-items).

### Custom Role for Automation

For CI/CD pipelines and automation:

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "functiongraph:function:getConfig",
                "functiongraph:trigger:create",
                "functiongraph:trigger:listSpecifiedFunctionTriggers"
            ],
            "Resource": ["urn:fss:*:*:function:*"]
        }
    ]
}
```

## Verifying Permissions

### Check User Permissions

```bash
# List the system policies and roles visible to the account (KooCLI 7.2.12 flags)
hcloud IAM KeystoneListPermissions --cli-region=cn-north-4 --display_name "FunctionGraph"

# List all custom policies of the account
hcloud IAM KeystoneListPermissions --cli-region=cn-north-4 --domain_id "your_domain_id"

# Probe the FunctionGraph trigger APIs directly (needs functiongraph:trigger:get /
# functiongraph:trigger:listSpecifiedFunctionTriggers)
hcloud FunctionGraph ListFunctionTriggers \
    --cli-region=cn-north-4 \
    --function_urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest"
```

`hcloud IAM CreatePolicyV5`, `hcloud IAM KeystoneListPermissions`,
`hcloud FunctionGraph ListFunctionTriggers` and `hcloud FunctionGraph ShowFunctionTrigger` were
verified against the KooCLI 7.2.12 `--help` output for this document.

### Permission Testing Script

```python
import os
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkfunctiongraph.v2 import FunctionGraphClient
from huaweicloudsdkfunctiongraph.v2.region.functiongraph_region import FunctionGraphRegion
from huaweicloudsdkfunctiongraph.v2.model.list_functions_request import ListFunctionsRequest

def test_permission():
    credentials = BasicCredentials(
        ak=os.environ.get('HUAWEI_AK'),
        sk=os.environ.get('HUAWEI_SK'),
        project_id=os.environ.get('HUAWEI_PROJECT_ID')
    )

    # Correct form: with_region() takes a FunctionGraphRegion object, never a bare region string.
    client = FunctionGraphClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(FunctionGraphRegion.value_of(os.environ.get('HUAWEI_REGION'))) \
        .build()

    try:
        # Test list functions (requires functiongraph:function:list).
        # SDK methods take a request object, not keyword arguments.
        request = ListFunctionsRequest()
        response = client.list_functions(request)
        print("Has function list permission")

        # Additional tests can be added here

    except Exception as e:
        print(f"Permission denied: {e}")

test_permission()
```

**Already correct, no change needed:** the `with_region(...)` call in this permission-testing
snippet already uses the object form
`.with_region(FunctionGraphRegion.value_of(os.environ.get('HUAWEI_REGION')))` and imports
`FunctionGraphRegion`, so it was not affected by the bug fixed in
[SDK Installation Guide](./sdk-installation-guide.md). The `list_functions` call in this snippet
was corrected to pass a `ListFunctionsRequest`; the SDK client methods take a request object and
do not accept keyword arguments such as `limit=1`.

## Permission Troubleshooting

### Error: 403 Forbidden

**Cause**: Missing required IAM permission

**Solution**:

1. Check if `functiongraph:trigger:create` is in policy
2. Verify policy is attached to user/role
3. Check resource scope matches target function
4. For OBS triggers, see
   [OBS Event Triggers: Additional Permissions (NOT VERIFIED)](#obs-event-triggers-additional-permissions-not-verified)

### Error: Unauthorized

**Cause**: Invalid or expired credentials

**Solution**:

1. Verify AK/SK are correct
2. Check if credentials have been rotated
3. Re-configure KooCLI authentication

## Security Best Practices

1. **Principle of Least Privilege**: Grant only required permissions
2. **Use Resource Restrictions**: Limit to specific functions/regions
3. **Add Conditions**: Restrict by IP, time, or MFA
4. **Separate Environments**: Use different policies for dev/prod
5. **Regular Audits**: Review and remove unused permissions
6. **Temporary Credentials**: Use STS for short-lived access

## Policy Examples by Use Case

### Development Environment

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "functiongraph:*"
            ],
            "Resource": ["urn:fss:cn-north-4:*:function:dev-*:*"]
        }
    ]
}
```

### Production Environment (Restricted)

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "functiongraph:function:getConfig",
                "functiongraph:trigger:get",
                "functiongraph:trigger:listSpecifiedFunctionTriggers"
            ],
            "Resource": ["urn:fss:cn-north-4:*:function:prod-*:*"]
        }
    ]
}
```

### CI/CD Pipeline

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "functiongraph:function:getConfig",
                "functiongraph:trigger:create",
                "functiongraph:trigger:update",
                "functiongraph:trigger:delete"
            ],
            "Resource": ["urn:fss:*:*:function:*"],
            "Condition": {
                "StringEquals": {
                    "g:UserName": "cicd-service-account"
                }
            }
        }
    ]
}
```

`functiongraph:trigger:update` in this example is the unverified action noted above; the other
three are verified.

## Related Documentation

- [FunctionGraph Permissions and Authorization Items](https://support.huaweicloud.com/api-functiongraph/functiongraph_06_1100.html) — verified source for the authorization items above (fetched 2026-11-03)
- [CreateFunctionTrigger API](https://support.huaweicloud.com/api-functiongraph/functiongraph_06_0122.html) — verified (fetched 2026-11-03)
- [ShowFunctionTrigger API](https://support.huaweicloud.com/api-functiongraph/functiongraph_06_0120.html) — verified (fetched 2026-11-03)
- [OBS Event Trigger Guide](./obs-trigger-guide.md)
- [Verification Method](./verification-method.md)
