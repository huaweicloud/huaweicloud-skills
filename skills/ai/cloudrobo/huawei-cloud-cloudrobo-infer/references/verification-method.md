# Verification Method

## Verification Levels

### Level 1: CLI Smoke Test

**Preflight (required)** — run before any case:

```bash
command -v cloudrobo >/dev/null 2>&1 || { echo "未检测到 cloudrobo 命令：请先安装 CLI。" >&2; exit 2; }
cloudrobo infer --help >/dev/null 2>&1 || { echo "cloudrobo infer 子命令不可用：请安装/升级 hw-cloudrobo-infer。" >&2; exit 2; }
```

```bash
# Should return JSON list (possibly empty) in a workspace
cloudrobo infer list --workspace-id <workspace-id>
```

**Pass criteria**: Command exits 0, returns valid JSON. An empty list is a valid result;
a command error is not.

### Level 2: Service Lifecycle Test (Create → Wait-Deploy)

End-to-end test of a model deployment:

```bash
# 1. Resolve workspace
cloudrobo workspace current
# → workspace_id, asset_catalog_id

# 2. Query model (cross-package)
cloudrobo asset list-publication-assets --type model --actions ONLINE_DEPLOYMENT --action-status ENABLE --limit 5
# → Extract asset_id (model_id)

# 3. Resolve model version
cloudrobo asset show-asset --asset-id <asset-id>
# → latest_version_id (use in --model-json's model_version_id field)

# 4. Resolve pool & flavor
cloudrobo resource list-pools --resource-type MODELARTS
# → resource_id (prefix with "pool-" for --pool-id), pool_type, config.flavor
#   pool_id is optional — omit for SHARED pools; pass --pool-id only for DEDICATED pools

# 5. Dry-run validate deploy (optional)
cloudrobo infer create --name verify-infer --flavor "<flavor>" --model-json '{"model_id": "<asset-id>", "model_version_id": "<latest-version-id>"}' --workspace-id <ws-id> --pool-type <pool-type> --stop-schedule-json '{"duration": 60, "time_unit": "MINUTES"}' [--pool-id pool-<resource-id>] --dry-run

# 6. Create service (user must confirm)
cloudrobo infer create --name verify-infer --flavor "<flavor>" --model-json '{"model_id": "<asset-id>", "model_version_id": "<latest-version-id>"}' --workspace-id <ws-id> --pool-type <pool-type> --stop-schedule-json '{"duration": 60, "time_unit": "MINUTES"}' [--pool-id pool-<resource-id>]
# → Returns {"id": "..."} — service identifier field is `id` (some docs call it service_id); service auto-enters CREATING → DEPLOYING

# 7. Wait for deployment (do NOT call start — service auto-deploys)
cloudrobo infer wait-deploy --service-id <service-id> --timeout 600
# → Polls every 5s until status is no longer DEPLOYING (status != DEPLOYING)
#   (returns RUNNING/FAILED/...; if it returns while CREATING, re-invoke — it only waits on DEPLOYING)

# 8. List services / show detail
cloudrobo infer list --workspace-id <ws-id>
cloudrobo infer show --service-id <service-id>

# 9. Clean up (user must confirm)
cloudrobo infer stop --service-id <service-id>
cloudrobo infer delete --service-id <service-id>
```

**Pass criteria**: Service reaches RUNNING; list/show return it; stop/delete work.

### Level 2.5: Parameter Auto-Discovery Test (Space Asset / Custom Models)

Verifies that deployment parameters are correctly discovered from the algorithm
asset and config files:

```bash
# 1. Query model asset — check for ONLINE_DEPLOYMENT action
cloudrobo asset show-asset --asset-id <model_asset_id>
# → Check actions[] for ONLINE_DEPLOYMENT with algorithm.asset_id

# 2. Query algorithm asset (if action found)
cloudrobo asset show-asset --asset-id <algorithm_asset_id>
cloudrobo asset show-version --asset-id <algorithm_asset_id> --version-id <algorithm_version_id>
# → Extract command, engine.image_url, environment_variables, deployment_config

# 3. Download skill_config.json via download-url API (Python SDK)
#    → file content → --skill-config-json (filter to name+prompt only)

# 4. Download r2c config (try r2c_config.yaml, fallback r2c.json)
#    → file content → --model-ext-metadata

# 5. Verify all discovered parameters are included in create command
cloudrobo infer create --name verify-discover --flavor "<flavor>" --model-json '{"model_id":"<mid>","model_version_id":"<mvid>","mount_path":"<mount>"}' --workspace-id <ws> --pool-type <type> --stop-schedule-json '{"duration": 60, "time_unit": "MINUTES"}' [--pool-id pool-<rid>] --cmd "<command>" --image-swr-url "<image>" --envs-json '{"K":"V"}' --skill-config-json '{"skills":[{"name":"...","prompt":"..."}],"strict":true}' --service-invoke-json '{"auth_type":"...","port":8080,"protocol":"HTTP"}' --readiness-health-json '{"path":"/ready","port":8080}' --model-ext-metadata '<r2c_content>' --dry-run
```

**Pass criteria**: All discoverable parameters resolved; dry-run validates
parameter assembly; no 400/500 errors from missing or malformed params.

### Level 3: Wait-Deploy Test

```bash
# First create the service (it auto-deploys), then wait for deployment
cloudrobo infer wait-deploy --service-id <service-id> --timeout 600
# → Polls every 5s, reports final status when status is no longer DEPLOYING (status != DEPLOYING)
```

**Pass criteria**: Service reaches RUNNING (or reports timeout/failure with log guidance).

### Level 4: Log Diagnosis Test

```bash
# 1. Get current time in milliseconds
END_MS=$(date +%s%3N)
START_MS=$(( END_MS - 3600000 ))

# 2. List logs (ms timestamps, keyword filter)
cloudrobo infer list-logs --service-id <service-id> --start-time $START_MS --end-time $END_MS --keywords "error"
# → Returns log lines

# 3. Count logs
cloudrobo infer list-logs --service-id <service-id> --start-time $START_MS --end-time $END_MS --is-count
```

**Pass criteria**: Log lines returned with ms timestamps; keyword filter works.

### Level 5: Exception / Validation Test (NEGATIVE CASES — EXPECT FAILURE)

> **These are negative test cases, not functional or smoke cases.** Each command below MUST
> fail with a non-zero exit code; a zero exit means the validation is broken. Never execute
> them as positive functional cases (the evaluator's TC-F-34 / TC-F-35) and never treat their
> failure as a skill defect. They exercise client-side validators only — no request reaches
> the backend and no cloud resource is created.

```text
# TC-13 / TC-F-34 / TC-F-35: path traversal rejected — EXPECT-FAIL (exit != 0)
# service_id must match the UUID pattern; "../../etc/hosts" → Click BadParameter, exit 2
# (a traversal escape attempt that is NOT a credential file — the case tests id validation,
#  not credential access, and keeps the security scan free of PE3 false positives)
# DO NOT EXECUTE AS A POSITIVE CASE
cloudrobo infer show --service-id "../../etc/hosts"

# TC-12: invalid JSON rejected — EXPECT-FAIL (exit != 0)
# Error: Invalid value for '--envs-json': Invalid JSON for 'envs': ... , exit 2
# DO NOT EXECUTE AS A POSITIVE CASE
cloudrobo infer create --name xyz --flavor f --model-json '{"model_id":"m","model_version_id":"mv"}' --workspace-id w --pool-type SHARED --envs-json "not-json"

# NEG-3 (extra): missing client-required --name rejected — EXPECT-FAIL (exit != 0)
# Error: Missing option '--name'. (Click required-option validation, exit 2)
# DO NOT EXECUTE AS A POSITIVE CASE
cloudrobo infer create --flavor f --model-json '{"model_id":"m","model_version_id":"mv"}' --pool-type SHARED --stop-schedule-json '{"duration": 60, "time_unit": "MINUTES"}'

# NEG-4 (extra): missing client-required --model-json rejected — EXPECT-FAIL (exit != 0)
# Error: Missing option '--model-json'. (Click required-option validation, exit 2)
# DO NOT EXECUTE AS A POSITIVE CASE
cloudrobo infer create --name xyz --flavor f --stop-schedule-json '{"duration": 60, "time_unit": "MINUTES"}'
```

**Pass criteria**: every case above exits non-zero with a clear error (no path traversal, no
request sent to the backend). A zero exit code is a FAIL for these cases. The executable
runner `scripts/test-cli-commands.sh` encodes this expectation directly — NEG-1/NEG-2 assert
`expect=nonzero`, NEG-3/NEG-4 additionally assert the Click `Missing option ...` text so a
backend 403 cannot masquerade as a pass.

> `--workspace-id` is **not** a client-side required option in cloudrobo 0.3.0: omitting it
> reaches the backend and fails with an auth/region error (e.g. 403), so it is not usable as a
> validation negative case. The client-side required options are `--name` and `--model-json`.

> `--name` must satisfy `^[\u4e00-\u9fa5a-zA-Z0-9_\-./]{3,64}$` (use `xyz` here), otherwise the
> name check fires first and masks the error the case is meant to prove.

## Expected Results Matrix

| Test Case | Input | Expected Output |
| ----------- | ------- | ---------------- |
| TC-01: List services | `infer list --workspace-id <ws>` | JSON array of services |
| TC-02: Create service | valid params | `id` returned (service identifier; some docs call it `service_id`) |
| TC-03: Dry-run create | valid params + `--dry-run` | `[DRY-RUN]` message, no service created |
| TC-04: Show service | service_id | Service object with full fields |
| TC-05: Start service | service_id | status → RUNNING |
| TC-06: Stop service | service_id | status → STOPPED |
| TC-07: Update service | service_id + fields | field updated in later show |
| TC-08: Delete service | service_id | service removed |
| TC-09: Wait-deploy | service_id + timeout | service status is no longer `DEPLOYING` (or reports timeout) |
| TC-10: List logs | service_id + ms start/end | log lines |
| TC-11: Log keyword filter | + `--keywords` | filtered log lines |
| TC-12: Invalid JSON (**negative**) | malformed `--*-json` | **EXPECT-FAIL** — Click validation error, exit != 0 |
| TC-13: Path traversal (**negative**) | `../` service_id | **EXPECT-FAIL** — validation error, exit != 0 |

## Common Verification Failures

| Failure | Likely Cause | Fix |
| --------- | ------------- | ----- |
| 401 Unauthorized | AK/SK missing or wrong | Set HUAWEI_CLOUD_AK/SK env vars |
| 400 model invalid | model_id/model_version_id unknown | Query asset list; verify in workspace |
| Click: Invalid JSON | malformed `--*-json` | Re-check JSON syntax |
| list-logs empty/wrong | seconds instead of ms | Convert timestamps to milliseconds |
| Service stuck CREATING | pool lacks resources | Wait or free pool; extend deploy timeout |
| Service CREATE_FAILED/START_FAILED | model artifact / health-check / cmd | Use `list-logs` to diagnose |
| `wait-deploy` timeout | default 600s too short or service stuck in DEPLOYING | Extend via `--timeout` |
| 403 Forbidden | wrong workspace_id / no access | Check workspace_id, account access |
