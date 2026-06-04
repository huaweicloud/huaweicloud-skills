# Firmware Upgrade Reference

## Firmware Information

### Get Firmware Version

**Command:** `npu-smi info -t version -i <npu_id>`

**Natural Language:** `Firmware version`

**Output:** Current firmware version

### Get All Versions

**Command:** `npu-smi info -t all-version -i <npu_id>`

**Natural Language:** `All versions`, `Version details`

**Output:** Detailed version information

## Upgrade Process

### Check for Updates

**Command:** `npu-smi upgrade -c -i <npu_id>`

**Natural Language:** `Check firmware update`

**Output:** Available firmware versions

### Upgrade Firmware

**Command:** `npu-smi upgrade -f <firmware_file> -i <npu_id>`

**Natural Language:** `Upgrade firmware`

**Sensitive:** Requires confirmation

**Parameters:** Path to firmware file

**Example:**
```bash
npu-smi upgrade -f /path/to/firmware.bin -i 0
```

**Important Notes:**
1. Ensure NPU is in a stable state before upgrade
2. Backup current configuration if needed
3. Upgrade may take several minutes
4. Device may reboot after upgrade

### Upgrade from Repository

**Command:** `npu-smi upgrade -r <repo_url> -i <npu_id>`

**Natural Language:** `Upgrade from repository`

**Sensitive:** Requires confirmation

## Upgrade Status

### Get Upgrade Progress

**Command:** `npu-smi info -t upgrade-progress -i <npu_id>`

**Natural Language:** `Upgrade progress`

**Output:** Current upgrade progress percentage

### Cancel Upgrade

**Command:** `npu-smi upgrade -a cancel -i <npu_id>`

**Natural Language:** `Cancel upgrade`

**Sensitive:** Requires confirmation

## Rollback

### Rollback to Previous Version

**Command:** `npu-smi upgrade -a rollback -i <npu_id>`

**Natural Language:** `Rollback firmware`

**Sensitive:** Requires confirmation

**Important:** Rollback may not be available on all devices

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
