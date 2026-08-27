# Acceptance Criteria - Kunpeng Source Code Migration Assessment

Validation criteria for correct and incorrect patterns when using this skill.

## Table of Contents

- [Security Criteria](#security-criteria)
- [Local OS Detection Criteria](#local-os-detection-criteria)
- [Local DevKit Installation Criteria](#local-devkit-installation-criteria)
- [Server Preparation Criteria](#server-preparation-criteria)
- [hcloud CLI Criteria](#hcloud-cli-criteria)
- [ECS Provisioning Criteria](#ecs-provisioning-criteria)
- [SSH Connection Criteria](#ssh-connection-criteria)
- [DevKit Installation Criteria](#devkit-installation-criteria)
- [Source Code Scan Criteria](#source-code-scan-criteria)
- [Report Criteria](#report-criteria)

---

## Security Criteria

### ✅ Correct Patterns

| # | Pattern | Description |
|---|---------|-------------|
| 1 | Use unified paramiko SSH via built-in `ssh_client.py` script | Verify paramiko password connection (no key injection, no ControlMaster); subcommands: `test`, `exec`, `put`, `put-dir`, `save-env` |
| 2 | Never echo or print any credential values | No passwords are stored; `MIGRATE_SSH_PASS` is wiped from `os.environ` after each connection |
| 3 | Refuse credentials provided in conversation | Politely redirect to env var setup; password must be set via `MIGRATE_SSH_PASS` environment variable |
| 4 | Use `ssh_client.py` (paramiko + password from env) for SSH | No `sshpass`, no ControlMaster, cross-platform; unified paramiko approach |
| 5 | Read-only operations on source code | Scan only, never modify source files |
| 6 | Never ask for AK/SK in conversation | Guide user to `hcloud configure` or environment variables |
| 7 | Never provision ECS without user confirmation | Must get explicit "yes" before creating resources |
| 8 | Run `ssh_client.py test` after provisioning | Verify SSH connection after ECS creation |
| 9 | Remind user to clean up resources after scan | Present Resource Cleanup Reminder at end of workflow |

### ❌ Incorrect Patterns

| # | Pattern | Description |
|---|---------|-------------|
| 1 | Ask user to type SSH password in chat | Credentials must never be accepted in conversation |
| 2 | Echo/print password or pass via argv | Password must only be read from `MIGRATE_SSH_PASS` env var |
| 3 | Use `sshpass` or ControlMaster or key injection | Use unified paramiko + password from env var instead |
| 4 | Modify source code during scan | Migration assessment is read-only |
| 5 | Install packages unrelated to DevKit | Only DevKit and its dependencies |
| 6 | Ask user for AK/SK in conversation | Must use `hcloud configure` or environment variables |
| 7 | Provision ECS without user confirmation | Must get explicit "yes" before creating paid resources |
| 8 | Skip `ssh_client.py test` after provisioning | MUST verify SSH connection after ECS creation |
| 9 | Skip Resource Cleanup Reminder after provisioning | MUST remind user to delete resources manually |

---

## Local OS Detection Criteria

### ✅ Correct Patterns

| # | Pattern | Description |
|---|---------|-------------|
| 1 | Detect local OS before asking user | Run `uname -m` and `cat /etc/os-release` first |
| 2 | Classify OS as supported or unsupported | Match against DevKit-supported OS list |
| 3 | Offer local install option only if OS is supported | openEuler, CentOS, Ubuntu, Kylin, UOS, etc. |
| 4 | Skip local install option if OS is unsupported | Windows, macOS → directly ask about remote server |
| 5 | Use alternative OS detection if /etc/os-release fails | lsb_release, /etc/redhat-release, /etc/issue |
| 6 | Detect architecture (x86_64 vs aarch64) | Determines DevKit package to download |

### ❌ Incorrect Patterns

| # | Pattern | Description |
|---|---------|-------------|
| 1 | Skip OS detection and assume remote install | Must detect OS first to offer local option |
| 2 | Offer local install on Windows/macOS | DevKit only supports Linux |
| 3 | Assume OS type without detection | Must actually run detection commands |
| 4 | Ignore architecture detection | Wrong DevKit package will be downloaded |
| 5 | Hardcode OS type | Must detect dynamically at runtime |

---

## Local DevKit Installation Criteria

### ✅ Correct Patterns

| # | Pattern | Description |
|---|---------|-------------|
| 1 | Check if DevKit is already installed locally | `devkit --version` before attempting install |
| 2 | Install dependencies before DevKit | python3, curl based on OS package manager |
| 3 | Select correct DevKit package by architecture | x86_64 → `Linux-x86-64`, aarch64 → `Linux-Kunpeng` |
| 4 | Copy hidden `.devkit` file during install | Required for DevKit execution |
| 5 | Verify installation after install | `devkit --version` and `devkit --help` |
| 6 | Ask user for local source code path | Must not assume the path |
| 7 | Verify source code path exists before scanning | `test -d <path>` |

### ❌ Incorrect Patterns

| # | Pattern | Description |
|---|---------|-------------|
| 1 | Install DevKit without checking existing installation | Risk of clobbering prior config — must verify first |
| 2 | Miss `.devkit` hidden file during copy | Will cause execvp failure |
| 3 | Use wrong architecture package | `cannot execute binary file` error |
| 4 | Scan without verifying source path | May scan non-existent directory |
| 5 | Assume source code path without asking | Must ask the user |

---

## Server Preparation Criteria

### ✅ Correct Patterns

| # | Pattern | Description |
|---|---------|-------------|
| 1 | Ask user about server availability first | Use `ask_followup_question` before any other action |
| 2 | Guide environment variable configuration | Provide clear instructions for setting `KUNPENG_SERVER_*` |
| 3 | Check existing environment variables before prompting | May already be configured from previous session |
| 4 | Offer provisioning as alternative | When user has no server, offer Huawei Cloud ECS |
| 5 | Present server specification before provisioning | Show flavor, image, disk, cost info |
| 6 | Get explicit confirmation before provisioning | User must say "yes" or equivalent |

### ❌ Incorrect Patterns

| # | Pattern | Description |
|---|---------|-------------|
| 1 | Skip server availability check | Must ask user first |
| 2 | Assume user has a server | User may not have one |
| 3 | Provision ECS without confirmation | Creates paid resources without consent |
| 4 | Hardcode server IP | Must come from environment variables or provisioning |
| 5 | Skip environment variable verification | Must verify before attempting SSH |

---

## hcloud CLI Criteria

### ✅ Correct Patterns

| # | Pattern | Description |
|---|---------|-------------|
| 1 | Check hcloud installation before use | `hcloud version` to verify |
| 2 | Guide user to `hcloud configure` for auth | Interactive, secure credential setup |
| 3 | Use `--param=value` format for all hcloud commands | Required by hcloud CLI |
| 4 | Verify authentication before provisioning | Test with `hcloud ECS ListServersDetails` |
| 5 | Use `--cli-output=json` for structured parsing | Enables programmatic result processing |

### ❌ Incorrect Patterns

| # | Pattern | Description |
|---|---------|-------------|
| 1 | Ask user for AK/SK in conversation | Security violation |
| 2 | Use `--param value` format (space instead of =) | hcloud requires equals sign |
| 3 | Skip authentication check | May fail during provisioning |
| 4 | Use `hcloud configure set` with plaintext AK/SK | Exposes credentials in command history |

---

## ECS Provisioning Criteria

### ✅ Correct Patterns

| # | Pattern | Description |
|---|---------|-------------|
| 1 | Use Kunpeng (ARM64) flavor | `kc1.2xlarge.2` or similar KC1/KC2 flavor |
| 2 | Use Huawei Cloud EulerOS 2.0 image | Official ARM64 image |
| 3 | Create new VPC + Subnet | Isolated network for the assessment |
| 4 | Create Security Group with SSH rule | Allow TCP 22 inbound |
| 5 | Restrict SSH to agent IP when possible | Detect agent public IP and add specific rule |
| 6 | Create EIP for remote access | Required for SSH from agent machine |
| 7 | Save connection info to secure file | `/tmp/kunpeng_server_env.sh` with chmod 600 |
| 8 | Load environment variables after provisioning | `source /tmp/kunpeng_server_env.sh` |
| 9 | Verify SSH connectivity after provisioning | Test connection before proceeding |
| 10 | Remind user about cost and cleanup | Server incurs charges until deleted |
| 11 | **Provide cleanup commands as TEXT ONLY** | AI must NOT auto-execute delete commands |
| 12 | **List all resource IDs before cleanup** | User must verify resources before deleting |
| 13 | **Warn about irreversibility of deletion** | Deletion is HIGH-RISK and IRREVERSIBLE |

### ❌ Incorrect Patterns

| # | Pattern | Description |
|---|---------|-------------|
| 1 | Use x86 flavor for Kunpeng assessment | Defeats the purpose of ARM64 migration |
| 2 | Open SSH to 0.0.0.0/0 without agent IP restriction | Security risk |
| 3 | Save password in world-readable file | Must use chmod 600 |
| 4 | Skip SSH verification after provisioning | May proceed with unreachable server |
| 5 | Not remind user about ongoing costs | User may forget to delete server |
| 6 | **AI auto-executes `hcloud ... Delete*` commands** | **HIGH-RISK: AI must NEVER auto-delete resources** |
| 7 | **AI runs cleanup scripts without user confirmation** | **User must review and confirm resource list first** |
| 8 | **AI deletes resources without listing IDs first** | **User must see exactly what will be deleted** |

---

## SSH Connection Criteria

### ✅ Correct Patterns

| # | Pattern | Example |
|---|---------|---------|
| 1 | Use environment variables for all SSH parameters | `python <skill_dir>/scripts/ssh_client.py exec "<command>"` (reads env vars; paramiko reads `MIGRATE_SSH_PASS` from env, no key injection) |
| 2 | Set connection timeout | `ssh -o ConnectTimeout=10` |
| 3 | Handle host key checking | `ssh -o StrictHostKeyChecking=no` for first-time connections |
| 4 | Verify connection before proceeding | Test with `echo 'SSH connection successful'` |
| 5 | Use default port when not specified | `KUNPENG_SERVER_PORT=${KUNPENG_SERVER_PORT:-22}` |

### ❌ Incorrect Patterns

| # | Pattern | Example |
|---|---------|---------|
| 1 | Hardcoded IP address | `ssh root@<hardcoded-ip>` |
| 2 | Hardcoded password | `sshpass -p 'mypassword'` |
| 3 | No connection timeout | `ssh user@host` (may hang indefinitely) |
| 4 | Skip connectivity test | Proceed without verifying SSH connection |
| 5 | Use password in command line arguments | `ssh user@host -p password` (visible in ps) |

---

## DevKit Installation Criteria

### ✅ Correct Patterns

| # | Pattern | Description |
|---|---------|-------------|
| 1 | Detect OS type before downloading | Parse `/etc/os-release` to determine OS |
| 2 | Detect architecture before downloading | Use `uname -m` to determine x86_64 or aarch64 |
| 3 | Check existing installation first | `devkit --version` before attempting install |
| 4 | Use official download URL | From `mirrors.huaweicloud.com` or official page |
| 5 | Verify installation after install | `devkit --version` and `devkit scan --help` |
| 6 | Clean up installation files | Remove `/tmp/devkit-install` after installation |

### ❌ Incorrect Patterns

| # | Pattern | Description |
|---|---------|-------------|
| 1 | Assume OS type without detection | Don't assume CentOS without checking |
| 2 | Download wrong architecture package | x86 package on ARM64 server will fail |
| 3 | Skip existing installation check | Risk of clobbering prior configuration — must verify first |
| 4 | Use unofficial download sources | Security risk |
| 5 | Leave installation files on server | Wastes disk space |

---

## Source Code Scan Criteria

### ✅ Correct Patterns

| # | Pattern | Description |
|---|---------|-------------|
| 1 | Ask user for source code path | Use `ask_followup_question` for the path |
| 2 | Verify source directory exists | `test -d <path>` before scanning |
| 3 | Count source files before scanning | Verify there are files to scan |
| 4 | Auto-detect language if not specified | Based on file extensions |
| 5 | Use correct scan type | `-t porting` for migration assessment |
| 6 | Specify output directory | `-o /tmp/devkit-report` |
| 7 | Handle scan errors gracefully | Check exit code and report errors |

### ❌ Incorrect Patterns

| # | Pattern | Description |
|---|---------|-------------|
| 1 | Guess or assume source code path | Must ask the user |
| 2 | Skip directory verification | May scan non-existent path |
| 3 | Use wrong scan type | `-t performance` is not migration assessment |
| 4 | Overwrite existing report without asking | May lose previous scan results |
| 5 | Ignore scan exit code | May present incomplete results |
| 6 | Scan without DevKit installed | Must install DevKit first |

---

## Report Criteria

### ✅ Correct Patterns

| # | Pattern | Description |
|---|---------|-------------|
| 1 | Present structured summary | Overall score, issue counts, categories |
| 2 | List critical issues first | Prioritize by severity |
| 3 | Include file and line information | Help user locate issues |
| 4 | Provide remediation suggestions | For each issue category |
| 5 | Offer to download full report | HTML report for detailed viewing |
| 6 | Include compatibility score | Quantitative assessment |
| 7 | Save report to fixed local path | Windows: `C:\devkit-report\`; Linux/macOS: `/home/devkit-report/` |
| 8 | Create save directory if not exists | `mkdir -p` on Linux/macOS, `New-Item -ItemType Directory -Force` on Windows |

### ❌ Incorrect Patterns

| # | Pattern | Description |
|---|---------|-------------|
| 1 | Dump raw JSON to user | Parse and present in readable format |
| 2 | Omit critical issues | All issues must be reported |
| 3 | No remediation guidance | User needs to know how to fix issues |
| 4 | Report only file names without line numbers | Hard to locate issues |
| 5 | Skip compatibility score | Important overall metric |
| 6 | Save report to arbitrary/relative path | MUST use fixed path: `C:\devkit-report` (Windows) or `/home/devkit-report` (Linux/macOS) |
