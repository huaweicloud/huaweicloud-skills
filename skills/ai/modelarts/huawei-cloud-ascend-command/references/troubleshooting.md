# Troubleshooting and Practical Experience

## 1. Connection Issues

### Issue: SSH connection failed

**Symptom:** `paramiko.ssh_exception.AuthenticationException` or connection timeout

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
| `npu-smi not found` | CANN not installed | Install CANN toolkit |
| `Connection refused` | SSH not running | Start SSH daemon |
| `Permission denied` | No device access | Add user to video group |
| `Unknown command` | Invalid input | Check command format |
| `Sensitive operation` | Need confirmation | Reply "confirm" or "cancel" |
