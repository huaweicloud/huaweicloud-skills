# Verification Method

## Verification Levels

### Level 1: CLI Smoke Test

```bash
# Should return JSON list (possibly empty) in a workspace
cloudrobo infer list --workspace-id <workspace-id>
```

**Pass criteria**: Command exits 0, returns valid JSON.

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

# 5. Dry-run validate deploy (optional)
cloudrobo infer create --name verify-infer --flavor "<flavor>" --model-json '{"model_id": "<asset-id>", "model_version_id": "<latest-version-id>"}' --workspace-id <ws-id> --pool-id pool-<resource-id> --pool-type <pool-type> --stop-schedule-json '{"duration": 60, "time_unit": "MINUTES"}' --dry-run

# 6. Create service (user must confirm)
cloudrobo infer create --name verify-infer --flavor "<flavor>" --model-json '{"model_id": "<asset-id>", "model_version_id": "<latest-version-id>"}' --workspace-id <ws-id> --pool-id pool-<resource-id> --pool-type <pool-type> --stop-schedule-json '{"duration": 60, "time_unit": "MINUTES"}'
# → Returns service_id (service auto-enters CREATING → DEPLOYING)

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
cloudrobo infer create --name verify-discover --flavor "<flavor>" --model-json '{"model_id":"<mid>","model_version_id":"<mvid>","mount_path":"<mount>"}' --workspace-id <ws> --pool-id pool-<rid> --pool-type <type> --stop-schedule-json '{"duration": 60, "time_unit": "MINUTES"}' --cmd "<command>" --image-swr-url "<image>" --envs-json '{"K":"V"}' --skill-config-json '{"skills":[{"name":"...","prompt":"..."}],"strict":true}' --service-invoke-json '{"auth_type":"...","port":8080,"protocol":"HTTP"}' --readiness-health-json '{"path":"/ready","port":8080}' --model-ext-metadata '<r2c_content>' --dry-run
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

### Level 5: Exception / Validation Test

```bash
# 1. Path traversal rejected
cloudrobo infer show --service-id "../etc/passwd"
# → Expected validation error

# 2. Invalid JSON rejected
cloudrobo infer create --name x --flavor f --model-json '{"model_id":"m","model_version_id":"mv"}' --workspace-id w --pool-id p --pool-type SHARED --envs-json "not-json"
# → Expected Click validation error: Invalid JSON

# 3. Missing workspace rejected
cloudrobo infer create --name x --flavor f --model-json '{"model_id":"m","model_version_id":"mv"}' --pool-id p --pool-type SHARED
# → Expected Click validation error: Missing option '--workspace-id'
```

**Pass criteria**: Invalid inputs rejected with clear errors, no path traversal.

## Expected Results Matrix

| Test Case | Input | Expected Output |
| ----------- | ------- | ---------------- |
| TC-01: List services | `infer list --workspace-id <ws>` | JSON array of services |
| TC-02: Create service | valid params | service_id returned |
| TC-03: Dry-run create | valid params + `--dry-run` | `[DRY-RUN]` message, no service created |
| TC-04: Show service | service_id | Service object with full fields |
| TC-05: Start service | service_id | status → RUNNING |
| TC-06: Stop service | service_id | status → STOPPED |
| TC-07: Update service | service_id + fields | field updated in later show |
| TC-08: Delete service | service_id | service removed |
| TC-09: Wait-deploy | service_id + timeout | service status is no longer `DEPLOYING` (or reports timeout) |
| TC-10: List logs | service_id + ms start/end | log lines |
| TC-11: Log keyword filter | + `--keywords` | filtered log lines |
| TC-12: Invalid JSON | malformed `--*-json` | Click validation error |
| TC-13: Path traversal | `../` service_id | validation error |

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
