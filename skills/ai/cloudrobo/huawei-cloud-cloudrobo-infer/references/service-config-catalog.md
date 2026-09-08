# Service Config Reference

## InferServiceDto (create inference service request body)

Required fields: `name`, `flavor`, `model`, `workspace_id`, `pool_id`, `pool_type`

| Field | Type | Required | Description | Example |
| ------- | ------ | ---------- | ------------- | --------- |
| `name` | string | Yes | Service name | `vla-infer-v1` |
| `flavor` | string | Yes | Compute flavor | `Ascend-910B` |
| `model` | object | Yes | Model ref: `{model_id, model_version_id, mount_path?}` | `{"model_id":"m1","model_version_id":"mv1","mount_path":"/mnt/model"}` |
| `workspace_id` | string (UUID) | Yes | Workspace ID | `w1b2c3d4-...` |
| `pool_id` | string | Yes | Compute pool ID | `pool-123` |
| `pool_type` | string | Yes | Pool type | `SHARED` / `DEDICATED` |
| `description` | string | No | Service description | `VLA inference` |
| `image_swr_url` | string | No | Custom image SWR URL | `swr.cn-.../repo/img:tag` |
| `cmd` | string | No | Start command | `python serve.py` |
| `envs` | array | No | Env vars | `[{"key":"K","value":"V"}]` |
| `stop_schedule` | object | No | Auto-stop schedule | see below |
| `service_invoke` | object | No | Service invocation config | see below |
| `skill_config` | object | No | Skill configuration | see below |
| `files` | array | No | Attached files | see below |
| `model_ext_metadata` | string (JSON/YAML) | No | Model extension metadata | see below |
| `startup_health` | object | No | Startup probe | see Health Checks |
| `readiness_health` | object | No | Readiness probe | see Health Checks |
| `liveness_health` | object | No | Liveness probe | see Health Checks |
| `deploy_timeout_minutes` | int | No | Deploy timeout (minutes) | `30` |
| `internet_access_enable` | bool | No | Public internet access (default false) | `false` |

> The CLI exposes these JSON-backed fields via `--*-json` flags (e.g. `--envs-json`,
> `--startup-health-json`, `--stop-schedule-json`, `--service-invoke-json`, `--skill-config-json`,
> `--files-json`). `--model-ext-metadata` accepts a raw JSON/YAML string (no `-json` suffix).
> `--model-json` (required) sets the model ref: `{"model_id": "...", "model_version_id": "...", "mount_path": "..."}`.

## Health Checks (three probes)

```json
{
  "startup_health":   { "path": "/startup",   "port": 8080, "period_seconds": 10, "timeout_seconds": 5 },
  "readiness_health": { "path": "/ready",     "port": 8080, "period_seconds": 10, "timeout_seconds": 5 },
  "liveness_health":  { "path": "/live",      "port": 8080, "period_seconds": 10, "timeout_seconds": 5 }
}
```

- `startup_health` — pod startup gate (failures during startup)
- `readiness_health` — traffic routing gate (readiness failures stop routing traffic)
- `liveness_health` — restart trigger (liveness failures restart the pod)

## Log Query Request (list_infer_service_logs)

```json
{
  "start_time": 1750000000000,   // milliseconds (13-digit, required)
  "end_time":   1750003600000,   // milliseconds (13-digit, required)
  "keywords":    "error"
}
```

| Field | Type | Required | Description |
| ------- | ------ | ---------- | ------------- |
| `start_time` | int (ms) | Yes | Start timestamp (**milliseconds**) |
| `end_time` | int (ms) | Yes | End timestamp (**milliseconds**) |
| `keywords` | string | No | Keyword filter |
| `limit` / `line_num` / `is_desc` / `is_count` / `highlight` | — | No | Pagination/format controls |

CLI `list-logs`: `--service-id --start-time <ms> --end-time <ms> [--limit] [--is-desc] [--line-num] [--is-count] [--keywords] [--highlight] [--dry-run]`

## wait-deploy CLI helper

`wait-deploy` is a **client-side polling** helper (not a backend API). It performs:

1. Poll `show_infer_service(service_id)` every **5s** until status is no longer `DEPLOYING`, i.e. `status != "DEPLOYING"`, and returns whatever state follows (e.g., `RUNNING`, `FAILED`, `STOPPED`).
2. Default timeout is **600s** (configurable via `--timeout`, range 1–3600).
3. Returns the final service status when deployment completes or fails.
4. Raises timeout: client raises `RuntimeError`; CLI prints a JSON error and raises `click.ClickException` (non-zero exit).

**Exact client behavior (`InferClient.wait_deploy`, `client.py`):**
```python
def wait_deploy(self, service_id: str, timeout: int = 600) -> dict:
    validate_safe_id(service_id, "service_id")
    elapsed = 0
    while elapsed < timeout:
        service = self.show_infer_service(service_id)   # GET /v1/infer-services/{service_id}
        if service.get("status") != "DEPLOYING":        # status leaves DEPLOYING → return immediately
            return service
        time.sleep(5)                                   # fixed 5s poll interval
        elapsed += 5
    last = self.show_infer_service(service_id)
    raise RuntimeError(
        f"wait-deploy timeout after {timeout}s, last status: {last.get('status')}"
    )
```

Key semantics:
- **Return condition**: `status != "DEPLOYING"`. It does **NOT** wait through `CREATING` — after `create` the backend transitions `CREATING → DEPLOYING → RUNNING`; if `wait-deploy` is invoked while the service is still `CREATING`, it returns immediately with the `CREATING` status (since `CREATING != DEPLOYING`). In practice call it after `create`; if it returns with `CREATING`, immediately re-invoke it to continue blocking on `DEPLOYING`.
- **No independent REST path**: `wait-deploy` maps to no backend endpoint; it repeatedly calls `show_infer_service` (`GET /v1/infer-services/{service_id}`).
- **ID validation**: `validate_safe_id(service_id, "service_id")` — empty/`..`/`/`/`\` rejected.

**Important**: `wait-deploy` does NOT create the service. Call `create` first, then `wait-deploy`.
Do NOT call `start` after `create` — the service auto-deploys (CREATING → DEPLOYING → RUNNING).
`start` is only for restarting a `STOPPED` service.

## Parameter Auto-Discovery Sources

For space asset / custom models, the following `create` parameters can be
auto-discovered from the model's associated algorithm asset and config files.
Embodiment plaza models typically have these pre-configured and skip discovery.

| infer create parameter | Source | Discovery path | Priority |
| ----------------------- | ------ | -------------- | -------- |
| `--model-json.model_id` | Model asset | `show-asset` → `asset_id` | Required |
| `--model-json.model_version_id` | Model version | `show-asset` → `latest_version_id` | Required |
| `--model-json.mount_path` | Algorithm `deployment_config` | action → algorithm asset → `ext_metadata.deployment_config.model_mount_path` | If found |
| `--skill-config-json` | `skill_config.json` file | `download-url?file_name=skill_config.json` → download content | File > ext_metadata |
| `--cmd` | Algorithm `ext_metadata` | action → algorithm asset → `ext_metadata.command` | If found |
| `--image-swr-url` | Algorithm `engine` | action → algorithm asset → `ext_metadata.engine.image_url` | If found |
| `--envs-json` | Algorithm `environment_variables` | action → algorithm asset → array→map | If found |
| `--service-invoke-json` | Algorithm `deployment_config` | action → algorithm asset → `ext_metadata.deployment_config.service_invoke` | If found |
| `--readiness-health-json` | Algorithm `deployment_config` | action → algorithm asset → `ext_metadata.deployment_config.readiness_health` | If found |
| `--model-ext-metadata` | `r2c_config.yaml` or `r2c.json` file | Try `download-url?file_name=r2c_config.yaml`, fallback `r2c.json` | If found |

**download-url API** (not wrapped by CLI/SDK; call HttpClient directly):

```python
from cloudrobo_core.sdk import Config, HttpClient
from cloudrobo_asset.client import AssetClient
import requests

config = Config()
http = HttpClient(config)
asset_client = AssetClient(http)

resp = http.get(
    asset_client._url(f'/v1/assets/{asset_id}/versions/{version_id}/download-url'),
    params={'file_name': '<file_name>'}
)
content = requests.get(resp['file_url']).text
```

**Key rules:**

1. Query proactively after model selection
2. Discovered parameters must be included in `create`
3. User can modify discovered values before deployment
4. Graceful degradation: skip undiscovered parameters silently
5. Bare models (no algorithm): ask user for optional params
6. Envs: asset array `[{"name":"K","default":"V"}]` → infer map `{"K":"V"}`
7. Skill items: keep only `name`+`prompt`; drop `priority`/`description`
8. Config file content is authoritative over ext_metadata

## Status states

Inference service `status` (observed from `list`/`show`) includes lifecycle states such as
`CREATING` / `DEPLOYING` / `RUNNING` / `STOPPED` / `UPDATING` / `DELETING` and failure terminal states
(e.g. `CREATE_FAILED`, `START_FAILED`). Poll `show` until the desired state; on failure use
`list-logs` for diagnosis.

## SDK / CLI coverage matrix

SDK (9 methods) / CLI (9 commands) coverage:

| Operation | SDK method | CLI command | API path |
| ----------- | ------------ | ------------- | ---------- |
| create_infer_service | `create_infer_service(req)` | `create` | `POST /v1/infer-services` |
| list_infer_services | `list_infer_services(**params)` | `list` | `GET /v1/infer-services` |
| show_infer_service | `show_infer_service(service_id)` | `show` | `GET /v1/infer-services/{service_id}` |
| update_infer_service | `update_infer_service(service_id, req)` | `update` | `PUT /v1/infer-services/{service_id}` |
| delete_infer_service | `delete_infer_service(service_id)` | `delete` | `DELETE /v1/infer-services/{service_id}` |
| start_infer_service | `start_infer_service(service_id)` | `start` | `POST /v1/infer-services/{service_id}/start` |
| stop_infer_service | `stop_infer_service(service_id)` | `stop` | `POST /v1/infer-services/{service_id}/stop` |
| list_infer_service_logs | `list_infer_service_logs(service_id, req)` | `list-logs` | `POST /v1/infer-services/{service_id}/logs` |
| wait_deploy | `wait_deploy(service_id, timeout)` | `wait-deploy` | client-side polling |

**Key notes:**

- The backend validates request payloads (including JSON params passed as `str`).
- `wait-deploy` is a client-side polling helper (both SDK and CLI); it does NOT create or start the service.
- `list-logs`/`list_infer_service_logs` require **millisecond** timestamps.

## Command Examples (CLI + SDK)

### Create an Inference Service

```bash
cloudrobo infer create --name <service-name> --flavor "<flavor>" --model-json '{"model_id": "<model-id>", "model_version_id": "<model-version-id>"}' --workspace-id <workspace-id> --pool-id pool-<resource-id> --pool-type <pool-type> [--description "desc"] [--envs-json '[...]'] [--stop-schedule-json '{"duration": 60, "time_unit": "MINUTES"}'] [--dry-run]
```

```python
from cloudrobo_core.sdk import Config, HttpClient
from cloudrobo_infer import InferClient

config = Config()
http_client = HttpClient(config)
client = InferClient(http_client)

service = client.create_infer_service({
    "name": "vla-infer-v1",
    "flavor": "<flavor>",
    "model": {"model_id": "<mid>", "model_version_id": "<mvid>"},
    "workspace_id": config.workspace_id,
    "pool_id": "pool-<resource-id>",
    "pool_type": "<pool-type>",
    "stop_schedule": {"duration": 60, "time_unit": "MINUTES"},
    "description": "VLA inference service"
})
print(service)  # includes service_id
```

### Wait-Deploy (CLI convenience)

```bash
cloudrobo infer wait-deploy --service-id <service-id> [--timeout 600]
```

```python
from cloudrobo_core.sdk import Config, HttpClient
from cloudrobo_infer import InferClient

config = Config()
http_client = HttpClient(config)
client = InferClient(http_client)

# After create, the service auto-deploys (CREATING → DEPLOYING → RUNNING).
# Do NOT call start_infer_service — it will fail with 400 on a DEPLOYING service.
# start_infer_service is only for restarting a STOPPED service.

# Wait for deployment to complete
result = client.wait_deploy("<service-id>", timeout=600)
print(result)  # includes final status (RUNNING, FAILED, etc.)
```

### List Inference Services

```bash
cloudrobo infer list --workspace-id <ws> [--limit 20] [--offset 0] [--status <status>]
  [--name <name>] [--model-id <mid>] [--model-name <mn>] [--model-version-id <mvid>]
  [--model-version-name <mvn>] [--user-name <un>] [--user-id <uid>]
  [--sort-key <key>] [--sort-dir <dir>]
```

```python
services = client.list_infer_services(workspace_id=config.workspace_id)
for s in services.get("items", []):
    print(s["name"], s["status"], s["model"]["model_id"])
```

### Show Service Detail

```bash
cloudrobo infer show --service-id <service-id>
```

```python
svc = client.show_infer_service("<service-id>")
print(svc["name"], svc["status"])
```

### Start / Stop Service

```bash
cloudrobo infer start --service-id <service-id>
cloudrobo infer stop  --service-id <service-id>
```

```python
client.start_infer_service("<service-id>")
client.stop_infer_service("<service-id>")
```

### Update Service

```bash
cloudrobo infer update --service-id <service-id> --description "new desc" [--model-ext-metadata '<json>'] [--dry-run]
```

```python
client.update_infer_service("<service-id>", {"description": "new desc"})
```

### Delete Service

```bash
cloudrobo infer delete --service-id <service-id> [--dry-run]
```

```python
client.delete_infer_service("<service-id>")
```

### List Service Logs

```bash
cloudrobo infer list-logs --service-id <service-id> --start-time <milliseconds> --end-time <milliseconds> [--limit 100] [--keywords "error"] [--is-desc] [--line-num <num>] [--is-count] [--highlight] [--dry-run]
```

```python
import time
end_ms = int(time.time() * 1000)
start_ms = end_ms - 3600_000
logs = client.list_infer_service_logs(
    "<service-id>",
    {"start_time": start_ms, "end_time": end_ms, "keywords": "error"},
)
print(logs)
```

> **Note**: `list-logs`/`list_infer_service_logs` require **millisecond** timestamps.

## Parameter Resolution & Confirmation

| Parameter | Source | Required | Confirmation Needed |
| ----------- | -------- | ---------- | --------------------- |
| `--workspace-id` | `cloudrobo workspace current` (or `list` + `use`) | Yes | Let user choose if no default |
| `--model-json` | `list-publication-assets` / `list-assets --catalog-id` / `search-assets` → `asset_id` + `show-asset` → `latest_version_id` | Yes (create) | Let user choose model; assemble `{"model_id": "...", "model_version_id": "..."}`; verify `ONLINE_DEPLOYMENT` = `ENABLE` |
| `--pool-id` | `cloudrobo resource list-pools --resource-type MODELARTS` → `pool-{resource_id}` (prefix `pool-`) | Yes (create) | Let user choose from available pools |
| `--pool-type` | `cloudrobo resource list-pools --resource-type MODELARTS` → `pool_type` | Yes (create) | Paired with pool selection |
| `--flavor` | `cloudrobo resource list-pools --resource-type MODELARTS` → `config.flavor` (CPU/GPU/ASCEND) | Yes (create) | Let user choose from pool's flavor list |
| `--stop-schedule-json` | Constructed: `{"duration": <N>, "time_unit": "MINUTES"}` | Yes (create, in practice) | Set duration with user consent |
| `--service-id` | User or prior `create` output | Yes (show/start/stop/update/delete/logs/wait-deploy) | Verify before mutating |
| `--start-time`/`--end-time` | User | Yes (list-logs) | **milliseconds** |
| `--cmd` | Algorithm asset `ext_metadata.command` | No (create) | Show discovered value; user may modify |
| `--image-swr-url` | Algorithm asset `ext_metadata.engine.image_url` | No (create) | Show discovered value; user may modify |
| `--envs-json` | Algorithm asset `ext_metadata.environment_variables` (array→map) | No (create) | Show discovered value; user may modify |
| `--skill-config-json` | `download-url?file_name=skill_config.json` | No (create) | Show discovered value; check `strict` field for custom prompt support; user may modify |
| `--service-invoke-json` | Algorithm `deployment_config.service_invoke` | No (create) | Show discovered value; user may modify |
| `--readiness-health-json` | Algorithm `deployment_config.readiness_health` | No (create) | Show discovered value; user may modify |
| `--model-ext-metadata` | `download-url?file_name=r2c_config.yaml` (fallback `r2c.json`) | No (create) | Show discovered value; user may modify; if both files missing, ask user whether to provide config (warn: missing config prevents robo-dispatcher operations) |
| `--model-json.mount_path` | Algorithm `deployment_config.model_mount_path` | No (create) | Show discovered value; user may modify |
| `--dry-run` | — | No | Preview without submitting |
| Health-check JSONs | User | No (create) | Validate JSON schema |

**Mutating operations** (create/start/stop/update/delete) must prompt the user
for confirmation before execution, especially start because it consumes pool resources.

## Edge Cases

| Scenario | Handling |
| ---------- | ---------- |
| Missing `model_id` | create requires model; query asset or ask user |
| Invalid JSON param | create validates JSON via `_parse_json_options`; raises `click.BadParameter` with clear message |
| Client-side validation | `@validate_params` decorator on `create`/`update`/`list-logs` validates request body before HTTP call; raises `ValidationError` |
| Wrong timestamp unit | `list-logs` requires **ms**; if seconds given, convert (×1000) |
| Service not found | show/start/stop/delete return `ResourceNotFoundError`; verify `service_id` |
| Path traversal | `validate_safe_id(service_id)` blocks `../` input |
| Pool capacity | START may stay pending if pool lacks resources; report & reduce or wait |
| Deploy timeout | `wait-deploy` defaults to 600s; extend via `--timeout` |
| Deployment FAILED | Use health-check JSON, check model artifact, then `list-logs` for diagnosis. **Never auto-delete** — ask user confirmation before any `delete` |
| Public internet access | Default OFF; enable via the valueless CLI flag `--internet-access-enable` (takes no value — `=true` or trailing `true` errors) with user consent. SDK layer accepts `"1"`/`"true"`/`"yes"` strings for the boolean field |
| AK/SK not set | Operations fail at HTTP signing; set `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK` |
| 403 "Model asset permission deny" | Check `show-asset` — `ONLINE_DEPLOYMENT` action must be `ENABLE`; model status must be `RELEASE` (not `DRAFT`/`CREATING`); plaza models may need subscription first |
| 500 "Internal error" on create | `--model-json`'s `model_version_id` must be `latest_version_id` from `show-asset`, NOT `actions[].algorithm.version_id` |
| Missing `--stop-schedule-json` | Not CLI-required but **required by backend**; without it creation fails. Format: `{"duration": 60, "time_unit": "MINUTES"}` |
| `list-assets --repository-id` returns empty | Use `--catalog-id <asset_catalog_id>` (from `workspace current`) instead — `--repository-id` + `--type` filter is unreliable |
| model_id/flavor/pool_id | Never hardcoded; resolved dynamically via query commands, then user selects |
| No algorithm association | Bare model; ask user whether to manually provide optional params (cmd/image/envs/etc.) |
| download-url 404 | Config file not uploaded; skip that parameter silently |
| skill_config.json extra fields | Filter to only `name`+`prompt`; drop `priority`/`description` |
| envs format mismatch | Asset uses array `[{"name":"K","default":"V"}]`; convert to map `{"K":"V"}` for infer |
| r2c_config.yaml not found | Fallback to `r2c.json`; if both missing, ask user whether to provide their own r2c config file. Warn that missing `--model-ext-metadata` will prevent robo-dispatcher operations from working (see `huawei-cloud-cloudrobo-dispatch` skill for details) |
| Cross-skill invocation | This skill does not call other skills; it consumes model IDs (train/asset) and produces a `service_id` consumable by dispatch |
| Mutating operations | create/start/stop/update/delete should be confirmed by the user |
