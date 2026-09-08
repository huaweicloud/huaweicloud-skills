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
  - inference
  - service-deployment
  - model-serving
  - infer-service
  - wait-deploy
  - model-inference
---

> **Windows / PowerShell:** Examples use bash syntax. To run on Windows PowerShell:
> - Flatten `\` line continuations to a single line, or end lines with a backtick.
> - Set env vars with `$env:NAME="value"` instead of `export NAME="value"`.
> - Single-quoted JSON `'{"a":"b"}'` works as-is.

## Overview

The `cloudrobo-infer` skill manages the full lifecycle of CloudRobo **inference services**
(also called model-serving / inference-service). It lets the agent deploy a model (identified
by `model_id` + `model_version_id` passed as a `--model-json` JSON object) into a long-running
inference service, monitor and operate that service (start / stop / update / delete / logs),
and use `wait-deploy` to poll until the service status is no longer `DEPLOYING`
(`status != "DEPLOYING"`), at which point it returns any other state (e.g., RUNNING, FAILED, STOPPED).
> Note: `wait-deploy` only waits on the `DEPLOYING` phase — it does NOT wait through `CREATING`.
> Read the [Wait-Deploy](references/service-config-catalog.md#wait-deploy-cli-helper) reference for exact semantics.

**Applicable scenarios:**

- **Model deployment** — Deploy a model as an inference service (create → wait-deploy)
- **Wait-Deploy** — Poll every 5s until service status is no longer `DEPLOYING` (5s interval, 600s default)
- **Service O&M** — List deployed services, show detail, update config, start/stop
- **Log diagnosis** — `list-logs` with millisecond time range and keyword filter
- **Cross-skill orchestration** — Consume models exported by `cloudrobo-train`; expose the
  service to `robo-dispatcher` for embodied tasks (via `infer_service_id`).

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

All operations target the `cloudrobo-service` backend and require a valid `workspace_id`
(default workspace is used unless explicitly provided). Deploying a service consumes compute
(pool) resources — always confirm before starting a long-running service.

## Prerequisites

- See `references/cli-installation-guide.md` for CLI installation, AK/SK authentication, and
  workspace configuration.
- A valid `workspace_id` (resolve via `cloudrobo workspace current` or `list` + `use`).
- A deployable model: `model_id` (=`asset_id`) + `model_version_id` (=`latest_version_id`),
  passed to `create` as a single `--model-json` argument:
  `--model-json '{"model_id": "<asset_id>", "model_version_id": "<latest_version_id>"}'`.
  The model must have `ONLINE_DEPLOYMENT` action with `status: "ENABLE"` in its `show-asset`
  output. Models in `DRAFT`/`CREATING` status cannot be deployed (403 error).
- A compute pool: `pool_id` (prefix `resource_id` with `pool-`, i.e. `pool-<resource_id>`)
  + `pool_type` + `flavor`, resolved via `cloudrobo resource list-pools --resource-type MODELARTS`. Only pools with
  `status: "AVAILABLE"` are usable.
- `--stop-schedule-json` is **required in practice** for `create` (though not CLI-required).
  Format: `{"duration": <N>, "time_unit": "MINUTES"}`.

## Workflow

### Natural-Language-First Principle

Every workflow below starts from a user intent (1-2 sentences), not from manual CLI/SDK
orchestration. The skill then drives the matching command chain and reports state feedback
(status changes, polling progress).

### Model Deployment Workflow (interactive parameter resolution)

Scenario: "我想创建一个推理服务" / "Deploy model X as an inference service."

Core principle: **query each required parameter → present options → let user choose → assemble
full command → execute.**

1. **Resolve workspace** — `cloudrobo workspace current`.
   - If a default workspace is set → use `workspace_id` and `asset_catalog_id` directly.
   - If not set → `cloudrobo workspace list` → present workspace names + IDs to the user →
     `cloudrobo workspace use --workspace-id <id>` → re-run `current` to confirm.

2. **Ask model source & type** — ask the user two questions in this order:
   - **Source** (where to search, ask first): embodiment plaza (具身广场), workspace assets
     (空间资产), or custom (自定义). **The source decides the entire parameter policy below** —
     embodiment plaza models are pre-configured on the platform and must **only** carry the
     required core parameters; space asset / custom models run the auto-discovery flow.
   - **Type** (by `ext_metadata.model_type`, ask second): perception (感知), vln (导航),
     vla (操作), planning (规划).
   - If the user is vague (e.g. "so101 相关的模型") → skip both questions and use
     `search-assets` for a global keyword search.
   - Once the source is known, branch immediately to the matching parameter policy in
     the [Model Source → Parameter Policy](#model-source--parameter-policy) table before
     assembling `create`.

3. **Query models** — search based on the user's choice:
   - **Embodiment plaza**: `cloudrobo asset list-publication-assets --type model
     --actions ONLINE_DEPLOYMENT --action-status ENABLE` (returns RELEASE models with
     online deployment enabled).
   - **Workspace assets**: `cloudrobo asset list-assets --catalog-id <asset_catalog_id>
     --type model` (note: use `--catalog-id` from workspace, NOT `--repository-id`).
   - **Keyword search**: `cloudrobo asset search-assets --keyword "<keyword>" --type model`.
   - Present matching models (name, asset_id, status, model_type) to the user for selection.

4. **Resolve model version** — `cloudrobo asset show-asset --asset-id <asset_id>`.
   - Use `latest_version_id` to populate the `model_version_id` field in `--model-json`.
   - If `version_count > 1` → `cloudrobo asset list-versions --asset-id <id>` → let user choose.
   - **Verify deployability**: check `actions` array — `ONLINE_DEPLOYMENT` must have
     `status: "ENABLE"`. If `DISABLE`, the model cannot be deployed (403 error).
   - **Verify model status**: `status` should be `RELEASE` (plaza) or published state.
     `DRAFT`/`CREATING` models will be rejected with 403 "Model asset permission deny".

5. **Auto-discover deployment parameters — space asset / custom models ONLY**.
   **Embodiment plaza models (具身广场): skip this entire step and DO NOT carry any of the
   parameters below (nothing here, and nothing from `--cmd`/`--image-swr-url`/`--envs-json`/
   `--skill-config-json`/`--service-invoke-json`/`--readiness-health-json`/`--model-ext-metadata`/
   `--model-json.mount_path`).** Plaza models are pre-configured on the platform — their
   orchestration, image, envs, skills, health probes and r2c mapping are already bound to the
   model. Passing these extra parameters for a plaza model risks invalid/config-mismatch
   deployment and is exactly the "不该带的参数" this workflow forbids.

   **Space asset / custom models**: after resolving the model version, check whether the model
   has an associated algorithm asset that provides deployment parameters. These are auto-discovered
   from the model's algorithm asset and config files:

   a. **Check ONLINE_DEPLOYMENT action** — in the `show-asset` output from Step 4,
      look at `actions[]` for `type: "ONLINE_DEPLOYMENT"`. If present and
      `status: "ENABLE"`, it contains `algorithm.asset_id` + `algorithm.version_id`
      pointing to the associated algorithm asset.

   b. **Query algorithm asset** (if action found) —
      `cloudrobo asset show-asset --asset-id <algorithm.asset_id>` then
      `cloudrobo asset show-version --asset-id <algorithm.asset_id>
      --version-id <algorithm.version_id>` to get the algorithm's `ext_metadata`:
      - `ext_metadata.command` → `--cmd`
      - `ext_metadata.engine.image_url` → `--image-swr-url`
      - `ext_metadata.environment_variables` (array of `{"name":"K","default":"V"}`)
        → convert to map `{"K":"V"}` → `--envs-json`
      - `ext_metadata.deployment_config.model_mount_path` → `--model-json.mount_path`
      - `ext_metadata.deployment_config.service_invoke` → `--service-invoke-json`
      - `ext_metadata.deployment_config.readiness_health` → `--readiness-health-json`

   c. **Download skill_config.json** — via the `download-url` API (CLI/SDK not
      wrapped; use HttpClient directly):
      ```python
      from cloudrobo_core.sdk import Config, HttpClient
      from cloudrobo_asset.client import AssetClient
      import requests

      config = Config()
      http = HttpClient(config)
      asset_client = AssetClient(http)

      resp = http.get(
          asset_client._url(f'/v1/assets/{asset_id}/versions/{version_id}/download-url'),
          params={'file_name': 'skill_config.json'}
      )
      skill_config = requests.get(resp['file_url']).text
      ```
      - Filter skill items to only `name` + `prompt` fields (drop `priority`/
        `description` extra fields) → `--skill-config-json`
      - **`strict` field**: controls whether the deployed service accepts only
        predefined skill prompts or also allows user custom prompts:
        - `strict: true` — service only accepts the predefined skills (matched
          by `name`); user cannot input custom prompts at runtime
        - `strict: false` or omitted — service allows users to input their own
          custom prompts at runtime, in addition to the predefined skills
        - If the customer wants to accept custom prompts, ensure `strict` is
          `false` or not present in the skill_config.json

   d. **Download r2c config** — same `download-url` API, fallback rule:
      - Try `file_name=r2c_config.yaml` first
      - If that fails (404), try `file_name=r2c.json`
      - If both fail (no r2c config file found):
        - **Ask the user** whether they want to provide their own r2c config file
        - Explain that while missing `--model-ext-metadata` does not block
          deployment, it will prevent subsequent robo-dispatcher operations
          from working (see `huawei-cloud-cloudrobo-dispatch` skill for details
          on robo-dispatcher workflows)
        - If user provides a config file, use its content as `--model-ext-metadata`
        - If user declines, proceed without `--model-ext-metadata` (warn that
          robo-dispatcher operations will not be available)
      - File content (raw string) → `--model-ext-metadata`

   > **Priority**: config files > ext_metadata fields > ask user. If a parameter
   > cannot be discovered, skip it silently (do not block deployment). For
   > "bare" models with no algorithm association, ask the user whether to
   > manually provide optional parameters.

6. **Resolve pool & flavor** — `cloudrobo resource list-pools --resource-type MODELARTS`.
   - Present available pools (resource_name, pool_type, status, flavors) to the user.
   - Only pools with `status: "AVAILABLE"` are usable.
   - Pool fields: `resource_id` → `--pool-id` (prefix with `pool-`, e.g.
     `pool-d1cc6d45-...`), `pool_type` → `--pool-type` (Choice: `DEDICATED` / `SHARED`).
   - Flavors are under `config.flavor` grouped by hardware type (CPU/GPU/ASCEND).
   - Let the user select a pool and a flavor string (e.g. `"1 * SNT9B2 | 24 vCPUs | 192 GiB"`).

7. **Confirm parameters & deploy** — present the `create` command to the user, **choosing the
   variant that matches the model source from Step 2** (see the
   [Model Source → Parameter Policy](#model-source--parameter-policy) table). The two variants
   must NOT be mixed.

   **Variant A — embodiment plaza model (具身广场, required core parameters ONLY):**
   ```bash
   cloudrobo infer create --name <service-name> --flavor "<flavor>" --model-json '{"model_id": "<asset_id>", "model_version_id": "<latest_version_id>"}' --workspace-id <workspace_id> --pool-id pool-<resource_id> --pool-type <pool_type> --stop-schedule-json '{"duration": 60, "time_unit": "MINUTES"}' [--dry-run]
   ```
   - **Do NOT add** `--cmd`/`--image-swr-url`/`--envs-json`/`--skill-config-json`/
     `--service-invoke-json`/`--readiness-health-json`/`--model-ext-metadata`/`--model-json.mount_path`.
     Plaza models are pre-configured on the platform; carrying these extra parameters is a
     deployment risk and is explicitly forbidden by this workflow.

   **Variant B — space asset / custom model (空间资产/自定义, with auto-discovered params):**
   ```bash
   cloudrobo infer create --name <service-name> --flavor "<flavor>" --model-json '{"model_id": "<asset_id>", "model_version_id": "<latest_version_id>", "mount_path": "<mount_path>"}' --workspace-id <workspace_id> --pool-id pool-<resource_id> --pool-type <pool_type> --stop-schedule-json '{"duration": 60, "time_unit": "MINUTES"}' [--cmd "<command>"] [--image-swr-url "<image_url>"] [--envs-json '{"KEY":"VALUE"}'] [--skill-config-json '{"skills":[{"name":"...","prompt":"..."}],"strict":true}'] [--service-invoke-json '{"auth_type":"...","port":8080,"protocol":"HTTP"}'] [--readiness-health-json '{"path":"/ready","port":8080}'] [--model-ext-metadata '<r2c_config_file_content>'] [--dry-run]
   ```
   - Only include parameters that were actually discovered (Step 5); omit undiscovered ones.
   - `--model-json.mount_path` only included when algorithm's `deployment_config` provides it.
   - `--envs-json` must be converted from asset array format to map format.
   - `--skill-config-json` skill items keep only `name`+`prompt`; drop `priority`/`description`.
   - `--model-ext-metadata` takes the raw file content (string).
   - Recommend `--dry-run` first to validate parameter assembly.
   - `--stop-schedule-json` is **required in practice** (though not CLI-required); without it
     the backend may reject the creation. Format: `{"duration": <N>, "time_unit": "MINUTES"}`.
   - After dry-run succeeds, confirm with the user and execute without `--dry-run`.
   - Record the returned `service_id`.

8. **Wait for deployment** — `cloudrobo infer wait-deploy --service-id <sid>` to poll every
   5s until status is no longer `DEPLOYING` (`status != "DEPLOYING"`), returning whatever state
   follows (e.g., `RUNNING`, `FAILED`).
   - After `create`, the service auto-enters `CREATING` → `DEPLOYING`. **Do NOT call `start`**
     immediately after `create` — it will return 400 "Status DEPLOYING does not support start".
   - `start` is only for restarting a `STOPPED` service, not for initial deployment.
   - **Precise semantics**: `wait-deploy` returns the moment `status != "DEPLOYING"`. It does NOT
     wait through the `CREATING` phase — if you call it while the service is still `CREATING`, it
     returns immediately with the `CREATING` status. In practice, call it after `create` and let
     the backend transition `CREATING → DEPLOYING → RUNNING`; the helper blocks on `DEPLOYING`.

9. **Report** — output `service_id`, model name, flavor, and final status.
   - If status is `FAILED` → run `cloudrobo infer list-logs` for diagnosis.
   - **Never auto-delete a failed service.** If cleanup is needed, present the `delete`
     command and **ask the user for explicit confirmation** before executing it.

> **Asset note**: model_id/version_id/flavor/pool_id must be resolved dynamically via the
> query commands above; never hardcode them. Always let the user choose from queried options.

### Model Source → Parameter Policy (authoritative decision table)

This table is the **single source of truth** for which `create` parameters to carry, based on
the model source resolved in Step 2. It is referenced by `cloudrobo-model-workflow` Stage 3 to
keep both skills consistent. When creating any inference service, resolve the model source first
and then apply exactly the matching column — **do not mix variants**.

| Model source (from Step 2) | Search command (Step 3) | Auto-discovery (Step 5) | `create` parameters to carry |
|----------------------------|-------------------------|--------------------------|------------------------------|
| **Embodiment plaza (具身广场)** | `asset list-publication-assets --type model --actions ONLINE_DEPLOYMENT --action-status ENABLE` | **SKIP entirely** — model is pre-configured on platform | **Required core only**: `--name`, `--flavor`, `--model-json` (`model_id`+`model_version_id`), `--workspace-id`, `--pool-id`, `--pool-type`, `--stop-schedule-json`. **Do NOT carry** `--cmd`/`--image-swr-url`/`--envs-json`/`--skill-config-json`/`--service-invoke-json`/`--readiness-health-json`/`--model-ext-metadata`/`--model-json.mount_path` |
| **Space asset / custom (空间资产/自定义)** | `asset list-assets --catalog-id <asset_catalog_id> --type model` / `search-assets --keyword ...` | **Run Step 5 fully** — query algorithm asset (cmd/image/envs/mount_path/service-invoke/readiness-health) + download `skill_config.json` + r2c config | Required core **plus** every parameter actually discovered in Step 5; omit undiscovered ones silently |
| Unknown model id (user passed explicit id) | `asset show-asset --asset-id <id>` | Determine from `show-asset`: if the model carries an `ONLINE_DEPLOYMENT` action pointing to a platform algorithm → treat as space-asset path (run Step 5). If the model's deployment config is self-contained/pre-configured → carry required core only | As per the resolved path |

> **Rationale**: Embodiment plaza models bundle their orchestration, image, envs, health probes,
> skills and r2c feature mapping on the platform. Re-supplying these in `create` for a plaza model
> is redundant and risks invalid/mismatched deployment (this is the "不该带的参数不要带" rule). Space
> asset / custom models have no such bundled config, so their parameters must be auto-discovered and
> passed explicitly.


### Wait-Deploy Workflow (CLI convenience)

Scenario: "Wait for this inference service to finish deploying."

1. `cloudrobo infer wait-deploy --service-id <sid> [--timeout 600]`
   - `wait-deploy` is a **CLI client-side polling helper**: it polls `show` every 5s until the
     service status is no longer `DEPLOYING` (`status != "DEPLOYING"`) and returns any other state
     (e.g., `RUNNING`, `FAILED`, `STOPPED`).
   - Default timeout is 600s (CLI `--timeout` range 1–3600); if exceeded, the client raises
     `RuntimeError` and the CLI reports a timeout error (JSON error + `ClickException`, non-zero exit).
2. **Feedback** — report final status; on `FAILED` suggest `list-logs` for diagnosis.

> **Note**: `wait-deploy` does NOT create the service. Call `create` first, then `wait-deploy`.
> Do NOT call `start` after `create` — the service auto-deploys (CREATING → DEPLOYING → RUNNING).
> `start` is only for restarting a `STOPPED` service.

### Service O&M / Lookup Workflow (module + workspace)

Scenario: "What inference services are running in my workspace?"

1. `cloudrobo infer list --workspace-id <ws> [--status <status>] [--model-id <mid>]
   [--name <name>] [--model-name <mn>] [--model-version-id <mvid>] [--model-version-name <mvn>]
   [--user-name <un>] [--user-id <uid>]` with pagination (`--limit`/`--offset`)
   and sorting (`--sort-key`/`--sort-dir`).
2. `cloudrobo infer show --service-id <sid>` for a full config snapshot.
3. Report status and key fields (model, flavor, status, pool).

### Service Start/Stop Workflow (module)

Scenario: "Stop the inference service behind this API." / "Bring it back up."

1. Confirm the service via `show --service-id <sid>`.
2. `cloudrobo infer stop --service-id <sid>` or `cloudrobo infer start --service-id <sid>`
   (mutating; confirm before executing).
3. Poll `show` until the desired terminal state (`STOPPED` / `RUNNING`).

### Log Diagnosis Workflow (module)

Scenario: "Why is my deployed service failing? Show me its logs."

1. `cloudrobo infer list-logs --service-id <sid> --start-time <ms> --end-time <ms>` — both
   timestamps are **milliseconds** (13-digit). Optionally filter `--keywords`, `--limit`,
   `--line-num`, `--is-count`, `--highlight`, `--is-desc`.
2. Review log lines and correlate with `show` status (e.g. `CREATE_FAILED`/`START_FAILED`).
3. Suggest remediation (pool capacity, model artifact, health-check config).

### Service Update / Deletion Workflow (module)

Scenario: "Reconfigure this service" / "Shut down and remove this service."

- **Update** — `cloudrobo infer update --service-id <sid> [--description <desc>]
  [--model-ext-metadata <json>] [--dry-run]` (mutating; confirm).
- **Delete** — `cloudrobo infer delete --service-id <sid> [--dry-run]` (mutating; irreversible; confirm).

### Combined Workflow A — Deploy a trained model (infer + train + asset)

Scenario: "I trained a VLA model; deploy it as an inference service."

1. Resolve workspace: `cloudrobo workspace current` (or `list` + `use`).
2. Query the trained model: `cloudrobo asset list-assets --catalog-id <asset_catalog_id>
   --type model` (or use the train skill's `output_models`); obtain `asset_id`.
3. Resolve model version: `cloudrobo asset show-asset --asset-id <asset_id>` → use
   `latest_version_id` in the `model_version_id` field of `--model-json`. Verify
   `ONLINE_DEPLOYMENT` action `status: "ENABLE"`.
4. Resolve pool & flavor: `cloudrobo resource list-pools --resource-type MODELARTS` → let user select `resource_id`
   and `flavor`.
4a. A trained model is a **space asset** → follow **Variant B / space-asset path** of the
    Model Deployment Workflow. (If the trained model has algorithm association) Auto-discover
    deployment parameters per Step 5 — query algorithm asset for
    cmd/image/envs/service-invoke/readiness-health, download skill_config.json and r2c config.
    Carrying these is the correct behavior for a space asset; the "do not carry" rule only
    applies to embodiment plaza models.
5. `cloudrobo infer create --name <name> --flavor "<flavor>"
   --model-json '{"model_id": "<asset_id>", "model_version_id": "<latest_version_id>"}'
   --workspace-id <ws> --pool-id pool-<resource_id>
   --pool-type <type> --stop-schedule-json '{"duration": 60, "time_unit": "MINUTES"}'`
   — add any parameters actually discovered in step 4a (per Step 7 Variant B).
6. `cloudrobo infer wait-deploy --service-id <sid>` — polls every 5s until status is no longer
   `DEPLOYING` (service auto-deploys after create; do NOT call `start` — it will fail with 400)
7. Report `service_id` and status. The service is now consumable.

> **Parameter auto-discovery**: For space asset / custom models, deployment parameters
> (cmd, image, envs, skill-config, health-checks, model-ext-metadata, etc.) are
> auto-discovered from the model's associated algorithm asset and config files per
> Step 5 above. See `references/service-config-catalog.md` → "Parameter Auto-Discovery
> Sources" for the full discovery table, download-url API code, and key rules.

## CLI Command Summary

```bash
cloudrobo infer <command> [OPTIONS]
```

| Subcommand | Description | Key options |
| ---------- | ----------- | ----------- |
| `create` | Deploy a new inference service | `--name`, `--flavor`, `--model-json`, `--workspace-id`, `--pool-id`, `--pool-type`, `--stop-schedule-json` |
| `wait-deploy` | Poll until deployment completes | `--service-id`, `--timeout` |
| `list` | List inference services | `--workspace-id`, `--status`, `--limit`, `--offset` |
| `show` | Show service detail | `--service-id` |
| `start` / `stop` | Start or stop a service | `--service-id` |
| `update` | Update service config | `--service-id`, `--description`, `--model-ext-metadata` |
| `delete` | Delete a service | `--service-id` |
| `list-logs` | Query service logs | `--service-id`, `--start-time` (ms), `--end-time` (ms), `--keywords` |

> **Full CLI/SDK examples, parameter resolution table, and edge cases**: see
> `references/service-config-catalog.md` → "Command Examples", "Parameter
> Resolution & Confirmation", and "Edge Cases".
> SDK exposes 9 methods, CLI exposes 9 commands (0 gaps);
> `wait-deploy` is a client-side polling helper available in both CLI and SDK.
> When CLI is inconvenient (dynamic JSON, cross-package queries), use the Python
> SDK directly — `InferClient` exposes the 9 methods.

## Reference Documents

- [CLI Installation Guide](references/cli-installation-guide.md) — cloudrobo CLI installation and configuration
- [IAM Policies](references/iam-policies.md) — Least-privilege credential & access model
- [Verification Method](references/verification-method.md) — Verification method details
- [Dataflow Diagram](references/dataflow-diagram.md) — Mermaid data flow diagrams
- [Acceptance Criteria](references/acceptance-criteria.md) — Acceptance criteria
- [Service Config Reference](references/service-config-catalog.md) — InferServiceDto fields, health checks, status, logs, parameter auto-discovery, CLI/SDK command examples, parameter resolution & confirmation, edge cases, coverage matrix

## Edge Cases

> See `references/service-config-catalog.md` → "Edge Cases" for the full
> scenario-handling table (missing model_id, invalid JSON, wrong timestamp unit,
> 403 permission deny, 500 internal error, missing stop-schedule, r2c config
> fallback, envs format mismatch, cross-skill invocation, etc.).

## Verification Method

### Specification Compliance Verification

```bash
bash scripts/test-cli-commands.sh
```

### Functional Testing

```bash
bash scripts/test-cli-commands.sh
```

### Test Cases

See `templates/test-vars.json` for the full test case list covering deployment, wait-deploy,
service lifecycle, logs, and safety scenarios.

### Verification Checklist

- After `create`, service appears in `list` with correct status
- After `wait-deploy`, service status is no longer `DEPLOYING` (`status != "DEPLOYING"`; reports timeout/failure with log guidance)
- After `start`/`stop`, `show` reflects the new status
- After `delete`, `show` returns not-found
- `list-logs` with **ms** timestamps returns log lines; keyword filter works
- Invalid JSON / path traversal are rejected; `../` blocked by `validate_safe_id`
- Mutating operations (especially start) prompt user confirmation

## Best Practices

- Resolve each `create` parameter via query commands, then let the user choose — never hardcode
- **Model source drives parameter policy**: resolve the source (Step 2) first, then apply the
  [Model Source → Parameter Policy](#model-source--parameter-policy) table. Embodiment plaza models
  carry **required core params only** (never `--cmd`/`--image-swr-url`/`--envs-json`/
  `--skill-config-json`/`--service-invoke-json`/`--readiness-health-json`/`--model-ext-metadata`/
  `--model-json.mount_path`); space asset / custom models run Step 5 auto-discovery and carry
  whatever is actually discovered
- Model search: prefer `list-publication-assets --actions ONLINE_DEPLOYMENT --action-status ENABLE`
  for deployable plaza models; use `list-assets --catalog-id <id>` for workspace models;
  use `search-assets --keyword "<kw>"` for fuzzy/keyword search
- `--model-json`'s `model_version_id` must be `latest_version_id` from `show-asset`, NOT `actions[].algorithm.version_id`
- Always include `--stop-schedule-json '{"duration": N, "time_unit": "MINUTES"}'` in `create`
- Use `wait-deploy` after `create` to poll until deployment completes (5s interval, 600s default). Do NOT call `start` after `create` — the service auto-deploys
- `wait-deploy` returns when `status != "DEPLOYING"`; it only blocks on the `DEPLOYING` phase (not `CREATING`), so call it after `create` and let the backend transition `CREATING → DEPLOYING → RUNNING` — if it returns while still `CREATING`, immediately re-invoke `wait-deploy`
- Use `--dry-run` on `create` to validate parameter assembly before actual submission
- Report health-check pickup as part of deployment verification
- Use `list-logs` with `--keywords` to rapidly isolate errors; remember **ms** timestamps
- Keep `internet_access_enable` OFF unless the user explicitly needs outbound access
- Mask sensitive envs/values; never echo credentials
- Combine with workspace (`cloudrobo workspace current`) and asset skills to resolve workspace/model context; combine with dispatch to execute embodied tasks
