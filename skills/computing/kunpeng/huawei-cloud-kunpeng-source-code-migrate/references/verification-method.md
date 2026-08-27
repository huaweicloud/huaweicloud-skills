# Verification Method - Kunpeng Source Code Migration Assessment

Step-by-step verification methods for each task in the migration assessment workflow.

> **⚠️ SSH Command Execution:**
>
> All `remote_exec` calls in this document MUST be replaced with the built-in `ssh_client.py` script:
> ```bash
> # Instead of: remote_exec "<command>"
> # Use:
> python <skill_dir>/scripts/ssh_client.py exec "<command>" [timeout]
> ```
> The `ssh_client.py` script uses **unified paramiko-based SSH** (password from `MIGRATE_SSH_PASS` environment variable, no ControlMaster, no key injection). No `sshpass` is needed. The password is read from `os.environ` (or Windows user-level registry as fallback), never passed via argv, and wiped from `os.environ` immediately after each connection is established.

## Table of Contents

- [End-to-End Verification](#end-to-end-verification)
- [Task 0: OS Detection and Environment Preparation Verification](#task-0-os-detection-and-environment-preparation-verification)
- [Task 0a: Local DevKit Installation Verification](#task-0a-local-devkit-installation-verification)
- [Task 1: SSH Connection Verification](#task-1-ssh-connection-verification)
- [Task 2: DevKit Installation Verification (Remote)](#task-2-devkit-installation-verification-remote)
- [Task 3: Source Code Scan Verification](#task-3-source-code-scan-verification)
- [Security Verification](#security-verification)

---

## End-to-End Verification

Complete end-to-end verification of the migration assessment workflow.

**Prerequisites:**
- SSH connection is configured via built-in `ssh_client.py` script (paramiko + password from `MIGRATE_SSH_PASS` env var)
- Environment variables are set (`KUNPENG_SERVER_HOST`, `KUNPENG_SERVER_PORT`, `KUNPENG_SERVER_USER`, `MIGRATE_SSH_PASS`)
- Remote server is accessible via SSH (paramiko + password from MIGRATE_SSH_PASS env var)
- Source code exists on the remote server

**Verification steps:**

```bash
# Step 1: Verify environment variables are set
[ -n "$KUNPENG_SERVER_HOST" ] && echo "PASS: KUNPENG_SERVER_HOST is set" || echo "FAIL: KUNPENG_SERVER_HOST is not set"
[ -n "$KUNPENG_SERVER_USER" ] && echo "PASS: KUNPENG_SERVER_USER is set" || echo "FAIL: KUNPENG_SERVER_USER is not set"

# Step 2: Test SSH connection (paramiko reads MIGRATE_SSH_PASS from env)
python <skill_dir>/scripts/ssh_client.py test

# Step 3: Verify DevKit is installed
python <skill_dir>/scripts/ssh_client.py exec "devkit --version && echo 'PASS: DevKit is installed'" 2>&1

# Step 4: Run a test scan
python <skill_dir>/scripts/ssh_client.py exec "devkit porting src-mig -i <TEST_SOURCE_PATH> -o /tmp/devkit-report && echo 'PASS: Scan completed successfully'" 2>&1

# Step 5: Verify report was generated
python <skill_dir>/scripts/ssh_client.py exec "ls -la /tmp/devkit-report/ && echo 'PASS: Report files exist'" 2>&1
```

---

## Task 0: OS Detection and Environment Preparation Verification

### Verify local OS was detected

**Manual check:** Confirm that the skill ran `uname -m` and `cat /etc/os-release` to detect the local OS before asking the user any questions.

### Verify OS classification

```bash
# Check that OS was correctly classified
OS_INFO=$(cat /etc/os-release 2>/dev/null)
ARCH=$(uname -m)

# Verify architecture detection
if [ "$ARCH" = "x86_64" ] || [ "$ARCH" = "aarch64" ]; then
    echo "PASS: Architecture detected as $ARCH"
else
    echo "FAIL: Unexpected architecture: $ARCH"
fi

# Verify OS type detection
SUPPORTED=false
for os in openEuler CentOS Ubuntu Kylin UOS EulerOS Debian SUSE NeoKylin; do
    if echo "$OS_INFO" | grep -qi "$os"; then
        echo "PASS: OS detected as $os (supported for local install)"
        SUPPORTED=true
        break
    fi
done

if [ "$SUPPORTED" = false ]; then
    echo "INFO: Local OS not in DevKit-supported list (remote install required)"
fi
```

### Verify user was asked about install location (if OS is supported)

**Manual check:** If local OS is supported, confirm the skill asked: "您希望在哪里安装DevKit进行源码迁移评估？" with options for local and remote install.

### Verify user was directed to remote path (if OS is unsupported)

**Manual check:** If local OS is Windows/macOS/unsupported, confirm the skill directly asked about remote server availability without offering local install.

### Verify hcloud CLI installation (if provisioning path)

```bash
which hcloud && echo "PASS: hcloud is installed" || echo "FAIL: hcloud not found"
hcloud version 2>&1
```

### Verify hcloud authentication (if provisioning path)

```bash
RESULT=$(hcloud ECS ListServersDetails --region=cn-southwest-2 --cli-output="cols=ServerId" 2>&1)
if echo "$RESULT" | grep -qi "authentication\|unauthorized\|credential"; then
    echo "FAIL: hcloud is not authenticated"
else
    echo "PASS: hcloud is authenticated"
fi
```

### Verify ECS provisioning (if provisioning path)

```bash
[ -f "/tmp/kunpeng_server_env.sh" ] && echo "PASS: Environment file exists" || echo "FAIL: Environment file not found"

source /tmp/kunpeng_server_env.sh 2>/dev/null
[ -n "$KUNPENG_SERVER_HOST" ] && echo "PASS: KUNPENG_SERVER_HOST is set" || echo "FAIL: KUNPENG_SERVER_HOST not set"
```

### Verify SSH connectivity (if remote path)

```bash
python <skill_dir>/scripts/ssh_client.py test
```

---

## Task 0a: Local DevKit Installation Verification

### Verify DevKit is installed locally

```bash
VERSION=$(cd /usr/local/devkit && ./devkit --version 2>&1)
if echo "$VERSION" | grep -q "devkit"; then
    echo "PASS: DevKit is installed locally - $VERSION"
else
    echo "FAIL: DevKit is not installed locally"
fi
```

### Verify DevKit hidden file exists

```bash
[ -f /usr/local/devkit/.devkit ] && echo "PASS: .devkit hidden file exists" || echo "FAIL: .devkit hidden file is missing"
```

### Verify DevKit src-mig command works

```bash
HELP=$(cd /usr/local/devkit && ./devkit porting src-mig --help 2>&1)
if echo "$HELP" | grep -q "src-mig"; then
    echo "PASS: DevKit src-mig command is available"
else
    echo "FAIL: DevKit src-mig command is not available"
fi
```

### Verify local source code path

```bash
# After user provides source path
SOURCE_PATH="<user_provided_path>"
[ -d "$SOURCE_PATH" ] && echo "PASS: Source directory exists" || echo "FAIL: Source directory not found"

FILE_COUNT=$(find "$SOURCE_PATH" -type f \( -name '*.c' -o -name '*.cpp' -o -name '*.h' -o -name '*.java' -o -name '*.py' -o -name '*.go' \) 2>/dev/null | wc -l)
[ "$FILE_COUNT" -gt 0 ] && echo "PASS: Found $FILE_COUNT source files" || echo "FAIL: No source files found"
```

---

## Task 1: SSH Connection Verification

### Verify environment variables are set

```bash
# Check each required variable (only check if set, never print values)
[ -n "$KUNPENG_SERVER_HOST" ] && echo "PASS" || echo "FAIL: KUNPENG_SERVER_HOST not set"
[ -n "$KUNPENG_SERVER_USER" ] && echo "PASS" || echo "FAIL: KUNPENG_SERVER_USER not set"
```

### Verify SSH connectivity

```bash
# Test basic SSH connection (paramiko reads MIGRATE_SSH_PASS from env)
RESULT=$(python <skill_dir>/scripts/ssh_client.py exec "echo 'OK'" 2>&1)

if [ "$RESULT" = "OK" ]; then
    echo "PASS: SSH connection successful"
else
    echo "FAIL: SSH connection failed - $RESULT"
fi
```

### Verify remote server information

```bash
# Get OS information
python <skill_dir>/scripts/ssh_client.py exec "cat /etc/os-release" && echo "PASS: OS information retrieved"

# Get architecture
ARCH=$(python <skill_dir>/scripts/ssh_client.py exec "uname -m")
if [ "$ARCH" = "x86_64" ] || [ "$ARCH" = "aarch64" ]; then
    echo "PASS: Architecture is $ARCH (supported)"
else
    echo "FAIL: Architecture $ARCH is not supported"
fi
```

### Verify SSH connection is working

```bash
# Test that SSH connection works (paramiko + password from MIGRATE_SSH_PASS env var)
python <skill_dir>/scripts/ssh_client.py test
```

---

## Task 2: DevKit Installation Verification

### Verify DevKit is installed

```bash
VERSION=$(remote_exec "devkit --version" 2>&1)
if echo "$VERSION" | grep -q "DevKit"; then
    echo "PASS: DevKit is installed - $VERSION"
else
    echo "FAIL: DevKit is not installed or not in PATH"
fi
```

### Verify DevKit scan command is available

```bash
HELP=$(remote_exec "devkit scan --help" 2>&1)
if echo "$HELP" | grep -q "scan"; then
    echo "PASS: DevKit scan command is available"
else
    echo "FAIL: DevKit scan command is not available"
fi
```

### Verify DevKit version is sufficient

```bash
# DevKit version should be >= 23.0
VERSION=$(remote_exec "devkit --version" 2>&1)
echo "DevKit version: $VERSION"
# Manual verification of version number
```

### Verify OS detection

```bash
OS_INFO=$(remote_exec "cat /etc/os-release 2>/dev/null")
echo "OS information: $OS_INFO"

# Verify OS is in supported list
if echo "$OS_INFO" | grep -qi "openEuler\|CentOS\|EulerOS\|Ubuntu\|Debian\|Kylin\|NeoKylin\|UOS\|SUSE"; then
    echo "PASS: OS is supported"
else
    echo "FAIL: OS is not in supported list"
fi
```

---

## Task 3: Source Code Scan Verification

### Verify source code directory exists

```bash
SOURCE_PATH="<user_provided_path>"
EXISTS=$(remote_exec "test -d '$SOURCE_PATH' && echo 'YES' || echo 'NO'")
if [ "$EXISTS" = "YES" ]; then
    echo "PASS: Source directory exists"
else
    echo "FAIL: Source directory not found: $SOURCE_PATH"
fi
```

### Verify source code files are present

```bash
FILE_COUNT=$(remote_exec "find '$SOURCE_PATH' -type f \( -name '*.c' -o -name '*.cpp' -o -name '*.h' -o -name '*.go' -o -name '*.java' -o -name '*.py' -o -name '*.f90' -o -name '*.s' -o -name '*.scala' \) | wc -l")
if [ "$FILE_COUNT" -gt 0 ]; then
    echo "PASS: Found $FILE_COUNT source code files"
else
    echo "FAIL: No source code files found in $SOURCE_PATH"
fi
```

### Verify scan completes successfully

```bash
# Run scan
remote_exec "devkit scan -t porting -i '$SOURCE_PATH' -o /tmp/devkit-report"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "PASS: Scan completed successfully (exit code 0)"
else
    echo "FAIL: Scan failed with exit code $EXIT_CODE"
fi
```

### Verify report files are generated

```bash
REPORT_FILES=$(remote_exec "find /tmp/devkit-report -type f | wc -l")
if [ "$REPORT_FILES" -gt 0 ]; then
    echo "PASS: Report files generated ($REPORT_FILES files)"
    remote_exec "ls -la /tmp/devkit-report/"
else
    echo "FAIL: No report files generated"
fi
```

### Verify report content is valid

```bash
# Check JSON report
JSON_VALID=$(remote_exec "python3 -c \"import json; json.load(open('/tmp/devkit-report/porting_result.json')); print('VALID')\" 2>/dev/null")
if [ "$JSON_VALID" = "VALID" ]; then
    echo "PASS: JSON report is valid"
else
    echo "FAIL: JSON report is invalid or not found"
fi

# Check HTML report
HTML_EXISTS=$(remote_exec "test -f /tmp/devkit-report/porting_report.html && echo 'YES' || echo 'NO'")
if [ "$HTML_EXISTS" = "YES" ]; then
    echo "PASS: HTML report exists"
else
    echo "INFO: HTML report not found (may use different format)"
fi
```

---

## Security Verification

### Verify no credentials are logged

```bash
# Check that no credential values appear in command history
# (This is a manual check - ensure the skill never echoes credentials)

# Verify environment variables are used correctly
echo "Security checklist:"
echo "  [ ] SSH credentials read from environment variables only"
echo "  [ ] No credential values echoed or printed"
echo "  [ ] No credentials stored in files (except /tmp/kunpeng_server_env.sh with chmod 600)"
echo "  [ ] No destructive commands executed on remote server"
echo "  [ ] Source code is not modified during scan"
echo "  [ ] AK/SK never requested in conversation"
echo "  [ ] ECS provisioning only with user confirmation"
echo "  [ ] Security group SSH rule restricted to agent IP when possible"
```

### Verify read-only operations

```bash
# Verify no files were modified in the source directory
# (Compare timestamps before and after scan)
BEFORE=$(remote_exec "find '$SOURCE_PATH' -type f -printf '%T@ %p\n' | sort | md5sum")
# ... run scan ...
AFTER=$(remote_exec "find '$SOURCE_PATH' -type f -printf '%T@ %p\n' | sort | md5sum")

if [ "$BEFORE" = "$AFTER" ]; then
    echo "PASS: No source files were modified during scan"
else
    echo "FAIL: Source files were modified during scan"
fi
```
