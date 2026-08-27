# Troubleshooting - Kunpeng Source Code Migration Assessment

Common issues and solutions for the Kunpeng source code migration assessment skill.

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

- [Local OS Detection Issues](#local-os-detection-issues)
- [Local DevKit Installation Issues](#local-devkit-installation-issues)
- [Environment Variable Issues](#environment-variable-issues)
- [SSH Connection Issues](#ssh-connection-issues)
- [hcloud CLI Issues](#hcloud-cli-issues)
- [ECS Provisioning Issues](#ecs-provisioning-issues)
- [DevKit Installation Issues (Remote)](#devkit-installation-issues-remote)
- [DevKit Scan Issues](#devkit-scan-issues)
- [Report Issues](#report-issues)
- [Network Issues](#network-issues)

---

## Local OS Detection Issues

### 1. Cannot determine local OS type

**Problem:**
`detect_os.py` returns `os_type=unsupported` or the script fails to run.

**Root cause:**
- Python is not available on the agent machine
- The OS is not in the DevKit-supported list
- The script encountered an unexpected error

**Solution:**
1. Ensure Python 3 is available: `python --version`
2. Run the script with verbose output to diagnose:
   ```bash
   python <skill_dir>/scripts/detect_os.py
   ```
3. If the script fails, manually check OS using Python:
   ```bash
   python -c "import platform; print(platform.system(), platform.machine(), platform.platform())"
   ```
4. If `os_type=unsupported`, treat the OS as unsupported and guide user to remote install

### 2. Windows OS detected — local install not available

**Problem:**
Agent is running on Windows, which does not support DevKit local installation.

**Solution:**
This is expected behavior. Guide the user to use a remote Linux server:
1. If user has a remote server → Guide SSH environment variable configuration
2. If user has no server → Offer to provision a Kunpeng ECS on Huawei Cloud

### 3. macOS detected — local install not available

**Problem:**
Agent is running on macOS, which does not support DevKit local installation.

**Solution:**
Same as Windows — guide the user to use a remote Linux server.

### 4. Unsupported Linux distribution detected

**Problem:**
The local Linux distribution is not in the DevKit-supported list (e.g., Arch Linux, Fedora, Alpine).

**Solution:**
1. Inform the user that their OS is not officially supported for DevKit
2. Guide them to use a remote server with a supported OS
3. If they want to try local install anyway, warn them it may not work correctly

---

## Local DevKit Installation Issues

### 1. execvp failed after local install

**Problem:**
`error: execvp failed: No such file or directory` when running `devkit --version` locally.

**Root cause:**
The hidden file `.devkit` was not copied during installation (should not happen if using `install_devkit.sh`).

**Solution:**
```bash
# Check if .devkit exists
ls -la /usr/local/devkit/.devkit

# If missing, re-run the installation script
bash <skill_dir>/scripts/install_devkit.sh --yes
```

### 2. Local DevKit download failed

**Problem:**
Cannot download DevKit package on the local machine.

**Solution:**
1. Check internet connectivity: `curl -I https://mirrors.huaweicloud.com`
2. Check disk space: `df -h /tmp`
3. Try a specific version: `bash <skill_dir>/scripts/install_devkit.sh --yes --version=25.3.0`
4. If no internet, use offline installation: `bash <skill_dir>/scripts/install_devkit.sh --yes --offline=/path/to/package.tar.gz`

### 3. Local DevKit scan fails with permission error

**Problem:**
`Permission denied` when running DevKit scan on local source code.

**Solution:**
```bash
# Check source code directory permissions
ls -la <source_path>

# Run with appropriate user or adjust permissions
sudo chmod -R o+r <source_path>
```

### 4. Local DevKit scan out of memory

**Problem:**
DevKit scan fails with OOM on the local machine.

**Solution:**
```bash
# Check available memory
free -h

# Reduce concurrent processes
cd /usr/local/devkit && ./devkit porting src-mig -i <source_path> -o /tmp/report -s 'c' -np 1
```

### 5. Architecture mismatch on local install

**Problem:**
`cannot execute binary file: Exec format error` when running locally installed DevKit.

**Root cause:**
Downloaded the wrong architecture package (e.g., x86 package on aarch64 machine).

**Solution:**
```bash
# Check local architecture
uname -m

# x86_64 → use Linux-x86-64 package
# aarch64 → use Linux-Kunpeng package

# Re-download with correct architecture and re-install
```

---

## Environment Variable Issues

### 1. Environment variables not found in current shell (Windows)

**Problem:**
`printenv | grep KUNPENG` returns nothing, even though variables are set in Windows System Properties.

**Root cause:**
On Windows (MSYS2/Git Bash), environment variables set via Windows System Properties or PowerShell `$env:` may NOT be visible in the bash shell. The bash shell has its own environment that does not inherit from Windows User/System environment variables.

**Solution:**
Check Windows User and System environment variables using PowerShell, then import them:

```bash
# Check Windows User environment variables
powershell -NoProfile -Command "[System.Environment]::GetEnvironmentVariable('KUNPENG_SERVER_HOST','User')"

# Import all variables into current shell
export KUNPENG_SERVER_HOST=$(powershell -NoProfile -Command "[System.Environment]::GetEnvironmentVariable('KUNPENG_SERVER_HOST','User')")
export KUNPENG_SERVER_PORT=$(powershell -NoProfile -Command "[System.Environment]::GetEnvironmentVariable('KUNPENG_SERVER_PORT','User')")
export KUNPENG_SERVER_USER=$(powershell -NoProfile -Command "[System.Environment]::GetEnvironmentVariable('KUNPENG_SERVER_USER','User')")
```

### 2. Environment variable not set

**Problem:**
`KUNPENG_SERVER_HOST` or other required variable is not set in any location.

**Solution:**
Set the environment variable before running the skill. The `MIGRATE_SSH_PASS` environment variable is read by `ssh_client.py` (paramiko mode) for each SSH connection. The password is wiped from `os.environ` immediately after each connection is established. No ControlMaster, no key injection.

```bash
# Linux/macOS
export KUNPENG_SERVER_HOST=<your-server-ip>
export KUNPENG_SERVER_PORT=22
export KUNPENG_SERVER_USER=root

# Windows (PowerShell - current session)
$env:KUNPENG_SERVER_HOST = "<your-server-ip>"
$env:KUNPENG_SERVER_PORT = "22"
$env:KUNPENG_SERVER_USER = "root"

# Windows (System Properties - persistent)
# Set via System Properties > Environment Variables > User variables
```

### 3. Passwordless SSH not configured

**Problem:**
SSH commands fail with `Permission denied (publickey)`.

**Solution:**
This skill uses paramiko + password from `MIGRATE_SSH_PASS` env var (no key injection, no ControlMaster). Run the built-in `ssh_client.py test` subcommand to verify the paramiko password connection:
```
→ Run: python <skill_dir>/scripts/ssh_client.py test
→ The script reads MIGRATE_SSH_PASS from env var and verifies the connection.
```

### 4. Environment variables not persisted

**Problem:**
Environment variables are lost after terminal restart.

**Solution:**
Add to shell profile (Linux/macOS):
```bash
echo 'export KUNPENG_SERVER_HOST=<your-server-ip>' >> ~/.bashrc
source ~/.bashrc
```

Or set as Windows User environment variable (persistent across restarts).

---

## SSH Connection Issues

### 1. Authentication failed

**Problem:**
SSH connection fails with `Authentication failed`.

**Root cause:**
The `MIGRATE_SSH_PASS` environment variable is not set, is incorrect, or the username is wrong.

**Solution:**
Verify the `MIGRATE_SSH_PASS` environment variable is set to the correct password and `KUNPENG_SERVER_USER` is correct. Then re-run the built-in `ssh_client.py test` subcommand to verify the connection:
```
→ Run: python <skill_dir>/scripts/ssh_client.py test
```

### 2. Connection refused

**Problem:**
`ssh: connect to host <IP> port <PORT>: Connection refused`

**Root cause:**
- SSH service (sshd) is not running on the remote server
- SSH is listening on a different port
- Firewall is blocking the connection

**Solution:**
```bash
# Verify SSH service is running (on the remote server)
systemctl status sshd

# Check SSH listening port
ss -tlnp | grep ssh

# Check firewall rules
iptables -L -n | grep <PORT>
```

### 4. Permission denied

**Problem:**
`Permission denied (publickey)`.

**Root cause:**
- `MIGRATE_SSH_PASS` environment variable was not set or is incorrect
- `KUNPENG_SERVER_HOST` / `KUNPENG_SERVER_USER` environment variables are incorrect

**Solution:**
1. Ensure `MIGRATE_SSH_PASS` environment variable is set with the correct server password
2. Re-run the built-in `ssh_client.py test` subcommand to verify the connection:
```
→ Run: python <skill_dir>/scripts/ssh_client.py test
```

### 5. Host key verification failed

**Problem:**
`Host key verification failed.`

**Solution:**
This skill uses paramiko with `AutoAddPolicy()` which automatically accepts and saves host keys. If the issue persists, it may be due to a changed server host key (e.g., server was reinstalled). paramiko handles this automatically — no manual `ssh-keygen -R` is needed. If you still encounter issues, verify the server IP and network connectivity.

### 6. Connection timeout

**Problem:**
`ssh: connect to host <IP> port <PORT>: Connection timed out`

**Solution:**
1. Verify the server IP is correct
2. Check network connectivity: `ping <IP>`
3. Check if the server is accessible from the local network
4. Increase timeout: add `-o ConnectTimeout=30` to SSH command

### 7. MSYS2 path conversion error (Windows only)

**Problem:**
When using `ssh_client.py put`, `get`, `put-dir`, `get-dir`, or `get-report` on Windows, the remote path gets mangled:

```
ERROR: Remote path 'C:/Users/ADMINI~1/AppData/Local/Temp/2/install_devkit.sh' looks like a Windows path.
MSYS2/Git Bash converted the Unix path before Python saw it.
```

**Root cause:**
On Windows, the AI agent's Bash tool runs commands through MSYS2/Git Bash. The MSYS2 runtime automatically converts Unix-style paths in command arguments to Windows paths **before Python starts**. For example, `/tmp/install_devkit.sh` becomes `C:/Users/<user>/AppData/Local/Temp/2/install_devkit.sh`. This happens at the MSYS2 runtime level, not in Python, so Python's `sys.argv` already contains the mangled path.

**Solution: Use paramiko SFTP API directly**

Bypass the shell entirely by calling paramiko's SFTP API from Python. Paths are Python strings — no shell involved, no conversion, no quoting issues:

```python
import os, paramiko

host = os.environ.get('KUNPENG_SERVER_HOST')
port = int(os.environ.get('KUNPENG_SERVER_PORT', '22'))
user = os.environ.get('KUNPENG_SERVER_USER', 'root')
password = os.environ.get('MIGRATE_SSH_PASS')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, port=port, username=user, password=password, timeout=30)

sftp = client.open_sftp()
sftp.put(r'C:\local\install_devkit.sh', '/tmp/install_devkit.sh')
sftp.chmod('/tmp/install_devkit.sh', 0o755)
sftp.close()
client.close()
```

**Alternative: Set `MSYS_NO_PATHCONV=1` (bash syntax)**

```bash
# CORRECT — bash syntax (MSYS2/Git Bash)
MSYS_NO_PATHCONV=1 python <skill_dir>/scripts/ssh_client.py put "C:\local\file.sh" "/tmp/file.sh"
```

> **⚠️ Common mistakes that do NOT work:**
>
> | Wrong approach | Why it fails |
> |----------------|-------------|
> | `$env:MSYS_NO_PATHCONV=1; python ...` | PowerShell syntax — bash does not recognize `$env:` |
> | `cmd /c "set MSYS_NO_PATHCONV=1 && python ..."` | Env var set in cmd subprocess, not propagated to MSYS2 runtime |
> | `set MSYS_NO_PATHCONV=1` (in bash) | `set` is cmd syntax; bash uses `export` |

**Key takeaway for AI agents:**

| Task | Recommended approach |
|------|---------------------|
| File upload/download | paramiko SFTP API directly (see above) |
| Directory upload/download | paramiko SFTP API with recursive walk |
| Report download | paramiko SFTP API, or `MSYS_NO_PATHCONV=1 ssh_client.py get-report` |
| Command execution | `ssh_client.py exec "<cmd>"` |
| Large content transfer | **Never** use `exec` with base64/heredoc — upload file via SFTP first |

---

## hcloud CLI Issues

### 1. hcloud: command not found

**Problem:**
`hcloud: command not found` when trying to run hcloud commands.

**Root cause:**
hcloud (KooCLI) is not installed or not in PATH.

**Solution:**
Install hcloud following the [CLI installation guide](cli-installation-guide.md):

```bash
# Linux (x86_64)
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-amd64.tar.gz"
tar -xzf huaweicloud-cli-linux-amd64.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/

# Verify
hcloud version
```

### 2. hcloud authentication failed

**Problem:**
`authentication failed`, `unauthorized`, or `Invalid AK/SK` when running hcloud commands.

**Root cause:**
- AK/SK not configured
- AK/SK are incorrect or expired
- IAM user does not have required permissions

**Solution:**
1. Run `hcloud configure set --cli-region=cn-southwest-2 --cli-access-key=<AK> --cli-secret-key=<SK>` to set credentials
2. Or run `hcloud configure set` interactively
3. Verify credentials: `hcloud ECS ListServersDetails --region=cn-southwest-2`
4. Check IAM permissions: ensure `ECS FullAccess`, `VPC FullAccess`, `EIP FullAccess` are granted

> **⚠️ Windows note:** On Windows (MSYS2/Git Bash), `export HUAWEICLOUD_SDK_AK=...` and `$env:HUAWEICLOUD_SDK_AK = "..."` do NOT work. Always use `hcloud configure set --cli-access-key=... --cli-secret-key=...`.

### 3. hcloud insufficient permissions

**Problem:**
`Forbidden` or `insufficient permissions` when creating resources.

**Solution:**
The IAM user needs the following permissions:
- `ECS FullAccess` — Create/manage ECS instances
- `VPC FullAccess` — Create/manage VPC, Subnet, Security Group
- `EIP FullAccess` — Create/manage Elastic IPs
- `IMS Access` — List images

### 4. hcloud parameter format error

**Problem:**
`Invalid parameter` or unexpected error when running hcloud commands.

**Root cause:**
hcloud requires `--param=value` format (equals sign, no space between param and value).

**Solution:**
```bash
# Correct format
hcloud ECS ListServersDetails --region=cn-southwest-2

# Wrong format (will fail)
hcloud ECS ListServersDetails --region cn-southwest-2
```

### 5. hcloud region not found

**Problem:**
`Region not found` or `The region does not exist` error.

**Solution:**
1. Verify the region ID: `cn-southwest-2` (Guiyang 1)
2. List available regions: `hcloud IAM ListRegions`
3. Ensure the region is enabled for your account

---

## ECS Provisioning Issues

### 1. Insufficient ECS quota

**Problem:**
`Quota exceeded` or `Resources are insufficient` during ECS creation.

**Solution:**
1. Check current ECS instances: `hcloud ECS ListServersDetails --region=cn-southwest-2`
2. Delete unused instances or request quota increase through Huawei Cloud console
3. Try a different availability zone (e.g., `cn-southwest-2b`)

### 2. Insufficient account balance

**Problem:**
`Account balance insufficient` or `Order payment failed` error.

**Solution:**
1. Recharge account balance through Huawei Cloud console
2. Or use a different account with sufficient balance

### 3. Image not found

**Problem:**
Cannot find Huawei Cloud EulerOS 2.0 ARM64 image in the target region.

**Solution:**
1. List available ARM64 images: `hcloud IMS ListImages --region=cn-southwest-2 --__imagetype=gold --__os_type=Linux`
2. The image name may vary by region; look for images containing "EulerOS" and "2.0"
3. If no EulerOS image is available, try openEuler as an alternative

### 4. Flavor not available

**Problem:**
`Flavor kc1.2xlarge.2 is not available` in the target AZ.

**Solution:**
1. List available flavors: `hcloud ECS ListFlavors --region=cn-southwest-2 --availability_zone=cn-southwest-2a`
2. Try alternative Kunpeng flavors:
   - `kc1.xlarge.2` (2C4G)
   - `kc1.2xlarge.2` (4C8G)
   - `kc2.xlarge.2` (2C4G, newer generation)
3. Try a different availability zone

### 5. VPC creation failed

**Problem:**
VPC creation returns an error.

**Solution:**
1. Check VPC quota: `hcloud VPC ListVpcs --region=cn-southwest-2`
2. VPC CIDR may conflict with existing VPCs — try a different CIDR (e.g., `10.0.0.0/16`)
3. Check IAM permissions for VPC creation

### 6. EIP creation failed

**Problem:**
EIP creation returns an error.

**Solution:**
1. Check EIP quota: `hcloud VPC ListPublicips --region=cn-southwest-2`
2. Check account balance (EIP requires pre-paid or post-paid setup)
3. Try a different EIP type or bandwidth size

### 7. ECS creation job failed

**Problem:**
ECS creation job status is `FAIL`.

**Solution:**
1. Check the fail reason: `hcloud ECS ShowJob --region=cn-southwest-2 --job_id=<id>`
2. Common causes:
   - Image not available in the selected AZ
   - Flavor sold out in the selected AZ
   - Insufficient quota or balance
3. Try a different availability zone or flavor

### 8. SSH not available after provisioning

**Problem:**
Cannot SSH to the newly created server after waiting.

**Solution:**
1. Wait a few more minutes — the server may still be initializing (cloud-init)
2. Check security group rules — ensure TCP 22 inbound is allowed
3. Check EIP assignment — verify the EIP is bound to the ECS
4. Try VNC login from Huawei Cloud console to diagnose
5. Check if the server status is `ACTIVE`: `hcloud ECS ShowServer --region=cn-southwest-2 --server_id=<id>`

### 8a. SCP blocks security group rule creation

**Problem:**
`hcloud VPC CreateSecurityGroupRule` returns `Forbidden` or `Policy doesn't allow vpc:securityGroupRules:create`.

**Root cause:**
The IAM account's SCP (Service Control Policy) explicitly denies `vpc:securityGroupRules:create`, even with `VPC FullAccess` permission.

**Solution:**
1. Add the SSH inbound rule manually in Huawei Cloud console:
   - Navigate to VPC > Security Groups > select the group > Inbound Rules > Add Rule
   - Protocol: TCP, Port: 22, Source: `<your-ip>/32` (NEVER use `0.0.0.0/0`)
2. After adding the rule, wait 1-2 minutes for it to take effect
3. Retry SSH connection

> **⚠️ Security:** Never use `0.0.0.0/0` as the source CIDR for SSH rules. Always restrict to a specific IP or CIDR range.

### 8b. hcloud API parameter errors

**Problem:**
`Invalid parameter` or `Parameter xxx not found` when creating resources via hcloud.

**Root cause:**
hcloud API parameters use nested object prefixes. Common mistakes:

| API | Wrong Parameter | Correct Parameter |
|-----|----------------|-------------------|
| CreateVpc | `--name` | `--vpc.name` |
| CreateVpc | `--cidr` | `--vpc.cidr` |
| CreateSubnet | `--vpc_id` | `--subnet.vpc_id` |
| CreateSubnet | `--name` | `--subnet.name` |
| CreateSubnet | `--gateway_ip` | `--subnet.gateway_ip` |
| CreateSecurityGroup | `--name` | `--security_group.name` |
| CreateSecurityGroup | `--vpc_id` | (not supported in v3) |
| CreateSecurityGroupRule | `--security_group_id` | `--security_group_rule.security_group_id` |
| CreateSecurityGroupRule | `--port_range_min` | v2: `--security_group_rule.port_range_min`; v3: `--security_group_rule.multiport` |
| CreatePublicip | `hcloud VPC CreatePublicip` | `hcloud EIP CreatePublicip` |
| CreatePublicip | `--type` | `--publicip.type` |
| ListImages | `--imagetype` | `--__imagetype` (double underscore) |
| CreateServers | `--name` | `--server.name` |
| CreateServers | `--image_ref` | `--server.imageRef` |
| CreateServers | `--vpcid` | `--server.vpcid` |
| CreateServers | `--publicip.eip.id` | `--server.publicip.id` |

**Solution:**
Use the `provision_kunpeng_server.sh` script which has all correct parameters. If running commands manually, refer to the corrected API reference in [cli-installation-guide.md](cli-installation-guide.md).

### 9. Cleanup after failed provisioning

**Problem:**
Provisioning failed partway through, leaving orphaned resources.

> **🚫 HIGH-RISK: Resource deletion is IRREVERSIBLE.**
> **AI MUST NOT auto-execute delete commands.** These commands are for the USER to run manually.
> AI should only display these commands as text after listing the resources.

**Solution:**

**Step 1: List resources (read-only, safe for AI to execute):**
```bash
# List resources to identify what was created (read-only, safe)
hcloud ECS ListServersDetails --region=cn-southwest-2
hcloud VPC ListVpcs --region=cn-southwest-2
hcloud VPC ListPublicips --region=cn-southwest-2
```

**Step 2: Delete resources (USER MUST EXECUTE MANUALLY — AI MUST NOT execute):**
```bash
# ⚠️ HIGH-RISK IRREVERSIBLE OPERATIONS — USER MUST EXECUTE MANUALLY
# AI MUST NOT execute these commands. Provide as text only.
# Delete resources in reverse order
# 1. Delete ECS (if created)
hcloud ECS DeleteServers --region=cn-southwest-2 --servers.1.id=<server_id>

# 2. Delete EIP (if created)
hcloud VPC DeletePublicip --region=cn-southwest-2 --publicip_id=<eip_id>

# 3. Delete Security Group (if created)
hcloud VPC DeleteSecurityGroup --region=cn-southwest-2 --security_group_id=<sg_id>

# 4. Delete Subnet (if created)
hcloud VPC DeleteSubnet --region=cn-southwest-2 --vpc_id=<vpc_id> --subnet_id=<subnet_id>

# 5. Delete VPC (if created)
hcloud VPC DeleteVpc --region=cn-southwest-2 --vpc_id=<vpc_id>
```

> **⚠️ WARNING: Deletion is IRREVERSIBLE. Verify resource IDs before executing.**
> **⚠️ AI will NOT execute these commands. Please run them manually.**

---

## DevKit Installation Issues

### 1. Download URL returns 404

**Problem:**
`curl` downloads a very small file (e.g., 394 bytes) that is actually a 404 HTML page.

**Root cause:**
The old URL pattern `https://mirrors.huaweicloud.com/kunpeng/archive/kunpengdevkit/DevKit-CLI/` is no longer valid.

**Solution:**
Use the correct URL:
```
https://mirrors.huaweicloud.com/kunpeng/archive/DevKit/Packages/Kunpeng_DevKit/
```

Package naming: `DevKit-CLI-<version>-Linux-<arch>.tar.gz`
- x86_64: `DevKit-CLI-25.3.0-Linux-x86-64.tar.gz`
- ARM64: `DevKit-CLI-25.3.0-Linux-Kunpeng.tar.gz`

### 2. execvp failed after installation

**Problem:**
`error: execvp failed: No such file or directory` when running `devkit --version`

**Root cause:**
The hidden file `.devkit` was not copied during installation (should not happen if using `install_devkit.sh`).

**Solution:**
```bash
# Check if .devkit exists
ls -la /usr/local/devkit/.devkit

# If missing, re-run the installation script
python <skill_dir>/scripts/ssh_client.py exec "bash /tmp/install_devkit.sh --yes" 300
```

> **⚠️ If using `install_devkit.sh`, this error should not occur.** The script explicitly copies the `.devkit` hidden file. If you see this error, the installation was likely done manually without the script.

### 3. Download failed (network)

**Problem:**
`curl: (7) Failed to connect to mirrors.huaweicloud.com` or `wget: unable to resolve host address`

**Root cause:**
- Remote server has no internet access
- DNS resolution failure
- Firewall blocking outbound connections

**Solution:**
1. Check network connectivity on the remote server:
   ```bash
   remote_exec "curl -I https://mirrors.huaweicloud.com"
   ```
2. If no internet access, use offline installation (see [devkit-installation-guide.md](devkit-installation-guide.md#offline-installation))
3. Configure proxy if needed:
   ```bash
   export http_proxy=http://proxy:port
   export https_proxy=http://proxy:port
   ```

### 4. Installation permission denied

**Problem:**
`Permission denied` or `sudo: a password is required`

**Root cause:**
- SSH user does not have sudo privileges
- sudo requires a password

**Solution:**
1. Use root user: `KUNPENG_SERVER_USER=root`
2. Or configure passwordless sudo for the user
3. Or install to user directory without sudo:
   ```bash
   mkdir -p ~/devkit && tar -xzf DevKit-CLI-*.tar.gz -C ~/devkit
   export PATH=~/devkit:$PATH
   ```

### 5. Missing dependencies

**Problem:**
DevKit fails to start due to missing system libraries.

**Common missing dependencies:**

| Error Message | Missing Package | Install Command |
|---------------|----------------|-----------------|
| `libstdc++.so.6: version not found` | libstdc++ | `yum install libstdc++` / `apt install libstdc++6` |
| `libpython3.so: not found` | python3 | `yum install python3` / `apt install python3` |
| `libc.so.6: version not found` | glibc | `yum install glibc` / `apt install libc6` |

### 6. DevKit command not found after installation

**Problem:**
`devkit: command not found` even after installation.

**Solution:**
```bash
# Run from install directory
cd /usr/local/devkit && ./devkit --version

# Or create symlink
sudo ln -s /usr/local/devkit/devkit /usr/local/bin/devkit
```

### 7. Architecture mismatch

**Problem:**
`cannot execute binary file: Exec format error`

**Root cause:**
Downloaded the wrong architecture package (e.g., x86 package on ARM64 server).

**Solution:**
1. Check server architecture: `uname -m`
2. x86_64 → use `Linux-x86-64` package
3. aarch64 → use `Linux-Kunpeng` package
4. Re-download and re-install

---

## DevKit Scan Issues

### 1. Unknown sub command: scan

**Problem:**
`error: Unknown sub command: scan`

**Root cause:**
The correct command is `devkit porting src-mig`, NOT `devkit scan -t porting`.

**Solution:**
```bash
cd /usr/local/devkit && ./devkit porting src-mig -i <source_path> -o <output_path> -s '<languages>'
```

### 2. Output directory does not exist

**Problem:**
`The path <output_path> does not exist or you do not have the permission to access the path.`

**Root cause:**
The output directory must be created before running the scan command.

**Solution:**
```bash
mkdir -p /tmp/devkit-report/<project_name>
```

### 3. Invalid compiler version

**Problem:**
`Invalid arguments: argument -p/--compiler: invalid choice: 'gcc9.4.0'`

**Root cause:**
The compiler version string must match exactly one of the supported values.

**Solution:**
Check available compiler versions:
```bash
cd /usr/local/devkit && ./devkit porting src-mig --help
```
Common versions: `gcc4.8.5`, `gcc7.3.0`, `gcc9.3.0`, `gcc10.2.0`, `gcc12.3.0`

### 4. Scan hangs or takes too long

**Problem:**
Scan does not complete within a reasonable time.

**Solution:**
```bash
# Check if scan is still running
remote_exec "ps aux | grep devkit | grep -v grep"

# Check system resources
remote_exec "top -bn1 | head -20"

# For large codebases, scan specific subdirectories
devkit porting src-mig -i /path/to/subproject -o /tmp/devkit-report -s 'c'
```

### 5. Scan out of memory

**Problem:**
Scan fails with `Out of memory` or system OOM killer terminates the process.

**Solution:**
```bash
# Check available memory
remote_exec "free -h"

# Reduce thread count
devkit porting src-mig -i <source_path> -o <output_path> -s 'c' -np 1
```

### 6. Scan produces empty results

**Problem:**
Scan completes but finds no issues.

**Possible causes:**
1. Source code is already fully compatible with ARM64
2. Source code files are in an unsupported language
3. DevKit version is outdated and doesn't detect newer patterns
4. Source directory contains only non-source files (e.g., only `.md`, `.txt`)

**Solution:**
```bash
# Verify source files exist
remote_exec "find <source_path> -type f -name '*.c' -o -name '*.cpp' | wc -l"

# Check DevKit version
remote_exec "cd /usr/local/devkit && ./devkit --version"

# Try with explicit language
devkit porting src-mig -i <source_path> -o <output_path> -s 'c, c++'
```

---

## Report Issues

### 1. Report files not found

**Problem:**
No report files in the output directory after scan.

**Solution:**
```bash
# Check output directory
remote_exec "ls -la /tmp/devkit-report/"

# Check if scan completed successfully
remote_exec "echo $?"  # Should be 0

# Try a different output directory
devkit porting src-mig -i <source_path> -o /home/user/devkit-report -s 'c'
```

### 2. Cannot download report from remote server

**Problem:**
SCP download of report files fails.

**Solution:**
```bash
# Read report content directly via SSH (paramiko reads MIGRATE_SSH_PASS from env) and save to fixed local path
# On Linux/macOS:
mkdir -p /home/devkit-report
python <skill_dir>/scripts/ssh_client.py exec "cat /tmp/devkit-report/*_en.json" > /home/devkit-report/report.json
python <skill_dir>/scripts/ssh_client.py exec "cat /tmp/devkit-report/*.html" > /home/devkit-report/report.html

# On Windows (PowerShell):
New-Item -ItemType Directory -Force -Path "C:\devkit-report"
python <skill_dir>\scripts\ssh_client.py exec "cat /tmp/devkit-report/*_en.json" | Out-File -FilePath "C:\devkit-report\report.json" -Encoding utf8
python <skill_dir>\scripts\ssh_client.py exec "cat /tmp/devkit-report/*.html" | Out-File -FilePath "C:\devkit-report\report.html" -Encoding utf8

# Compress and download (alternative method)
python <skill_dir>/scripts/ssh_client.py exec "cd /tmp/devkit-report && tar -czf /tmp/report.tar.gz *"
# Then use SFTP (paramiko reads MIGRATE_SSH_PASS from env) to download the tar.gz to the fixed local path
scp "$KUNPENG_SERVER_USER@$KUNPENG_SERVER_HOST:/tmp/report.tar.gz" /home/devkit-report/
```

### 3. Report is corrupted or incomplete

**Problem:**
Report file exists but cannot be parsed.

**Solution:**
1. Re-run the scan
2. Try a different output format: `-r json` or `-r csv`
3. Check disk space on the remote server: `df -h`

### 4. Unicode/encoding error when reading report

**Problem:**
`UnicodeDecodeError` or `UnicodeEncodeError` when reading CSV/JSON report on Windows.

**Root cause:**
CSV files may have BOM (Byte Order Mark) character, and Windows console may use GBK encoding.

**Solution:**
- Strip BOM from output: `stdout.lstrip('\ufeff')`
- Use UTF-8 encoding with error handling: `.encode('utf-8', errors='replace')`
- Write output to `sys.stdout.buffer` instead of `print()`

---

## Network Issues

### 1. Cannot reach remote server

**Problem:**
`No route to host` or `Network is unreachable`

**Solution:**
1. Verify the server IP: `ping <IP>`
2. Check VPN connection if the server is behind a VPN
3. Verify the server is powered on and network is configured

### 2. Cannot reach Huawei Cloud mirrors

**Problem:**
Cannot download DevKit from `mirrors.huaweicloud.com`

**Solution:**
1. Check DNS resolution: `nslookup mirrors.huaweicloud.com`
2. Check if the server is behind a proxy
3. Use offline installation method
4. Try alternative download source from the official DevKit page

### 3. Firewall blocking SSH

**Problem:**
Firewall on the remote server blocks incoming SSH connections.

**Solution:**
```bash
# On the remote server, open SSH port
# CentOS/RHEL/openEuler
sudo firewall-cmd --permanent --add-port=22/tcp
sudo firewall-cmd --reload

# Ubuntu/Debian
sudo ufw allow 22/tcp
```
