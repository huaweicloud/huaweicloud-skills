# DevKit Operations Workflow (Step 6-9)

> This document is the DevKit operations workflow, containing the detailed Step 6-9 flow.
> For command templates, parameter descriptions, and script usage, see [DevKit Operations Guide](devkit-operations-guide.md).

---

## Step 6: Verify Login, Upload Scripts & Install (DevKit + Maven)

> **?? AUTO-TRIGGERED by Step 5 Success**: This step is **automatically triggered** when ECS creation succeeds and status is `ACTIVE`. Do NOT wait for user confirmation ? execute all 3 sub-steps as a **continuous flow** immediately after Step 5 completes. This is a mandatory transition: Step 5 success ? Step 6 (login verify ? upload scripts ? install DevKit + Maven).

After ECS creation and EIP binding, perform the following as a **continuous flow** with three sub-steps ? verify SSH login, upload 3 shell scripts, and execute install_devkit.sh (installs DevKit + Maven).

> **EIP Rule**: `${DEVKIT_ECS_EIP}` is obtained **ONLY** by querying hcloud for the created devkit server. See [Security Rules](rules.md).

### 6.1 Verify SSH Login

```bash
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "uname -m"
```

If auth fails ? Re-detect `DEVKIT_ECS_USER` and `DEVKIT_ECS_PASSWORD` from User ? Machine levels, retry. If still fails ? Ask user to update/add env vars. **NEVER** call `hcloud ECS BatchResetServersPassword` or any password reset API. See [Security Rules](rules.md) for the complete failure handling flow.

### 6.2 Upload 3 Shell Scripts to /home

All scripts are co-located with `devkit_remote.py` in the `scripts/` directory. Upload from devkit_remote.py's directory:

```bash
# Upload via scp (run from devkit_remote.py's directory, i.e., scripts/)
scp install_devkit.sh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP}:${DEVKIT_HOME}/
scp scan_devkit.sh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP}:${DEVKIT_HOME}/
scp encrypt-nodes-verify.sh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP}:${DEVKIT_HOME}/

# Or via devkit_remote.py (auto-uploads all scripts)
py scripts/devkit_remote.py --region ${HUAWEI_REGION} upload
```

| Script | Local Path (relative to devkit_remote.py) | Remote Path | Purpose |
|--------|-----------------------------------|-------------|---------|
| install_devkit.sh | `install_devkit.sh` | ${DEVKIT_HOME}/install_devkit.sh | DevKit installation |
| scan_devkit.sh | `scan_devkit.sh` | ${DEVKIT_HOME}/scan_devkit.sh | Scan execution |
| encrypt-nodes-verify.sh | `encrypt-nodes-verify.sh` | ${DEVKIT_HOME}/encrypt-nodes-verify.sh | Password encryption & SSH verification |

If upload fails ? report error and **STOP**.

### 6.3 Execute install_devkit.sh (DevKit + Maven)

After scripts are uploaded successfully, **immediately** execute `install_devkit.sh`. The script auto-detects the server's CPU architecture (`uname -m`) and performs two installations in sequence:

1. **DevKit** ? Check OS ? detect architecture ? download package ? extract to `${DEVKIT_HOME}/DevKit/` ? add to PATH ? verify (`devkit version`)
2. **Maven 3.8.8** ? Check/install JDK + Maven (for `mvn_analyse` scan mode)

| Detected Architecture | Package | Download URL |
|----------------------|---------|-------------|
| x86_64 | `DevKit-Sys-Mig-CLI-26.1.RC1-Linux-x86-64.tar.gz` | `https://kunpeng-repo.obs.cn-north-4.myhuaweicloud.com/Kunpeng%20DevKit/Kunpeng%20DevKit%2026.1.RC1/DevKit-Sys-Mig-CLI-26.1.RC1-Linux-x86-64.tar.gz` |


Install command:
```bash
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "bash ${DEVKIT_HOME}/install_devkit.sh"
```

- The script will: check OS (CentOS 7.6 or Ubuntu 20.04 only) ? detect architecture via `uname -m` ? download DevKit package ? extract to `${DEVKIT_HOME}/DevKit/` ? add to PATH ? verify DevKit (`devkit version`) ? install Maven 3.8.8 (JDK + Maven)

### 6.4 Progress Polling (Progress Polling)

DevKit installation and scanning may take a long time (5-15 minutes). The AI should use a progress polling mechanism to continuously report progress to the user, avoiding long periods with no output.

#### Installation Progress Polling

```bash
# Run installation in background on DevKit ECS, output to log file
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "bash ${DEVKIT_HOME}/install_devkit.sh > /tmp/devkit_install.log 2>&1 &"

# Poll installation progress (read log tail every 10-20 seconds)
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "tail -5 /tmp/devkit_install.log"
```

**Polling Status Determination**:

| Log Content | Status | Action |
|-------------|--------|--------|
| `DevKit installation complete` | ? DONE | Proceed to Step 7 |
| `ERROR` / `FAILED` | ? FAILED | Stop, report error |
| Other content | ? RUNNING | Wait 10-20s then poll again |
| No log change for over 60s | ?? TIMEOUT | Report timeout, ask user whether to continue waiting |

#### Scan Progress Polling

```bash
# Run scan in background on DevKit ECS, output to log file
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "bash ${DEVKIT_HOME}/scan_devkit.sh ${SCAN_MODE} > /tmp/devkit_scan.log 2>&1 &"

# Poll scan progress (read log tail every 10-20 seconds)
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "tail -5 /tmp/devkit_scan.log"
```

**Polling Status Determination**:

| Log Content | Status | Action |
|-------------|--------|--------|
| `scan complete` / `Renamed` | ? DONE | Proceed to Step 9 (download reports) |
| `ERROR` / `failed` | ? FAILED | Stop, report error |
| `Scanning:` / `Processing:` | ? RUNNING | Wait 10-20s then poll again |
| No log change for over 120s | ?? TIMEOUT | Report timeout, ask user whether to continue waiting |

#### Polling Rules

1. **Polling interval**: 10-20 seconds
2. **Timeout threshold**: Installation 60s no change, scan 120s no change
3. **Each poll**: Read the last 5-10 lines of the log, report current progress to the user
4. **doom-loop safe**: Use the `read` tool to increment offset when reading the log, avoiding repeated reads
5. **User-visible**: Each polling result is displayed to the user, maintaining transparency

---

## Step 7: Remote Scan Target Configuration (REQUIRED after DevKit + Maven installation)

> **?? MANDATORY**: After DevKit + Maven installation completes (Step 6), the AI MUST prompt the user to configure `nodes.conf`. This is a required step before any scan can be executed. Do NOT skip this step or auto-proceed to scanning.

After DevKit installation, prompt the user to configure the remote scan target server nodes file. The nodes file defines the target servers to scan (IP, SSH credentials, scan paths).

| Architecture | Nodes File Path |
|-------------|----------------|
| x86_64 | `${DEVKIT_HOME}/DevKit/DevKit-Sys-Mig-CLI-26.1.RC1-Linux-x86-64/sys-mig/nodes/nodes.conf` |


Prompt the user:

```
??  DevKit + Maven installed. Before running remote scan, you MUST configure the target server nodes file:
    Path: ${DEVKIT_HOME}/DevKit/DevKit-Sys-Mig-CLI-26.1.RC1-Linux-x86-64/sys-mig/nodes/nodes.conf
    This file defines the remote scan target servers (IP, SSH credentials, scan paths).
    Please edit this file on the DevKit server, then notify when configuration is complete.
```

Wait for user confirmation. Once confirmed, proceed to **Encrypt Passwords & Verify SSH Connectivity** below.

### Encrypt Passwords & Verify SSH Connectivity (After nodes.conf configured)

> **?? KEY RULE ? SSH Verification MUST Run on the DevKit Server**: When verifying SSH connectivity to target servers defined in `nodes.conf`, the SSH test MUST be executed **from the DevKit server** (using `sshpass`/`ssh` on the DevKit server). **NEVER** use `paramiko` or any local Python SSH library from the agent's local machine to directly test connectivity to nodes.conf targets ? the local machine may not have network access to the target servers, but the DevKit server does (since DevKit will be the one connecting to targets during scanning). All SSH verification is done via the `encrypt-nodes-verify.sh` script running on the DevKit server.

After the user finishes editing `nodes.conf`, run the encryption and verification script **on the DevKit server** to:

1. Encrypt plaintext `ssh_pass` values using `sys-mig -ec`
2. Replace plaintext passwords with encrypted ones in `nodes.conf`
3. Verify SSH connectivity to each target server
4. List failed connections and reasons
5. **If failures exist**: prompt user to fix nodes.conf, then re-run ? only failed agents are re-encrypted and re-verified; already-verified agents are skipped

#### Iterative Verification Flow

```
[1st Run] Encrypt all plaintext ssh_pass ? Verify all hosts
    ?
    ??? All pass ? ? Done, ready for scan
    ?
    ??? Some fail ? Prompt user to fix nodes.conf for failed agents
                       ?
                       ?
                  [User fixes nodes.conf]
                       ?
                       ?
                  [Re-run script]
                       ?
                       ??? Skip already-verified agents (no re-encryption, no re-verify)
                       ??? Encrypt only failed agents' ssh_pass
                       ??? Verify only failed agents
                       ?
                       ??? All pass ? ? Done
                       ??? Still some fail ? Repeat (user fixes ? re-run)
```

> **Key behavior**: Already-verified agents are tracked in `/tmp/devkit_nodes_verified_hosts`. On re-run, these agents are completely skipped ? no re-encryption, no re-verification. Only previously-failed agents are processed. To start fresh: `find /tmp -name devkit_nodes_verified_hosts -delete`.

#### Commands

```bash
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "bash ${DEVKIT_HOME}/encrypt-nodes-verify.sh"
```

Or specify a custom nodes.conf path:

```bash
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "bash ${DEVKIT_HOME}/encrypt-nodes-verify.sh /path/to/nodes.conf"
```

Quick command (via devkit_remote.py):

```bash
py scripts/devkit_remote.py --region ${HUAWEI_REGION} encrypt-verify
py scripts/devkit_remote.py --region ${HUAWEI_REGION} encrypt-verify --nodes-conf /custom/path/nodes.conf
```

#### nodes.conf Format Reference

```
[groupName]
192.168.0.2  ssh_pass=<encrypted_password> scan_dir=/home
192.168.0.3  ssh_pass=<encrypted_password> scan_dir=/home/test,/home/test1
[groupName:vars]
ssh_user=root
ssh_port=22
[groupName:children]
childGroupName
```

- `ssh_pass`: MUST use encrypted password (via `devkit sys-mig -ec`), NOT plaintext. **?? Plaintext ssh_pass values must NEVER appear in AI output** ? always mask as `***` or `<encrypted_password>`.
- `ssh_user`: SSH login username for the target server
- `ssh_port`: SSH port (default: 22)
- `scan_dir`: Target server scan directory (comma-separated for multiple)

#### ?? nodes.conf Safe Display Rule

When the AI needs to show `nodes.conf` content in chat, it MUST use the `--mask` mode of `encrypt-nodes-verify.sh`:

```bash
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "bash ${DEVKIT_HOME}/encrypt-nodes-verify.sh --mask"
```

**NEVER** run `cat`/`grep`/`sed`/`head`/`tail` on `nodes.conf` and pipe the result into chat ? plaintext passwords would leak.

#### ?? Pre-Scan Password Check & Encryption Flow

Before executing any `devkit sys-mig` scan command, the AI MUST follow this flow:

```
User requests scan (or nodes.conf configuration complete)
    ?
    ?
Check: Does nodes.conf contain plaintext ssh_pass?
    ?
    ??? YES (plaintext found)
    ?       ?
    ?       ?
    ?   Run encrypt-nodes-verify.sh (without --mask)
    ?       1. Encrypt plaintext ssh_pass via sys-mig -ec
    ?       2. Replace plaintext with encrypted values in nodes.conf
    ?       3. Verify SSH connectivity to each target server (from DevKit server)
    ?       4. All pass ? proceed to scan
    ?       5. Some fail ? prompt user to fix, re-run, then scan
    ?
    ??? NO (all already encrypted)
            ?
            ?
        Run encrypt-nodes-verify.sh to verify SSH connectivity to targets
            1. All SSH pass ? proceed to scan
            2. Some fail ? prompt user to fix, re-run, then scan
```

> **?? SSH Verification is ALWAYS required before scan**, regardless of whether passwords are already encrypted.

**How to check**: Run `encrypt-nodes-verify.sh --check` on the DevKit server:

```bash
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "bash ${DEVKIT_HOME}/encrypt-nodes-verify.sh --check"
```

Output:
- `PLAINTEXT_FOUND: <count>` ? plaintext passwords exist, must encrypt before scan
- `ALL_ENCRYPTED` ? all passwords already encrypted, safe to scan directly

**Scanning with plaintext passwords is FORBIDDEN.** The user MUST explicitly run `encrypt-nodes-verify.sh` to encrypt passwords before executing any scan commands. The `scan_devkit.sh` script performs a pre-scan check and will ABORT if plaintext passwords are detected.

### Quick Commands (via devkit_remote.py)

```bash
py scripts/devkit_remote.py --region ${HUAWEI_REGION} install                  # Auto-detect arch, download & install
py scripts/devkit_remote.py --region ${HUAWEI_REGION} install --version 26.1.RC1  # Specify version
py scripts/devkit_remote.py --region ${HUAWEI_REGION} verify                   # Verify installation
```

---

## Step 8: Execute DevKit Scan

After Step 7 (nodes.conf configuration + encryption + SSH verification) is complete, scanning can begin. The user may explicitly request a scan, or scanning can proceed after Step 7 passes.

> **Scan Trigger**: Scanning is ready once Step 7 is complete (nodes.conf configured, passwords encrypted, SSH to all targets verified).

> **?? Pre-Scan Check (MANDATORY)**: When a scan is requested, ensure Step 7 is completed:
> - nodes.conf configured with target servers
> - Passwords encrypted via `encrypt-nodes-verify.sh`
> - SSH to all target servers verified from DevKit server
>
> If user requests scan directly without completing Step 7, follow the Pre-Scan Password Check & Encryption Flow above first.
>
> This check runs automatically inside `scan_devkit.sh` (via `encrypt_and_verify` function).

> **Pre-Scan Encryption**: `scan_devkit.sh` runs `encrypt-nodes-verify.sh` before executing any scan commands. This ensures:
> 1. Plaintext passwords in `nodes.conf` are encrypted via `sys-mig -ec`
> 2. Encrypted passwords replace plaintext values in `nodes.conf`
> 3. SSH connectivity to target servers is verified
> 4. Only after encryption completes do the actual DevKit scan commands run

> **Maven Environment Auto-Check**: When `mvn_analyse` scan mode is executed, `scan_devkit.sh` automatically checks and installs Maven (via `install_devkit.sh --check-maven`) before running the scan command.

> **?? KEY RULE ? Scan Targets the IP Addresses in nodes.conf, NOT the DevKit Server**: Scan targets are read from `nodes.conf`. The fixed scan commands use `-mn all` (stmt/sbom) or default paths to target the servers defined in `nodes.conf`.

> **?? PARAMETER CONFIRMATION (MANDATORY)**: Before executing ANY scan command, AI MUST present all scan parameters to the user for explicit confirmation:

```
========================================
  Scan Parameter Summary
========================================
  Scan Mode:    ${SCAN_MODE} (stmt|sbom|mvn_analyse|container_mig)
  Scan Target:  from nodes.conf (remote) or local path
  Report Path:  ${DEVKIT_HOME}/report/
  Log Level:    ${LOG_LEVEL} (0=DEBUG, 1=INFO, 2=WARNING, 3=ERROR)
========================================
Confirm the above parameters? (yes/no)
```

- **User says yes** ? Execute scan
- **User says no or no response** ? Do NOT execute; ask user to correct parameters

> For scan command templates and parameter descriptions, see [DevKit Operations Guide](devkit-operations-guide.md).

### Quick Command (via devkit_remote.py)

```bash
py scripts/devkit_remote.py --region ${HUAWEI_REGION} scan stmt                # Inventory information collection
py scripts/devkit_remote.py --region ${HUAWEI_REGION} scan sbom                # System component information collection
py scripts/devkit_remote.py --region ${HUAWEI_REGION} scan mvn_analyse         # Maven project source code migration analysis
py scripts/devkit_remote.py --region ${HUAWEI_REGION} scan container_mig       # Container image migration
```

---

## Step 9: Download Reports to Local

> **?? MANDATORY after scan success**: After the scan succeeds and report directories are renamed, the AI **MUST** ask the user to provide a local download path, then download the reports to local.

### Flow

1. **Scan succeeds** ? reports are generated under `${DEVKIT_HOME}/report/` on the DevKit server
2. **Rename report directories** ? rename `sys-mig_<IP>_<timestamp>` to `<scan_mode>_<IP>_<timestamp>` format
3. **Ask user for download path** ? The AI uses the `question` tool to ask the user to provide a local directory path (**no default value, must be explicitly provided by the user**)
4. **Download reports to local** ? download reports to the user-specified path via SFTP

> **?? CRITICAL**: User MUST provide the local directory path. No default. If not provided ? **STOP** and ask again.

### Download Reports via SFTP

```bash
py scripts/devkit_remote.py --region ${HUAWEI_REGION} download-report --local-dir <user_provided_path>
```

This will:
1. Connect to the server via SSH/SFTP (paramiko)
2. Read the list of reports generated by the **last scan** (from `/tmp/devkit_last_scan_reports.txt` on the DevKit server)
3. Download only the report files (HTML, CSV, JSON, ZIP, etc.) from the last scan to the user-specified local directory
4. For **container_mig** reports: only download key files (HTML, JSON, Dockerfile at top level), skipping `incompatible/` and `output/` dirs
5. Preserve the remote directory structure

> To download **all** historical reports instead of just the last scan, add `--all`:
> ```bash
> py scripts/devkit_remote.py --region ${HUAWEI_REGION} download-report --local-dir <path> --all
> ```
>
> To download **full** container_mig report including `incompatible/` and `output/` dirs, add `--full`:
> ```bash
> py scripts/devkit_remote.py --region ${HUAWEI_REGION} download-report --local-dir <path> --full
> ```

### Verify Download

Display downloaded files to user:
```
Downloaded reports to: <local_dir>
  <local_dir>/<scan_mode>_<ip>_<timestamp>/...
```

---

## Related Documents

- [DevKit Operations Guide](devkit-operations-guide.md) ? SSH connection, command templates, script usage
- [Security Rules](rules.md) ? SSH architecture and password management
- [Troubleshooting](troubleshooting.md) ? Common issues and solutions
