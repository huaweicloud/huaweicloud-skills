# DevKit Operations Guide (SSH / Commands / Templates / Scripts)

> This document is the DevKit operations guide, containing SSH connection architecture, scan command templates, parameter descriptions, and script usage.
> For workflow steps, see [DevKit Operations Workflow](devkit-operations-workflow.md).

---

## Two-Layer SSH Connection Architecture

All remote operations follow a strict two-layer SSH model. See [Security Rules](rules.md#two-layer-ssh-architecture) for the complete architecture definition.

> **?? FORBIDDEN**: `paramiko` MUST NEVER connect to nodes.conf target servers. Only the DevKit server has connectivity to targets. All target-server SSH operations are delegated to shell scripts running ON the DevKit server.

---

## SSH Connection Guide

### Layer 1: Agent ? DevKit ECS (paramiko)

**Tool**: Python paramiko (`devkit_remote.py`)
**Credential Source**: `DEVKIT_ECS_USER` + `DEVKIT_ECS_PASSWORD` environment variables (User ? Machine level)
**EIP Source**: Automatically obtained via hcloud query

```
Agent (local machine)
    ?
    ?  paramiko SSHClient.connect(
    ?      hostname=DEVKIT_ECS_EIP,
    ?      username=DEVKIT_ECS_USER,
    ?      password=${DEVKIT_ECS_PASSWORD}
    ?  )
    ?
    ?
DevKit ECS (public EIP)
```

**Connection Flow**:
1. Query DevKit ECS EIP from hcloud
2. Read `DEVKIT_ECS_USER` and `DEVKIT_ECS_PASSWORD` from environment variables
3. paramiko establishes SSH connection (password stays in Python process memory, never appears in `ps -ef`)
4. Upload scripts via SFTP
5. Execute remote commands via SSH exec_command

**Authentication Failure Handling**:
- Re-detect environment variables (User ? Machine level)
- If new values found ? retry with new values
- If no new values ? prompt user to update environment variables, STOP
- **FORBIDDEN** `hcloud ECS BatchResetServersPassword`

### Layer 2: DevKit ECS ? nodes.conf Targets (sshpass/ssh)

**Tool**: Shell `sshpass` + `ssh` (executed on DevKit ECS)
**Credential Source**: Encrypted `ssh_pass` in `nodes.conf`
**Execution Method**: `encrypt-nodes-verify.sh` runs on DevKit ECS

```
DevKit ECS
    ?
    ?  SSHPASS=<decrypted_password> sshpass -e ssh \
    ?      -o StrictHostKeyChecking=no \
    ?      user@target_ip "echo OK"
    ?
    ?
Target Server (defined in nodes.conf)
```

**Connection Flow**:
1. `encrypt-nodes-verify.sh` reads `nodes.conf`
2. Check whether `ssh_pass` is already encrypted
3. If encrypted ? use `sshpass -e` (environment variable) to verify SSH
4. If plaintext ? encrypt and replace first, then verify
5. Verification results are recorded to `/tmp/devkit_nodes_verified_hosts`

**Security Constraints**:
- **FORBIDDEN** `sshpass -p` (password appears in `ps -ef`) ? use `sshpass -e` (environment variable)
- **FORBIDDEN** paramiko connecting to nodes.conf target servers
- **FORBIDDEN** directly SSH from Agent local machine to nodes.conf target servers

### SSH Connection Verification Commands

**Layer 1 Verification** (Agent ? DevKit ECS):
```bash
# Via devkit_remote.py
py scripts/devkit_remote.py --region ${HUAWEI_REGION} check

# Or direct SSH
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "uname -m"
```

**Layer 2 Verification** (DevKit ECS ? targets):
```bash
# Execute on DevKit ECS
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "bash ${DEVKIT_HOME}/encrypt-nodes-verify.sh"

# Check encryption status (user must explicitly run encryption if plaintext found)
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "bash ${DEVKIT_HOME}/encrypt-nodes-verify.sh --check"

# Display nodes.conf (password masked)
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "bash ${DEVKIT_HOME}/encrypt-nodes-verify.sh --mask"
```

---

## Fixed Scan Commands

| Mode | Command | Report | Description |
|------|---------|--------|-------------|
| stmt | `devkit sys-mig -c stmt -mn all -o ${DEVKIT_HOME}/report -l 1` | CSV | Inventory information collection |
| sbom | `devkit sys-mig -c sbom -mn all -o ${DEVKIT_HOME}/report -l 1` | HTML/JSON | System component information collection |
| mvn_analyse | `devkit sys-mig -c mvn_analyse -d <pom_path> -o <report_path>` | HTML | Maven project source code migration analysis |
| container_mig | `devkit sys-mig -c container_mig --image <image_path> --dockerfile <Dockerfile_path> -o <report_path> -l 0` | HTML/JSON | Container image migration |

---

## Command-Line Scan Templates & Input Rules

> **?? Command-Line Scan Chat Display Rule**: When the user selects stmt/sbom command-line scan or executes mvn_analyse/container_mig, the AI MUST display the template and parameter description for the corresponding mode in the chat, then wait for the user to input the scan command.

### stmt Command-Line Scan

```
Please fill in parameters according to the template:
  devkit sys-mig -c stmt -d <scan_path> -src <scan_path> -o <report_path> -l <log_level>
```

**Parameter Description:**

| Parameter | Description |
|------|------|
| `-c/--command` | Required parameter. Collects inventory information, can generate CSV report |
| `-d/--directory` | Optional parameter. Input scan file directory, supports multiple directories separated by spaces |
| `-src/--source` | Optional parameter. Input source code directory, used to count source code lines. Supports multiple directories separated by spaces |
| `-o/--output` | Optional parameter. Report output directory, defaults to the report directory where the sys-mig binary is located |
| `-l/--log-level` | Optional parameter. Set log level, default is 1. 0=DEBUG, 1=INFO, 2=WARNING, 3=ERROR |

**?? stmt Input Method Rule (MANDATORY, zero exceptions)**: The AI MUST execute in the following order:
1. **First display the command template (code block) and parameter description (md table) above in the chat text**, so the user can see the complete parameter description
2. **Then use the `question` tool** to let the user directly input the complete scan command, **showing only 1 input box, with no selection options**. Specifically:
   - `header`: `"stmt scan command"`
   - `question`: `"Please input the complete stmt scan command"`
   - `options`: empty array `[]` (no selection options provided, user can only input the command via the custom input box)
   - **FORBIDDEN** to provide any options in `options` (such as example commands, common commands, recommended commands, etc.)
   - **FORBIDDEN** to use multiple `question` prompts or multiple input boxes to collect each parameter separately (e.g., `-d`, `-src`, `-o`, `-l` input separately)
   - The complete command MUST be input all at once in a **single input box**

### sbom Command-Line Scan

```
Please fill in parameters according to the template:
  devkit sys-mig -c sbom -d <scan_path> -o <report_path> -l <log_level>
```

**Parameter Description:**

| Parameter | Description |
|------|------|
| `-c/--command` | Required parameter. Collects component information, can generate HTML or JSON report |
| `-d/--directory` | Optional parameter. Input scan file directory, supports multiple directories separated by spaces |
| `-o/--output` | Optional parameter. Report output directory, defaults to the report directory where the sys-mig binary is located |
| `-l/--log-level` | Optional parameter. Set log level, default is 1. 0=DEBUG, 1=INFO, 2=WARNING, 3=ERROR |

**?? sbom Input Method Rule (MANDATORY, zero exceptions)**: The AI MUST execute in the following order:
1. **First display the command template (code block) and parameter description (md table) above in the chat text**, so the user can see the complete parameter description
2. **Then use the `question` tool** to let the user directly input the complete scan command, **showing only 1 input box, with no selection options**. Specifically:
   - `header`: `"sbom scan command"`
   - `question`: `"Please input the complete sbom scan command"`
   - `options`: empty array `[]` (no selection options provided, user can only input the command via the custom input box)
   - **FORBIDDEN** to provide any options in `options`
   - **FORBIDDEN** to use multiple `question` prompts or multiple input boxes to collect each parameter separately
   - The complete command MUST be input all at once in a **single input box**

### mvn_analyse Command-Line Scan

**?? mvn_analyse Scan Pre-Flow (MANDATORY, zero exceptions)**: Before displaying the scan template, the AI MUST execute the following pre-checks in order:

**Step 1: Check DevKit Server Maven Installation Status**

The AI executes `source /etc/profile && mvn -v` on the DevKit server via SSH:
- **Installed** ? outputs version number, proceed to Step 2
- **Not installed** ? The AI invokes the `check_and_install_maven` function in `install_devkit.sh` via SSH to detect and install the Maven environment:
  - Execute command: `bash ${DEVKIT_HOME}/install_devkit.sh --check-maven`
  - This command invokes the `check_and_install_maven` function, which auto-detects and installs JDK + Maven
  - After installation, verify again with `source /etc/profile && mvn -v`; if still fails, report error and terminate
  - Installation successful ? outputs version number, proceed to Step 2

**Step 2: Ask User Whether Maven Repository Exists**

The AI uses the `question` tool to ask the user:
- `header`: `"Maven Repository"`
- `question`: `"Does a Maven repository exist on the DevKit server? (Path: ${MAVEN_HOME}/conf/settings.xml)"`
- `options`:
  - `"Exists, scan directly"`: skip, proceed directly to scan command input
  - `"Does not exist"`: The AI prompts the user to prepare the Maven repository before continuing the scan

**Step 3: Scan Command Input and Execution**

```
Please fill in parameters according to the template:
  devkit sys-mig -c mvn_analyse -d <pom_path> -o <report_path> -l <log_level>
```

**Parameter Description:**

| Parameter | Description |
|------|------|
| `-c/--command` | Required parameter. Maven project source code migration analysis, can generate HTML report |
| `-d/--directory` | Optional parameter. Input pom.xml scan file directory, supports multiple directories separated by spaces |
| `-o/--output` | Optional parameter. Report output directory, defaults to the report directory where the sys-mig binary is located |
| `-l/--log-level` | Optional parameter. Set log level, default is 1. 0=DEBUG, 1=INFO, 2=WARNING, 3=ERROR |

**?? mvn_analyse Input Method Rule (MANDATORY, zero exceptions)**: The AI MUST execute in the following order:
1. **First display the command template (code block) and parameter description (md table) above in the chat text**
2. **Then use the `question` tool** to let the user directly input the complete scan command, **showing only 1 input box, with no selection options**
   - `header`: `"mvn_analyse scan command"`
   - `question`: `"Please input the complete mvn_analyse scan command"`
   - `options`: empty array `[]`
   - **FORBIDDEN** to provide any options in `options`
   - **FORBIDDEN** to use multiple input boxes to collect each parameter separately
   - The complete command MUST be input all at once in a **single input box**

### container_mig Command-Line Scan

```
Please fill in parameters according to the template:
  devkit sys-mig -c container_mig --image <image_path> --dockerfile <Dockerfile_path> -o <report_path> -l <log_level>
```

**Parameter Description:**

| Parameter | Description |
|------|------|
| `-c/--command` | Required parameter. Container image migration, can generate Dockerfile, build dependency resource files, and HTML and JSON reports |
| `--image` | Required parameter. Input the x86 image package to be migrated, which can be exported via docker save |
| `--dockerfile` | Optional parameter. Input the Dockerfile used when building the image |
| `-o/--output` | Optional parameter. Report output directory, defaults to the report directory where the sys-mig binary is located |
| `-l/--log-level` | Optional parameter. Set log level, default is 1. 0=DEBUG, 1=INFO, 2=WARNING, 3=ERROR |

**?? container_mig Input Method Rule (MANDATORY, zero exceptions)**: The AI MUST execute in the following order:
1. **First display the command template (code block) and parameter description (md table) above in the chat text**
2. **Then use the `question` tool** to let the user directly input the complete scan command, **showing only 1 input box, with no selection options**
   - `header`: `"container_mig scan command"`
   - `question`: `"Please input the complete container_mig scan command"`
   - `options`: empty array `[]`
   - **FORBIDDEN** to provide any options in `options`
   - **FORBIDDEN** to use multiple input boxes to collect each parameter separately
   - The complete command MUST be input all at once in a **single input box**

> After the user inputs the scan command, the AI passes the command to the DevKit server via SSH for execution.

---

## Scan Mode Details

### stmt ? Inventory Information Collection

Script prompt selection:
- **Option 1 (default scan)**: Remote scan ? configure nodes.conf ? check target servers ? encrypt & verify ? `devkit sys-mig -c stmt -mn all -o ${DEVKIT_HOME}/report -l 1`
- **Option 2 (command-line scan)**: Local scan, the AI displays the template and parameter description in the chat, prompts the user to input the complete scan command, and executes after confirmation

Report: `stmt.csv` (Chinese), `stmt_en.csv` (English), naming format `stmt_<target_server_IP>_<timestamp>`

### sbom ? System Component Information Collection

Script prompt selection:
- **Option 1 (default scan)**: Remote scan ? configure nodes.conf ? check target servers ? encrypt & verify ? `devkit sys-mig -c sbom -mn all -o ${DEVKIT_HOME}/report -l 1`
- **Option 2 (command-line scan)**: Local scan, the AI displays the template and parameter description in the chat, prompts the user to input the complete scan command, and executes after confirmation

Report: `sbom.html`, naming format `sbom_<target_server_IP>_<timestamp>`

### mvn_analyse ? Maven Project Source Code Migration Analysis (can only be executed standalone)

The script only provides the command-line scan option. When executing, the AI MUST first complete the pre-flow (Maven installation check + Maven repository configuration inquiry), then display the template and parameter description, prompt the user to input the complete scan command, and execute after confirmation.

**Pre-Flow (MANDATORY)**:
1. Check DevKit server Maven installation ? auto-install if not installed
2. Ask user whether a Maven repository exists on the DevKit server ? prompt user to prepare first if it does not exist
3. Proceed to scan command input, execute scan after user inputs the command

Report: `mvn_analyse.html`, naming format `mvn_analyse_<target_server_IP>_<timestamp>`

**?? Post-Scan Processing Suggestions (MANDATORY)**: After the mvn_analyse scan completes and the report is downloaded, the AI **MUST** display the following post-processing suggestions in the chat:

```
mvn_analyse scan post-processing suggestions:
  a: Review the assessment report, modify settings.xml according to the "processing suggestions", and configure the Huawei Kunpeng Maven repository
     Reference: https://mirrors.huaweicloud.com/mirrorDetail/5fbb71cd07bbb121c2aded7b?mirrorName=kunpeng_maven&catalog=arm
  b: Delete the corresponding locally downloaded software
     mvn dependency:purge-local-repository -DreResolve=false -DmanualInclude=<software> -f <pom_file_path>
  c: After processing is complete, re-scan
     devkit sys-mig -c mvn_analyse -d <pom_path> -o <report_path>
  d: Review the assessment report, confirm there are no more dependencies that need modification or replacement
```

### container_mig ? Container Image Migration (can only be executed standalone)

The script only provides the command-line scan option. The AI displays the template and parameter description in the chat, prompts the user to input the complete scan command, and executes after confirmation.

Report: `incompatible/` (files incompatible with Arm architecture), `output/` (files compatible with Arm architecture), naming format `container_mig_<target_server_IP>_<timestamp>`

**?? Post-Scan Processing Suggestions (MANDATORY)**: After the container_mig scan completes and the report is downloaded, the AI **MUST** display the following post-processing suggestions in the chat:

```
container_mig scan post-processing suggestions:
   1. According to the "processing suggestions" in the architecture-related dependency files, download the corresponding software packages or source code
   2. After replacing the dependency files, merge them into the output/ directory
   3. Use docker build to rebuild the Arm-architecture-compatible image
```

---

## Report Naming Convention

DevKit internally names reports using the **devkit internal IP** (e.g., `sys-mig_<devkit_internal_IP>_<timestamp>`). The `scan_devkit.sh` script automatically renames report directories and zip files to `<scan_mode>_<nodes_IP>_<timestamp>` format:

| Original (DevKit default) | Renamed (<scan_mode>_<nodes_IP>_<timestamp>) |
|---------------------------|-----------------------------------|
| `sys-mig_<devkit_internal_IP>_<timestamp>/` (contains stmt.csv) | `stmt_<nodes_IP>_<timestamp>/` |
| `sys-mig_<devkit_internal_IP>_<timestamp>.zip` (stmt) | `stmt_<nodes_IP>_<timestamp>.zip` |
| `sys-mig_<devkit_internal_IP>_<timestamp>_merged.zip` (sbom) | `sbom_<nodes_IP>_<timestamp>.zip` |
| `sys-mig_<devkit_internal_IP>_<timestamp>/` (contains sbom.html) | `sbom_<nodes_IP>_<timestamp>/` |

---

## Script Usage (devkit_remote.py)

```bash
py scripts/devkit_remote.py --region ${HUAWEI_REGION} login                    # Check SSH + upload scripts
py scripts/devkit_remote.py --region ${HUAWEI_REGION} install                  # Auto-detect arch, download & install DevKit
py scripts/devkit_remote.py --region ${HUAWEI_REGION} install --version 26.1.RC1  # Specify DevKit version
py scripts/devkit_remote.py --region ${HUAWEI_REGION} verify                   # Verify DevKit installation
py scripts/devkit_remote.py --region ${HUAWEI_REGION} encrypt-verify           # Encrypt nodes.conf passwords & verify SSH to targets

py scripts/devkit_remote.py --region ${HUAWEI_REGION} scan stmt                # Inventory information collection
py scripts/devkit_remote.py --region ${HUAWEI_REGION} scan sbom                # System component information collection
py scripts/devkit_remote.py --region ${HUAWEI_REGION} scan mvn_analyse         # Maven project source code migration analysis
py scripts/devkit_remote.py --region ${HUAWEI_REGION} scan container_mig       # Container image migration
py scripts/devkit_remote.py --region ${HUAWEI_REGION} download-report --local-dir <path>  # Download reports from last scan only (container_mig: key files only)
py scripts/devkit_remote.py --region ${HUAWEI_REGION} download-report --local-dir <path> --all  # Download ALL reports
py scripts/devkit_remote.py --region ${HUAWEI_REGION} download-report --local-dir <path> --full  # Download full container_mig report (including incompatible/ and output/)
```

---

## Related Documents

- [DevKit Operations Workflow](devkit-operations-workflow.md) ? Step 6-9 workflow
- [Security Rules](rules.md) ? SSH architecture and password management
- [Troubleshooting](troubleshooting.md) ? Common issues and solutions
