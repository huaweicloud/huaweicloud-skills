# Configuration Management Reference

## Fan Speed Control

### Get Fan Mode

**Command:** `npu-smi info -t fan -i <npu_id>`

**Natural Language:** `Fan mode`, `Fan speed`

**Output:** Current fan mode (auto/manual) and speed

### Set Fan Mode to Manual

**Command:** `npu-smi set -t fan-mode -i <npu_id> -c <chip_id> -d 1`

**Natural Language:** `Set fan manual`

**Sensitive:** Requires confirmation

### Set Fan Mode to Auto

**Command:** `npu-smi set -t fan-mode -i <npu_id> -c <chip_id> -d 0`

**Natural Language:** `Set fan auto`

**Sensitive:** Requires confirmation

### Set Fan Speed

**Command:** `npu-smi set -t fan-speed -i <npu_id> -c <chip_id> -d <percentage>`

**Natural Language:** `Set fan speed`

**Parameters:** Speed percentage (0-100)

**Sensitive:** Requires confirmation

## ECC Configuration

### Enable ECC

**Command:** `npu-smi set -t ecc-enable -i <npu_id> -c <chip_id> -d 1`

**Natural Language:** `Enable ECC`

**Sensitive:** Requires confirmation

**Note:** Requires reboot to take effect

### Disable ECC

**Command:** `npu-smi set -t ecc-enable -i <npu_id> -c <chip_id> -d 0`

**Natural Language:** `Disable ECC`

**Sensitive:** Requires confirmation

**Note:** Requires reboot to take effect

## Performance Mode

### Get Performance Mode

**Command:** `npu-smi info -t perf-mode -i <npu_id>`

**Natural Language:** `Performance mode`

**Output:** Current performance mode

### Set Performance Mode

**Command:** `npu-smi set -t perf-mode -i <npu_id> -d <mode>`

**Natural Language:** `Set performance mode`

**Sensitive:** Requires confirmation

## Clock Configuration

### Get Clock Info

**Command:** `npu-smi info -t clock -i <npu_id>`

**Natural Language:** `Clock info`, `Clock frequency`

**Output:** Clock frequency information

### Set Clock Mode

**Command:** `npu-smi set -t clock-mode -i <npu_id> -d <mode>`

**Natural Language:** `Set clock mode`

**Sensitive:** Requires confirmation

## Security Configuration

### Get Security Status

**Command:** `npu-smi info -t security -i <npu_id>`

**Natural Language:** `Security status`

**Output:** Security configuration status

### Enable Secure Boot

**Command:** `npu-smi set -t secure-boot -i <npu_id> -d 1`

**Natural Language:** `Enable secure boot`

**Sensitive:** Requires confirmation

## Thermal Throttling

### Get Thermal Status

**Command:** `npu-smi info -t thermal -i <npu_id>`

**Natural Language:** `Thermal status`

**Output:** Thermal throttling status

### Set Temperature Threshold

**Command:** `npu-smi set -t temp-threshold -i <npu_id> -c <chip_id> -d <temp>`

**Natural Language:** `Set temperature threshold`

**Sensitive:** Requires confirmation

## Configuration Reset

### Reset to Default

**Command:** `npu-smi set -t reset -i <npu_id>`

**Natural Language:** `Reset NPU`, `Factory reset`

**Sensitive:** Requires confirmation

**Warning:** This will reset all configuration settings
