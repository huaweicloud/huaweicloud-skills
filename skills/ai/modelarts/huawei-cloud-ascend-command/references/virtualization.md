# Virtualization Reference

## vNPU Management

### List vNPUs

**Command:** `npu-smi info -t vdevice -i <npu_id>`

**Natural Language:** `List vNPUs`, `Virtual NPUs`

**Output:** All virtual NPUs on the device

### Get vNPU Info

**Command:** `npu-smi info -t vdevice-detail -i <npu_id> -v <vpu_id>`

**Natural Language:** `vNPU info`, `Virtual device info`

**Output:** Detailed vNPU information

## Create vNPU

### Create vNPU with Default Settings

**Command:** `npu-smi set -t vdevice-create -i <npu_id> -d <vpu_id>`

**Natural Language:** `Create vNPU`, `New virtual NPU`

**Sensitive:** Requires confirmation

**Parameters:** vpu_id - Virtual device ID (0-7)

### Create vNPU with Custom Settings

**Command:** `npu-smi set -t vdevice-create -i <npu_id> -d <vpu_id> -m <memory_size> -c <core_count>`

**Natural Language:** `Create vNPU with memory`

**Sensitive:** Requires confirmation

**Parameters:**
- memory_size: Memory allocation in MB
- core_count: Number of cores

## Delete vNPU

### Delete vNPU

**Command:** `npu-smi set -t vdevice-delete -i <npu_id> -d <vpu_id>`

**Natural Language:** `Delete vNPU`, `Remove virtual NPU`

**Sensitive:** Requires confirmation

**Warning:** This will destroy all data on the vNPU

## vNPU Configuration

### Configure vNPU Memory

**Command:** `npu-smi set -t vdevice-memory -i <npu_id> -v <vpu_id> -d <size>`

**Natural Language:** `Set vNPU memory`

**Sensitive:** Requires confirmation

### Configure vNPU Cores

**Command:** `npu-smi set -t vdevice-core -i <npu_id> -v <vpu_id> -d <count>`

**Natural Language:** `Set vNPU cores`

**Sensitive:** Requires confirmation

## vNPU Status

### Get vNPU Status

**Command:** `npu-smi info -t vdevice-status -i <npu_id> -v <vpu_id>`

**Natural Language:** `vNPU status`

**Output:** Current status of vNPU

### Start vNPU

**Command:** `npu-smi set -t vdevice-start -i <npu_id> -d <vpu_id>`

**Natural Language:** `Start vNPU`

**Sensitive:** Requires confirmation

### Stop vNPU

**Command:** `npu-smi set -t vdevice-stop -i <npu_id> -d <vpu_id>`

**Natural Language:** `Stop vNPU`

**Sensitive:** Requires confirmation

## Passthrough Mode

### Enable Passthrough

**Command:** `npu-smi set -t passthrough-enable -i <npu_id> -d 1`

**Natural Language:** `Enable passthrough`

**Sensitive:** Requires confirmation

**Note:** Requires device reboot

### Disable Passthrough

**Command:** `npu-smi set -t passthrough-enable -i <npu_id> -d 0`

**Natural Language:** `Disable passthrough`

**Sensitive:** Requires confirmation

## Virtualization Best Practices

### Planning vNPU Allocation

1. **Check available resources:**
   ```bash
   npu-smi info -t memory -i 0
   ```

2. **Determine vNPU requirements:**
   - Memory per vNPU
   - Core count per vNPU
   - Number of vNPUs needed

3. **Allocate resources accordingly:**
   - Total memory <= physical memory
   - Total cores <= available cores

### Performance Considerations

- vNPU shares physical resources
- Higher vNPU count = more resource contention
- Monitor vNPU usage regularly

### Security Considerations

- Isolate sensitive workloads
- Monitor vNPU access
- Regularly update vNPU firmware

## Troubleshooting vNPU Issues

### Issue: Cannot create vNPU

**Symptom:** `vdevice creation failed`

**Possible causes:**
1. Insufficient resources
2. vNPU already exists
3. Virtualization not enabled

**Solution:**
1. Check available resources
2. Delete existing vNPU first
3. Enable virtualization in BIOS

### Issue: vNPU not starting

**Symptom:** `vdevice start failed`

**Possible causes:**
1. Resource allocation error
2. Firmware issue
3. Permission denied

**Solution:**
1. Check resource allocation
2. Update firmware
3. Run as root

### Issue: vNPU performance slow

**Possible causes:**
1. Resource contention
2. Other vNPUs using resources
3. Physical device throttling

**Solution:**
1. Reduce vNPU count
2. Monitor resource usage
3. Check physical device health
