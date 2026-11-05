# Verification Steps and Methods

Reproducible verification for `huawei-cloud-ascend-command`. Every command below
is meant to be run from the skill directory:

```bash
cd skills/ai/modelarts/huawei-cloud-ascend-command
```

`python3` may be `python` on Windows.

## Prerequisite Verification

### 1. Verify Python3

```bash
python3 --version  # Python3 >= 3.8
```

### 2. Verify Local NPU Environment

```bash
# Check if npu-smi is available locally
npu-smi info -l 2>/dev/null || echo "npu-smi not found locally"
```

### 3. Verify the SSH Dependency (paramiko)

```bash
python3 -c "import paramiko; print(paramiko.__version__)" || echo "paramiko missing (pip install -r requirements.txt)"
```

## Functional Verification

### Local Mode Verification

```bash
# Basic device query
python3 scripts/main.py --command "NPU list"

# Check health
python3 scripts/main.py --command "NPU health check"

# Get temperature
python3 scripts/main.py --command "NPU temperature"

# Direct npu-smi command
python3 scripts/main.py --npu-smi "info -l"
```

### SSH Remote Mode Verification

```bash
# Remote device query
python3 scripts/main.py --command "NPU list" --host 192.168.1.100 --user root --password xxx

# Remote health check
python3 scripts/main.py --command "NPU health check" --host 192.168.1.100 --user root --password xxx

# Remote temperature
python3 scripts/main.py --command "NPU temperature" --host 192.168.1.100 --user root --password xxx
```

### Interactive Mode Verification

```bash
python3 scripts/main.py
# Then type commands interactively:
# - NPU list
# - NPU health check
# - set fan auto        (→ confirm gate; then reply "confirm")
# - rollback firmware   (→ confirm gate; then reply "confirm")
# - exit
```

## Regression Verification Matrix (18 fixed items)

| # | Item | Reproduction command | Expected result |
|---|------|----------------------|-----------------|
| 1 | B115-1 version field | inspect `SKILL.md` frontmatter | `version: 1.0.0` present (unchanged) |
| 2 | B115-2 direct passthrough | `python3 scripts/main.py --command "npu-smi info -l"` | `-l` executed verbatim (no NL routing) |
| 3 | B115-3 create vNPU | `python3 scripts/main.py --command "create vNPU NPU0 Chip0 template vir04"` | create-vNPU confirmation gate (not template info) |
| 4 | B115-4 None input | `python3 -c "from scripts.executor import NpuExecutor; print(NpuExecutor().handle_command(None))"` | help JSON with `"status": "help"`, no exception |
| 5 | B115-5 FLOPS without ascend-dmi | `python3 scripts/main.py --command "Run FLOPS test"` | friendly `❌ ascend-dmi not found ...`, no traceback |
| 6 | B115-6 activate synonym | `python3 scripts/main.py --command "activate upgrade mcu NPU0"` | activation confirmation gate |
| 7 | I178-1 fan auto | `python3 scripts/main.py --command "set fan auto"` | `Set fan to auto mode` gate (never 50%) |
| 8 | I178-2 SSH errors | `python3 scripts/main.py --command "NPU health check" --host 127.0.0.1 --user root --password x` | `[ERROR] NPU-SSH-AUTH` or `[ERROR] NPU-SSH-UNREACHABLE`; **not** `No NPU devices found` |
| 9 | I178-3 Chinese trigger | `python3 scripts/main.py --command "查看NPU温度"` | temperature output (not `Unknown command`) |
| 10 | I178-4 ECC direction | `python3 scripts/main.py --command "set ECC"` | `Please specify direction: 'enable ECC' or 'disable ECC'` (not disable) |
| 11 | I178-5 vNPU spelling | stub `_run_npu_smi` (see below) | captured argv contains `create-vnpu` / `destroy-vnpu` |
| 12 | I178-6 rollback route | `python3 scripts/main.py --command "rollback firmware"` | rollback confirmation gate |
| 13 | I88-1 SKILL.md size | count lines of `SKILL.md` | ≤ 200 |
| 14 | I88-2 category | inspect `SKILL.md` frontmatter | `category: operational` present |
| 15 | I88-3 requirements | `cat requirements.txt` | `paramiko>=2.11,<4` declared |
| 16 | I88-4 graceful errors | `python3 scripts/main.py --command "NPU list"` without local `npu-smi` | `[ERROR] NPU-CMD-NOT-FOUND` + suggestion, exit 1, no traceback |
| 17 | I88-5 Error Handling section | inspect `SKILL.md` | `## Error Handling & Stability` present |
| 18 | I88-6 stability contract centralized | inspect `SKILL.md` + `references/troubleshooting.md` | SKILL.md states the contract; troubleshooting expands it |

### A. Chinese input and direct passthrough

```bash
# Chinese temperature request must route to the temperature handler
python3 scripts/main.py --command "查看NPU温度"

# Chinese aliases are normalized before routing (温度/功耗/显存/算力/固件/风扇/自动...)
python3 scripts/main.py --command "查询NPU功耗"
python3 scripts/main.py --command "查看显存"
python3 scripts/main.py --command "设置风扇自动"

# Direct commands are executed verbatim, before NL routing
python3 scripts/main.py --command "npu-smi info -l"
python3 scripts/main.py --command "npu-smi info -t board -i 0"
```

`npu-smi info -l` must reach the client with the `-l` argument intact. On a host
without `npu-smi`, the expected graceful result is `[ERROR] NPU-CMD-NOT-FOUND`
(not a temperature/device summary and not `Unknown command`).

### B. Routing and confirmation gates

```bash
# Fan mode vs. fan speed
python3 scripts/main.py --command "set fan auto"
python3 scripts/main.py --command "set fan manual"
python3 scripts/main.py --command "set fan speed 70"
python3 scripts/main.py --command "set fan"                 # → clarification, no gate

# ECC direction is mandatory
python3 scripts/main.py --command "set ECC"                 # → clarification, no gate
python3 scripts/main.py --command "disable ECC"             # → disable gate

# Firmware
python3 scripts/main.py --command "firmware version"
python3 scripts/main.py --command "upgrade status"
python3 scripts/main.py --command "rollback firmware"
python3 scripts/main.py --command "activate firmware mcu NPU0"
python3 scripts/main.py --command "activate upgrade mcu NPU0"

# Virtualization routing order
python3 scripts/main.py --command "create vNPU NPU0 Chip0 template vir04"
python3 scripts/main.py --command "template info NPU0"
```

Expected gates (exact phrases):

| Input | Gate text |
|-------|-----------|
| `set fan auto` | `⚠️ Sensitive operation: Set fan to auto mode` |
| `set fan manual` | `⚠️ Sensitive operation: Set fan to manual mode` |
| `set fan speed 70` | `⚠️ Sensitive operation: Set fan speed to 70%` |
| `create vNPU NPU0 Chip0 template vir04` | `⚠️ Sensitive operation: Create vNPU on NPU 0 Chip 0 (template: vir04)` |
| `rollback firmware` | rollback confirmation gate (mentions rollback may not be supported on all devices) |
| `activate upgrade mcu NPU0` | `⚠️ Sensitive operation: Activate mcu firmware on NPU 0 (requires reboot)` |

Each gate must be followed by `Please reply 'confirm' or 'cancel'`, and no
command may be dispatched before `confirm`.

### C. Dispatch verification with a stub client

Interactive confirmation (or a stubbed client) is needed to assert the exact
command that is finally sent. Run from the skill directory:

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, "scripts")
from executor import NpuExecutor

captured = []
ex = NpuExecutor()
ex.client._run_npu_smi = lambda args: captured.append(args) or "stub-ok"

# create vNPU
ex.pending_confirmation = ("create_vnpu", 0, 0, "vir04")
ex.handle_command("confirm")
# destroy vNPU
ex.pending_confirmation = ("destroy_vnpu", 0, 0, 100)
ex.handle_command("confirm")
# rollback firmware
ex.pending_confirmation = ("upgrade_rollback", 1)
ex.handle_command("confirm")
# fan mode / fan speed
ex.handle_command("set fan auto");  ex.handle_command("confirm")
ex.handle_command("set fan speed 70"); ex.handle_command("confirm")

for c in captured:
    print(c)
assert any("create-vnpu" in c for c in captured), "create-vnpu missing"
assert any("destroy-vnpu" in c for c in captured), "destroy-vnpu missing"
assert any("rollback" in c for c in captured), "rollback missing"
assert any("pwm-mode" in c for c in captured), "pwm-mode missing"
assert any("pwm-duty-ratio" in c for c in captured), "pwm-duty-ratio missing"
assert not any("vnru" in c for c in captured), "misspelled vnru command"
print("OK: dispatch assertions passed")
PY
```

Expected dispatches:

| Operation | Dispatched command |
|-----------|--------------------|
| create vNPU | `npu-smi set -t create-vnpu -i 0 -c 0 -f vir04` |
| destroy vNPU | `npu-smi set -t destroy-vnpu -i 0 -c 0 -v 100` |
| rollback firmware | `npu-smi upgrade -a rollback -i 1` |
| fan auto | `npu-smi set -t pwm-mode -d 1` |
| fan speed 70 | `npu-smi set -t pwm-duty-ratio -d 70` |

> Note: `_execute_confirmed` expects the `upgrade_rollback` op tuple; confirm
> the actual tuple shape in `scripts/executor.py` before running this snippet and
> adjust the tuple if the field order differs.

### D. Error handling without NPU hardware

```bash
# 1. None / non-string / empty input must return help JSON, never raise
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from executor import NpuExecutor
ex = NpuExecutor()
for bad in (None, 123, '', '   '):
    out = ex.handle_command(bad)
    assert 'help' in out, out
print('OK: input defense')
"

# 2. Local mode without npu-smi → typed error, exit code 1, no traceback
python3 scripts/main.py --command "NPU list"; echo "EXIT=$?"

# 3. FLOPS without ascend-dmi → friendly message, no FileNotFoundError
python3 scripts/main.py --command "Run FLOPS test"

# 4. SSH failure is reported, never turned into an empty device list
python3 scripts/main.py --command "NPU health check" --host 127.0.0.1 --user root --password x; echo "EXIT=$?"
python3 scripts/main.py --command "NPU health check" --host 192.0.2.1 --user root --password x; echo "EXIT=$?"
```

Acceptance for step 4:

- Output starts with `[ERROR] NPU-SSH-AUTH` (an SSH server answered and rejected
  the credentials) or `[ERROR] NPU-SSH-UNREACHABLE` (nothing listening /
  unreachable).
- Output is followed by `Message:` and `Suggestion:` lines.
- `EXIT=1`.
- The output must **not** contain `No NPU devices found`.
- `192.0.2.1` (TEST-NET-1) is intentionally unreachable; the wait is bounded by
  the single retry (~2 × 10s), not ~60s.
- Without `paramiko` installed, the missing import is surfaced as a friendly
  `NPU-SSH-ERROR`/suggestion rather than a traceback.

### E. Structural and gate verification

```bash
# Compile all three scripts
python3 -m py_compile scripts/npu_client.py scripts/executor.py scripts/main.py

# SKILL.md length (target ≤ 200)
wc -l SKILL.md

# Total files in the skill (≤ 30)
find . -type f | wc -l

# Repository gate (FAIL must be 0; the existing `version` WARN is acceptable)
bash <repo>/skills/devtools/common/huawei-cloud-skill-creator/scripts/validate-skill.sh -s .
```

## Expected Results

| Test Case | Expected Output |
|-----------|----------------|
| Python3 check | Python version >= 3.8 |
| Local NPU list | Shows NPU devices, or `[ERROR] NPU-CMD-NOT-FOUND` when npu-smi is absent |
| Help command | Shows supported commands list |
| Remote command | NPU info from remote server, or `[ERROR] NPU-SSH-*` when the connection fails |
| `set fan auto` | `Set fan to auto mode` confirmation gate |
| `查看NPU温度` | Temperature output for the selected device |
| `set ECC` | Direction clarification request |
| `rollback firmware` | Rollback confirmation gate |
| `npu-smi info -l` | Verbatim `npu-smi info -l` output |
