---
name: huawei-cloud-devkit-application-check-cli
description: |
  Use Kunpeng DevKit CLI to collect installed software information (packages, middleware, databases) from application systems, analyze Maven POM file dependency compatibility, and generate migration assessment reports.Automatically creates a Kunpeng ECS server, uploads DevKit scripts, and on user request installs DevKit and executes scans.
  Trigger words: "system migration", "information collection", "maven migration", "container migration", "system migration assessment", "系统迁移", "信息收集", "maven迁移", "容器迁移", "系统迁移评估"
tags:
  - DevKit Application Check
  - Kunpeng Migration Assessment
  - Maven POM Compatibility
  - System Migration
  - Software Compatibility Analysis
metadata: {"devkit": {"version": "1.0.0", "requires": {"bins": ["hcloud"]}, "install": [{"kind": "shell", "command": "Invoke-WebRequest -Uri https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -OutFile ./hcloud_install.sh; bash ./hcloud_install.sh -y"}]}, "execution_modes": {"cli": {"description": "hcloud CLI commands (28 commands)", "available": true}, "sdk": {"description": "Huawei Cloud SDK (22 of 32 commands have SDK equivalents)", "available": true, "note": "22 hcloud CLI commands have SDK equivalents; 6 CLI-only commands and 4 local scripts do not"}, "api": {"description": "REST API (22 of 32 commands have API equivalents)", "available": true, "note": "22 hcloud CLI commands have API equivalents; 6 CLI-only commands and 4 local scripts do not"}, "manual": {"description": "Local script execution (4 scripts)", "available": true, "scripts": ["scripts/devkit_remote.py", "scripts/encrypt-nodes-verify.sh", "scripts/install_devkit.sh", "scripts/scan_devkit.sh"]}}}
version: v1.1.0
---

⚠️ **Security Rules**:
1. AK/SK MUST be passed via environment variables. NEVER expose AK/SK/Password in plaintext.
2. **🔴 No Plaintext Passwords in AI Output**: `DEVKIT_ECS_PASSWORD` value and `nodes.conf` plaintext `ssh_pass` values MUST NEVER appear in plaintext anywhere in AI-generated content — including chat responses, internal thinking/reasoning, tool call arguments, command examples, error messages, debug output, and status reports. Always mask as `***` or use placeholders (`<your_password>`, `<encrypted_password>`). This is a **hard prohibition with zero exceptions**.
3. **🔴 nodes.conf Password Masking**: To safely display `nodes.conf` content, run `bash ${DEVKIT_HOME}/encrypt-nodes-verify.sh --mask` on the DevKit server (outputs all `ssh_pass` values masked as `***`). NEVER `cat`/`grep`/`sed` `nodes.conf` directly into chat output.
4. **🔴 Mandatory Encryption Replacement**: Before any scan, AI MUST run `encrypt-nodes-verify.sh` on the DevKit server to encrypt plaintext `ssh_pass` via `sys-mig -ec` and replace plaintext values in `nodes.conf` with encrypted ones. NEVER execute `devkit sys-mig` scan commands while `nodes.conf` still contains plaintext passwords.
5. **🔴 DEVKIT_ECS_PASSWORD Masking**: The DevKit server password (`DEVKIT_ECS_PASSWORD` env var value) MUST NEVER appear in plaintext in any AI output (chat, thinking, tool calls, logs). Always mask as `***` or `<your_password>`. Command examples must use `${DEVKIT_ECS_PASSWORD}` (variable reference), never the actual value.
6. **🔴 No Temporary Scripts**: NEVER use the `Write` tool to create temporary script files (e.g., `_exec_scan.py`, `_rename.py`, etc.). All commands must use inline execution (`py -c`, `bash -c`, etc.) or call existing scripts directly.
7. **🔴 Prefer Inline Execution**: When executing Python code, prefer `py -c "..."` inline mode instead of creating temporary `.py` files.
8. **🔴 Return Errors Only on Failure**: When a command fails, only return the error message for user troubleshooting. NEVER rewrite scripts, NEVER print full commands, NEVER auto-retry. Let the user decide next steps.
9. **🔴 Parameter Confirmation**: Before executing ANY command or API call, ALL parameters MUST be explicitly confirmed by the user. NO defaults. NO implicit assumptions. NO execution without explicit user approval. Parameters requiring confirmation: Region (user selects from 4 options each time, no cache/reuse), Network (VPC/subnet/security group names, CIDR), ECS (instance name, flavor, OS image, adminPass source), Credentials (`DEVKIT_ECS_USER`/`DEVKIT_ECS_PASSWORD`), Scan (mode, path, report path, log level), Report (local download path). Confirmation flow: AI collects parameters → presents summary → asks "Confirm above parameters? (yes/no)" → user explicitly says yes → execute; user says no or no response → do NOT execute. **NEVER** execute with unconfirmed parameters, assumed defaults, or without explicit user approval.
10. **🔴 Display Language**: ALL user-facing display content MUST be in Simplified Chinese. This includes: configuration instructions and prompts (e.g., AK/SK setup guides, network configuration, ECS parameters), parameter confirmation summaries, error messages and troubleshooting suggestions, step progress notifications and status reports, scan type selection options and descriptions, and any text output intended for the user to read. **NEVER** display English instructions, prompts, or descriptions to the user. When referencing English content from reference documents, AI MUST translate it to Simplified Chinese before displaying to the user. Technical terms (e.g., hcloud, AK/SK, VPC, ECS, EIP, SSH, SFTP, nodes.conf, DevKit) and command syntax remain in English.
11. **🔴 No Guessing — Always Consult Skill Documents**: Before executing ANY operation (especially scan commands, ECS creation, script execution, parameter templates), AI MUST first read the relevant skill reference documents (e.g., `references/devkit-operations-guide.md`, `references/ecs-creation.md`, `references/devkit-operations-workflow.md`) to obtain the correct command templates, parameter names, and formats. **NEVER** guess or fabricate command parameters, command templates, API parameters, or file paths from memory or assumptions. **NEVER** present command templates to the user without first verifying them against the skill documentation. If unsure about a command or parameter, read the corresponding reference document first. This rule applies to ALL steps: scan command templates (stmt/sbom/mvn_analyse/container_mig), ECS creation parameters, network configuration, script execution, etc.
12. **🔴 No Re-run of Create Commands**: NEVER re-run any create command (CreateServers, CreateVpc, etc.) if the first call's output parsing fails or returns empty. The resource was likely already created. Instead, query existing resources by name to find the created resource. Re-running create commands produces duplicate resources, wasting quota and incurring costs.

See [Security Rules](references/rules.md).

---

# huawei-cloud-devkit-application-check-cli

## Overview

End-to-end workflow for Kunpeng application migration assessment:

1. **Check hcloud** → Verify hcloud CLI installed and AK/SK configured; if not, install and configure
2. **Select Region** → Ask user to choose target region from 4 options (no default)
3. **Network Setup** → Detect or create VPC + Subnet + Security Group
4. **A: Detect Existing ECS** → Query `devkit-ecs-*` prefix ECS (MANDATORY before any flavor/OS selection); if found, list all for user to choose **reuse** or **create new**; if reuse → skip Steps 4B-6, proceed to Step 7; if create new or none found → proceed to Step 4B
4. **B: Select Flavor/OS** → Architecture fixed to x86_64; user selects flavor from available 4U8G flavors in ac/C/S/T/X series only (query ListFlavors with --availability_zone, filter vcpus=4 ram=8192, id matches ^ac|^c|^s|^t|^x; recommend ≥1 per series) and OS (CentOS 7.6 / Ubuntu 20.04); instance name auto-generated as `devkit-ecs-{timestamp}`; resolve credentials (no defaults). **Image query uses ECS Nova API** (`GET /v2.1/{project_id}/images/detail`) with `HW_ARCH == "x86_64"` architecture check and GPU keyword exclusion (gpu/with cuda/with tesla/with graphic/vroce)
5. **Create ECS + EIP** → **Confirm all ECS parameters with user** → Create ECS with confirmed spec and bind EIP → **upon success, AUTOMATICALLY proceed to Step 6**
6. **Login, Upload & Install** → Verify SSH login → upload 3 shell scripts → execute install_devkit.sh (DevKit + Maven) — **auto-triggered by Step 5 success**
7. **Configure nodes.conf & Pre-Scan Verification** → Prompt user to configure nodes.conf → encrypt passwords via `encrypt-nodes-verify.sh` → verify SSH to target servers from DevKit server → ready for scan
8. **Scan** → **Confirm scan mode and parameters with user** → Execute scan; scan targets read from nodes.conf; reports renamed to `<scan_mode>_<nodes_IP>_<timestamp>`
9. **Download Reports** → Download scan reports to local (user provides path)

> **CRITICAL**: Step 8 (Scan) is ONLY executed when the user explicitly requests it. Do NOT proceed with scans without explicit user request.

---

## Command Execution Modes

This skill uses two categories of commands with distinct execution modes:

### CLI Execution (hcloud commands)

All Huawei Cloud resource operations (ECS, EIP, VPC, Subnet, Security Group, configure) are executed via `hcloud` CLI. These commands have CLI equivalents and most also have SDK/API equivalents.

- **Executor**: `cli` (hcloud CLI)
- **Risk level**: low
- **Count**: 28 commands
- **Examples**: `hcloud ECS CreateServers`, `hcloud VPC ListVpcs`, `hcloud configure set`, etc.

### Manual Execution (local scripts)

The following 4 local scripts are executed manually on the Agent or DevKit server. They do **not** have hcloud CLI, SDK, or API equivalents — they are custom scripts for SSH operations, DevKit installation, encryption, and scanning.

| Script | Purpose | Executor | Risk Level | SDK/API |
|--------|---------|----------|------------|---------|
| `scripts/devkit_remote.py` | SSH/SFTP to DevKit server (paramiko), EIP auto-resolve from hcloud | manual | high | Not available |
| `scripts/encrypt-nodes-verify.sh` | Encrypt plaintext passwords in nodes.conf & verify SSH to targets | manual | high | Not available |
| `scripts/install_devkit.sh` | Install DevKit CLI + Maven on DevKit server (auto-detect arch) | manual | high | Not available |
| `scripts/scan_devkit.sh` | Execute DevKit sys-mig scan (stmt/sbom/mvn_analyse/container_mig) | manual | high | Not available |

> **Note**: `devkit_remote.py` internally calls `hcloud` CLI for EIP resolution, but the script itself is a local Python script (requires `paramiko`) and cannot be mapped to a single hcloud command or SDK method.

---

## SSH Command Execution Guidelines

These guidelines apply to ALL SSH remote operations performed via `devkit_remote.py` throughout the workflow. Following them prevents two classes of failures: missing PATH in non-interactive shells and incorrect command parsing due to unescaped shell metacharacters.

### Always Use ssh_exec Wrapper

- ALL SSH remote commands in `devkit_remote.py` MUST go through `ssh_exec()` with `login_shell=True`, including report discovery (`find`, `cat`) commands.
- NEVER call `client.exec_command()` directly — it bypasses `bash -l -c` wrapping, causing PATH missing in non-interactive shells where tools like `devkit`, `sys-mig`, and `maven` are not found.
- If a command truly doesn't need a login shell, pass `login_shell=False` explicitly to `ssh_exec()` instead of bypassing the function entirely. This makes the intent explicit rather than silently dropping the wrapper.

### Command Escaping in Login Shell Wrapping

- When wrapping SSH commands in `bash -l -c`, ALWAYS use `shlex.quote(cmd)` to escape the original command string.
- Correct: `wrapped = f"bash -l -c {shlex.quote(cmd)}"`
- NEVER use bare f-string interpolation (e.g., `f"bash -l -c '{cmd}'`) — commands containing single quotes, spaces, or shell metacharacters will be parsed incorrectly by the remote shell.
- Verified patterns:
  - `uname -m` → `bash -l -c 'uname -m'`
  - `bash ${DEVKIT_HOME}/install_devkit.sh 2.1.0` → `bash -l -c 'bash ${DEVKIT_HOME}/install_devkit.sh 2.1.0'`

### Remote Execution Inline Mode

NEVER create temporary script files (e.g., `devkit_remote.py`, `_exec_scan.py`). Complex SSH operations must use inline execution instead. This reinforces Security Rules #6 and #7.

- **bash inline**: `bash -c "ssh -o StrictHostKeyChecking=no user@host 'command'"`
- **Python inline**: `py -c "import paramiko; ..."` — keep it single-line, avoid multi-line heredoc
- **hcloud native**: prefer hcloud built-in commands (e.g., `ECS ListServersDetails`) over custom SSH scripts
- **Multi-step operations**: split into multiple independent inline commands executed sequentially, rather than writing a single script file

---

## hcloud Resource Query Guidelines

When querying existing devkit resources (ECS, EIP, VPC, etc.), follow these standard steps to avoid repeated trial-and-error in local parsing.

1. **Verify command first**: run `hcloud ECS ListServersDetails --cli-region=${HUAWEI_REGION} --cli-output=json` standalone to inspect the raw output format before writing any parsing logic.
2. **Use server-side filtering**: prefer hcloud `--filter` parameters to reduce data volume and avoid heavy local parsing.
3. **Query EIP**: `hcloud EIP ListPublicips --cli-output=json 2>/dev/null`, then match by `vnic.port_id` against the target ECS.
4. **Query VPC**: `hcloud VPC ListVpcs --cli-output=json 2>/dev/null`, then filter by `name` prefix `devkit-`.
5. **Verify each step**: confirm the previous step's output is correct before proceeding to the next, avoiding cascading errors from unverified assumptions.

---

## Safe Resource Creation Pattern (All Create Commands)

Create commands such as `CreateServers`, `CreateVpc`, etc. are **non-idempotent** — running them twice creates two separate resources. To avoid duplicate resources, wasted quota, and unexpected charges, follow this safe creation pattern for every create-class command:

1. **Output to file first**: Redirect the command output to a file rather than parsing it inline.
   ```bash
   hcloud ECS CreateServers ... > create_result.json
   ```
2. **Parse from file**: Parse the saved file using `jq` or `py -c`, never a direct pipe. This isolates parsing from command execution and preserves the raw output for debugging.
   ```bash
   py -c "import json; d=json.load(open('create_result.json')); print(d['serverIds'][0])"
   ```
3. **Query on parse failure, never retry**: If parsing fails or returns empty, the resource was likely already created. Query by name to find it instead of re-running the create command.
   ```bash
   hcloud ECS ListServersDetails --name devkit-ecs-xxx --cli-region=${HUAWEI_REGION} --cli-output=json
   ```
4. **NEVER re-run create commands**: Re-running a create command produces a duplicate resource, wasting quota and incurring costs. Always query first.

This pattern reinforces Security Rule #12 and applies to ALL non-idempotent hcloud create commands (`CreateServers`, `CreateVpc`, `CreateSubnet`, `CreateSecurityGroup`, etc.).

### CreateServers Response Format

`hcloud ECS CreateServers` returns the following structure:

```json
{
  "job_id": "xxx",
  "serverIds": ["server-id-1"]
}
```

**Note**: The response is **not** `{server: {id, name, status}}`. Parse `serverIds[0]` to obtain the server ID. After extracting the ID, poll `hcloud ECS ShowServer --server_id <id>` until `status` becomes `ACTIVE` before proceeding.

---

## Step 1: Check hcloud Environment (MANDATORY)

Verify hcloud CLI (≥7.2.2) and AK/SK configured. If not, install and configure. If connectivity fails, **STOP**.

### Step 1.1: Check hcloud CLI Installation
- Run `hcloud version` to verify hcloud CLI is installed and version ≥ 7.2.2
- If not installed → install per [CLI Installation Guide](references/cli-installation-guide.md) → re-check

### Step 1.2: Check AK/SK Configuration
- Run `hcloud configure list` to check if AK/SK is configured (existence check only)
- **🔴 NEVER execute `hcloud configure set` on behalf of the user. NEVER read AK/SK from env vars and write them into hcloud profile. Credential configuration is the user's responsibility. AI only performs `hcloud configure list` existence checks.**
- If AK/SK **not configured** → display: "For security constraints, AK/SK cannot be received in conversation. Please configure AK/SK following the steps below:" → **detect current OS environment (Windows/Linux) and show ONLY the corresponding platform's configuration methods** per [CLI Installation Guide §4](references/cli-installation-guide.md) → **WAIT** for user to configure → re-check `hcloud configure list` (verification only)
- If still not configured → **STOP**
- If configured → proceed to Step 1.3

### Step 1.3: Verify Connectivity
- Run `hcloud ECS ListCloudServers --cli-region=cn-north-4 --limit=1` to verify connectivity
- If fails → **STOP**

See [CLI Installation & hcloud Setup](references/cli-installation-guide.md).

---

## Step 2: Select Target Region

Present 4 region options (cn-north-4, cn-east-3, cn-south-1, cn-southwest-2). **No default.** **NEVER** cache or reuse a previously selected region.

See [CLI Installation & hcloud Setup](references/cli-installation-guide.md).

---

## Step 3: Network Setup

Detect or create VPC + Subnet + Security Group by `devkit-*` prefix. If found, ask user whether to reuse. **All network parameters (VPC name, subnet name, security group name, CIDR) MUST be confirmed by user before creation.** **NEVER reuse without user consent.** New resource naming: VPC=`devkit-vpc-{timestamp}` (CIDR 192.168.0.0/16), Subnet=`devkit-subnet-{timestamp}` (CIDR 192.168.0.0/24, gateway 192.168.0.1), Security Group=`devkit-secgroup-{timestamp}`.

See [Network Configuration, Architecture Selection & ECS Creation](references/ecs-creation.md).

---

## Step 4: Detect Existing ECS or Select Flavor/OS & Resolve Credentials

### Step 4.1: Detect Existing ECS (MANDATORY — must execute BEFORE Step 4.2)

Detect existing ECS by `devkit-ecs-*` prefix using `hcloud ECS ListCloudServers --cli-region=${HUAWEI_REGION}`. **This detection MUST be performed BEFORE any flavor/OS selection. NEVER skip this sub-step.**

- **If 1 or more found**: list all existing `devkit-ecs-*` ECS (name, IP, status, flavor) → ask user to choose: **reuse an existing ECS** or **create new**
  - **If user chooses reuse**: user selects which ECS → record its EIP and SSH credentials → **SKIP Steps 5 and 6** (no need to create ECS or install DevKit) → proceed directly to **Step 7** (Configure nodes.conf & Pre-Scan Verification)
  - **If user chooses create new**: proceed to Step 4.2
- **If none found**: proceed to Step 4.2

> **🔴 HARD RULE**: NEVER proceed to Step 4.2 (flavor/OS selection) without first executing Step 4.1 (detect existing ECS). NEVER create a new ECS without first asking the user whether to reuse an existing one.

### Step 4.2: Select Flavor, OS & Resolve Credentials (only when creating new ECS)

Architecture is **fixed to x86_64** (no ARM/aarch64). User must select flavor from available 4U8G flavors in **ac/C/S/T/X series only** and choose OS (CentOS 7.6 / Ubuntu 20.04). **Flavor selection rule**: query `hcloud ECS ListFlavors --cli-region=${HUAWEI_REGION} --availability_zone=${AZ} --limit=2000` (⚠️ **limit MUST be ≥2000** — some AZs have 700+ flavors; `--limit=500` will miss 4U8G flavors), filter `vcpus=4` (⚠️ **API returns `vcpus` as string** — always use `int()` conversion before comparison) and `ram=8192`, **ONLY include** flavor id matching `^ac`/`^c`/`^s`/`^t`/`^x` (exclude all other series). **Recommendation rule**: present ≥1 flavor from each available series (ac, C, S, T, X) as options. **Image selection rule (ECS Nova API)**: query images via ECS Nova API `GET https://ecs.{region}.myhuaweicloud.com/v2.1/{project_id}/images/detail` (NOT `hcloud IMS ListImages`), then filter in Python: ① **architecture check** `metadata.HW_ARCH == "x86_64"` (skip non-x86_64), ② **GPU keyword exclusion** skip images with name containing `gpu`/`with cuda`/`with tesla`/`with graphic`/`vroce`, ③ **bare metal/ARM exclusion** skip names containing `baremetal`/`bms`/`arm`/`aarch64`/`kunpeng`/`ai`/`with uniagent`, ④ **name match** image name contains OS pattern (`CentOS 7.6 64bit` or `Ubuntu 20.04 server 64bit`), ⑤ **public image preference** prefer `metadata.__image_type == "gold"`. **Only these 2 OS options are valid — NEVER offer other OS options.** Instance name is **auto-generated** as `devkit-ecs-{timestamp}` (NOT user-selected, NOT recommended by AI). **No defaults.** **All parameters (flavor, OS) MUST be confirmed by user before proceeding.** Credentials come **ONLY** from `DEVKIT_ECS_USER` / `DEVKIT_ECS_PASSWORD` env vars — **user must confirm these are correct before use.** **NEVER** call `hcloud ECS BatchResetServersPassword`.

See [Network Configuration, Architecture Selection & ECS Creation](references/ecs-creation.md).

---

## Step 5: Create ECS and Bind EIP

> **Prerequisite**: Step 4.1 detection must have determined that a new ECS is needed (either no existing `devkit-ecs-*` ECS found, or user explicitly chose "create new"). If user chose "reuse existing" in Step 4.1, this step is **SKIPPED** — proceed directly to Step 7.

**Before ECS creation, present ALL parameters (instance name, flavor, OS, VPC, subnet, security group, adminPass source) to user for explicit confirmation.** **NEVER reuse without user consent.** `DEVKIT_ECS_EIP` obtained **ONLY** by querying hcloud. Fixed creation params: root volume=GPSSD 40GB, EIP bandwidth=300Mbit/s (chargemode=traffic, sharetype=PER, iptype=5_bgp).

> **🔴 AUTO-PROCEED RULE**: Once ECS creation succeeds and status is `ACTIVE`, **AUTOMATICALLY** proceed to Step 6 — verify SSH login, upload scripts, and execute install_devkit.sh (DevKit + Maven). Do NOT wait for user confirmation. Step 6 is a mandatory continuous flow triggered by Step 5 success.

See [Network Configuration, Architecture Selection & ECS Creation](references/ecs-creation.md).

---

## Step 6: Verify Login, Upload Scripts & Install (DevKit + Maven)

> **🔴 AUTO-TRIGGERED**: This step is **automatically triggered** by Step 5 success (ECS created & ACTIVE). No user confirmation is required. Execute all 3 sub-steps as a continuous flow: verify SSH login → upload 3 shell scripts → execute install_devkit.sh (DevKit + Maven).

See [DevKit Operations Workflow](references/devkit-operations-workflow.md).

---

## Step 7: Configure nodes.conf & Pre-Scan Verification

> **🔴 MANDATORY after Step 6**: Once DevKit + Maven installation completes, the AI MUST prompt the user to configure `nodes.conf` for remote scan targets. This step is required before any scan can be executed.

### 7.1 Configure nodes.conf

AI prompts user to configure `nodes.conf` with target server IPs, SSH credentials, and scan directories. See [DevKit Operations Workflow](references/devkit-operations-workflow.md).

### 7.2 Password Encryption

AI runs `encrypt-nodes-verify.sh --check` to detect plaintext passwords in `nodes.conf`. If plaintext found, encrypts them using `sys-mig -ec`. See [DevKit Operations Workflow](references/devkit-operations-workflow.md).

### 7.3 SSH Verification

AI verifies SSH connectivity to all target servers. If any host fails, scan is aborted. See [DevKit Operations Workflow](references/devkit-operations-workflow.md).

### 7.4 Direct Scan Path (User requests scan without prior configuration)

If the user directly requests a scan (skipping Step 7.1-7.3), the AI MUST perform the pre-scan mandatory check flow (nodes.conf exists → password encryption check → SSH verification → scan).

See [DevKit Operations Workflow](references/devkit-operations-workflow.md) for detailed Step 7 configuration, encryption, and verification procedures.

---

## Step 8: Scan

Execute scan. Scan targets read from nodes.conf. **Before executing any scan command, AI MUST present all scan parameters (scan mode, scan path, report path, log level) to user for explicit confirmation. NO defaults. NO execution without user approval.**

> **Scan Trigger**: Scanning can begin once Step 7 (nodes.conf configuration + encryption + SSH verification) is complete. The user may explicitly request a scan, or scanning can proceed after Step 7 passes.

- **stmt/sbom interactive selection**: Option 1 = default remote scan (`-mn all`); Option 2 = command-line local scan.
- **mvn_analyse/container_mig interactive selection**: Only command-line scan is provided.
- **mvn_analyse prerequisite flow (MANDATORY)**: Before executing mvn_analyse scan, AI MUST first: ① check DevKit server Maven installation (if not installed, call `install_devkit.sh --check-maven` i.e. `check_and_install_maven` function for environment detection and installation) → ② ask user whether Maven repository exists on DevKit server (if not, prompt user to prepare first) → ③ proceed to scan command input. See `references/devkit-operations-guide.md` → "mvn_analyse Command-Line Scan".
- **Command-line scan flow**: AI displays command template (code block) and parameter description (md table) in chat, then prompts user to input complete scan command, and executes scan after user input.
- **Report naming format**: `<scan_mode>_<target_server_IP>_<timestamp>`, report path `${DEVKIT_HOME}/report/`.

> **🔴 Scan Type Selection Rule (MANDATORY, zero exceptions)**: When AI uses the `question` tool to let user select scan type, it **MUST and ONLY** provide the following 6 options, **NEVER** use inaccurate descriptions like "source migration remote scan" or "source migration local scan":
>
> | Option Label | Description | Requires nodes.conf |
> |-------------|-------------|---------------------|
> | `stmt remote scan` | Scan system configuration statements of remote target servers | ✅ Yes |
> | `stmt local scan` | Scan system configuration statements of DevKit ECS local machine | ❌ No |
> | `sbom remote scan` | Scan software package dependencies of remote target servers | ✅ Yes |
> | `sbom local scan` | Scan software package dependencies of DevKit ECS local machine | ❌ No |
> | `mvn_analyse (Maven source migration analysis)` | Analyze Maven project pom.xml dependency Kunpeng compatibility, **local only** | ❌ No |
> | `container_mig (container image migration)` | Migrate x86 container images to ARM-compatible architecture, **local only** | ❌ No |
>
> - **NEVER** provide "source migration remote scan" option (mvn_analyse does not support remote scan)
> - **NEVER** provide "source migration local scan" option (inaccurate description, should be mvn_analyse or container_mig)
> - After user selection, execute corresponding command-line scan flow

> **🔴 Command-Line Scan Input Rule (MANDATORY, zero exceptions)**: AI MUST use the `question` tool (`options: []`) to let user input complete scan command in a **single input box**. **NEVER** provide preset command options, **NEVER** use multiple input boxes to collect parameters separately. See `references/devkit-operations-guide.md` → "Command-Line Scan Templates & Input Rules" for detailed templates and input rules.

> **🔴 Post-Scan Follow-up Suggestion Rule (MANDATORY)**: After mvn_analyse and container_mig scan completion and report download, AI **MUST** display corresponding mode's follow-up suggestions in chat. See `references/devkit-operations-guide.md` → "Scan Mode Details" for each mode's "Post-Scan Follow-up Suggestions".

See [DevKit Operations Workflow](references/devkit-operations-workflow.md).

---

## Step 9: Download Reports

> **🔴 MANDATORY after scan success**: After scan succeeds and report directory renaming completes, AI **MUST** ask user to provide local download path (**no default value, must be explicitly provided by user**), then download reports to local via SFTP.

See [DevKit Operations Workflow](references/devkit-operations-workflow.md).

---

## Troubleshooting: hcloud JSON Parsing

When inline Python parsing of hcloud output raises `JSONDecodeError` or `Traceback`, the root cause is typically non-JSON content mixed into the output stream. Follow these steps to resolve:

1. **Add `--cli-output=json`** parameter to the hcloud command to request pure JSON output.
2. **Suppress stderr warnings** by appending `2>/dev/null` to the pipeline, preventing warning lines from contaminating the JSON stream.
3. **Extract JSON segment** if prefix content persists: use `sed -n '/^{/,$p'` to extract from the first `{` to end of output before parsing.
4. **Inspect raw output first**: run the hcloud command standalone to confirm the JSON structure before writing parsing logic.
5. **Avoid direct `json.load(sys.stdin)`**: instead use `raw = sys.stdin.read().strip()` and manually locate the JSON boundaries, which is more resilient to leading/trailing non-JSON content.

---

## Troubleshooting: Duplicate ECS from Retried CreateServers

### Q: Duplicate DevKit ECS Created with Same Name

**Cause**: `CreateServers` parsing failed and was retried, but the create command is non-idempotent — each call creates a new instance.

**Solution**:

1. **Query all instances by name**:
   ```bash
   hcloud ECS ListServersDetails --name devkit-ecs-xxx --cli-region=${HUAWEI_REGION} --cli-output=json
   ```
2. **Keep one instance, delete extras**:
   ```bash
   hcloud ECS DeleteServers --server_ids <duplicate-id-1> --cli-region=${HUAWEI_REGION}
   ```
   Choose one instance to keep (preferably the one with `ACTIVE` status and a bound EIP) and delete the rest.
3. **Release orphaned EIPs**: List all EIPs, find unbound ones (no `vnic.port_id`), and release them:
   ```bash
   hcloud EIP ListPublicIps --cli-region=${HUAWEI_REGION} --cli-output=json
   # Identify EIPs where vnic.port_id is empty, then release:
   hcloud EIP DeletePublicIp --publicip_id <orphan-eip-id> --cli-region=${HUAWEI_REGION}
   ```
4. **Proceed with kept instance ID**: Record the kept instance ID and proceed to Step 6 (Login, Upload & Install).

> **Prevention**: Always follow the [Safe Resource Creation Pattern](#safe-resource-creation-pattern-all-create-commands) — output to file, parse from file, and query by name on parse failure. NEVER re-run create commands.

---

## References

- [CLI Installation & hcloud Setup](references/cli-installation-guide.md)
- [Network Configuration, Architecture Selection & ECS Creation](references/ecs-creation.md)
- [Security Rules](references/rules.md)
- [DevKit Operations Guide](references/devkit-operations-guide.md)
- [DevKit Operations Workflow](references/devkit-operations-workflow.md)
- [Acceptance Criteria](references/acceptance-criteria.md)
- [IAM Permission Policies](references/iam-policies.md)
- [Verification Methods](references/verification-method.md)
- [Prerequisites](references/prerequisites.md)
- [Troubleshooting](references/troubleshooting.md)
