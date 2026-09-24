# ECS Validation Rules for Shutdown Experiment

## Overview

Before generating experiment configuration, each target ECS instance must pass compatibility validation. This document defines the validation rules and their rationale.

## Validation Rules

### Rule 1: Status Must Be ACTIVE

**Check**: Instance `status` field must be `ACTIVE` (power_state = 1 / RUNNING).

**Rationale**: You can only shut down a running instance. If the instance is already stopped (SHUTOFF), in error state, or being migrated, the shutdown API call will fail or be meaningless.

**On Failure**: The instance is marked as incompatible. The experiment cannot proceed for this target.

---

### Rule 2: Spot/Bidding Instance Warning

**Check**: Instance `charging_mode` is checked for spot/bidding (竞价/竞享) billing.

**Rationale**: Spot and bidding instances have an interruption mechanism — their lifecycle is not fully controlled by the user. When a spot instance is "stopped", the cloud platform may release it entirely instead of performing a graceful shutdown. After release, the instance cannot be restarted, making rollback impossible.

**On Warning**: The instance is still allowed in the experiment, but a warning is issued:
> "Spot/bidding instance: shutdown may trigger release instead of graceful stop. Consider using a pay-per-use or yearly/monthly instance."

---

### Rule 3: AS Scaling Group Association

**Check**: Query AS (Auto Scaling) service to determine if the instance is a member of a scaling group.

**Rationale**: If an instance belongs to an AS scaling group, shutting it down may trigger:
1. The scaling group to detect the instance as "unhealthy" and remove it
2. The scaling group to launch a new replacement instance
3. This unintended scaling activity pollutes the experiment results

**On Warning**: A warning is issued recommending to pause scaling activities before the experiment:
> "Instance belongs to AS group '{group_id}'. Consider pausing scaling activities first."

---

### Rule 4: Single-AZ Deployment Risk

**Check**: If all target instances are in the same Availability Zone (AZ), flag as HA risk.

**Rationale**: If all targets are in one AZ, shutting them down simultaneously means:
1. No cross-AZ redundancy during the experiment
2. A real AZ failure would have the same blast radius
3. The experiment may cause complete service outage instead of partial degradation

**On Warning**: A warning is issued:
> "All N targets are in the same AZ — no cross-AZ redundancy during experiment."

---

### Rule 5: Shutdown Billing Impact

**Check**: Instance `charging_mode` determines billing behavior during shutdown.

**Rationale**: Different billing modes have different cost implications during shutdown:

| Billing Mode | Shutdown Billing Behavior |
|---|---|
| On-demand (按需) | Basic resources (vCPU/memory) stop billing. Disks/EIP/bandwidth continue. |
| Yearly/Monthly (包年包月) | Billing continues regardless (pre-paid). No cost impact. |
| Spot (竞价) | May be released — billing stops but instance is gone. |
| Special instances (local disk, FPGA, BMS) | Continue billing during shutdown. |

**On Pass**: Informational note about billing impact is added to the validation result.

## Validation Result Format

```json
{
  "total": 2,
  "all_compatible": true,
  "warning_count": 1,
  "instance_results": [
    {
      "instance_id": "i-xxx",
      "checks": [...],
      "warnings": ["Instance belongs to AS group ..."],
      "errors": [],
      "compatible": true
    }
  ],
  "recommendation": "All targets are compatible but with warnings. Review warnings before proceeding."
}
```

## Decision Matrix

| Errors | Warnings | Result |
|---|---|---|
| 0 | 0 | ✅ Compatible — proceed |
| 0 | >0 | ⚠️ Compatible with warnings — review before proceeding |
| >0 | any | ❌ Not compatible — fix errors first |
