# IAM Policies for Huawei Cloud CloudDeploy

Least-privilege IAM policies for the operations performed by this skill (`huawei-cloud-deployment-task-management`).
CloudDeploy (CodeArts Deploy) permissions are granted through the IAM service; the pre-defined
system roles are `CodeArts Deploy ReadOnlyAccess` and `CodeArts Deploy FullAccess`. The JSON below
mirrors the read/write action set those roles cover, for custom-policy use.

## Query & Analyze (R3 — read-only)

Least privilege for query/analyze actions (`huawei_list_clouddeploy_apps`,
`huawei_list_clouddeploy_tasks`, `huawei_get_clouddeploy_task`,
`huawei_analyze_clouddeploy_failure`, `huawei_analyze_clouddeploy_artifact`):

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "codeartsdeploy:app:list",
        "codeartsdeploy:task:list",
        "codeartsdeploy:task:get",
        "codeartsdeploy:history:list",
        "codeartsdeploy:host:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```

> **Note:** The exact action names follow the IAM permission model shown on the IAM console for
> CodeArts Deploy (`codeartsdeploy:*` granular actions). If action names differ in your environment,
> the pre-defined system role **`CodeArts Deploy ReadOnlyAccess`** grants equivalent read-only access
> and is the simplest choice. `huawei_analyze_clouddeploy_artifact` additionally needs read access to
> the OBS bucket holding artifacts (`obs:object:GetObject` on the target bucket).

## Manage (R2/R1 — write)

For create/start/delete actions (`huawei_create_clouddeploy_app`, `huawei_create_clouddeploy_task`,
`huawei_start_clouddeploy_task`, `huawei_delete_clouddeploy_task`), add write permissions. The
pre-defined **`CodeArts Deploy FullAccess`** role is the simplest option; the least-privilege
alternative is:

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "codeartsdeploy:app:create",
        "codeartsdeploy:app:update",
        "codeartsdeploy:app:delete",
        "codeartsdeploy:task:create",
        "codeartsdeploy:task:update",
        "codeartsdeploy:task:delete",
        "codeartsdeploy:task:start",
        "codeartsdeploy:task:list",
        "codeartsdeploy:task:get",
        "codeartsdeploy:app:list",
        "codeartsdeploy:history:list",
        "codeartsdeploy:host:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## Related Permissions for Prerequisites

| Prerequisite | Required Permission |
|--------------|--------------------|
| OBS bucket/object for artifacts (default artifact source) | `obs:bucket:ListAllMyBuckets`, `obs:object:GetObject` on the target bucket/object |
| Target hosts (ECS/BMS/CCI) | Host must be registered in the deployment group; the CloudDeploy agent runs on the host, no extra IAM permission for read operations |
| CodeArts project | The project must be enabled as a CodeArts (DevCloud) project in the region |

## Security Notes

- **Never hardcode AK/SK** in scripts, commands, or documents. Credentials come from
  `hcloud configure` profile or the `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK`
  (or `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`) environment variables.
- Mask any AK/SK-like values in command output before reporting results.
- Use `--params.N.type=encrypt` (task parameters) for secrets; never ship plaintext credentials in
  deployment scripts or task parameter values.
- Delete and start operations require explicit user confirmation (R1/R2).