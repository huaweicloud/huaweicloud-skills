# Configuration Management Reference

## Fan Control

> **Implementation alignment (ISSUE-001):** the implemented sub-commands are
> `set -t pwm-mode -d <0|1>` for the **mode** and
> `set -t pwm-duty-ratio -d <0-100>` for the **speed**. Earlier documentation
> used the fictional `fan-mode` / `fan-speed` spellings; this section now
> mirrors `scripts/npu_client.py` (`set_fan_mode()` / `set_fan_speed()`).

### Get Fan Mode

**Command:** `npu-smi info -t fan -i <npu_id>`

**Natural Language:** `Fan mode`, `Fan speed`

**Output:** Current fan mode (auto/manual) and speed

### Set Fan Mode to Auto

**Command:** `npu-smi set -t pwm-mode -d 1`

**Natural Language:** `Set fan auto`, `Fan auto`, `Auto fan`, `Set fan mode auto`

**Confirm gate:** `⚠️ Sensitive operation: Set fan to auto mode` → reply `confirm` / `cancel`

**Sensitive:** Requires confirmation

### Set Fan Mode to Manual

**Command:** `npu-smi set -t pwm-mode -d 0`

**Natural Language:** `Set fan manual`, `Fan manual`, `Manual fan`, `Set fan mode manual`

**Confirm gate:** `⚠️ Sensitive operation: Set fan to manual mode` → reply `confirm` / `cancel`

**Sensitive:** Requires confirmation

### Set Fan Speed

**Command:** `npu-smi set -t pwm-duty-ratio -d <percentage>`

**Natural Language:** `Set fan speed 70`, `Set fan speed 70%`, `Fan speed NPU0 70`

**Parameters:** Duty ratio percentage (0-100); values outside the range are clamped

**Confirm gate:** `⚠️ Sensitive operation: Set fan speed to <N>%` → reply `confirm` / `cancel`

**Sensitive:** Requires confirmation

### Ambiguous Fan Input (Clarification, Nothing Dispatched)

| Input | Behavior |
|-------|----------|
| `set fan` (no `auto`/`manual`, no number) | Asks the user to specify `auto` / `manual` or a `0-100` speed. **No** confirmation gate is armed and **no** default such as 50% is assumed. |
| `set fan speed` (no number) | Asks for a `0-100` value; no confirmation gate is armed. |

**Routing rule:** the fan **mode** branch is evaluated first and covers
`fan mode`, `auto fan`, `manual fan`, `fan auto`, `fan manual`,
`set fan auto`, `set fan manual`. The **speed** branch is only reached when the
input contains `fan speed` or an explicit number. Therefore `set fan auto` is
always a mode change, never a 50% speed change.

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

### Ambiguous ECC Input (Clarification, Nothing Dispatched)

**Natural Language:** `set ECC`, `ECC` (with no `enable`/`on` and no
`disable`/`off`)

**Behavior:** replies `Please specify direction: 'enable ECC' or 'disable ECC'`.
No confirmation gate is armed and **disable is never assumed** — an unspecified
direction must not silently disable ECC (ISSUE-004).

**Sensitive:** Requires confirmation only after the direction is explicit

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
