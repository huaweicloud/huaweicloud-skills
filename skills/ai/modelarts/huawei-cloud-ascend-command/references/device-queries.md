# Device Queries Reference

## Basic Device Information

### List All Devices

**Command:** `npu-smi info -l`

**Natural Language:** `NPU list`, `List NPU devices`

**Output:** Shows all NPU devices with health status

### Full Device Info

**Command:** `npu-smi info`

**Natural Language:** `NPU info`, `NPU details`

**Output:** Comprehensive device information

### Board Information

**Command:** `npu-smi info -m`

**Natural Language:** `Board info`, `NPU board`

**Output:** Card and chip mapping

## Health Status

### Check Health

**Command:** `npu-smi info -t health -i <npu_id>`

**Natural Language:** `NPU health`, `Health check`

**Output:** Device health status (OK/Warning/Error)

## Temperature Monitoring

### Get Temperature

**Command:** `npu-smi info -t temp -i <npu_id> -c <chip_id>`

**Natural Language:** `NPU temperature`, `Temperature`

**Output:** Current temperature in Celsius

## Power Management

### Get Power Usage

**Command:** `npu-smi info -t power -i <npu_id> -c <chip_id>`

**Natural Language:** `NPU power`, `Power usage`

**Output:** Current power consumption in Watts

## Memory Information

### Get Memory Usage

**Command:** `npu-smi info -t memory -i <npu_id> -c <chip_id>`

**Natural Language:** `NPU memory`, `Memory info`, `HBM`

**Output:** Memory usage details

## Utilization

### Get Utilization

**Command:** `npu-smi info -t usages -i <npu_id> -c <chip_id>`

**Natural Language:** `NPU utilization`, `Usage`

**Output:** NPU utilization percentage

## ECC Status

### Get ECC Status

**Command:** `npu-smi info -t ecc -i <npu_id> -c <chip_id>`

**Natural Language:** `ECC status`, `ECC info`, `ECC`

**Output:** ECC enable status and error counts

## Process Information

### Get Processes

**Command:** `npu-smi info -t proc-mem -i <npu_id>`

**Natural Language:** `NPU processes`, `Process info`

**Output:** Running processes on NPU

## PCIe Information

### Get PCIe Errors

**Command:** `npu-smi info -t pcie-err -i <npu_id>`

**Natural Language:** `PCIe errors`, `PCIe info`, `PCIe`

**Output:** PCIe error statistics

## Topology

### Get Topology

**Command:** `npu-smi info -t topo -i <npu_id>`

**Natural Language:** `Topology`

**Output:** NPU topology information

## Specifying Target Device

All commands support specifying target device:

```
NPU0 temperature
NPU1 health check
NPU0 Chip1 memory
```

If not specified, defaults to NPU 0, Chip 0.
