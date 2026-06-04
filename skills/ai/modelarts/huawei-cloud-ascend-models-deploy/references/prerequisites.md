# Prerequisites

Required conditions before using this skill.

## Hardware Requirements

| Requirement | Specification |
|-------------|---------------|
| NPU Type | Ascend 910B series (910B1/B2/B3/B4) |
| NPU Cards | Depends on model (1-16 cards) |
| Memory | Sufficient for model weights |
| Disk | >100GB for model cache |

## Software Requirements

| Software | Version |
|----------|---------|
| OS | Ubuntu 22.04 / EulerOS 2.0 |
| Python | >= 3.8 |
| CANN | >= 8.0 |
| vLLM | Ascend version |

## Network Requirements

| Requirement | Description |
|-------------|-------------|
| OBS Access | For downloading model weights |
| Port | Configurable (default 8080) |
| SSH | For remote deployment |

## Permission Requirements

| Permission | Purpose |
|------------|---------|
| npu-smi | NPU management |
| Docker | Container operations |
| /home/modelarts-agent | Deployment directory |

## Quick Check

```bash
# Check NPU
npu-smi info

# Check Python
python3 --version

# Check disk
df -h /home

# Check directory
ls -la /home/modelarts-agent
```
