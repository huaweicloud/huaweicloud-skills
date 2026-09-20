# Acceptance Criteria

## Overview

This document defines the acceptance criteria for the huawei-cloud-devkit-application-check-cli skill, used to determine whether the full Kunpeng application migration assessment workflow has succeeded.

## Functional Acceptance Criteria

### 1. hcloud Environment Check

| Acceptance Item | Criteria | Verification Method |
|-----------------|----------|---------------------|
| hcloud installed | Version ≥ 7.2.2 | Run `hcloud version` |
| AK/SK configured | Cloud resources queryable | Run `hcloud ECS ListCloudServers` |
| Region selected | One of cn-north-4 / cn-east-3 / cn-south-1 / cn-southwest-2 | Check user selection record |
| No default region | No caching, no reuse of last selection | Each session requires user to select |

### 2. Network Configuration

| Acceptance Item | Criteria | Verification Method |
|-----------------|----------|---------------------|
| VPC created | Name matches `devkit-vpc-*` prefix | Query VPC list |
| Subnet created | Name matches `devkit-subnet-*` prefix, associated with correct VPC | Query subnet list |
| Security group created | Name matches `devkit-secgroup-*` prefix | Query security group list |
| Reuse requires confirmation | Must ask user when existing resources detected | Check interaction records |

### 3. ECS Instance Creation & EIP Binding

| Acceptance Item | Criteria | Verification Method |
|-----------------|----------|---------------------|
| Instance status | ACTIVE | Query ECS status |
| Instance name | Matches `devkit-ecs-*` prefix | Query instance details |
| Architecture correct | x86_64 (fixed) | Run `uname -m` |
| Flavor correct | 4U8G ac/C/S/T/X series flavor (matches user selection) | Query instance flavor |
| OS image correct | CentOS 7.6 or Ubuntu 20.04 (x86_64, non-GPU) | Query via ECS Nova API, verify `HW_ARCH == "x86_64"` and no GPU keywords in name |
| EIP bound | Has public IP and is reachable | Query EIP status + ping test |
| adminPass source | Only from `DEVKIT_ECS_PASSWORD` environment variable | Check creation command |
| No password reset called | `BatchResetServersPassword` not executed | Check operation logs |

### 4. SSH Login & Script Upload

| Acceptance Item | Criteria | Verification Method |
|-----------------|----------|---------------------|
| SSH login succeeds | Can execute remote commands | `ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "uname -m"` |
| Credential source | Only from User→Machine level environment variables | Check env var detection records |
| install_devkit.sh uploaded | Exists at `${DEVKIT_HOME}/install_devkit.sh` | Remote file check |
| scan_devkit.sh uploaded | Exists at `${DEVKIT_HOME}/scan_devkit.sh` | Remote file check |
| encrypt-nodes-verify.sh uploaded | Exists at `${DEVKIT_HOME}/encrypt-nodes-verify.sh` | Remote file check |
| Auto-proceed to Step 6 | After ECS ACTIVE, login verification starts without user confirmation | Check workflow continuity |

### 5. DevKit & Maven Installation

| Acceptance Item | Criteria | Verification Method |
|-----------------|----------|---------------------|
| DevKit installed | `devkit version` returns version number | Remote execute `devkit version` |
| DevKit install path | `${DEVKIT_HOME}/DevKit/DevKit-Sys-Mig-CLI-26.1.RC1-Linux-*` | Remote directory check |
| Architecture auto-detected | x86_64 → x86-64 package | Check install logs |
| Maven installed | `mvn -v` returns 3.8.x version | Remote execute `mvn -v` |
| Maven version | 3.8.8 | Check `mvn -v` output |
| JDK installed | `java -version` is executable | Remote execute `java -version` |

### 6. nodes.conf Configuration & Password Encryption

| Acceptance Item | Criteria | Verification Method |
|-----------------|----------|---------------------|
| nodes.conf configured | Contains at least 1 target host entry | Remote file content check (`--mask` mode) |
| Passwords encrypted | `ssh_pass` values match Base64 pattern (length ≥ 20) | Run `encrypt-nodes-verify.sh --check` outputs `ALL_ENCRYPTED` |
| SSH connectivity verified | All target servers SSH reachable | Check `encrypt-nodes-verify.sh` verification results |
| Plaintext passwords replaced | No plaintext `ssh_pass` in nodes.conf | Run `encrypt-nodes-verify.sh --check` |
| Safe display | nodes.conf content in chat shows `ssh_pass` as `***` | Run `encrypt-nodes-verify.sh --mask` check output |

### 7. Scan Execution

| Acceptance Item | Criteria | Verification Method |
|-----------------|----------|---------------------|
| Pre-scan password check | `--check` or `encrypt-nodes-verify.sh` executed | Check `scan_devkit.sh` logs |
| stmt scan | Generates CSV report | Check stmt report under `${DEVKIT_HOME}/report/` |
| sbom scan | Generates HTML/JSON report | Check sbom report under `${DEVKIT_HOME}/report/` |
| mvn_analyse scan | Generates HTML report | Check mvn_analyse report under `${DEVKIT_HOME}/report/` |
| container_mig scan | Generates HTML/JSON report | Check container_mig report under `${DEVKIT_HOME}/report/` |
| Report naming convention | `<scan_mode>_<nodes_IP>_<timestamp>` format | Check report directory names |
| Scan targets correct | Targets from nodes.conf IPs, not DevKit server | Check scan command parameters |

### 8. Report Download

| Acceptance Item | Criteria | Verification Method |
|-----------------|----------|---------------------|
| Reports downloaded | Local directory contains report files | Check local file list |
| Directory structure preserved | Remote directory structure matches locally | Compare remote and local file paths |
| User-provided path | Local save path provided by user, no default | Check interaction records |


## Security Acceptance Criteria

| Acceptance Item | Criteria | Verification Method |
|-----------------|----------|---------------------|
| AK/SK not exposed in plaintext | AK/SK shown as `***` or placeholder in chat | Check chat output |
| DEVKIT_ECS_PASSWORD not exposed in plaintext | Password shown as `***` or `<your_password>` in chat | Check chat output |
| nodes.conf ssh_pass not exposed in plaintext | ssh_pass shown as `***` or `<encrypted_password>` in chat | Check chat output |
| No hardcoded credentials | No plaintext AK/SK/password values in code/commands | Code review |
| EIP source compliant | Only from hcloud queries, not environment variables | Check EIP resolution logic |
| No password reset API called | `BatchResetServersPassword` not executed | Check operation logs |
| paramiko does not connect to target servers | paramiko only connects to DevKit server | Check SSH connection targets |
| Pre-scan passwords encrypted | No plaintext passwords in nodes.conf during scan | Run `encrypt-nodes-verify.sh --check` |

## Acceptance Test Cases

### Test Case 1: Full Workflow (x86_64 Architecture)

**Preconditions**:
- Valid AK/SK (set via environment variables `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`)
- `DEVKIT_ECS_USER` and `DEVKIT_ECS_PASSWORD` environment variables set (User→Machine level)
- Target servers reachable with correct SSH credentials

**Steps**:

✅ **Correct Example**:
```bash
# 1. hcloud environment check
hcloud version

# 2. Select region (user selects cn-north-4)
# 3. Network configuration (auto-detect/create VPC+subnet+security group)
# 4. Architecture fixed x86_64, select flavor from available 4U8G ac/C/S/T/X series flavors, OS CentOS 7.6

# 5. Create ECS + EIP (auto-proceed to Step 6)
hcloud ECS CreateServers --cli-region=${HUAWEI_REGION} \
  --server.name=devkit-ecs-{timestamp} \
  --server.flavorRef=${FLAVOR_ID} \
  --server.imageRef=${IMAGE_ID} \
  --server.adminPass=${DEVKIT_ECS_PASSWORD} \
  ...

# 6. Auto: SSH login verification → upload scripts → install DevKit + Maven
py scripts/devkit_remote.py --region ${HUAWEI_REGION} login
py scripts/devkit_remote.py --region ${HUAWEI_REGION} install

# 7. Configure nodes.conf → encrypt passwords → verify SSH
py scripts/devkit_remote.py --region ${HUAWEI_REGION} encrypt-verify

# 8. Scan
py scripts/devkit_remote.py --region ${HUAWEI_REGION} scan stmt

# 9. Download reports
py scripts/devkit_remote.py --region ${HUAWEI_REGION} download-report --local-dir /home/user/reports
```

**Expected Results**:
- All functional acceptance items pass
- All 4 scan modes generate reports
- Reports downloaded to local specified directory

### Test Case 2: Password Encryption Detection & Auto-Replacement

**Preconditions**:
- DevKit installed
- nodes.conf contains plaintext `ssh_pass` values

**Steps**:

✅ **Correct Example**:
```bash
# Detect plaintext passwords
py scripts/devkit_remote.py --region ${HUAWEI_REGION} encrypt-verify --check
# Expected output: PLAINTEXT_FOUND: <count>

# Execute encryption replacement + SSH verification
py scripts/devkit_remote.py --region ${HUAWEI_REGION} encrypt-verify
# Expected: plaintext passwords encrypted and replaced, SSH verification passes

# Check again
py scripts/devkit_remote.py --region ${HUAWEI_REGION} encrypt-verify --check
# Expected output: ALL_ENCRYPTED
```

**Expected Results**:
- `--check` correctly detects plaintext passwords
- After encryption, `ssh_pass` values in nodes.conf are in Base64 format
- Second `--check` outputs `ALL_ENCRYPTED`

### Test Case 3: Direct Scan with Already-Encrypted Passwords

**Preconditions**:
- DevKit installed
- All `ssh_pass` in nodes.conf are already encrypted

**Steps**:

✅ **Correct Example**:
```bash
# Check password status
py scripts/devkit_remote.py --region ${HUAWEI_REGION} encrypt-verify --check
# Expected output: ALL_ENCRYPTED

# Direct scan (skip encryption step)
py scripts/devkit_remote.py --region ${HUAWEI_REGION} scan stmt
```

**Expected Results**:
- `--check` outputs `ALL_ENCRYPTED`
- `scan_devkit.sh` skips encryption step, directly executes scan
- Scan reports generated successfully

### Test Case 4: Safe Display of nodes.conf

**Preconditions**:
- DevKit installed
- nodes.conf configured

**Steps**:

✅ **Correct Example**:
```bash
# Safe display (passwords masked)
py scripts/devkit_remote.py --region ${HUAWEI_REGION} encrypt-verify --mask
# Expected: all ssh_pass values shown as ***
```

❌ **Incorrect Example**:
```bash
# Do NOT cat nodes.conf directly to chat
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "cat /path/to/nodes.conf"
# Plaintext passwords would be exposed
```

**Expected Results**:
- `--mask` mode output shows all `ssh_pass` values as `***`
- No plaintext passwords appear in chat

### Test Case 5: SSH Authentication Failure Handling

**Preconditions**:
- `DEVKIT_ECS_PASSWORD` environment variable has wrong value

**Steps**:

❌ **Incorrect Example**:
```bash
# SSH login fails
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "uname -m"
# Expected: Authentication failed
```

**Expected Results**:
- Auto re-detects `DEVKIT_ECS_USER` / `DEVKIT_ECS_PASSWORD` (User→Machine level)
- If new values detected, retries SSH
- If still fails, prompts user to update environment variables
- `BatchResetServersPassword` not called
- Error messages contain no plaintext passwords

### Test Case 6: Auto-Install After ECS Creation

**Preconditions**:
- Network configuration completed
- Architecture/flavor/OS selected
- Credentials resolved

**Steps**:

✅ **Correct Example**:
```bash
# After ECS creation, without user confirmation, proceed:
# 1. SSH login verification
# 2. Upload 3 scripts to ${DEVKIT_HOME}/
# 3. Execute install_devkit.sh (DevKit + Maven)
```

**Expected Results**:
- Auto-proceeds from Step 5 to Step 6
- No additional user confirmation required
- DevKit and Maven installed successfully

## Acceptance Report Template

```markdown
# Acceptance Report

## Basic Information
- Skill Name: huawei-cloud-devkit-application-check-cli
- Test Time: 2026-08-12 10:00:00
- Tester: TestUser
- Architecture: x86_64
- Region: cn-north-4

## Acceptance Results
| Item | Result | Notes |
|------|--------|-------|
| hcloud Environment | PASS | |
| Network Configuration | PASS | |
| ECS Creation & EIP Binding | PASS | |
| SSH Login & Script Upload | PASS | |
| DevKit Installation | PASS | |
| Maven Installation | PASS | |
| nodes.conf Configuration | PASS | |
| Password Encryption | PASS | |
| Scan Execution | PASS | |
| Report Download | PASS | |
| Security Check | PASS | |

## Summary
- Passed: 11 items
- Failed: 0 items
- Conclusion: PASSED
```
