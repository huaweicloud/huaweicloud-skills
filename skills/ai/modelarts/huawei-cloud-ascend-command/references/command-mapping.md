# Command Mapping Reference

Complete natural language → `npu-smi` / `ascend-dmi` command mapping for
`huawei-cloud-ascend-command`. This is the expanded form of the mapping tables
that used to live in `SKILL.md`.

## Direct Command Passthrough

Any input whose trimmed, lower-cased form starts with `npu-smi` is executed
**verbatim** before natural-language routing. Nothing is rewritten or dropped:

| Input | Executed command |
|-------|------------------|
| `npu-smi info -l` | `npu-smi info -l` |
| `npu-smi info -t board -i 0` | `npu-smi info -t board -i 0` |
| `--npu-smi "info -l"` (CLI flag) | `npu-smi info -l` |

This is why `npu-smi info -l` no longer falls into the semantic `NPU info`
branch and silently loses `-l`.

## Device Queries

| Natural Language | Command | Description |
|-----------------|---------|-------------|
| List all NPU devices | `npu-smi info -l` | List all NPU devices |
| NPU card info | `npu-smi info -m` | Card and chip mapping |
| NPU info | `npu-smi info` | Full NPU information |

## Health Check

| Natural Language | Command | Description |
|-----------------|---------|-------------|
| NPU health check | `npu-smi info -t health -i 0` | Check device health |
| Check NPU status | `npu-smi info -t health -i 0` | Check device health |

## Temperature / Power / Memory

| Natural Language | Command | Description |
|-----------------|---------|-------------|
| NPU temperature | `npu-smi info -t temp -i 0 -c 0` | Get temperature |
| NPU power | `npu-smi info -t power -i 0 -c 0` | Get power usage |
| NPU memory | `npu-smi info -t memory -i 0 -c 0` | Get memory info |
| NPU utilization | `npu-smi info -t usages -i 0 -c 0` | Get utilization |

## Configuration

| Natural Language | Command | Description |
|-----------------|---------|-------------|
| Set ECC (enable) | `npu-smi set -t ecc-enable -i 0 -c 0 -d 1` | Enable ECC (requires confirmation) |
| Set ECC (disable) | `npu-smi set -t ecc-enable -i 0 -c 0 -d 0` | Disable ECC (requires confirmation) |
| Set fan auto | `npu-smi set -t pwm-mode -d 1` | Set fan to auto mode (requires confirmation) |
| Set fan manual | `npu-smi set -t pwm-mode -d 0` | Set fan to manual mode (requires confirmation) |
| Set fan speed N | `npu-smi set -t pwm-duty-ratio -d N` | Duty ratio in `0-100` (requires confirmation); value is clamped to `0-100` |
| Clear ECC errors | `npu-smi clear -t ecc-info -i 0 -c 0` | Clear ECC error count (requires confirmation) |

**Ambiguity handling (no command is dispatched):**

| Input | Behavior |
|-------|----------|
| `set ECC` (no enable/disable) | Replies `Please specify direction: 'enable ECC' or 'disable ECC'`; no confirmation gate is armed |
| `set fan` (no mode word, no number) | Asks for `auto` / `manual` or a `0-100` speed; **never** defaults to 50% |
| `set fan speed` (no number) | Asks for a `0-100` value; no confirmation gate is armed |

**Fan mapping notes**

- Mode and speed are **different** `npu-smi` sub-commands in the implementation:
  mode is `set -t pwm-mode -d <0|1>` (auto = `1`, manual = `0`) and speed is
  `set -t pwm-duty-ratio -d <0-100>`. The older `fan-mode` / `fan-speed`
  spellings are not the implemented commands — see
  [configuration.md](configuration.md).
- `Set fan auto` / `Set fan manual` route to the mode branch; `Set fan speed N`
  routes to the speed branch. When a phrase carries both, the mode branch wins.

## Firmware Upgrade

| Natural Language | Command | Description |
|-----------------|---------|-------------|
| Firmware version | `npu-smi upgrade -b mcu -i 0` | Query firmware version |
| Upgrade firmware | `npu-smi upgrade -t mcu -i 0 -f file.hpm` | Upload firmware (requires confirmation) |
| Upgrade status / check | `npu-smi upgrade -q mcu -i 0` | Query upgrade status (read-only) |
| Rollback firmware | `npu-smi upgrade -a rollback -i <npu_id>` | Roll back to the previous firmware version (requires confirmation) |
| Activate firmware / Activate upgrade | `npu-smi upgrade -a mcu -i 0` | Activate uploaded firmware (requires confirmation; device reboot) |

- Component is parsed from the input (`mcu`, `bootloader`, `vrd`); `mcu` is the
  default when no component is named.
- `activate upgrade mcu NPU0` is accepted as a synonym of `activate firmware`
  and enters the same activation confirmation gate.
- The firmware branch order is **version → upload → status/check → rollback →
  activate**, so `rollback firmware` cannot be shadowed by another branch.

## Virtualization

| Natural Language | Command | Description |
|-----------------|---------|-------------|
| vNPU info | `npu-smi info -t info-vnpu -i 0 -c 0` | Query vNPU info |
| vNPU mode | `npu-smi info -t vnru-mode` | Query vNPU/AVI mode |
| Template info | `npu-smi info -t template-info -i 0` | Query template info |
| Create vNPU | `npu-smi set -t create-vnpu -i 0 -c 0 -f vir04` | Create vNPU (requires confirmation) |
| Destroy vNPU | `npu-smi set -t destroy-vnpu -i 0 -c 0 -v <vnpu_id>` | Destroy vNPU (requires confirmation) |

**Spelling**: the dispatched sub-commands are `create-vnpu` and `destroy-vnpu`.
The historical `create-vnru` / `destroy-vnru` spelling was a defect and must not
be reintroduced (npu-smi has no such sub-command).

**Routing order**: `create vNPU` / `new vNPU` and `destroy vNPU` /
`delete vNPU` are matched **before** the template branch; the template branch
matches `template` / `templates` as whole words (plus the compound keywords
`template info` / `vNPU template` / `template-info`). That is what lets
`create vNPU NPU0 Chip0 template vir04` reach the create handler instead of the
template-info handler, while `show template` / `list templates` reach the
template-info handler instead of being swallowed by the temperature branch
(`temp` is matched as a whole word only, so it never fires inside `template`).

**Temperature vs template disambiguation**: the temperature branch routes on
the whole words `temperature` / `temp` only (`\btemp(erature)?\b`), so an input
containing `template` (e.g. `show template`, `list templates`) can never be
silently dispatched as `npu-smi info -t temp -i 0 -c 0`.

## Certificate Management

| Natural Language | Command | Description |
|-----------------|---------|-------------|
| Certificate info | `npu-smi info -t tls-cert -i 0 -c 0` | View TLS certificate |
| Certificate expiration | `npu-smi info -t tls-cert-period -i 0 -c 0` | Query certificate expiration threshold |

## FLOPS Test (ascend-dmi)

**Default behavior: single device FP16, fast return (~2 seconds)**

| Natural Language | Command | Description |
|-----------------|---------|-------------|
| FLOPS test | `ascend-dmi -f -d 0 -t fp16 -q` | Default: NPU 0, FP16 |
| NPU FLOPS | `ascend-dmi -f -d 0 -t fp16 -q` | Same as above |
| NPU 3 FLOPS | `ascend-dmi -f -d 3 -t fp16 -q` | Specify NPU 3 |
| FP32 FLOPS | `ascend-dmi -f -d 0 -t fp32 -q` | FP32 precision |
| All devices FLOPS | 8 devices async parallel | All NPUs tested simultaneously |

**Execution strategy:**

- **Single device**: Direct execution, ~2 seconds return
- **Multi-device**: Async parallel execution, total ~2 seconds (not serial 16 seconds)
- **Precision**: Default fp16, supports fp32/bf16/int8/hf32

**Failure handling**: if `ascend-dmi` is not installed, the skill returns a
friendly `❌ ascend-dmi not found ...` message instead of raising
`FileNotFoundError`; a timed-out test reports `❌ FLOPS test timed out (120s)`;
a non-zero return code reports the stderr summary.

## Related Documents

- [configuration.md](configuration.md) — full configuration reference (fan / ECC)
- [firmware-upgrade.md](firmware-upgrade.md) — firmware and rollback details
- [virtualization.md](virtualization.md) — vNPU and template details
- [certificate-management.md](certificate-management.md) — certificate details
- [troubleshooting.md](troubleshooting.md) — `NPU-*` error codes
