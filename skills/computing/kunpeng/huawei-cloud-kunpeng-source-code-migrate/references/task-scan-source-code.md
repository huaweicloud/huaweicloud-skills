# Task 3: Scan Source Code and Generate Migration Report

Use DevKit CLI to scan the specified source code directory and generate a migration assessment report for the Kunpeng (ARM64) platform.

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

- [Overview](#overview)
- [Step 1: Ask User for Source Code Path](#step-1-ask-user-for-source-code-path)
- [Step 2: Verify Source Code Directory](#step-2-verify-source-code-directory)
- [Step 3: Detect Source Code Language](#step-3-detect-source-code-language)
- [Step 4: Run DevKit Scan](#step-4-run-devkit-scan)
- [Step 5: Retrieve and Present Migration Report](#step-5-retrieve-and-present-migration-report)
- [Step 6: Post-Scan Reminders (After Assessment Completes)](#step-6-post-scan-reminders-after-assessment-completes)
- [Report Interpretation](#report-interpretation)
- [Error Handling](#error-handling)

---

## Overview

This task uses the Kunpeng DevKit CLI tool to scan source code and generate a migration assessment report. The report identifies potential migration issues when porting the code from x86_64 to ARM64 (Kunpeng) architecture.

**Supported languages:** C, C++, Assembly (ASM), Fortran, Go, Java, Python, Scala

**⚠️ The actual DevKit command is `devkit porting src-mig`, NOT `devkit scan`.**

**Official documentation:** https://www.hikunpeng.com/document/detail/zh/kunpengdevps/portingadvisor/demo/smartdenovoptCli_21_0001.html

---

## Step 1: Ask User for Source Code Path

**⚠️ REQUIRED — You MUST follow these rules:**

1. **Always ask the user** to specify the source code path on the remote server before scanning. Do NOT scan without user confirmation.
2. **Never scan local source code**.
3. **Never upload local files to the remote server without permission** — You must ask the local files path first, then upload them to the remote server.
4. **List available source code directories** on the remote server to help the user choose if needed.

First, list available source code directories on the remote server to help the user choose:

```bash
# List common source code locations
remote_exec "echo '=== /home ===' && ls -la /home/ 2>/dev/null && echo '=== /opt ===' && ls -la /opt/ 2>/dev/null && echo '=== /root ===' && ls -la /root/ 2>/dev/null"

# Find source code projects (directories containing source files)
remote_exec "find /home /opt /root -maxdepth 3 -type d \\( -name '.git' -o -name 'src' -o -name 'lib' \\) 2>/dev/null | head -20"

# Count source files by directory
remote_exec "for dir in /home/*; do if [ -d \"\$dir\" ]; then count=\$(find \"\$dir\" -maxdepth 3 -type f \\( -name '*.c' -o -name '*.cpp' -o -name '*.java' -o -name '*.py' -o -name '*.go' \\) 2>/dev/null | wc -l); if [ \"\$count\" -gt 0 ]; then echo \"\$dir: \$count source files\"; fi; fi; done"
```

Use `ask_followup_question` to ask the user:

```
请提供远程服务器上需要扫描的源码目录路径（绝对路径），或选择以下已发现的项目：

  [列出发现的项目及源文件数量]

支持的语言：C, C++, ASM, Fortran, Go, Java, Python, Scala
```

**The user must provide:**

| # | Parameter | Description |
|---|-----------|-------------|
| 1 | **Source code directory path** | Absolute path to the source code on the remote server |

**Optional parameters the user may specify:**

| # | Parameter | Default | Description |
|---|-----------|---------|-------------|
| 2 | **Target language** | Auto-detected | Explicitly specify the source code language |
| 3 | **Build tool** | Auto-detected | `make`, `cmake`, `automake`, `go`, `bazel`, `blade` |
| 4 | **Compiler version** | Auto-detected | e.g., `gcc9.3.0` |
| 5 | **Remote output directory** | `/tmp/devkit-report/<project_name>` | Directory on the remote server for the migration report output |

> **⚠️ Local report save path is FIXED and cannot be overridden by the user via this parameter.** See Step 5 for the fixed local save path rules.

---

## Step 2: Verify Source Code Directory

Before scanning, verify that the source code directory exists and contains files.

**Check if directory exists:**

```bash
remote_exec "test -d '<SOURCE_PATH>' && echo 'Directory exists' || echo 'Directory not found'"
```

**If directory not found:**

```
Source code directory not found: <SOURCE_PATH>
Please verify the path and provide the correct directory path.
```

**Check directory contents:**

```bash
remote_exec "ls -la '<SOURCE_PATH>'"
```

**Count source code files by language:**

```bash
remote_exec "cd '<SOURCE_PATH>' && echo 'C files:' && find . -name '*.c' | wc -l && echo 'C++ files:' && find . -name '*.cpp' -o -name '*.cc' -o -name '*.cxx' | wc -l && echo 'ASM files:' && find . -name '*.s' -o -name '*.S' -o -name '*.asm' | wc -l && echo 'Fortran files:' && find . -name '*.f' -o -name '*.f90' -o -name '*.f95' | wc -l && echo 'Go files:' && find . -name '*.go' | wc -l && echo 'Java files:' && find . -name '*.java' | wc -l && echo 'Python files:' && find . -name '*.py' | wc -l && echo 'Scala files:' && find . -name '*.scala' | wc -l"
```

**If no source code files are found:**

```
No recognized source code files found in: <SOURCE_PATH>
Supported file extensions: .c, .h, .cpp, .cc, .cxx, .hpp, .s, .S, .asm, .f, .f90, .f95, .f03, .go, .java, .py, .scala
Please verify the directory contains source code files.
```

---

## Step 3: Detect Source Code Language

If the user did not specify the language, auto-detect it based on file extensions.

**Auto-detection logic:**

```bash
remote_exec "cd '<SOURCE_PATH>' && \
  C_COUNT=\$(find . -name '*.c' -o -name '*.h' | wc -l) && \
  CPP_COUNT=\$(find . -name '*.cpp' -o -name '*.cc' -o -name '*.cxx' -o -name '*.hpp' | wc -l) && \
  ASM_COUNT=\$(find . -name '*.s' -o -name '*.S' -o -name '*.asm' | wc -l) && \
  FORTRAN_COUNT=\$(find . -name '*.f' -o -name '*.f90' -o -name '*.f95' -o -name '*.f03' | wc -l) && \
  GO_COUNT=\$(find . -name '*.go' | wc -l) && \
  JAVA_COUNT=\$(find . -name '*.java' | wc -l) && \
  PYTHON_COUNT=\$(find . -name '*.py' | wc -l) && \
  SCALA_COUNT=\$(find . -name '*.scala' | wc -l) && \
  echo \"C:\$C_COUNT C++:\$CPP_COUNT ASM:\$ASM_COUNT Fortran:\$FORTRAN_COUNT Go:\$GO_COUNT Java:\$JAVA_COUNT Python:\$PYTHON_COUNT Scala:\$SCALA_COUNT\""
```

**Build the `-s` parameter for DevKit:**

Based on detected languages, build the source-type parameter:

| Detected Languages | `-s` Value |
|-------------------|-----------|
| C only | `'c'` |
| C and C++ | `'c, c++'` |
| C, C++, and ASM | `'c, c++, asm'` |
| Java and Python | `'java, python'` |
| Go | `'go'` |
| Fortran | `'fortran'` |

> **Note:** DevKit can scan mixed-language projects. The language parameter helps DevKit apply the correct analysis rules.

---

## Step 4: Run DevKit Scan

Execute the DevKit CLI `porting src-mig` command on the remote server.

**⚠️ The correct command is `devkit porting src-mig`, NOT `devkit scan -t porting`.**

**Create output directory:**

```bash
remote_exec "mkdir -p /tmp/devkit-report/<project_name>"
```

**Build the scan command:**

```bash
# Base command (must run from devkit install directory)
cd /usr/local/devkit && ./devkit porting src-mig \
  -i '<SOURCE_PATH>' \
  -o /tmp/devkit-report/<project_name> \
  -s '<SOURCE_TYPES>' \
  -r all \
  -l 1
```

**For C/C++ projects with build system, add build parameters:**

```bash
cd /usr/local/devkit && ./devkit porting src-mig \
  -i '<SOURCE_PATH>' \
  -o /tmp/devkit-report/<project_name> \
  -s 'c, c++, asm' \
  -b make \
  -c 'make all' \
  -p gcc9.3.0 \
  -r all \
  -l 1
```

**For interpreted languages (Java, Python, Scala), no build command needed:**

```bash
cd /usr/local/devkit && ./devkit porting src-mig \
  -i '<SOURCE_PATH>' \
  -o /tmp/devkit-report/<project_name> \
  -s 'java, python' \
  -r all \
  -l 1
```

**Command parameters reference:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `-i` / `--input` | Yes | Source code directory path |
| `-o` / `--output` | Yes | Output directory (MUST already exist) |
| `-s` / `--source-type` | Yes | Source language(s), comma-separated: `c`, `c++`, `asm`, `fortran`, `go`, `python`, `java`, `scala` |
| `-c` / `--cmd` | For C/C++/Fortran/Go | Build/compiling command line |
| `-b` / `--build-tool` | For C/C++/Fortran/Go | Build tool: `make`, `cmake`, `automake`, `go`, `bazel`, `blade` |
| `-p` / `--compiler` | For C/C++ | Compiler version (e.g., `gcc9.3.0`) |
| `-f` / `--fortran-compiler` | For Fortran | Fortran compiler version (e.g., `gfortran9`) |
| `-r` / `--report-type` | No | Report format: `all`, `json`, `html`, `csv` (default: `all`) |
| `-l` / `--log-level` | No | Log level: `0`(DEBUG), `1`(INFO), `2`(WARN), `3`(ERROR) |

**⚠️ Important notes:**
- The output directory specified by `-o` **must already exist** before running the command, otherwise DevKit will fail with an error.
- The `devkit` binary must be run from its installation directory (`cd /usr/local/devkit`).
- For compiler version (`-p`), use exact version strings like `gcc9.3.0`, NOT `gcc9.4.0` (check available versions with `devkit porting src-mig --help`).

**Monitor scan progress:**

The scan may take several minutes depending on the codebase size. Monitor the process:

```bash
# Check if scan is still running
remote_exec "ps aux | grep devkit | grep -v grep"
```

**Wait for scan completion:**

```bash
# Check for output files
remote_exec "ls -la /tmp/devkit-report/<project_name>/"
```

---

## Step 5: Retrieve and Present Migration Report

After the scan completes, retrieve the migration report from the remote server and present it to the user.

**⚠️ Fixed Local Report Save Path:**

The migration assessment report MUST be saved to a fixed local directory based on the agent's OS. This path is fixed and MUST NOT be changed unless the user explicitly requests a different location.

| Agent OS | Local Report Save Path |
|----------|----------------------|
| Windows | `C:\devkit-report` |
| Linux / macOS | `/home/devkit-report` |

> **Note:** Report files (HTML, JSON, CSV) are saved directly under the save path, with NO project_name subdirectory.

**Step 5.1: Determine the local report save path**

```bash
# Detect agent OS and set the local report save path
# On Linux/macOS:
LOCAL_REPORT_DIR="/home/devkit-report"
mkdir -p "$LOCAL_REPORT_DIR"

# On Windows (PowerShell):
# $LOCAL_REPORT_DIR = "C:\devkit-report"
# New-Item -ItemType Directory -Force -Path $LOCAL_REPORT_DIR
```

**Step 5.2: List report files on the remote server**

```bash
remote_exec "ls -la /tmp/devkit-report/<project_name>/"
```

**Step 5.3: Read the report summary (JSON)**

```bash
# Find and read the JSON report
remote_exec "cat /tmp/devkit-report/<project_name>/*_zh.json 2>/dev/null || cat /tmp/devkit-report/<project_name>/*_en.json 2>/dev/null"
```

**Step 5.4: Read the CSV report for detailed issue list**

```bash
remote_exec "cat /tmp/devkit-report/<project_name>/*_en.csv 2>/dev/null"
```

**Step 5.5: Download and save the report to the fixed local path**

The HTML report provides the best visualization. You MUST download it from the remote server and save it to the fixed local report save path.

**Use the built-in `ssh_client.py get-report` subcommand (recommended, cross-platform)**

The `get-report` subcommand is the simplest and most reliable way to download the DevKit migration report. It automatically:
- Connects to the remote server via paramiko (password from `MIGRATE_SSH_PASS` env var)
- Filters files matching the `Code_Porting_*.{html,json,csv,txt}` pattern
- Creates the local directory if it does not exist
- Downloads all matching files and prints a summary with file sizes

```bash
# Download report with defaults:
#   remote_dir = /tmp/devkit-report
#   local_dir  = C:\devkit-report (Windows) or /home/devkit-report (Linux/macOS)
MSYS_NO_PATHCONV=1 python <skill_dir>/scripts/ssh_client.py get-report

# Or specify custom paths:
MSYS_NO_PATHCONV=1 python <skill_dir>/scripts/ssh_client.py get-report "/tmp/devkit-report" "C:/devkit-report"
```

**Alternative: Use `get` or `get-dir` for more control**

```bash
# Download a single report file:
MSYS_NO_PATHCONV=1 python <skill_dir>/scripts/ssh_client.py get "/tmp/devkit-report/Code_Porting_xxx.html" "C:/devkit-report/Code_Porting_xxx.html"

# Download entire report directory recursively:
MSYS_NO_PATHCONV=1 python <skill_dir>/scripts/ssh_client.py get-dir "/tmp/devkit-report" "C:/devkit-report"
```

> **⚠️ AI MUST use `get-report` (or `get`/`get-dir`) to download the report.** Do NOT manually write Python paramiko scripts, use `exec` with `cat`/base64 to pipe file content, or use `scp` commands — the built-in subcommands handle SFTP, path conversion, MSYS2 path mangling, and error handling correctly.

**Step 5.6: Present the HTML report to the user**

After downloading the HTML report file to the fixed local save path, use the `openBrowserInIDE` tool or inform the user of the file path:

```
鲲鹏迁移评估报告已生成并保存到本地：

  Windows: C:\devkit-report\report.html
  Linux/macOS: /home/devkit-report/report.html

请在浏览器中打开查看完整报告。
```

**Present the report summary to the user:**

Parse the report output and present a structured summary including:

1. **Overall migration assessment** — Whether the code needs migration
2. **Total files scanned** — Number of source files analyzed
3. **Files to be modified** — Number of files requiring changes
4. **Lines to be modified** — Total lines requiring changes
5. **Migration rules and suggestions** — Number of rules and suggestions
6. **Estimated workload** — Person-months estimate
7. **Issue categories:**
   - Assembly code issues (x86-specific instructions)
   - Compiler intrinsic functions (`__builtin_ia32_*`)
   - Platform-specific headers (`emmintrin.h`, etc.)
   - Platform macro branches (`#if` / `#elif defined(__aarch64__)`)
   - Build system / Makefile issues
   - Third-party library dependencies
8. **Detailed issue list** — File path, line number, issue description, and suggested fix
9. **Recommended actions** — Suggested fixes for each issue category

---

## Step 6: Post-Scan Reminders (After Assessment Completes)

> **⚠️ CRITICAL: After the migration assessment report is presented to the user, the AI MUST present the resource cleanup reminder. This reminder is TEXT ONLY — the AI MUST NOT execute any delete commands.**

### When to Present This Reminder

Present this reminder **immediately after** Step 5.6 (after the report summary is shown to the user). This is the final step of the workflow.

### Reminder: Resource Cleanup (Provisioning Path Only)

**Applies only if the server was provisioned via Step 3d.** Present the resource cleanup reminder with all resource IDs created during provisioning.

> **⛔ HIGH-RISK: AI MUST NOT auto-execute any delete commands.** These commands are provided for the USER to execute manually after reviewing the resource list.

```
### 🧹 Resource Cleanup Reminder

The following resources were created during this assessment and incur ongoing charges:

| Resource Type | Resource ID | Details |
|---------------|-------------|---------|
| ECS Instance  | <server_id> | <eip>, <flavor> |
| VPC           | <vpc_id>    | <vpc_name> |
| Subnet        | <subnet_id> | <subnet_name> |
| EIP           | <eip_id>    | <eip> |
| Security Group| <sg_id>     | <sg_name> |

To delete these resources, execute the following commands manually (in reverse order):

  hcloud ECS DeleteServers --cli-region=cn-southwest-2 --servers.1.id=<server_id>
  hcloud VPC DeletePublicip --cli-region=cn-southwest-2 --publicip_id=<eip_id>
  hcloud VPC DeleteSubnet --cli-region=cn-southwest-2 --vpc_id=<vpc_id> --subnet_id=<subnet_id>
  hcloud VPC DeleteSecurityGroup --cli-region=cn-southwest-2 --security_group_id=<sg_id>
  hcloud VPC DeleteVpc --cli-region=cn-southwest-2 --vpc_id=<vpc_id>

⚠️ WARNING: Deletion is IRREVERSIBLE. Verify resource IDs before executing.
⚠️ AI will NOT execute these commands. Please run them manually.
```

**No password rotation reminder is needed** — the password in `MIGRATE_SSH_PASS` is wiped from `os.environ` after each paramiko connection is established. No SSH keys are injected, no ControlMaster sockets are left open.

### Reminder: Existing Server Path (Step 3c) / Local Install Path (Step 3a)

For the existing-server path and local-install path, no resource cleanup is needed. The AI should simply conclude the workflow after presenting the report. No SSH keys are injected and no ControlMaster sockets are left open (unified paramiko approach via `ssh_client.py`).

---

## Report Interpretation

### Migration Assessment Levels

| Level | Description | Action Required |
|-------|-------------|----------------|
| **Do Not Need Migrated** | Code is architecture-independent or already compatible | No changes needed |
| **Need Migrated** | Architecture-specific code found | Changes required per report suggestions |

### Common Migration Issues

#### 1. Inline Assembly (x86 → ARM64)

**Issue:** x86 inline assembly using Intel/AT&T syntax
**Impact:** High — Assembly code is architecture-specific and must be rewritten
**Example:**
```c
// x86 inline assembly
__asm__ __volatile__("cpuid" : "=a"(a), "=b"(b), "=c"(c), "=d"(d) : "a"(func));
// Must be replaced with ARM64 equivalent or C code
```

! #### 2. Compiler Intrinsics

**Issue:** x86-specific compiler intrinsics (e.g., `__builtin_ia32_pslldqi128`, `__builtin_ia32_psrldqi128`)
**Impact:** High — These are not supported on ARM64, must find NEON equivalents
**Example:**
```c
// x86 intrinsic
__m128 a = _mm_add_ps(b, c);
// ARM64 NEON equivalent
float32x4_t a = vaddq_f32(b, c);
```

#### 3. Platform-Specific Headers

**Issue:** x86-specific header files (e.g., `emmintrin.h` for SSE2)
**Impact:** High — These headers are not available on ARM64
**Solution:** Replace with ARM64 NEON headers (`arm_neon.h`) and add `#elif defined(__aarch64__)` branches

#### 4. Platform Macro Branches

**Issue:** Code uses `#if` for platform detection without ARM64 branch
**Impact:** Medium — Need to add `#elif defined(__aarch64__)` branch
**Example:**
```c
// Before
#if defined(__SSE2__)
  // x86 SSE2 code
#endif

// After
#if defined(__SSE2__)
  // x86 SSE2 code
#elif defined(__aarch64__)
  // ARM64 NEON code
#endif
```

#### 5. Byte Order / Endianness

**Issue:** Code assumes little-endian byte order
**Impact:** Low-Medium — ARM64 can be little-endian, but code should be verified
**Note:** Kunpeng (ARM64) supports little-endian mode, so this is typically not a blocking issue

#### 6. Pointer Size Assumptions

**Issue:** Code assumes 32-bit pointer size or mixes int/pointer types
**Impact:** Medium — Need to use proper types (uintptr_t, size_t, etc.)

#### 7. Third-Party Libraries

**Issue:** Dependencies that don't have ARM64 builds
**Impact:** High — Must find ARM64-compatible alternatives or build from source

#### 8. Build System Issues

**Issue:** Makefiles/CMake with x86-specific flags or libraries
**Impact:** Low-Medium — Need to update build configuration

---

## Error Handling

### Scan Command Not Found

**Problem:** `devkit: command not found`

**Solution:** Return to Task 2 and install DevKit.

### Unknown Sub Command: scan

**Problem:** `error: Unknown sub command: scan`

**Cause:** The correct command is `devkit porting src-mig`, NOT `devkit scan`.

**Solution:** Use the correct command:
```bash
cd /usr/local/devkit && ./devkit porting src-mig -i <source_path> -o <output_path> -s '<languages>'
```

### Output Directory Does Not Exist

**Problem:** `The path <output_path> does not exist or you do not have the permission to access the path.`

**Cause:** The output directory must be created before running the scan.

**Solution:**
```bash
remote_exec "mkdir -p /tmp/devkit-report/<project_name>"
```

### Invalid Compiler Version

**Problem:** `invalid choice: 'gcc9.4.0'`

**Cause:** The compiler version string must match exactly one of the supported values.

**Solution:** Check available compiler versions:
```bash
remote_exec "cd /usr/local/devkit && ./devkit porting src-mig --help"
```
Common versions: `gcc4.8.5`, `gcc7.3.0`, `gcc9.3.0`, `gcc10.2.0`, `gcc12.3.0`

### Scan Permission Denied

**Problem:** `Permission denied` when accessing source code directory

**Solution:**
```bash
# Check directory permissions
remote_exec "ls -la '<SOURCE_PATH>'"

# Fix permissions if needed
remote_exec "chmod -R +r '<SOURCE_PATH>'"
```

### Scan Timeout

**Problem:** Scan takes too long for large codebases

**Solution:**
- For very large codebases, suggest scanning specific subdirectories
- Or increase the timeout with `--set-timeout`

### Empty Report

**Problem:** Scan completes but report is empty

**Possible causes:**
1. Source code directory contains no supported file types
2. DevKit version is outdated
3. Source code is already fully compatible

**Solution:**
```bash
# Verify source code files exist
remote_exec "find '<SOURCE_PATH>' -type f | head -20"

# Check DevKit version
remote_exec "cd /usr/local/devkit && ./devkit --version"
```

### Report Retrieval Failed

**Problem:** Cannot download report from remote server to the fixed local save path

**Solution:**
```bash
# Check report files on remote server
python <skill_dir>/scripts/ssh_client.py exec "ls -la /tmp/devkit-report/"

# Use the built-in get-report subcommand (handles SFTP, path conversion, errors):
MSYS_NO_PATHCONV=1 python <skill_dir>/scripts/ssh_client.py get-report

# Or download a specific file with get:
MSYS_NO_PATHCONV=1 python <skill_dir>/scripts/ssh_client.py get "/tmp/devkit-report/Code_Porting_xxx.json" "C:/devkit-report/Code_Porting_xxx.json"
```
