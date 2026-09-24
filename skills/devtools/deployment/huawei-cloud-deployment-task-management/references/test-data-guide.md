# Test Data Guide for huawei-cloud-deployment-task-management

How to supply real test data for automated / live verification of this skill.

## Why command examples use placeholders

For security (skill audit rule Q002-project-id-hardcode), this skill never embeds
a real 32-hex project ID / task ID / access key in code or templates. All command
examples use `{placeholders}` that must be replaced with concrete values belonging
to the scanned tenant before any **live** (non `--help`) execution.

The automated test pipeline only backfills a fixed whitelist (`region`,
`cli_region`, `id`, `instance_id`, `server_id`, `vpc_id`, `subnet_id`,
`flavor_id`, `image_id`). Business placeholders such as `{project_id}`,
`{task_id}`, `{app_name}`, `{template_id}`, `{artifact_bucket}` and
`{artifact_object_path}` are intentionally left for the executing environment to
fill in before live runs.

## Placeholders and how to fill them

| Placeholder | Meaning | How to obtain |
| ----------- | ------- | ------------- |
| `{region}` | Region, e.g. `cn-north-4` | `hcloud configure list` |
| `{project_id}` | IAM (CodeArts) project ID | `hcloud IAM KeystoneShowProject` or the test account project page |
| `{task_id}` | Deployment task ID | `hcloud CodeArtsDeploy ListDeployTasks --project_id={project_id}` |
| `{app_name}` | Application (app) name | `hcloud CodeArtsDeploy ListAllApp --project_id={project_id}` |
| `{template_id}` | Template ID for `CreateDeployTaskByTemplate` | No CLI list operation exists for deploy templates (`CodeArtsDeploy` has no `ShowTemplate`/`ListTemplates`) — copy the template ID from the **CodeArts Deploy console 模板库** when creating an app from a template, or from the template's page URL |
| `{artifact_bucket}` / `{artifact_object_path}` | OBS object referenced by the task artifact | Task detail artifact config (`ShowDeployTaskDetail`) |

## Backfilling before automated runs

`templates/test-defaults.json` exposes `request_defaults` (currently
`{project_id}` / `{domain_id}` placeholders). For live write-path coverage, a test
runner must set these to the scan tenant's real values **in its own test
environment** (do not commit real IDs):

```json
{
  "request_defaults": {
    "project_id": "<real-32-hex>",
    "domain_id": "<real-32-hex>"
  }
}
```

Modifying `templates/test-defaults.json` or `templates/test-vars.json` inside this
skill directory with real IDs would re-trigger the Q002 security rule, so real
values are supplied only by the executing test harness / environment overrides,
never committed to the repo.

## Service-name trap (expected behavior, not a defect)

`hcloud CloudDeploy ...` legitimately fails with
`[USE_ERROR]不支持的服务名称:CloudDeploy` because CodeArts Deploy is served by
KooCLI as `CodeArtsDeploy`. An automated harness must treat that "correct
rejection" as a **pass** (same semantics as the negative test `hcloud CloudDeploy
must fail`), not as a functional failure.

## OBS artifact check

`huawei_analyze_clouddeploy_artifact` uses `hcloud obs ...` (obsutil passthrough).
Before the first check on a machine, configure once and self-check:

```bash
# Interactive configuration (recommended) — AK/SK are typed at the terminal, never
# entered as command-line arguments, so they stay out of shell history / ps output:
hcloud obs config -interactive
# Non-interactive equivalent (CI only) — note the plaintext AK/SK in argv is a
# credential-leak vector (shell history / ps aux); prefer -interactive or env vars:
# hcloud obs config -i={access_key} -k={secret_key} -e=https://obs.{region}.myhuaweicloud.com
hcloud obs ls obs://{artifact_bucket}
```

If `hcloud obs ls obs://{artifact_bucket}` prints
`Warn: Please set ak, sk and endpoint in the configuration file!`, obsutil is not
configured yet (environment dependency) - run the config + `hcloud obs ls obs://{artifact_bucket}` above.
