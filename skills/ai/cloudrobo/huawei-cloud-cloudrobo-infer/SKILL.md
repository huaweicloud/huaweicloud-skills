---
name: huawei-cloud-cloudrobo-infer
description: >
  Manage CloudRobo inference services — deploy a model into a managed inference service,
  list/query deployed services and their logs, start/stop a running service, update or
  delete a service, and orchestrate the 'wait-deploy' convenience flow that polls a service
  until it finishes deploying. Inference services consume models produced by
  cloudrobo-train and are consumed by robo-dispatcher when dispatching embodied tasks.
  Triggers include: infer, inference, model deployment, deploy model, inference service,
  service deployment, start inference, stop inference, service logs, wait-deploy,
  model serving, 推理, 推理服务, 模型部署, 部署模型, 推理服务管理, 服务日志, 模型服务.
tags:
  - huawei-cloud-cloudrobo
  - infer
  - model-deployment
  - inference-service
  - 推理服务
---

> **Windows / PowerShell:** Examples use bash syntax. To run on Windows PowerShell:
> - Flatten `\` line continuations to a single line, or end lines with a backtick.
> - Set env vars with `$env:NAME="value"` instead of `export NAME="value"`.
> - Single-quoted JSON `'{"a":"b"}'` works as-is.

## Overview

The `cloudrobo-infer` skill manages the full lifecycle of CloudRobo **inference services**
(also called model-serving / inference-service): deploy a model (identified by `model_id` +
`model_version_id` passed as a `--model-json` JSON object) into a long-running service, then
operate it (start / stop / update / delete / logs), and use `wait-deploy` to poll until the
service status is no longer `DEPLOYING` (`status != "DEPLOYING"`), returning any other state
(e.g. RUNNING, FAILED, STOPPED).
> `wait-deploy` only waits on the `DEPLOYING` phase — it does NOT wait through `CREATING`.
> Exact semantics: [Wait-Deploy](references/service-config-catalog.md#wait-deploy-cli-helper).

**Applicable scenarios:**

- **Model deployment** — Deploy a model as an inference service (create → wait-deploy)
- **Wait-Deploy** — Poll every 5s until status is no longer `DEPLOYING` (600s default)
- **Service O&M** — List deployed services, show detail, update config, start/stop
- **Log diagnosis** — `list-logs` with millisecond time range and keyword filter
- **Cross-skill orchestration** — Consume models exported by `cloudrobo-train`; expose the
  service to `robo-dispatcher` for embodied tasks (via the service `id`).

**Out of Scope:**

- Model training / dataset, robots, dispatch, and asset / compute pool / workspace
  lifecycle are separate CloudRobo capabilities (train / dataset / robot / dispatch /
  asset / resource / workspace). Route those requests through the matching Agent skill;
  this skill only produces an inference service that dispatch consumes via its `id`.

**Architecture:**

```text
Agent / LLM
    │
    ├── CLI  →  cloudrobo infer <command>
    └── SDK  →  InferClient (Python)
                    │
                    ▼
              cloudrobo-service (REST API)
              /v1/infer-services/*
```

All operations target the `cloudrobo-service` backend with a valid `workspace_id`
(the default workspace is used unless explicitly provided). Deploying a service consumes
compute (pool) resources — always confirm before starting a long-running service.

## Prerequisites

- CLI installed, AK/SK configured, workspace resolved — `references/cli-installation-guide.md`.
- A valid `workspace_id` (`cloudrobo workspace current`, or `list` + `use`).
- A deployable model: `model_id` (=`asset_id`) + `model_version_id` (=`latest_version_id`):
  `--model-json '{"model_id": "<asset_id>", "model_version_id": "<latest_version_id>"}'`.
  The model must have `ONLINE_DEPLOYMENT` with `status: "ENABLE"` in `show-asset`;
  `DRAFT`/`CREATING` models are rejected with 403.
- A compute pool: `pool_type` + `flavor` (`cloudrobo resource list-pools --resource-type
  MODELARTS`, only `status: "AVAILABLE"` pools). `--pool-id pool-<resource_id>` is
  **optional** — pass it only for a dedicated pool.
- `--stop-schedule-json` is **required by the backend**:
  `{"duration": <N>, "time_unit": "MINUTES"}`.
- **Region**: `cloudrobo` (0.3.0) has no `--cli-region` command-line option (the root command
  only accepts `--verbose/-v`; region is not a CLI flag). Set it with
  `cloudrobo config set region <region>` (persisted to `~/.cloudrobo/config.yaml`) — default
  `cn-southwest-2`. Never append `--cli-region` to `cloudrobo` commands: an unknown option
  exits non-zero. `--cli-region` belongs to `hcloud`/KooCLI only, not here.

## 执行前置自检（Preflight — 每条命令前先做）

任一项失败立即输出中文提示并以非零码退出；**禁止静默等待、禁止把空结果当成成功**：

```bash
command -v cloudrobo >/dev/null 2>&1 || {
  echo "未检测到 cloudrobo 命令：请先安装聚合客户端 CLI（pip install hw-cloudrobo-client），详见 references/cli-installation-guide.md。" >&2; exit 2; }
cloudrobo infer --help >/dev/null 2>&1 || {
  echo "cloudrobo infer 子命令不可用：请安装或升级 hw-cloudrobo-client（聚合包，已含推理模块）后重试（cloudrobo --help 可确认已注册的命令）。" >&2; exit 2; }
cloudrobo asset --help >/dev/null 2>&1 || {
  echo "cloudrobo asset 命令组不可用（报错形如 Error: No such command asset）：说明只装了推理模块，模型资料解析无法进行。请改装聚合客户端 pip install hw-cloudrobo-client 后重试。" >&2; exit 2; }
```

- 凭证缺失不阻断上面的自检，但所有联网命令都会以 401 失败：先
  `export HUAWEI_CLOUD_AK=<ak> HUAWEI_CLOUD_SK=<sk>` 或
  `cloudrobo config set ak <ak> sk <sk>`，再重试。
- `scripts/test-cli-commands.sh` 自检更严：CLI、`infer` 子命令、AK/SK 任一缺失即输出中文
  提示并 `exit 2`（没有凭证时它不会给出虚假通过）。
- 查询类命令返回空列表属正常结果（0 条服务），不等同于失败；命令报错则必须如实上报。

## Workflow

### Natural-Language-First Principle

Every workflow below starts from a user intent (1-2 sentences), not from manual CLI/SDK
orchestration. The skill then drives the matching command chain and reports state feedback
(status changes, polling progress).

### Model Deployment Workflow (interactive parameter resolution)

Scenario: "我想创建一个推理服务" / "Deploy model X as an inference service."

Core principle: **query each required parameter → present options → let user choose →
assemble full command → execute.**

1. **Resolve workspace** — `cloudrobo workspace current`.
   - Default workspace set → use its `workspace_id` and `asset_catalog_id`.
   - Not set → `cloudrobo workspace list` → present names + IDs → `cloudrobo workspace use
     --workspace-id <id>` → re-run `current` to confirm.

2. **Ask model source & type** — ask in this order:
   - **Source** (where to search): embodiment plaza (具身广场), workspace assets (空间资产),
     or custom (自定义). The source decides the entire parameter policy below.
   - **Type** (by `ext_metadata.model_type`): perception (感知), vln (导航), vla (操作),
     planning (规划).
   - Vague request (e.g. "so101 相关的模型") → skip both and use `cloudrobo asset search-assets` by keyword.
   - Branch immediately to the [Model Source → Parameter Policy](#model-source--parameter-policy)
     table before assembling `create`.

3. **Query models**:
   - **Embodiment plaza**: `cloudrobo asset list-publication-assets --type model
     --actions ONLINE_DEPLOYMENT --action-status ENABLE`.
   - **Workspace assets**: `cloudrobo asset list-assets --catalog-id <asset_catalog_id>
     --type model` (use `--catalog-id`, NOT `--repository-id`).
   - **Keyword search**: `cloudrobo asset search-assets --keyword "<keyword>" --type model`.
   - Present matching models (name, asset_id, status, model_type) for selection.

4. **Resolve model version** — `cloudrobo asset show-asset --asset-id <asset_id>`.
   - `latest_version_id` → `model_version_id` in `--model-json`.
   - `version_count > 1` → `cloudrobo asset list-versions --asset-id <id>` → let user choose.
   - `ONLINE_DEPLOYMENT` must be `ENABLE`; model `status` must be `RELEASE` (or published),
     otherwise the platform returns 403.

5. **Auto-discover deployment parameters — space asset / custom models ONLY.**
   **Embodiment plaza models: skip this step entirely** and carry none of
   `--cmd`/`--image-swr-url`/`--envs-json`/`--skill-config-json`/`--service-invoke-json`/
   `--readiness-health-json`/`--model-ext-metadata`/`--model-json.mount_path` — plaza models
   are pre-configured on the platform, and extra parameters risk a mismatched deployment.

   For space asset / custom models, discover from the model's algorithm asset and its config
   files (algorithm asset → `ext_metadata.command` / `engine.image_url` /
   `environment_variables` / `deployment_config`; `skill_config.json` and r2c config via the
   `download-url` API). Full discovery table, `download-url` code, `strict` field and r2c
   fallback rules: `references/service-config-catalog.md` → "Parameter Auto-Discovery Sources".

   > **Priority**: config files > ext_metadata fields > ask user. Undiscoverable parameters
   > are skipped silently (never block deployment). For "bare" models with no algorithm
   > association, ask the user whether to supply optional parameters manually.

6. **Resolve pool & flavor** — `cloudrobo resource list-pools --resource-type MODELARTS`.
   - Only `status: "AVAILABLE"` pools are usable; present names, pool_type and flavors.
   - `resource_id` → `--pool-id pool-<resource_id>`; `pool_type` → `--pool-type`
     (`DEDICATED` / `SHARED`). Omit `--pool-id` for `SHARED` pools.
   - Flavors live under `config.flavor` grouped by hardware (CPU/GPU/ASCEND); let the user
     pick (e.g. `"1 * SNT9B2 | 24 vCPUs | 192 GiB"`).

7. **Confirm parameters & deploy** — present the `create` command using the variant that
   matches the source from Step 2 (never mix variants):

   **Variant A — embodiment plaza (required core parameters ONLY):**
   ```bash
   cloudrobo infer create --name <service-name> --flavor "<flavor>" --model-json '{"model_id": "<asset_id>", "model_version_id": "<latest_version_id>"}' --workspace-id <workspace_id> --pool-type <pool_type> --stop-schedule-json '{"duration": 60, "time_unit": "MINUTES"}' [--pool-id pool-<resource_id>] [--dry-run]
   ```

   **Variant B — space asset / custom (core + auto-discovered params):**
   ```bash
   cloudrobo infer create --name <service-name> --flavor "<flavor>" --model-json '{"model_id": "<asset_id>", "model_version_id": "<latest_version_id>", "mount_path": "<mount_path>"}' --workspace-id <workspace_id> --pool-type <pool_type> --stop-schedule-json '{"duration": 60, "time_unit": "MINUTES"}' [--pool-id pool-<resource_id>] [--cmd "<command>"] [--image-swr-url "<image_url>"] [--envs-json '{"KEY":"VALUE"}'] [--skill-config-json '{"skills":[{"name":"...","prompt":"..."}],"strict":true}'] [--service-invoke-json '{"auth_type":"...","port":8080,"protocol":"HTTP"}'] [--readiness-health-json '{"path":"/ready","port":8080}'] [--model-ext-metadata '<r2c_config_file_content>'] [--dry-run]
   ```

   - Include only parameters actually discovered in Step 5; `--pool-id` only for `DEDICATED`.
   - `--envs-json` takes a **map** (`{"K":"V"}`) — convert the asset's array form first.
   - `--skill-config-json` skill items keep only `name` + `prompt`.
   - Run with `--dry-run` first, confirm with the user, then re-run without `--dry-run`.

8. **Wait for deployment** — `cloudrobo infer wait-deploy --service-id <sid>` (polls every 5s
   until `status != "DEPLOYING"`, 600s default).
   - After `create` the service auto-enters `CREATING` → `DEPLOYING`. **Do NOT call `start`** —
     it returns 400 "Status DEPLOYING does not support start". `start` only restarts a
     `STOPPED` service.
   - If `wait-deploy` returns while still `CREATING`, immediately re-invoke it.

9. **Report** — output the service `id` (the returned identifier; some docs call it
   `service_id`), model name, flavor and final status. On `FAILED` → `list-logs` for diagnosis.
   **Never auto-delete a failed service** — present the `delete` command and ask for explicit
   confirmation.

> **Asset note**: model_id / version_id / flavor / pool_id must be resolved dynamically via the
> query commands above; never hardcode them. Always let the user choose from queried options.

### Model Source → Parameter Policy (authoritative decision table)

This table is the **single source of truth** for which `create` parameters to carry, based on
the model source resolved in Step 2. `cloudrobo-model-workflow` Stage 3 references it to keep
both skills consistent. Resolve the source first, then apply exactly the matching column —
**do not mix variants**.

| Model source (from Step 2) | Search command (Step 3) | Auto-discovery (Step 5) | `create` parameters to carry |
|----------------------------|-------------------------|--------------------------|------------------------------|
| **Embodiment plaza (具身广场)** | `cloudrobo asset list-publication-assets --type model --actions ONLINE_DEPLOYMENT --action-status ENABLE` | **SKIP entirely** — model is pre-configured on platform | **Required core only**: `--name`, `--flavor`, `--model-json` (`model_id`+`model_version_id`), `--workspace-id`, `--pool-type`, `--stop-schedule-json`; `--pool-id` only for `DEDICATED` pool. **Do NOT carry** `--cmd`/`--image-swr-url`/`--envs-json`/`--skill-config-json`/`--service-invoke-json`/`--readiness-health-json`/`--model-ext-metadata`/`--model-json.mount_path` |
| **Space asset / custom (空间资产/自定义)** | `cloudrobo asset list-assets --catalog-id <asset_catalog_id> --type model` / `cloudrobo asset search-assets --keyword ...` | **Run Step 5 fully** — query algorithm asset (cmd/image/envs/mount_path/service-invoke/readiness-health) + download `skill_config.json` + r2c config | Required core **plus** every parameter actually discovered in Step 5; omit undiscovered ones silently |
| Unknown model id (user passed explicit id) | `cloudrobo asset show-asset --asset-id <id>` | Determine from `show-asset`: `ONLINE_DEPLOYMENT` action pointing to a platform algorithm → treat as space-asset path (run Step 5); self-contained/pre-configured config → core only | As per the resolved path |

> **Rationale**: embodiment plaza models bundle their orchestration, image, envs, health probes,
> skills and r2c mapping on the platform. Re-supplying these in `create` is redundant and risks
> an invalid/mismatched deployment (the "不该带的参数不要带" rule). Space asset / custom models
> have no bundled config, so their parameters must be discovered and passed explicitly.

### Wait-Deploy Workflow (CLI convenience)

Scenario: "Wait for this inference service to finish deploying."

1. `cloudrobo infer wait-deploy --service-id <sid> [--timeout 600]` — client-side polling of
   `show` every 5s until `status != "DEPLOYING"`; returns any other state (`RUNNING`, `FAILED`,
   `STOPPED`). Timeout range 1–3600; on timeout it raises `RuntimeError` → JSON error +
   `ClickException`, non-zero exit.
2. **Feedback** — report the final status; on `FAILED` suggest `list-logs`.

> `wait-deploy` does NOT create the service — call `create` first, then `wait-deploy`. Do NOT
> call `start` after `create` (auto-deploys `CREATING → DEPLOYING → RUNNING`); `start` is only
> for restarting a `STOPPED` service.

### Service O&M / Lookup Workflow

Scenario: "What inference services are running in my workspace?"

1. `cloudrobo infer list --workspace-id <ws> [--status <status>] [--model-id <mid>]
   [--name <name>] [--model-name <mn>] [--model-version-id <mvid>] [--model-version-name <mvn>]
   [--user-name <un>] [--user-id <uid>]` + pagination (`--limit`/`--offset`) and sorting
   (`--sort-key`/`--sort-dir`).
2. `cloudrobo infer show --service-id <sid>` for a full config snapshot.
3. Report status and key fields (model, flavor, status, pool).

### Service Start/Stop Workflow

Scenario: "Stop the inference service behind this API." / "Bring it back up."

1. Confirm the service via `show --service-id <sid>`.
2. `cloudrobo infer stop --service-id <sid>` or `start --service-id <sid>` (mutating; confirm
   before executing).
3. Poll `show` until the desired terminal state (`STOPPED` / `RUNNING`).

### Log Diagnosis Workflow

Scenario: "Why is my deployed service failing? Show me its logs."

1. `cloudrobo infer list-logs --service-id <sid> --start-time <ms> --end-time <ms>` — both
   timestamps are **milliseconds** (13-digit). Optional: `--keywords`, `--limit`, `--line-num`,
   `--is-count`, `--highlight`, `--is-desc`.
2. Correlate log lines with `show` status (e.g. `CREATE_FAILED`/`START_FAILED`).
3. Suggest remediation (pool capacity, model artifact, health-check config).

### Service Update / Deletion Workflow

Scenario: "Reconfigure this service" / "Shut down and remove this service."

- **Update** — `cloudrobo infer update --service-id <sid> [--description <desc>]
  [--model-ext-metadata <json>] [--dry-run]` (mutating; confirm). `update` **only supports**
  `--description` and `--model-ext-metadata`; changing image/flavor/model/pool/stop-schedule
  is not supported — use `delete` + `create` to rebuild.
- **Delete** — `cloudrobo infer delete --service-id <sid> [--dry-run]` (mutating;
  irreversible; confirm). It removes only the service, **not** the model asset — delete assets
  through the CloudRobo asset skill (`cloudrobo asset delete-asset`).

### Combined Workflow A — Deploy a trained model (infer + train + asset)

Scenario: "I trained a VLA model; deploy it as an inference service."

1. Resolve workspace (`cloudrobo workspace current`).
2. Query the model (`cloudrobo asset list-assets --catalog-id <asset_catalog_id> --type model`)
   → `asset_id`.
3. `cloudrobo asset show-asset --asset-id <asset_id>` → `latest_version_id`; verify
   `ONLINE_DEPLOYMENT` = `ENABLE`.
4. `cloudrobo resource list-pools --resource-type MODELARTS` → user selects `resource_id`
   and `flavor`.
5. A trained model is a **space asset** → Variant B of Step 7: run Step 5 auto-discovery and
   carry whatever was discovered.
6. `cloudrobo infer create ...` (Variant B) → `cloudrobo infer wait-deploy --service-id <sid>`
   (do NOT call `start` — the service auto-deploys).
7. Report the service `id` and status; the service is now consumable.

## Core Commands

```bash
cloudrobo infer <command> [OPTIONS]
```

| Subcommand | Description | Key options |
| ---------- | ----------- | ----------- |
| `create` | Deploy a new inference service | `--name`, `--flavor`, `--model-json`, `--workspace-id`, `--pool-type`, `--stop-schedule-json` (required); `--pool-id` optional (dedicated pools only) |
| `wait-deploy` | Poll until deployment completes | `--service-id`, `--timeout` |
| `list` | List inference services | `--workspace-id`, `--status`, `--limit`, `--offset` |
| `show` | Show service detail | `--service-id` |
| `start` / `stop` | Start or stop a service | `--service-id` |
| `update` | Update service config | `--service-id`, `--description`, `--model-ext-metadata` |
| `delete` | Delete a service | `--service-id` |
| `list-logs` | Query service logs | `--service-id`, `--start-time` (ms), `--end-time` (ms), `--keywords` |

> SDK path: when CLI is inconvenient (dynamic JSON, cross-package queries), use `InferClient`
> — one consolidated snippet for the five main calls (`create` / `show` / `list` / `list-logs` /
> `wait-deploy`) lives in `references/service-config-catalog.md` → "InferClient Main-Chain Snippet".
> Parameter-resolution table and edge cases: same file → "Parameter Resolution &
> Confirmation", "Edge Cases". SDK exposes 9
> methods, CLI exposes 9 commands (0 gaps); `wait-deploy` is a client-side polling helper in both.
>
> **Return identifier**: `create`/`show`/`list`/`wait-deploy` identify the service with the `id`
> field (some API/SDK docs call it `service_id`). Use that value as `--service-id` for all
> downstream commands — there is no top-level `service_id` key in create/show responses.

## Parameter Confirmation

Resolve every value from query commands, present it to the user, then execute. Never hardcode
IDs or flavors; mutating commands (`create` / `start` / `stop` / `update` / `delete`) need an
explicit confirmation first.

| Parameter | Required | Resolution |
| --------- | -------- | ---------- |
| `--workspace-id` | create / list | `cloudrobo workspace current` (or `list` + `use`) |
| `--model-json` | create | `model_id` from asset search, `model_version_id` = `latest_version_id` from `show-asset` |
| `--flavor` | create | `cloudrobo resource list-pools --resource-type MODELARTS` → `config.flavor` |
| `--pool-type` | create | `SHARED` / `DEDICATED` from the selected pool |
| `--pool-id` | dedicated pool only | `pool-<resource_id>` from the selected pool |
| `--stop-schedule-json` | create | `{"duration": <N>, "time_unit": "MINUTES"}` (backend-required) |
| `--service-id` | show / start / stop / update / delete / logs / wait-deploy | `id` returned by `create`, `show` or `list` |
| `--dry-run` | create / update / delete | add to preview parameter assembly; no resource is created or changed |

## Reference Documents

- [CLI Installation Guide](references/cli-installation-guide.md) — installation, AK/SK, region, workspace
- [IAM Policies](references/iam-policies.md) — least-privilege credential & access model
- [Verification Method](references/verification-method.md) — verification levels and cases (negative cases are marked `EXPECT-FAIL`)
- [Dataflow Diagram](references/dataflow-diagram.md) — Mermaid data flow diagrams
- [Acceptance Criteria](references/acceptance-criteria.md) — acceptance criteria
- [Service Config Reference](references/service-config-catalog.md) — InferServiceDto fields, health checks, status, logs, parameter auto-discovery, InferClient main-chain snippet, parameter resolution, edge cases, coverage matrix

## Edge Cases

> See `references/service-config-catalog.md` → "Edge Cases" for the full table (missing
> model_id, invalid JSON, wrong timestamp unit, 403 permission deny, 500 internal error,
> missing stop-schedule, r2c config fallback, envs format mismatch, cross-skill invocation).

## Verification Method

Specification compliance and functional smoke both run the same scripted suite:

```bash
bash scripts/test-cli-commands.sh
```

The script runs a one-time preflight (CLI present, `infer` registered, AK/SK present;
region is reported when configured, otherwise the client default applies), executes the
read-only and dry-run cases in one batch, scores negative cases as `EXPECT-FAIL`
(pass means a non-zero exit code), and exits non-zero when any case fails.

### Test Cases

See `templates/test-vars.json` for the full case list (deployment, wait-deploy, lifecycle,
logs, safety). Cases marked `"result": "SKIP"` are mutating and never auto-run; cases marked
`"negative": true` must exit non-zero.

### Verification Checklist

- After `create`, service appears in `list` with correct status
- After `wait-deploy`, status is no longer `DEPLOYING` (or timeout/failure is reported with log guidance)
- After `start`/`stop`, `show` reflects the new status
- After `delete`, `show` returns not-found
- `list-logs` with **ms** timestamps returns log lines; keyword filter works
- Negative cases (`../` service_id, malformed JSON, missing `--name` / `--model-json`) exit non-zero
  with the client-side error text (Click `Missing option ...`)
- Mutating operations (especially start) prompt for user confirmation

## Best Practices

- Resolve each `create` parameter via query commands, then let the user choose — never hardcode
- **Model source drives parameter policy**: resolve the source (Step 2) first, then apply the
  [Model Source → Parameter Policy](#model-source--parameter-policy) table. Plaza models carry
  **required core params only**; space asset / custom models run Step 5 auto-discovery
- Model search: `cloudrobo asset list-publication-assets --actions ONLINE_DEPLOYMENT --action-status ENABLE`
  for deployable plaza models; `cloudrobo asset list-assets --catalog-id <id>` for workspace models;
  `cloudrobo asset search-assets --keyword "<kw>"` for fuzzy search
- `--model-json`'s `model_version_id` must be `latest_version_id` from `show-asset`, NOT
  `actions[].algorithm.version_id`
- Always include `--stop-schedule-json '{"duration": N, "time_unit": "MINUTES"}'` in `create`;
  omit `--pool-id` unless deploying to a dedicated pool
- Use `wait-deploy` after `create` (5s interval, 600s default). Do NOT call `start` after
  `create` — the service auto-deploys; re-invoke `wait-deploy` if it returns while `CREATING`
- Use `--dry-run` on `create` to validate parameter assembly before submission
- Report health-check pickup as part of deployment verification
- Use `list-logs` with `--keywords` to isolate errors fast; remember **ms** timestamps
- Keep `internet_access_enable` OFF unless the user explicitly needs outbound access
- Mask sensitive envs/values; never echo credentials
- Combine with workspace (`cloudrobo workspace current`) and asset skills to resolve context;
  combine with dispatch to execute embodied tasks