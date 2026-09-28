# Huawei Cloud SMS Troubleshooting and Error Codes Guide

This guide details common failure modes, error codes, and operational fixes encountered during Huawei Cloud Server Migration Service (SMS) workflows.

---

## 1. Quick Diagnostic Commands

When a migration task stalls, encounters network issues, or enters an error state, use the following KooCLI commands:

### Check Target Network & Security Group
Validate whether the destination security group and subnet permit required migration ports (22 for Linux; 22, 8899, 8900 for Windows):
```bash
# Query inbound rules on the destination security group:
hcloud VPC ListSecurityGroupRules/v3 --cli-region=cn-north-4 --security_group_id.1="{sg_id}"

# Query subnet firewall / network ACL rules:
hcloud VPC ListFirewall --cli-region=cn-north-4
```

### Target ECS Inspection and Task Recovery
If a migration task encounters an unrecoverable failure or is interrupted, inspect target instance status and release task bindings:
```bash
# Inspect target ECS state, power status, and disk attachments:
hcloud ECS ShowServer --cli-region=cn-north-4 --server_id="{target_ecs_vm_id}"

# Delete the failed task to release target server bindings and SMS locks:
hcloud SMS DeleteTask --cli-region=cn-north-4 --task_id="{task_id}"
```

---

## 2. Common SMS Error Codes & Resolution

### SMS.6603: Agent Connection Failure / Offline
- **Symptom**: Agent cannot connect to the SMS control plane during startup or heartbeat.
- **Root Causes**:
  1. **NTP Clock Drift**: Source system clock differs by > 15 minutes from standard time, leading to signature verification failures.
     - *Fix*: Run `ntpdate pool.ntp.org` (Linux) or `w32tm /resync` (Windows).
  2. **Outbound Port 443 Blocked**: Source firewall denies outbound HTTPS to the SMS control endpoint.
     - *Fix*: Verify connectivity using `curl -v https://sms.cn-north-4.myhuaweicloud.com` (China Site) or `curl -v https://sms.ap-southeast-3.myhuaweicloud.com` (International Site - Singapore).
  3. **Proxy Configuration**: If operating in a private network without direct internet, configure an HTTPS proxy for Agent registration.
  4. **Incorrect Domain / Enterprise Project Input**: Entering a bare region identifier (e.g., `cn-north-4`) instead of the full domain (`sms.cn-north-4.myhuaweicloud.com` for China Site, or `sms.ap-southeast-3.myhuaweicloud.com` for International Site Singapore).
     - *Fix*: Enter the complete domain corresponding to your site and valid Enterprise Project ID (or `0` for default).

### SMS.1901: Cannot Connect to Target Server
- **Symptom**: Task halts at stage `SSL_CONFIG` or `ATTACH_AGENT_IMAGE`.
- **Root Causes**:
  1. **Target Security Group Inbound Blocked**: Port 22 (Linux) or ports 22, 8899, 8900 (Windows) are not allowed from the source IP.
     - *Fix*: Create a dedicated security group with these exact rules, or add inbound rules to the target ECS security group permitting traffic from the source host IP.
  2. **Target Network ACL**: Subnet NACL blocks incoming packets or return ephemeral ports (1024-65535).
     - *Fix*: Inspect and update subnet ACL rules via `hcloud VPC ListFirewall` or VPC console.
  3. **EIP Not Bound**: If migrating over the public internet, verify target ECS has an associated Elastic Public IP (EIP).

### SMS.0601: Missing System Dependency (`rsync`)
- **Symptom**: Linux source server pre-check fails reporting missing file transfer utility.
- **Root Cause**: `rsync` package is not installed on the source Linux system.
- **Fix**:
  - RHEL/CentOS/EulerOS: `yum install -y rsync`
  - Ubuntu/Debian: `apt-get install -y rsync`

### SMS.1106: Target Disk Capacity Insufficient
- **Symptom**: Task creation fails with storage capacity validation error.
- **Root Cause**: The target disk size in the VM template is smaller than the source server disk partition size.
- **Fix**: Adjust VM template disk configuration (`--template.disk.1.size=...`) to ensure every target disk is equal to or larger than the corresponding source disk.

### SMS.0212 / SMS.1414: Agent Process Aborted or Restarted
- **Symptom**: Task fails unexpectedly midway through replication.
- **Root Cause**: Agent process was killed by Linux OOM-killer, system reboot, or user session logout.
- **Fix**: Run the agent in the background using `nohup ./startup.sh > sms_agent.log 2>&1 &` or deploy as a systemd service, and ensure at least 500 MB RAM is free.

### SMS.7111 & SMS.7101: Template Deletion Order Dependency
- **Symptom**:
  - Deleting a target template before deleting the migration task triggers error `SMS.7111` ("Template is associated with an existing migration task").
  - After deleting the task first, deleting the template returns `SMS.7101` ("Template not found").
- **Root Cause**:
  1. Huawei Cloud SMS enforces a referential integrity lock: active migration tasks hold an association with their target template.
  2. For auto-provisioned tasks (`exist_server: false`), deleting the migration task automatically unlinks or cascades deletion of the associated template.
- **Resolution**:
  1. Always adhere to the strict deletion sequence: **Task first, Template second**.
     ```bash
     hcloud SMS DeleteTask --cli-region={region} --task_id="{task_id}"
     ```
  2. Next attempt template deletion:
     ```bash
     hcloud SMS DeleteTemplate --cli-region={region} --id="{template_id}"
     ```
  3. If `DeleteTemplate` returns error `SMS.7101`, the template has already been automatically deleted; treat this as a successful completion.

### KooCLI Multi-Version Preamble Warning Breaking JSON Parsing (`VPC ListVpcs`)
- **Symptom**: Running `hcloud VPC ListVpcs` outputs a localized disclaimer line before the JSON object, causing `json.loads()` or programmatic JSON parsers to fail with syntax errors.
- **Root Cause**: The `VPC ListVpcs` API has multiple versions registered in KooCLI. When unversioned, KooCLI emits an informational notice to standard output before streaming the JSON response.
- **Fix**: Pin the API version explicitly in the command path using `ListVpcs/v3`:
  ```bash
  hcloud VPC ListVpcs/v3 --cli-region={region} --limit=10
  ```
  Specifying `/v3` directs KooCLI to invoke the v3 endpoint directly without outputting the multi-version warning.

### IMS ListImages Returns Empty Results with `--name` Filter
- **Symptom**: Searching for images using `--name="Ubuntu"` returns an empty `images` list even though Ubuntu images exist.
- **Root Cause**: The IMS API treats `--name` as a strict exact string equality filter. It does not perform partial substring matching or wildcard expansion.
- **Fix**:
  - **Platform Filtering with `--__platform` (Recommended)**: Use `--__platform` with the appropriate image type:
    ```bash
    # Filter public Linux images by platform (e.g., Ubuntu, CentOS, Debian, EulerOS):
    hcloud IMS ListImages --cli-region={region} --status=active --__imagetype="gold" --__platform="Ubuntu" --limit=10

    # Filter Windows marketplace images by platform:
    hcloud IMS ListImages --cli-region={region} --status=active --__imagetype="market" --__platform="Windows" --limit=10
    ```
  - For exact full-name queries: Specify the complete exact image name (e.g., `--name="Ubuntu 22.04 server 64bit"`).

### Invalid Operation `cutover` on `UpdateTaskStatus`
- **Symptom**: Executing `hcloud SMS UpdateTaskStatus --operation=cutover` fails client-side parameter validation.
- **Root Cause**: KooCLI strictly validates the `--operation` parameter against the allowed enum:
  `[start|stop|test|clone_test|restart|network_check|clear|skip|migration_test]`. The value `cutover` is not an accepted parameter value.
- **Fix**: To finalize cutover and clean up replication snapshots, use `--operation="clear"`:
  ```bash
  hcloud SMS UpdateTaskStatus --cli-region={region} --task_id="{task_id}" --operation="clear"
  ```

### Post-Cutover Task Status Remains `MIGRATE_SUCCESS`
- **Symptom**: After running `--operation="clear"`, the migration task status remains `MIGRATE_SUCCESS` instead of transitioning to `CLEARED` or `FINISHED`.
- **Root Cause**: This is the intended behavior of the SMS service. The task record retains its terminal success status (`MIGRATE_SUCCESS`), while cutover finalization is reflected on the **source server record**.
- **Fix**: Confirm cutover finalization by inspecting the source host status:
  ```bash
  hcloud SMS ShowServer --cli-region={region} --source_id="{source_server_id}"
  ```
### KooCLI JSON Serialization Defect on Windows Paths & Backslashes
- **Symptom**:
  When invoking `hcloud SMS CreateTask` for Windows source hosts using `--cli-jsonInput`, KooCLI outputs an internal formatting error:
  `failed to format json data: invalid character '...' after object key:value pair, raw output will be printed:`
  and the remote SMS API returns HTTP 400 with error code `SMS.9001` ("Invalid parameters.").
- **Root Cause**:
  KooCLI's parameter unmarshaler parses JSON input strings correctly into memory (e.g. `"C:\\"` becomes `C:\`). However, when serializing the outbound HTTP POST body, KooCLI uses manual string interpolation rather than standard JSON encoding, and fails to re-escape backslashes (`\` to `\\`). As a result:
  - In-memory `C:\` is serialized directly into the JSON string as `"name": "C:\"`.
  - The trailing backslash immediately precedes the closing quote `\"`, escaping the quote and leaving the JSON string literal open.
  - The subsequent properties are parsed as part of the string until a syntax error occurs, sending malformed JSON to the backend API.
- **Resolution (Solution 1: Double-Escaping - Recommended)**:
  Double-escape all backslashes in the `--cli-jsonInput` JSON file (4 backslashes per 1 physical backslash):
  - Partition drive letters: `"name": "C:\\\\"` (serializes to `"C:\\"` in outbound wire JSON).
  - Partition UUIDs: `"uuid": "\\\\\\\\?\\\\Volume{53f59b50-349b-4bb2-b625-0c6763337a0a}\\\\"`.
  - Use `templates/create-task-windows.json` as a validated template.
- **Alternative (CLI Argument Quoting)**:
  If passing parameters via CLI flags, lock literal double-backslashes inside single quotes:
  `--target_server.disks.1.physical_volumes.2.name='C:\\'`
- **Future KooCLI Version Compatibility**:
  This serialization defect was confirmed on KooCLI v7.2.12. If a future KooCLI release patches the JSON string escaping defect, double-escaping will produce redundant backslashes (`C:\\`) in the outbound wire JSON. In that scenario, revert to standard JSON escaping (2 backslashes: `"name": "C:\\"` and `"uuid": "\\\\?\\Volume{...}\\"`). Always test with `--dryrun` after upgrading KooCLI to confirm wire payload format.

### UEFI Windows Migration / Firmware Type Mismatch
- **Symptom**: Attempting to create an auto-provisioned task with a migration template for a UEFI Windows host fails, or target instance fails to boot after cutover due to firmware incompatibility.
- **Root Cause**: Huawei Cloud SMS does not support creating target servers from templates for UEFI Windows hosts. Furthermore, if an existing server is chosen but was created with BIOS boot mode, the firmware types mismatch (`SMS.11xx`: "Source firmware is UEFI, but target server firmware is BIOS").
- **Resolution**:
  1. Do not create or assign a target template for UEFI Windows source servers.
  2. Pre-create the target ECS on Huawei Cloud first, explicitly configuring UEFI boot mode (`hw_firmware_type: "uefi"`).
  3. Ensure disk capacity and partition layout (GPT for UEFI) match or exceed the source host.
  4. Create the migration task using `"exist_server": true` and `"target_server": { "vm_id": "{pre_created_target_ecs_vm_id}" }` (see `templates/create-task-existing-server.json`).

---

## 3. Post-Error Recovery Flow

1. Query task error details:
   ```bash
   hcloud SMS ShowTask --cli-region=cn-north-4 --task_id="{task_id}"
   ```
2. Inspect `error_json` field to locate the exact error code.
3. Apply the corresponding network or system remediation.
4. Restart the replication task:
   ```bash
   hcloud SMS UpdateTaskStatus --cli-region=cn-north-4 --task_id="{task_id}" --operation="restart"
   ```
