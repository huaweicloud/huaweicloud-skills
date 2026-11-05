# Troubleshooting and Practical Experience

## 0. Error Code Reference (NPU-*)

Every failure surfaced by the skill uses a stable three-line contract:

```
[ERROR] NPU-<CODE>
Message: <what failed>
Suggestion: <what to try next>
```

| Code | `kind` | Triggered when | Typical `Message` |
|------|--------|----------------|-------------------|
| `NPU-SSH-AUTH` | `ssh_auth` | SSH authentication is rejected (`paramiko.AuthenticationException`) — wrong password, unknown/locked user, or password auth disabled | `SSH authentication failed: Authentication failed.` |
| `NPU-SSH-UNREACHABLE` | `ssh_unreachable` | Host/port cannot be reached (`NoValidConnectionsError`, `socket.timeout`, `socket.error`, `ConnectionRefusedError`) | `Cannot reach SSH host <host>:<port>: ...` |
| `NPU-SSH-ERROR` | `ssh_error` | Any other SSH/paramiko failure (protocol, host key, channel, library) | `SSH error: ...` |
| `NPU-CMD-NOT-FOUND` | `command_not_found` | Local `npu-smi` (or `ascend-dmi`) binary missing / not in `PATH` (`FileNotFoundError`) | `npu-smi 未安装或不在 PATH 中` |
| `NPU-CMD-FAILED` | `command_failed` | Command ran but failed — non-zero exit code, or SSH returned stderr with empty stdout | includes exit code + stderr summary |
| `NPU-TIMEOUT` | `timeout` | Command exceeded the timeout (`subprocess.TimeoutExpired`); SSH connect timeout defaults to 10s, per-command timeout is 60s | timeout detail (the timed-out command and the limit reached) |

Plus the catch-all `[ERROR] NPU-UNEXPECTED` for an unforeseen exception; it
never prints a traceback.

**Boundary contract — connection failure never degrades into "No NPU devices
found":** SSH/connection errors are raised as `NpuCommandError` and propagate to
the top-level handler. They are **not** returned as command stdout, so parsing
never turns them into an empty device list. Consequences:

- An authentication failure shows `[ERROR] NPU-SSH-AUTH`, not `No NPU devices found`.
- An unreachable host shows `[ERROR] NPU-SSH-UNREACHABLE`, not `No NPU devices found`.
- `No NPU devices found` now means exactly one thing: the connection succeeded
  and the remote/local `npu-smi` genuinely reported no devices.

### Troubleshooting by code

**`NPU-SSH-AUTH`**
1. Re-check `--user` / `--password` (and `--port`); a stale password is the most
   common cause.
2. On the target machine confirm password login is enabled:
   `grep -i '^PasswordAuthentication' /etc/ssh/sshd_config` → should be `yes`.
3. Check the account is not locked or expired:
   `passwd -S <user>` / `chage -l <user>`.
4. The skill retries once before raising, so a single transient failure is
   already tolerated; a persistent `NPU-SSH-AUTH` is a credential/config issue.

**`NPU-SSH-UNREACHABLE`**
1. Verify the IP/port: `ping <host>` and `nc -vz <host> 22` (or `ssh -p <port> <user>@<host>`).
2. Confirm `sshd` is running on the target: `systemctl status sshd`.
3. Check firewall / cloud security group rules allow the SSH port
   (default 22); `127.0.0.1` is only reachable if an SSH server is actually
   listening locally.
4. Total wait is bounded by roughly `2 × ssh_timeout` (default ~20s) because of
   the single retry — a long silent wait means the host is filtering packets.

**`NPU-SSH-ERROR`**
1. Verify paramiko is installed: `python3 -c "import paramiko; print(paramiko.__version__)"`
   (install with `pip install -r requirements.txt`).
2. Check the server's SSH algorithm/host-key policy and any `known_hosts`
   restrictions.
3. Retry once; if it is transient the second attempt usually succeeds.

**`NPU-CMD-NOT-FOUND`**
1. Install the CANN toolkit / `npu-smi` on the target machine.
2. Ensure it is on `PATH`, e.g.
   `export PATH=$PATH:/usr/local/Ascend/ascend-toolkit/latest/bin`.
3. For FLOPS tests, confirm `ascend-dmi` is installed; otherwise the skill
   reports `❌ ascend-dmi not found ...` and continues without a traceback.

**`NPU-CMD-FAILED`**
1. Read the exit code and stderr summary in the `Message` line.
2. Re-run the same command directly via passthrough to see the full output:
   `python3 scripts/main.py --command "npu-smi info -l"`.
3. Common causes: insufficient permissions (run as root), device busy,
   unsupported sub-command for the chip, invalid firmware path.

**`NPU-TIMEOUT`**
1. Confirm the machine is responsive (`uptime`, `npu-smi info` by hand).
2. Long firmware operations can legitimately exceed 60s — run them directly on
   the target instead of through the skill's per-command timeout.
3. Reduce network latency or use a persistent SSH connection.

## 1. Connection Issues

### Issue: SSH connection failed

**Symptom:** `[ERROR] NPU-SSH-AUTH` (`paramiko.AuthenticationException`) or
`[ERROR] NPU-SSH-UNREACHABLE` (connection timeout / refused)

**Codes:** see section 0 above — authentication failure and host-unreachable are
reported distinctly, and **neither** degrades into `No NPU devices found`.

**Possible causes:**
1. Incorrect host IP address
2. Wrong username/password
3. SSH service not running on target machine
4. Firewall blocking port 22
5. SELinux restrictions

**Troubleshooting:**
```bash
# Test SSH connectivity
ssh root@<host> -p 22

# Check if SSH service is running
systemctl status sshd  # On target machine
```

**Solution:**
1. Verify host IP, username, and password
2. Ensure SSH service is running on target
3. Check firewall rules allow port 22

### Issue: Connection refused

**Symptom:** `Connection refused`

**Root cause:** SSH daemon not running or port blocked

**Solution:**
```bash
# On target machine
systemctl start sshd
systemctl enable sshd
```

## 2. NPU-SMI Issues

### Issue: npu-smi command not found

**Symptom:** `npu-smi: command not found`

**Root cause:** CANN software stack not installed or not in PATH

**Solution:**
```bash
# Source CANN environment
source /usr/local/Ascend/ascend-toolkit/set_env.sh

# Or add to PATH
export PATH=$PATH:/usr/local/Ascend/ascend-toolkit/latest/bin
```

### Issue: npu-smi returns empty output

**Possible causes:**
1. NPU device not detected
2. Driver not loaded
3. Permission issues

**Troubleshooting:**
```bash
# Check driver status
lsmod | grep ascend

# Check device nodes
ls /dev/davinci*

# Check permissions
ls -la /dev/davinci*
```

### Issue: Permission denied for /dev/davinci

**Symptom:** `Permission denied` when accessing NPU devices

**Root cause:** User doesn't have permission to access NPU device nodes

**Solution:**
```bash
# Add user to video group
usermod -aG video $USER

# Or set permissions (less secure)
chmod 666 /dev/davinci*
```

## 3. Command Execution Issues

### Issue: Command not recognized

**Symptom:** "Unknown command" response

**Root cause:** Input doesn't match any supported command patterns

**Solution:**
- Check command spelling
- Use simpler commands like "NPU list" or "NPU info"
- Type "help" to see supported commands

### Issue: Sensitive operation requires confirmation

**Symptom:** "Please reply 'confirm' or 'cancel'"

**Expected behavior:** This is expected for sensitive operations like:
- ECC enable/disable
- Fan mode changes
- Firmware upgrade
- vNPU creation/deletion

**Solution:** Reply with "confirm" to proceed or "cancel" to abort

## 4. Performance Issues

### Issue: Slow SSH connection

**Symptom:** Commands take long to execute remotely

**Root cause:** Network latency or slow SSH handshake

**Solution:**
- Enable SSH ControlMaster for persistent connections
- Use SSH compression
- Check network latency with ping

### Issue: FLOPS test takes too long

**Symptom:** Multi-device FLOPS test takes > 2 seconds

**Expected behavior:** Single device ~2 seconds, multi-device should be parallel

**Solution:** The skill automatically runs multi-device tests in parallel

## 5. Compatibility Issues

### Issue: Command not supported on this chip

**Symptom:** "Command not supported on this chip type"

**Root cause:** Some commands are chip-specific

**Solution:** The skill automatically downgrades to alternative commands when available

## 6. Common Error Messages

| Error Message | Cause | Solution |
|--------------|-------|----------|
| `[ERROR] NPU-SSH-AUTH` | SSH authentication rejected | Verify `--user`/`--password`, password login enabled, account not locked → section 0 |
| `[ERROR] NPU-SSH-UNREACHABLE` | Host/port unreachable, sshd down, security group blocks port | Verify host/port, `sshd` status, firewall/security group → section 0 |
| `[ERROR] NPU-SSH-ERROR` | Other SSH/paramiko failure | Check paramiko install and SSH server policy → section 0 |
| `[ERROR] NPU-CMD-NOT-FOUND` | `npu-smi` (or `ascend-dmi`) not installed / not in `PATH` | Install CANN toolkit, source `set_env.sh` → section 0 |
| `[ERROR] NPU-CMD-FAILED` | Command exited non-zero or returned stderr only | Read exit code + stderr, re-run via passthrough → section 0 |
| `[ERROR] NPU-TIMEOUT` | Command exceeded the 60s per-command timeout | Run long operations directly; check host responsiveness → section 0 |
| `[ERROR] NPU-UNEXPECTED` | Unforeseen exception (never a traceback) | Retry; check environment and parameters |
| `npu-smi not found` | CANN not installed | Install CANN toolkit |
| `Connection refused` | SSH not running | Start SSH daemon |
| `Permission denied` | No device access | Add user to video group |
| `Unknown command` | Invalid input | Check command format |
| `Sensitive operation` | Need confirmation | Reply "confirm" or "cancel" |
| `No NPU devices found` | Connection **succeeded** but npu-smi reported no devices | This is *not* a connection error — see section 0 boundary contract |
