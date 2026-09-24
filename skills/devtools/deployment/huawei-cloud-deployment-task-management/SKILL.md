---
name: huawei-cloud-deployment-task-management
description: |
  Huawei Cloud CloudDeploy (CodeArts Deploy / 部署) management, execution, and failure analysis
  using the KooCLI hcloud command-line client. Covers deploy application listing and creation,
  deployment task listing/detail/creation, task start, task deletion, deployment failure
  root-cause analysis (agent offline, timeout, missing artifact, permission), and OBS artifact
  link verification. Query and Analyze actions run automatically (R3); Create/Start actions
  require preview and user confirmation (R2); Delete requires explicit confirmation (R1).
  Supports AK/SK credentials and local hcloud profile authentication.
  Triggers include: "CloudDeploy", "CodeArts Deploy", "部署", "deploy task", "deployment",
  "deployment task", "deploy application", "部署任务", "部署应用", "start deploy", "发布部署",
  "release", "artifact deployment", "制品部署", "deploy failure", "部署失败",
  "pipeline deployment", "CI/CD deployment".
triggers:
  - "CloudDeploy"
  - "CodeArts Deploy"
  - "部署"
  - "deploy task"
  - "deployment"
  - "deployment task"
  - "deploy application"
  - "部署任务"
  - "部署应用"
  - "start deploy"
  - "发布部署"
  - "release"
  - "artifact deployment"
  - "制品部署"
  - "deploy failure"
  - "部署失败"
  - "pipeline deployment"
  - "CI/CD deployment"
tags: [huawei-cloud, clouddeploy, codearts, deployment, devops]
---

# Huawei Cloud CloudDeploy (CodeArts Deploy)

<!-- cli-install-version: 3.9.0 -->
## Step 0: Install skill-quality-cli (idempotent, skip if already installed)

The CLI installs into `~/.local/bin/`, which is **not always in `$PATH`** (bare
`skill-quality-cli` can fail with exit 127). Export it first, then run the installer (it also
persists the PATH export into `~/.bashrc` / `~/.profile` for future shells):

```bash
export PATH="$HOME/.local/bin:$PATH"
bash scripts/ensure_cli.sh
```

> The script installs the bundled `scripts/cli/` sources to `~/.local/bin/` when
> `skill-quality-cli` is not found (offline, no external download), re-exports PATH for the
> current session and persists it into `~/.bashrc` / `~/.profile`; it never blocks. If still
> not found, call the absolute path: `~/.local/bin/skill-quality-cli`.

## Overview

This skill operates Huawei Cloud CloudDeploy (CodeArts Deploy / 部署) through the `hcloud` CLI.
CloudDeploy automates application deployment to ECS/BMS/CCI/Kubernetes and other targets, pulling
artifacts (default source: OBS) and running deployment tasks created from templates. The skill covers:

| Category | Capabilities |
|----------|--------------|
| **Query** | List deploy applications (`huawei_list_clouddeploy_apps`), list deployment tasks (`huawei_list_clouddeploy_tasks`), get task detail (`huawei_get_clouddeploy_task`) |
| **Analyze** | Deployment failure root cause (`huawei_analyze_clouddeploy_failure` — agent offline/timeout/missing artifact/permission), OBS artifact link verification (`huawei_analyze_clouddeploy_artifact`) |
| **Manage** | Create application (`huawei_create_clouddeploy_app`), create deployment task referencing an app (`huawei_create_clouddeploy_task`), start deployment (`huawei_start_clouddeploy_task`), delete deployment task (`huawei_delete_clouddeploy_task`) |

> **Always run `hcloud CodeArtsDeploy <Operation> --cli-region={region} --help` before constructing a
> command** to discover the exact parameter names and required flags for the current KooCLI version.
> Do not answer from general knowledge — follow the procedures in this document.

**Dependency**: Quality telemetry is collected automatically via `skill-quality-cli` (installed by
`scripts/ensure_cli.sh` if absent).

### Critical Warnings

| Trap | Why |
|------|-----|
| **Flyway SQL dialect mismatch (H2 dev → MySQL prod)** | Spring Boot apps commonly develop with an H2 in-memory DB and deploy to RDS MySQL. Flyway migrations written with H2-specific syntax (`DATEADD`, `CHARACTER_LENGTH`, `BOOLEAN`) silently pass on H2 but fail on MySQL. Before deploying, audit `V*__*.sql` migration files: replace `DATEADD` with `DATE_ADD`, `BOOLEAN` with `TINYINT(1)`, and drop `characterEncoding=utf8mb4` from the Spring Boot datasource URL (RDS sets charset at instance level). Enable `Flyway.validate-on-migrate=true` in CI to catch dialect issues early. |
| **Service name is `CodeArtsDeploy`, not `CloudDeploy`** | `hcloud CloudDeploy <op>` reports "Unsupported service" (KooCLI 7.2.12). The real service name is `CodeArtsDeploy` (metadata directory `codeartsdeploy`). Always verify with `hcloud CodeArtsDeploy ListAllApp --cli-region=cn-north-4 --help`. |
| **Deployment hosts need the agent installed** | Target hosts (ECS/BMS/CCI) must have the CloudDeploy agent (`ICAgent`-style host agent) installed and online before a task can run. Check host status before starting a task — an offline agent is the #1 cause of "host offline / execution failed" results. |
| **Task must reference an application** | Create the deploy application first, then create the deployment task. A task without an application cannot be created or started (`CreateDeployTaskByTemplate` requires the app's project and template). |
| **Artifact source defaults to OBS** | Most deployment tasks pull artifacts from OBS buckets. Verify the bucket and object path exist and the service account has `GetObject` permission — otherwise the task fails at artifact download. |
| **Parallel deployments may conflict** | Multiple tasks deploying to the same host/group concurrently can conflict or deadlock. Use deployment groups, host locking, or serialized pipelines; check for an already `running` task before starting another. |
| **Security baseline** | Use IAM roles for deployment permissions, verify artifact integrity (checksum) before deploy, and never store plaintext credentials (AK/SK, DB passwords) in deployment scripts or task parameters (`--params` with `type=encrypt` exists for secrets). |

## Triggers

Use this skill when the user asks about CloudDeploy / CodeArts Deploy operations, deployment task
creation or management, artifact (OBS) configuration, or deployment failure troubleshooting.

**Trigger phrases**: "CloudDeploy", "CodeArts Deploy", "部署", "deploy task", "deployment",
"deployment task", "deploy application", "部署任务", "部署应用", "start deploy", "发布部署", "release",
"artifact deployment", "制品部署", "deploy failure", "部署失败", "pipeline deployment",
"CI/CD deployment".

**User utterance examples**:

1. "帮我创建一个部署应用/部署任务" (create a deploy application / deployment task)
2. "启动/查看/删除这个部署任务" (start / view / delete this deployment task)
3. "部署失败了，帮我分析一下原因" (deployment failed — analyze the root cause)
4. "检查一下 OBS 上的制品是否存在" (verify whether the OBS artifact exists)

## Prerequisites

1. **hcloud CLI** installed and authenticated — see `references/cli-installation-guide.md`
2. **Authentication** — one of:
   - **AK/SK credentials** — configure the default hcloud profile with your access key and secret
     key (see `references/cli-installation-guide.md`, section "Authentication"), or
   - Environment variables `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` (or `HUAWEI_ACCESS_KEY` /
     `HUAWEI_SECRET_KEY`) — hcloud auto-detects them
3. **IAM permissions** — `CodeArts Deploy ReadOnlyAccess` (or equivalent read actions) for
   query/analyze; `CodeArts Deploy FullAccess` (or the write actions listed in
   `references/iam-policies.md`) for create/start/delete — see `references/iam-policies.md`
4. **Region & project**: all CodeArtsDeploy APIs are region/project scoped. Pass
   `--cli-region={region}` and `--project_id={project_id}`. The project must be a CodeArts
   (DevCloud) project — an IAM project alone returns `Deploy.00016902 项目不存在`.
5. **Target hosts**: CloudDeploy agent installed and online on every target host (see Critical
   Warnings), and the OBS bucket/object for artifacts must exist in the same region.
6. **`skill-quality-cli`** — ensured by `bash scripts/ensure_cli.sh` (idempotent, skips if present)
   - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade)
   - Disable telemetry report: set `SKILL_QUALITY_REPORT=0` or `SKILL_QUALITY_DISABLE=1`

## Workflow

```
1. Identify intent:
   ├── Query (R3 auto): list apps / list tasks / get task detail
   ├── Analyze (R3 auto): failure root-cause analysis, OBS artifact link verification
   └── Manage (R1/R2): create app / create task / start task / delete task — preview + confirm
2. Gather scope: region, project_id, app/task IDs, time range (failure analysis), OBS path (artifact check)
3. Execute via hcloud CLI:
   ├── Query/Analyze → run command → return structured results
   └── Manage → show exact command + effect → wait for user confirmation → execute
4. Handle traps: agent offline → check host agent; artifact missing → verify OBS bucket/object;
   parallel conflict → check running tasks; dialect mismatch → audit Flyway migrations
5. Report results (JSON), masking AK/SK-like values in output
```

**Write-operation rule:** `huawei_create_clouddeploy_app`, `huawei_create_clouddeploy_task`,
`huawei_start_clouddeploy_task` (R2) and `huawei_delete_clouddeploy_task` (R1) MUST NOT execute
without an explicit user confirmation after the exact command and its effect are previewed.
For delete (R1) the user must confirm a second time in plain words (e.g. "确认删除").

## Core Commands

**Supported service (KooCLI): `CodeArtsDeploy` only.** This is the *single* supported service name
for this skill. `CloudDeploy` and `Deploy` are **not** supported service names — the hcloud CLI
rejects them with `[USE_ERROR]不支持的服务名称` (unsupported service), which is the **expected
correct-rejection** result. Any command in this skill MUST use `hcloud CodeArtsDeploy <Operation>`.

Service name is `CodeArtsDeploy` (KooCLI metadata directory `codeartsdeploy`; `CloudDeploy` is NOT
accepted). Region parameter `--cli-region={region}` is required on every command. The `--project_id`
is shown explicitly in examples; omit it only when your hcloud profile has a default project set.
Run each command as a **single line** (no `\` line continuations) so it stays directly copy-pasteable.
Parameter names below were verified against `hcloud CodeArtsDeploy <Operation> --help` (KooCLI 7.2.12).
Service name `CodeArtsDeploy`, every operation `ListAllApp` / `ListDeployTasks` /
`ShowDeployTaskDetail` / `ListDeployTaskHistoryByDate` / `CheckIsDuplicateAppName` / `CreateApp` /
`CreateDeployTaskByTemplate` / `StartDeployTask` / `DeleteDeployTask` — see the Parameter Confirmation
tables below for the exact `--key` names and constraints.

> **⚠️ Mandatory: every `hcloud` command in this skill MUST be wrapped with
> `skill-quality-cli run --skill-name huawei-cloud-deployment-task-management -- ` — bare `hcloud`
> calls are strictly forbidden.**

### Query — Applications (R3, auto)

```bash
# List deploy applications in a project (page/size required; default size 1000)
hcloud CodeArtsDeploy ListAllApp --cli-region={region} --project_id={project_id} --page=1 --size=100
skill-quality-cli run --skill-name huawei-cloud-deployment-task-management -- hcloud CodeArtsDeploy ListAllApp --cli-region={region} --project_id={project_id} --page=1 --size=100

# Filter by status (abort|failed|not_started|pending|running|succeeded|timeout|not_executed)
hcloud CodeArtsDeploy ListAllApp --cli-region={region} --project_id={project_id} --page=1 --size=100 --states.1=failed --states.2=running
skill-quality-cli run --skill-name huawei-cloud-deployment-task-management -- hcloud CodeArtsDeploy ListAllApp --cli-region={region} --project_id={project_id} --page=1 --size=100 --states.1=failed --states.2=running

# Sort by name or start time (DESC|ASC)
hcloud CodeArtsDeploy ListAllApp --cli-region={region} --project_id={project_id} --page=1 --size=100 --sort_by=DESC --sort_name=startTime
skill-quality-cli run --skill-name huawei-cloud-deployment-task-management -- hcloud CodeArtsDeploy ListAllApp --cli-region={region} --project_id={project_id} --page=1 --size=100 --sort_by=DESC --sort_name=startTime
```

### Query — Deployment Tasks (R3, auto)

```bash
# List deployment tasks (this legacy interface is maintained; ListAllApp is the new app-list API)
hcloud CodeArtsDeploy ListDeployTasks --cli-region={region} --project_id={project_id} --page=1 --size=50
skill-quality-cli run --skill-name huawei-cloud-deployment-task-management -- hcloud CodeArtsDeploy ListDeployTasks --cli-region={region} --project_id={project_id} --page=1 --size=50

# Get deployment task details by task ID
hcloud CodeArtsDeploy ShowDeployTaskDetail --cli-region={region} --task_id=00000000-0000-0000-0000-000000000000
skill-quality-cli run --skill-name huawei-cloud-deployment-task-management -- hcloud CodeArtsDeploy ShowDeployTaskDetail --cli-region={region} --task_id={task_id}
```

> `ShowDeployTaskDetail` is deprecated after 2024-09-30 (new equivalent `ShowAppDetailById`), but is
> still maintained and is the operation confirmed for `huawei_get_clouddeploy_task`.

### Analyze — Deployment Failure Root Cause (R3, auto)

```bash
# Query historical execution records of a task in a date range (interval ≤ 30 days)
hcloud CodeArtsDeploy ListDeployTaskHistoryByDate --cli-region={region} --project_id={project_id} --id=00000000-0000-0000-0000-000000000000 --start_date=2026-09-01 --end_date=2026-09-08 --page=1 --size=20
skill-quality-cli run --skill-name huawei-cloud-deployment-task-management -- hcloud CodeArtsDeploy ListDeployTaskHistoryByDate --cli-region={region} --project_id={project_id} --id={task_id} --start_date=2026-09-01 --end_date=2026-09-08 --page=1 --size=20
```

Diagnose the latest failed record by checking, in order:

1. **Agent offline / host not found** — target host status in the execution log; verify the
   CloudDeploy agent is installed and online on the host.
2. **Timeout** — `timeout` status; check artifact size, task timeout config, and target host resources.
3. **Artifact missing** — `artifact not found`; verify the OBS bucket and object path configured in
   the task (see `huawei_analyze_clouddeploy_artifact`).
4. **Permission denied** — verify IAM role/policy for the deployment account and host permissions.
5. **App-level errors** — e.g. `Deploy.00016902` (project not a CodeArts project), duplicate names,
   template errors.

### Analyze — OBS Artifact Link Verification (R3, auto)

```bash
# 1) Get the task detail and read the artifact configuration (bucket + object/package path)
hcloud CodeArtsDeploy ShowDeployTaskDetail --cli-region={region} --task_id=00000000-0000-0000-0000-000000000000
skill-quality-cli run --skill-name huawei-cloud-deployment-task-management -- hcloud CodeArtsDeploy ShowDeployTaskDetail --cli-region={region} --task_id={task_id}

# 2) One-time obsutil setup (before the first OBS check on each machine/region):
#    `hcloud obs ...` is an obsutil passthrough command (raw CLI, not a KooCLI SDK
#    API) — configure endpoint + reuse the same AK/SK as hcloud, then self-check
#    with a bucket-list passthrough that carries an explicit obs:// URI.
#    Prefer the interactive config below — AK/SK are typed at the terminal and stay
#    out of shell history / ps aux, avoiding the plaintext-credential leak vector of
#    passing -i=/-k= on the command line.
hcloud obs config -interactive
hcloud obs ls obs://{artifact_bucket}

# 3) Verify the OBS object exists (obsutil passthrough)
skill-quality-cli run --skill-name huawei-cloud-deployment-task-management -- hcloud obs ls obs://{artifact_bucket}/{artifact_object_path}
```

> **⚠️ Executor hint: `hcloud obs <command>` is a CLI passthrough to the obsutil binary (raw
> command-line execution), NOT an OBS SDK call.** Every OBS command in this skill — including
> `hcloud obs ls obs://...`, `hcloud obs cp`, `hcloud obs rm` — MUST be executed through the **CLI
> executor** (`hcloud ...` verbatim), and MUST NOT be routed to the OBS SDK (`huaweicloudsdkobs`) or
> translated into a Python SDK snippet. This is what allows the artifact check to run on any machine
> where `hcloud` + `obsutil` are installed, without an OBS SDK dependency.

Expected results: task shows an OBS artifact source; `ls` returns the object. If `hcloud obs` prints
`Warn: Please set ak, sk and endpoint in the configuration file!`, obsutil has not been configured
yet — run step 2 (config + `bucket list` self-check) before proceeding. If the object is
missing → advise re-uploading the artifact or fixing the task's artifact path; if access is denied →
check the OBS bucket policy and the deployment account's `GetObject` permission.

### Manage — Create Application (R2, preview + confirm)

```bash
# Pre-check that the application name is unique in the project (GET)
hcloud CodeArtsDeploy CheckIsDuplicateAppName --cli-region={region} --project_id={project_id} --name=test-app
skill-quality-cli run --skill-name huawei-cloud-deployment-task-management -- hcloud CodeArtsDeploy CheckIsDuplicateAppName --cli-region={region} --project_id={project_id} --name={app_name}

# Create the application (from template type; draft flag controls publish state)
hcloud CodeArtsDeploy CreateApp --cli-region={region} --project_id={project_id} --name=test-app --create_type=template --is_draft=false
skill-quality-cli run --skill-name huawei-cloud-deployment-task-management -- hcloud CodeArtsDeploy CreateApp --cli-region={region} --project_id={project_id} --name={app_name} --create_type=template --is_draft=false [--description={description}]
```

> Preview before executing: show the exact command and the application to be created, then wait for
> user confirmation (R2). If `CheckIsDuplicateAppName` returns "duplicate", choose another name.

### Manage — Create Deployment Task (R2, preview + confirm)

```bash
# Create a deployment task from a template (task must reference an existing application/project)
skill-quality-cli run --skill-name huawei-cloud-deployment-task-management -- hcloud CodeArtsDeploy CreateDeployTaskByTemplate --cli-region={region} --project_id={project_id} --project_name={project_name} --task_name={task_name} --template_id={template_id} [--configs.1.name={param_name} --configs.1.value={param_value} ...]
```

> Preview before executing: show the exact command and the task to be created, then wait for user
> confirmation (R2). The template determines the deployment steps; the application (project) must
> already exist (create it first with `huawei_create_clouddeploy_app`).

### Manage — Start Deployment (R2, preview + confirm)

```bash
# Start the deployment task (target hosts must have the agent online)
hcloud CodeArtsDeploy StartDeployTask --cli-region={region} --task_id=00000000-0000-0000-0000-000000000000
skill-quality-cli run --skill-name huawei-cloud-deployment-task-management -- hcloud CodeArtsDeploy StartDeployTask --cli-region={region} --task_id={task_id}

# Start with dynamic parameters (type: text|host_group|encrypt|enum)
skill-quality-cli run --skill-name huawei-cloud-deployment-task-management -- hcloud CodeArtsDeploy StartDeployTask --cli-region={region} --task_id={task_id} --params.1.key={param_name} --params.1.type=encrypt --params.1.value={param_value}
```

> Preview before executing: show the task, target hosts, and artifact source, then wait for user
> confirmation (R2). Check that no other task is currently `running` on the same hosts (parallel
> conflict trap). Use `--params.N.type=encrypt` for secrets — never plaintext credentials in scripts.

### Manage — Delete Deployment Task (R1, preview + explicit confirm)

```bash
# Delete a deployment task by task ID
hcloud CodeArtsDeploy DeleteDeployTask --cli-region={region} --task_id=00000000-0000-0000-0000-000000000000
skill-quality-cli run --skill-name huawei-cloud-deployment-task-management -- hcloud CodeArtsDeploy DeleteDeployTask --cli-region={region} --task_id={task_id}
```

> R1 delete operation: preview the exact command and the task being deleted, then require an explicit
> second confirmation (e.g. the user typing the task name or "确认删除") before execution. Deleting a
> task does not delete the application or the deployed resources.

## Parameter Confirmation

All parameter names below were verified against `hcloud CodeArtsDeploy <Operation> --help`
(KooCLI 7.2.12). Values in `{}` are placeholders — replace with real values.
**Do not invent parameter names** — re-run `--help` if in doubt.

### ListAllApp

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--cli-region` | Yes (auto) | string | Region where the API can be called |
| `--project_id` | Yes | string | CodeArts project ID |
| `--page` | Yes | integer | Page number, ≥ 1 |
| `--size` | Yes | integer | Items per page, default 1000 |
| `--group_id` | No | string | Application group ID; `no_grouped` for ungrouped apps |
| `--sort_by` | No | string | `DESC` or `ASC`, default `DESC` |
| `--sort_name` | No | string | `name` or `startTime` |
| `--states.[N]` | No | array\<string\> | `abort`\|`failed`\|`not_started`\|`pending`\|`running`\|`succeeded`\|`timeout`\|`not_executed` |

### ListDeployTasks

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--cli-region` | Yes (auto) | string | Region where the API can be called |
| `--project_id` | Yes | string | CodeArts project ID |
| `--page` | Yes | integer | Page number, ≥ 1 |
| `--size` | Yes | integer | Items per page, ≤ 100 |

### ShowDeployTaskDetail

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--cli-region` | Yes (auto) | string | Region where the API can be called |
| `--task_id` | Yes | string | Deployment task ID |

### ListDeployTaskHistoryByDate

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--cli-region` | Yes (auto) | string | Region where the API can be called |
| `--project_id` | Yes | string | CodeArts project ID |
| `--id` | Yes | string | Deployment task ID |
| `--start_date` | Yes | string | Start time, `yyyy-MM-dd` |
| `--end_date` | Yes | string | End time, `yyyy-MM-dd`; interval with start ≤ 30 days |
| `--page` | Yes | integer | Page number, ≥ 1 |
| `--size` | Yes | integer | Items per page, ≤ 100 |

### CheckIsDuplicateAppName

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--cli-region` | Yes (auto) | string | Region where the API can be called |
| `--project_id` | Yes | string | CodeArts project ID |
| `--name` | Yes | string | Application name to check |

### CreateApp

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--cli-region` | Yes (auto) | string | Region where the API can be called |
| `--project_id` | Yes | string | CodeArts project ID |
| `--name` | Yes | string | Application name |
| `--create_type` | Yes | string | `template` |
| `--is_draft` | Yes | boolean | Create as draft (`true`) or published (`false`) |
| `--description` | No | string | Application description |
| `--group_id` | No | string | Application group ID |
| `--arrange_infos.[N].*` | No | object | Application arrangement/steps definition |
| `--trigger.*` | No | object | Trigger source restrictions (`trigger_source`: 0 = all, 1 = pipeline only) |
| `--slave_cluster_id` | No | string | Custom slave resource pool ID |

### CreateDeployTaskByTemplate

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--cli-region` | Yes (auto) | string | Region where the API can be called |
| `--project_id` | Yes | string | CodeArts project ID |
| `--project_name` | Yes | string | Project name |
| `--task_name` | Yes | string | Task (application) name |
| `--template_id` | Yes | string | Deployment template ID — obtained from the **CodeArts Deploy console 模板库** when creating an app from a template (no CLI list operation exists for deploy templates; `ShowTemplate`/`ListTemplates` are not supported operations) |
| `--configs.[N].name` | No | string | Deployment parameter name |
| `--configs.[N].value` | No | string | Deployment parameter value |
| `--configs.[N].type` | No | string | `text`\|`host_group`\|`enum`\|`encrypt` (mandatory if `name` is set) |
| `--configs.[N].static_status` | No | integer | `1` = cannot change during deployment, `0` = can change |
| `--configs.[N].limits.[N].*` | No | object | Enumerated value optional parameters |
| `--configs.[N].task_id` | No | string | Auto-generated after app creation |
| `--slave_cluster_id` | No | string | Custom slave resource pool ID |

### StartDeployTask

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--cli-region` | Yes (auto) | string | Region where the API can be called |
| `--task_id` | Yes | string | Deployment task ID |
| `--params.[N].key` | No | string | Parameter name passed during deployment |
| `--params.[N].type` | No | string | `text`\|`host_group`\|`encrypt`\|`enum` (mandatory for dynamic params) |
| `--params.[N].value` | No | string | Parameter value |
| `--record_id` | No | string | Deployment record ID (rollback to previous deployment) |
| `--trigger_source` | No | string | `0` = no limit, `1` = pipeline-only trigger |

### DeleteDeployTask

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--cli-region` | Yes (auto) | string | Region where the API can be called |
| `--task_id` | Yes | string | Deployment task ID |

## KooCLI Command Format Standard

The generic invocation shape is `hcloud <service> <Operation> --cli-region=<region> [--key=value ...]`
— this is a **format description only**: `<...>` and `[--key=value]` are placeholders, never executed verbatim.

| Feature | Rule | Example |
|---------|------|---------|
| Service name | `CodeArtsDeploy` (metadata directory `codeartsdeploy`; `CloudDeploy` is NOT supported) | `hcloud CodeArtsDeploy ListAllApp --cli-region=cn-north-4` |
| Operation name | PascalCase | `ListAllApp`, `StartDeployTask` |
| Region parameter | `--cli-region=<value>` always included | `--cli-region=cn-north-4` |
| Simple parameter | `--key=value` | `--project_id=xxx` |
| Indexed parameter | `--key.N=value` | `--states.1=failed`, `--params.1.key=xxx` |
| Nested parameter | `--parent.child=value` | `--configs.1.type=encrypt` |
| Verification | Run `--help` first; parameter names come from `--help` output only | `hcloud CodeArtsDeploy CreateApp --cli-region=cn-north-4 --help` |

## Tool Parameter Validation (Mandatory)

Validate every parameter before execution; illegal input is rejected directly (never passed to `hcloud`):

| Validation | Rule |
| ---------- | ---- |
| Whitelist enum | Documented value sets (`--cli-region`, `--states.[N]`, `--sort_by`, `--size`, `--page`, `--create_type`, `--is_draft`, `--configs.[N].type`, `--params.[N].type`, ...) must match exactly; anything else → refuse, listing allowed values |
| Type check | Numeric params (`--page`, `--size`) must be positive integers (≥ 1; `--size` ≤ 100 for the list/task interfaces); name/ID params (`--project_id`, `--task_id`, `--id`, `--template_id`, `--app_name`) must be strings matching `[a-zA-Z0-9_-]+` |
| Date range | `--start_date`/`--end_date` must be `yyyy-MM-dd` and the interval ≤ 30 days; otherwise refuse |
| Secret params | `--params.[N].type=encrypt` values must never appear in logs/output; only `*`-masked representation is shown |
| Reject unknown | Params absent from `hcloud CodeArtsDeploy <Operation> --help` are rejected before running the command |

### Expected CLI rejections (for verification / boundary cases)

These are **expected error outcomes** — the CLI or API rejects the input and the rejection itself is
the correct result, not a skill defect:

| Input | Expected rejection |
|-------|--------------------|
| `--page=0` (or any page < 1) | `DEV-12-50002 page参数异常，仅支持数字（1~99999）` |
| Unknown `--task_id` format (e.g. non-32-char) | `DEV-12-50002 task_id参数异常，仅支持数字、字母字符（32个字符）` |
| Non-CodeArts (plain IAM) project id in `--project_id` | `Deploy.00016902 项目不存在` (project scope limitation) |
| Service name `CloudDeploy` / `Deploy` instead of `CodeArtsDeploy` | `[USE_ERROR]不支持的服务名称:CloudDeploy` (unsupported service — the supported name is `CodeArtsDeploy`) |
| Unknown parameter flag | `[USE_ERROR]不正确的参数:xxx` |
| `hcloud obs` without obsutil configured | `Warn: Please set ak, sk and endpoint in the configuration file!` |

## Reference Documents

- `references/iam-policies.md` — Least-privilege IAM policies for CloudDeploy
- `references/cli-installation-guide.md` — hcloud CLI installation and AK/SK/profile authentication (incl. OBS artifact check setup)
- `references/verification-method.md` — Verification procedures for query/analyze/manage actions
- `references/dataflow-diagram.md` — Mermaid data flow diagrams
- `references/acceptance-criteria.md` — Acceptance criteria for this skill
- `references/test-data-guide.md` — Test-data placeholders and how to backfill them
  before live runs
