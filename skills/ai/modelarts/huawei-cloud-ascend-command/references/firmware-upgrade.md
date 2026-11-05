# Firmware Upgrade Reference

> **Routed vs. manual:** entries marked **Routed** are reachable through natural
> language and are implemented in `scripts/executor.py` /
> `scripts/npu_client.py`. Entries marked **Manual** document an available
> `npu-smi` capability that the skill does not currently route; run them
> directly (for example via the `npu-smi` passthrough).

## Firmware Information

### Get Firmware Version — Routed

**Command:** `npu-smi upgrade -b <component> -i <npu_id>` (default component `mcu`)

**Natural Language:** `Firmware version`, `Query firmware`

**Output:** Current firmware version

### Get All Versions — Manual

**Command:** `npu-smi info -t all-version -i <npu_id>`

**Natural Language:** `All versions`, `Version details`

**Output:** Detailed version information

## Upgrade Process

### Check Upgrade Status — Routed

**Command:** `npu-smi upgrade -q <component> -i <npu_id>` (default component `mcu`)

**Natural Language:** `Upgrade status`, `Upgrade check`

**Output:** Current upgrade status

### Upgrade Firmware — Routed

**Command:** `npu-smi upgrade -t <component> -i <npu_id> -f <firmware_file>`

**Natural Language:** `Upgrade firmware`, `Upload firmware`

**Sensitive:** Requires confirmation

**Parameters:** Component (default `mcu`) and path to the firmware file

**Example:**
```bash
npu-smi upgrade -t mcu -i 0 -f /path/to/firmware.hpm
```

**Important Notes:**
1. Ensure NPU is in a stable state before upgrade
2. Backup current configuration if needed
3. Upgrade may take several minutes
4. Device may reboot after upgrade

### Upgrade from Repository — Manual

**Command:** `npu-smi upgrade -r <repo_url> -i <npu_id>`

**Natural Language:** `Upgrade from repository`

**Sensitive:** Requires confirmation (run directly; the skill does not route it)

## Upgrade Status

### Get Upgrade Progress — Manual

**Command:** `npu-smi info -t upgrade-progress -i <npu_id>`

**Natural Language:** `Upgrade progress`

**Output:** Current upgrade progress percentage

### Cancel Upgrade — Manual

**Command:** `npu-smi upgrade -a cancel -i <npu_id>`

**Natural Language:** `Cancel upgrade`

**Sensitive:** Requires confirmation (run directly; the skill does not route it)

## Activate Firmware

### Activate Uploaded Firmware

**Command:** `npu-smi upgrade -a <component> -i <npu_id>`

**Natural Language:** `Activate firmware`, `Activate upgrade`, `Firmware activate`

**Example:** `activate upgrade mcu NPU0` → `npu-smi upgrade -a mcu -i 0`

**Component:** parsed from the input (`mcu` / `bootloader` / `vrd`), default `mcu`

**Confirm gate:** `⚠️ Sensitive operation: Activate <component> firmware on NPU <npu_id> (requires reboot)`

**Sensitive:** Requires confirmation

**Note:** `activate upgrade` is an accepted synonym of `activate firmware` and
enters the same confirmation gate (ISSUE-006 / B115-6).

## Rollback

### Rollback to Previous Version

**Command:** `npu-smi upgrade -a rollback -i <npu_id>`

**Natural Language:** `Rollback firmware`, `Roll back firmware`, `Rollback`

**Confirm gate:** a rollback confirmation gate that warns "rollback may not be supported on all devices" → reply `confirm` / `cancel`

**Sensitive:** Requires confirmation

**Important:** Rollback may not be available on all devices

**Implementation:** routed by the firmware **rollback** branch (evaluated after
version / upload / status and before activate) to the
`rollback_firmware(npu_id)` client method. Example:
`rollback firmware NPU1` → `npu-smi upgrade -a rollback -i 1`.

## Upgrade Best Practices

### Pre-Upgrade Checklist

1. **Backup configuration:**
   ```bash
   npu-smi info > backup_before_upgrade.txt
   ```

2. **Check device health:**
   ```bash
   npu-smi info -t health -i 0
   ```

3. **Verify sufficient space:**
   ```bash
   df -h /var/log/npu/
   ```

4. **Stop running workloads:**
   ```bash
   # Stop any NPU-using applications
   ```

### During Upgrade

- Monitor progress periodically
- Do not interrupt the upgrade process
- Keep the system powered on

### Post-Upgrade

1. **Verify upgrade success:**
   ```bash
   npu-smi info -t version -i 0
   ```

2. **Check device health:**
   ```bash
   npu-smi info -t health -i 0
   ```

3. **Test basic functionality:**
   ```bash
   npu-smi info -l
   ```

## Troubleshooting Upgrade Issues

### Issue: Upgrade failed

**Symptom:** `Upgrade failed with error code`

**Possible causes:**
1. Invalid firmware file
2. Insufficient permissions
3. Device in use
4. Low disk space

**Solution:**
1. Verify firmware file integrity
2. Run as root
3. Stop all NPU processes
4. Free up disk space

### Issue: Firmware mismatch

**Symptom:** `Firmware version mismatch`

**Root cause:** Using firmware for different chip model

**Solution:** Use correct firmware for your chip type

### Issue: Upgrade stuck

**Symptom:** Upgrade progress stays at same percentage

**Solution:** Wait for timeout, then check logs
