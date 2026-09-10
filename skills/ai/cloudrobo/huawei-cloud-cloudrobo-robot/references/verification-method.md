# Verification Method

## Verification Levels

### Level 1: CLI Smoke Test

Verify the CLI is installed and authenticated:

```bash
# Should return JSON list (possibly empty)
cloudrobo robot list

# Should return SDK info
cloudrobo robot show-sdk

# Should list robots in a workspace
cloudrobo robot list --workspace-id <workspace-id>
```

**Pass criteria**: Command exits 0, returns valid JSON.

### Level 2: Robot Lifecycle Test (Register & CRUD)

End-to-end test of robot registration and management:

```bash
# 1. Set workspace (from workspace skill)
cloudrobo workspace list
cloudrobo workspace use <workspace-id>

# 2. Dry-run validate create (optional)
cloudrobo robot create --name verify-robot --type HUMANOID --manufacturer DemoMaker --robot-model B2-W --workspace-id <ws-id> --dry-run

# 3. Create robot (user must confirm)
cloudrobo robot create --name verify-robot --type HUMANOID --manufacturer DemoMaker --robot-model B2-W --workspace-id <ws-id>
# → Returns robot_id

# 4. Show robot detail
cloudrobo robot show --robot-id <robot-id>

# 5. List robots (with filter)
cloudrobo robot list --workspace-id <ws-id> --type HUMANOID

# 6. Update robot (user must confirm)
cloudrobo robot update --robot-id <robot-id> --description "Updated description"

# 7. Verify update
cloudrobo robot show --robot-id <robot-id>

# 8. Clean up (user must confirm)
cloudrobo robot delete --robot-id <robot-id>
```

**Pass criteria**: Robot created, shown, listed with filters, updated, and deleted; status reflects lifecycle.

### Level 3: Certificate / Access-Config Export Test

```bash
# 1. Export the robot access config (接入配置) / certificate zip; --output is required (directory)
mkdir -p ./certs
cloudrobo robot export-certificate --robot-id <robot-id> --password "temp-export-pw" --output ./certs

# 2. Verify file written (auto-generated: cert_config_{robot_name}_{timestamp}.zip)
ls -la ./certs/cert_config_*.zip
file ./certs/cert_config_*.zip
```

**Pass criteria**: Output zip written in binary mode, non-empty, filename matches `cert_config_{name}_{timestamp}.zip`.

### Level 4: SDK Query Test

```bash
cloudrobo robot show-sdk
# → Returns file_name/version/signed_url
```

**Pass criteria**: SDK download descriptor returned with OBS signed_url.

### Level 5: Exception & Path Traversal Test

```bash
# 1. Out-of-enum type rejected (CLI is case-insensitive; only invalid values fail)
cloudrobo robot create --name x --type invalid-type --manufacturer M --robot-model M --workspace-id <ws-id>
# → Expected click usage error: "not one of arm/humanoid/operation/other/quadruped/wheeled" (exit 2)

# 2. Path traversal rejected via validate_safe_id
cloudrobo robot show --robot-id "../etc/passwd"
# → Expected validation error

# 3. Missing workspace rejected
cloudrobo robot create --name x --type HUMANOID --manufacturer M --robot-model M
# → Expected 400/403 error
```

**Pass criteria**: Invalid inputs rejected with clear errors, no path traversal.

## Expected Results Matrix

| Test Case | Input | Expected Output |
| ----------- | ------- | ---------------- |
| TC-01: List robots | `robot list` | JSON array of robots |
| TC-02: Create robot | valid params | robot_id returned |
| TC-03: Dry-run create | valid params + `--dry-run` | `[DRY-RUN]` message, no robot created |
| TC-04: Show robot | robot_id | Robot object with full fields |
| TC-05: List filter by type | `--type HUMANOID` | filtered results |
| TC-06: Update robot | robot_id + fields | field updated in later show |
| TC-07: Delete robot | robot_id | robot removed |
| TC-08: Export certificate | robot_id + password | binary file written |
| TC-09: Show SDK | (no args) | file_name/version/signed_url |
| TC-10: Invalid type | out-of-enum type | click usage error (exit 2) |

## Common Verification Failures

| Failure | Likely Cause | Fix |
| --------- | ------------- | ----- |
| 401 Unauthorized | AK/SK missing or wrong | Set HUAWEI_CLOUD_AK/SK env vars |
| type usage error | type not in enum | Use one of: HUMANOID/QUADRUPED/ARM/OPERATION/WHEELED/OTHER (case-insensitive) |
| 403 Forbidden | wrong workspace_id / no access | Check workspace_id, account access |
| Path traversal error | malicious `robot_id` | validate_safe_id rejects; use valid UUID |
| Certificate file empty | wrong robot_id or output path | Re-check robot_id, ensure --output writable |
