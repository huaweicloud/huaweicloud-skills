# Verification Method

## Overview

This document describes the verification methods used to confirm a successful JiuwenSwarm deployment on Huawei Cloud Flexus L instances.

## Verification Phases

### Phase 1: Environment Verification

**Script**: `scripts/prepare_env.py`

**Checks**:
1. Python version >= 3.8
2. Required packages installed: `requests`, `huaweicloudsdkcore`, `huaweicloudsdkcoc`, and KooCLI (`hcloud`)
3. Huawei Cloud credentials (AK/SK) configured via environment variables
4. Credential validity confirmed via IAM API call

**Success Criteria**: All dependency modules checked successfully, credentials valid.

### Phase 2: Instance Creation Verification

**Script**: `scripts/create_instance.py`

**Checks**:
1. Instance status is `RUNNING` (polled via KooCLI `hcloud RMS ListAllResources`)
2. Public IP assigned and accessible
3. Instance ID and ECS instance ID obtained
4. Order status confirmed

**Success Criteria**: Instance is in RUNNING state with valid public IP.

### Phase 3: Dependency Installation Verification

**Script**: `scripts/install_deps.py`

**Checks**:
1. COC task status is `FINISHED`
2. Base tools installed: git, curl, vim, wget, net-tools
3. Python and Node.js environment available

**Success Criteria**: COC execution returns FINISHED status.

### Phase 4: Service Deployment Verification

**Script**: `scripts/deploy_service.py`

**Checks**:
1. COC task status is `FINISHED`
2. JiuwenSwarm installed successfully
3. systemd service configured
4. Service started without errors

**Success Criteria**: COC execution returns FINISHED, service is active.

### Phase 5: Deployment Result Verification

**Script**: `scripts/verify_deployment.py`

**Checks**:
1. COC deployment task status queried
2. `jiuwenswarm` service is running (`systemctl is-active` returns `active`)
3. `.env` file has `FRONTEND_HOST=0.0.0.0`
4. All ports bound to `0.0.0.0`: 5173, 18092, 19000, 19001
5. Service health check: `curl localhost:5173` returns HTTP 200
6. Web access URL generated: `http://{public_ip}:5173`

**Success Criteria**: All ports bound to 0.0.0.0, health check returns 200.

### Phase 6: Model Configuration Verification

**Script**: `scripts/config_model.py`

**Checks**:
1. `.env` file updated with API_BASE, API_KEY, MODEL_NAME, MODEL_PROVIDER
2. Original `.env` backed up
3. File permission set to 600
4. JiuwenSwarm service restarted successfully

**Success Criteria**: Configuration updated, service restarted.

### Phase 7: Channel Configuration Verification

**Script**: `scripts/config_channel.py`

**Checks**:
1. `config.yaml` updated with channel-specific fields
2. Original `config.yaml` backed up
3. File permission set to 644
4. JiuwenSwarm service restarted successfully

**Success Criteria**: Channel configured, service restarted.

## COC Task Status Verification

**Script**: `scripts/query_coc_status.py`

| Status | Description | Action |
|--------|-------------|--------|
| READY | Ready | No action needed |
| PROCESSING | Running | Wait and poll again |
| FINISHED | Completed successfully | Proceed to next phase |
| ABNORMAL | Execution abnormal | Investigate error, retry |
| CANCELED | Canceled | Investigate, re-execute |

**Usage**:
```bash
# Query single task status
python scripts/query_coc_status.py --uuid <execute_uuid>

# Query with detailed output
python scripts/query_coc_status.py --uuid <execute_uuid> --verbose

# Wait for task completion
python scripts/query_coc_status.py --uuid <execute_uuid> --wait

# Load UUID from JSON file
python scripts/query_coc_status.py --from-file new_instance_info.json
```

## Web Access Verification

After deployment, verify web access:

1. **Local check**: `curl localhost:5173` should return HTTP 200
2. **Port binding**: `ss -tlnp | grep 5173` should show `0.0.0.0:5173`
3. **External access**: `curl http://{public_ip}:5173` should return HTTP 200 (requires security group port 5173 open)

## Verification Output Format

### Success Output
```
============================================================
  JiuwenSwarm COC Deployment - Complete
============================================================

Target Instance:
  Name: {instance_name}
  ID: {instance_id}
  IP: {public_ip}

COC Execution:
  Execute UUID: {execute_uuid}
  Status: FINISHED

Deployment Result:
  Web Access: http://{public_ip}:5173
  Port Binding: 0.0.0.0:5173 (verified)
  Submit Time: {submit_time}

NOTE: Huawei Cloud security group must allow inbound TCP 5173
      for external web access.

============================================================
[SUCCESS] Deployment task completed!
============================================================
```

### Error Output
```
============================================================
[ERROR] Deployment Failed
============================================================

Error: {error_message}

Suggestions:
  1. Check Huawei Cloud credentials
  2. Verify instance status
  3. Check deployment logs

============================================================
```
