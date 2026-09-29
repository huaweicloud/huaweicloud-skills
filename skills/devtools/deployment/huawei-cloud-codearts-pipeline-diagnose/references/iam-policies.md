# IAM Policies for Huawei Cloud CodeArts Pipeline & Build

Least-privilege IAM policies for the operations performed by this skill
(`huawei-cloud-codearts-pipeline-diagnose`).

## Pre-defined System Policies (recommended)

Huawei Cloud IAM provides pre-defined system policies for CodeArts:

| Domain | Read-only (Query/Analyze) | Full (Query/Analyze + Manage) |
|--------|---------------------------|-------------------------------|
| CodeArts Pipeline (流水线) | `CodeArts Pipeline ReadOnlyAccess` | `CodeArts Pipeline FullAccess` |
| CodeArts Build (编译构建) | `CodeArts Build ReadOnlyAccess` | `CodeArts Build FullAccess` |

The simplest setup for this skill:

- **Query/Analyze only (R3)** — assign both ReadOnly roles:
  `CodeArts Pipeline ReadOnlyAccess` + `CodeArts Build ReadOnlyAccess`.
- **Full usage (R3 + R2/R1 manage)** — assign both Full roles:
  `CodeArts Pipeline FullAccess` + `CodeArts Build FullAccess`.

> Verify the exact role names in your IAM console (统一身份认证 → 用户组 → 授权 →
> 系统策略) — the display names may vary with console language. Do not guess
> action names: if you need a custom policy, obtain the exact granular actions
> from the IAM console's authorization schema (GetAuthorizationSchemaV5) or the
> official 权限及授权项说明 documentation.

## Query & Analyze (R3 — read-only)

Least privilege for query/analyze actions
(`huawei_list_pipelines`, `huawei_list_build_tasks`, `huawei_get_pipeline`,
`huawei_get_build_task`, `huawei_get_build_log`,
`huawei_diagnose_build_failure`, `huawei_diagnose_pipeline_failure`,
`huawei_extract_build_log_errors`):

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "codeartspipeline:pipeline:list",
        "codeartspipeline:pipeline:get",
        "codeartspipeline:run:list",
        "codeartspipeline:run:get",
        "codeartspipeline:log:get",
        "codeartsbuild:job:list",
        "codeartsbuild:job:get",
        "codeartsbuild:record:get",
        "codeartsbuild:log:get"
      ],
      "Resource": ["*"]
    }
  ]
}
```

> **Note:** The granular `codeartspipeline:*` / `codeartsbuild:*` action names
> above follow the IAM permission model shown in the IAM console's permission
> explorer for these services (`service:resource:action` naming). If action
> names differ in your environment (KooCLI upgrade, console version, or service
> rebranding), the pre-defined system roles `CodeArts Pipeline ReadOnlyAccess` +
> `CodeArts Build ReadOnlyAccess` grant equivalent read-only access and are the
> safest choice — prefer them over a hand-written custom policy.

## Manage (R2/R1 — write)

For create/start/delete actions (`huawei_create_pipeline`,
`huawei_create_build_task`, `huawei_start_pipeline`, `huawei_start_build_task`,
`huawei_delete_pipeline`, `huawei_delete_build_task`), add write permissions.
The pre-defined **`CodeArts Pipeline FullAccess`** + **`CodeArts Build
FullAccess`** roles are the simplest option; the least-privilege alternative is:

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "codeartspipeline:pipeline:create",
        "codeartspipeline:pipeline:update",
        "codeartspipeline:pipeline:delete",
        "codeartspipeline:pipeline:trigger",
        "codeartspipeline:run:start",
        "codeartspipeline:run:stop",
        "codeartspipeline:run:retry",
        "codeartspipeline:template:get",
        "codeartsbuild:job:create",
        "codeartsbuild:job:update",
        "codeartsbuild:job:delete",
        "codeartsbuild:job:start",
        "codeartsbuild:job:stop",
        "codeartsbuild:job:list",
        "codeartsbuild:job:get",
        "codeartsbuild:record:get",
        "codeartsbuild:log:get"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## Related Permissions for Prerequisites

| Prerequisite | Required Permission |
|--------------|--------------------|
| CodeArts project access | The IAM user must be a member of the CodeArts project (project member role) — project membership is managed in the CodeArts console, not IAM alone |
| Code source repository (CodeHub) | `codeartspipeline`/`codeartsbuild` tasks pull source from CodeHub/GitHub — the service account needs read access to the repository (repo membership or deploy key) |
| Build artifact storage (OBS/SWR) | If builds push artifacts to OBS or SWR, the corresponding `obs:object:PutObject` / SWR push permission is needed on the target bucket/repository |

## Security Notes

- **Never hardcode AK/SK** in scripts, commands, or documents. Credentials come
  from `hcloud configure` profile or the `HUAWEICLOUD_SDK_AK` /
  `HUAWEICLOUD_SDK_SK` (or `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`)
  environment variables.
- Mask any AK/SK-like values in command output before reporting results.
- Build/pipeline parameters that hold secrets must be stored encrypted (build
  parameter `type=encrypt`); never ship plaintext credentials in pipeline
  `--definition` JSON or build step properties.
- Delete and start operations require explicit user confirmation (R1/R2).