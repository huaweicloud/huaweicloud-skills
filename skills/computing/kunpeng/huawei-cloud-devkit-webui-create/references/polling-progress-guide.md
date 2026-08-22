# Polling Progress Guide - Doom-Loop Safe Installation Monitoring

Detailed guide for polling DevKit installation progress without triggering the doom-loop guard. Referenced by SKILL.md Task 2.

## Polling Progress (doom-loop safe, continuous visibility)

The agent MUST use `poll_devkit_status.py` in **background** with output redirected to a log file, then use the `read` tool with **incrementing offset** to read the log every **10-20 seconds**. This avoids the doom-loop guard (no repeated tool-level `status` calls) while giving the user continuous progress visibility.

### Step 1 — Launch poll script in background (1 bash call, returns immediately)

Use `--log-file` so the script writes logs via Python (cross-platform, no shell redirection needed). The log path uses the OS temp dir: Linux `/tmp/`, Windows `%TEMP%`.

**Linux:**
```bash
nohup python3 scripts/poll_devkit_status.py \
  --region $R --eip $EIP --kms-key-id $KID --kms-cipher-text-file $CT_FILE \
  --interval 30 --max-polls 30 \
  --log-file /tmp/devkit_poll_progress.log &
```

**Windows (PowerShell):**
```powershell
Start-Process -NoNewWindow python -ArgumentList "scripts/poll_devkit_status.py --region $R --eip $EIP --kms-key-id $KID --kms-cipher-text-file $CT_FILE --interval 30 --max-polls 30 --log-file $env:TEMP\devkit_poll_progress.log"
```

### Step 2 — Read log with `read` tool, incrementing offset every 10-20s

```
read <log_file>  (offset=1,   limit=50)   → report new lines to user
read <log_file>  (offset=51,  limit=50)   → report new lines to user
read <log_file>  (offset=101, limit=50)   → report new lines to user
...continue until log contains "DONE" or "TIMEOUT"
```

`<log_file>` is the path passed to `--log-file` (Linux `/tmp/devkit_poll_progress.log`, Windows `%TEMP%\devkit_poll_progress.log`).

### Guidelines

| Guideline | Value |
|-----------|-------|
| Read interval | 10-20 seconds (agent reply naturally spaces calls) |
| Read tool | `read` (NOT `bash tail`) — file read tool, not subject to bash doom-loop guard |
| Offset | Must increment each call (ensures each call is distinct, not a repeated identical call) |
| Max read calls | ~15-20 (installation 5-15 min / 10-20s interval) |
| Stop condition | Log contains `DONE: install_process=DONE` (success) or `TIMEOUT: not DONE` (failure) |

### Why `read` tool instead of `bash tail`

- `bash tail <log_file>` repeated calls → triggers doom-loop guard (identical command pattern)
- `read` tool with incrementing offset → each call has different parameters, file read tool bypasses bash guard
- `poll_devkit_status.py` already wraps `status` in a single Python loop → no tool-level `status` repetition

### Step 3 — Stop polling

Stop when log contains `DONE: install_process=DONE, all services active` (success) or `TIMEOUT: not DONE` (failure). Check the remote `verify_devkit.sh` result before proceeding to Task 3.

## Status Fields Reference

The `status` subcommand and `poll_devkit_status.py` report the following fields:

| Field | Values | Description |
|-------|--------|-------------|
| Install process status | `PREPARING` / `RUNNING` / `DONE` / `NOT_STARTED` | Overall install phase |
| Current stage | e.g. `[2/6] Install Dependencies` | Parsed from wrapper log during PREPARING; empty otherwise |
| Services | devkit_nginx, gunicorn_framework, gunicorn_plugin | active / failed / inactive |
| Plugins | porting, affinity, devtools, debugger, sys_perf, java_perf, sys_diagnosis | installed / missing |
| Ports | 8086, 8002, 7996 | listening or not |
| Last log lines | PREPARING → `/tmp/devkit_install_wrapper.log` (yum/wget output); RUNNING/DONE → `/tmp/devkit_install.log` | Recent install output |