# Verification Methods

## Overview

This document describes how to verify that each step of the huawei-cloud-devkit-application-check-cli skill has been executed successfully.

## 1. hcloud Environment Verification

### Verification Method

✅ **Correct Example**:
```bash
# Check hcloud version (must be >= 7.2.2)
hcloud version

# Check AK/SK configured
hcloud ECS ListCloudServers --cli-region=cn-north-4
```

### Expected Results
- hcloud version ≥ 7.2.2
- Cloud resources can be queried without authentication errors
- AK/SK passed via environment variables `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`

## 2. Network Configuration Verification

### Verification Method

✅ **Correct Example**:
```bash
# Verify VPC
hcloud VPC ListVpcs --cli-region=${HUAWEI_REGION} --limit=500
# Filter: name matches devkit-vpc-*

# Verify Subnet
hcloud VPC ListSubnets --cli-region=${HUAWEI_REGION} --vpc_id=${VPC_ID} --limit=500
# Filter: name matches devkit-subnet-*

# Verify Security Group
hcloud VPC ListSecurityGroups --cli-region=${HUAWEI_REGION} --limit=500
# Filter: name matches devkit-secgroup-*
```

### Expected Results
- VPC name matches `devkit-vpc-*` prefix
- Subnet name matches `devkit-subnet-*` prefix and is associated with the correct VPC
- Security group name matches `devkit-secgroup-*` prefix
- Security group auto-adds ICMP rule (0.0.0.0/0) after creation; SSH rule must be added manually by the user

## 3. ECS Instance & EIP Verification

### Verification Method

✅ **Correct Example**:
```bash
# Check server status
hcloud ECS ShowServer --cli-region=${HUAWEI_REGION} --server_id=${SERVER_ID}

# List devkit servers
hcloud ECS ListServersDetails --cli-region=${HUAWEI_REGION} --limit=500
# Filter: name matches devkit-ecs-*, status = ACTIVE
```

### Expected Results
- Server status is `ACTIVE`
- Instance name matches `devkit-ecs-*` prefix
- Has a public EIP and it is bound
- Architecture is x86_64 (fixed)
- Flavor matches user selection (4U8G ac/C/S/T/X series)
- EIP is obtained only from hcloud queries, not from environment variables

## 4. SSH Login & Script Upload Verification

### Verification Method

✅ **Correct Example**:
```bash
# Verify SSH login
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "uname -m"

# Verify scripts uploaded
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "stat ${DEVKIT_HOME}/install_devkit.sh ${DEVKIT_HOME}/scan_devkit.sh ${DEVKIT_HOME}/encrypt-nodes-verify.sh"
```

### Expected Results
- SSH login succeeds, returns architecture info x86_64
- All 3 scripts exist in `${DEVKIT_HOME}/` directory
- Credentials come only from `DEVKIT_ECS_USER` / `DEVKIT_ECS_PASSWORD` environment variables (User→Machine level)
- `BatchResetServersPassword` was not called

## 5. DevKit Installation Verification

### Verification Method

✅ **Correct Example**:
```bash
# Verify DevKit installation
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "source /etc/profile && devkit version"

# Verify DevKit directory
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "ls -d ${DEVKIT_HOME}/DevKit/DevKit-Sys-Mig-CLI-26.1.RC1-Linux-*"
```

### Expected Results
- `devkit version` returns a version number
- DevKit installation directory exists: `${DEVKIT_HOME}/DevKit/DevKit-Sys-Mig-CLI-26.1.RC1-Linux-x86-64/`

## 6. sshpass Installation Verification

### Verification Method

✅ **Correct Example**:
```bash
# Verify sshpass is installed on DevKit server
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "sshpass -V"
```

### Expected Results
- `sshpass -V` returns a version number, e.g., `sshpass 1.06`
- sshpass is installed and available for non-interactive SSH password authentication
- Installation is performed automatically by `install_devkit.sh` after DevKit installation
- CentOS 7 installs via epel-release repository, Ubuntu 20.04 installs via apt-get

### Installation Failure Troubleshooting

❌ **Problem**: `sshpass: command not found`

✅ **Solution**:
```bash
# CentOS 7
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "yum install -y epel-release && yum install -y sshpass"

# Ubuntu 20.04
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "apt-get update -y && apt-get install -y sshpass"
```

## 7. Maven Installation & Repository Configuration Verification

### Maven Installation Verification Method

✅ **Correct Example**:
```bash
# Verify Maven
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "source /etc/profile && mvn -v"

# Verify JDK
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "java -version"
```

### Maven Installation Expected Results
- `mvn -v` returns Apache Maven 3.8.8
- `java -version` is executable, JDK is installed
- Maven installation path: `${DEVKIT_HOME}/maven/apache-maven-3.8.8`

### Maven Repository Configuration Verification Method (mvn_analyse prerequisite)

✅ **Correct Example**:
```bash
# Check if settings.xml has Kunpeng Maven mirror configured
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "grep -l 'kunpeng' ${DEVKIT_HOME}/maven/apache-maven-3.8.8/conf/settings.xml 2>/dev/null && echo 'CONFIGURED' || echo 'NOT_CONFIGURED'"
```

### Maven Repository Configuration Expected Results
- settings.xml contains Kunpeng Maven repository mirror configuration
- `CONFIGURED` output means it is configured
- `NOT_CONFIGURED` output means configuration is needed
- Configuration reference: https://mirrors.huaweicloud.com/mirrorDetail/5fbb71cd07bbb121c2aded7b?mirrorName=kunpeng_maven&catalog=arm

### Maven Repository Configuration Method (when not configured)

✅ **Solution**:
```bash
# Backup original settings.xml and configure Kunpeng Maven mirror
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "cp ${DEVKIT_HOME}/maven/apache-maven-3.8.8/conf/settings.xml ${DEVKIT_HOME}/maven/apache-maven-3.8.8/conf/settings.xml.bak 2>/dev/null; cat >> ${DEVKIT_HOME}/maven/apache-maven-3.8.8/conf/settings.xml << 'EOF'
<mirror>
    <id>kunpeng-maven</id>
    <mirrorOf>*</mirrorOf>
    <url>https://mirrors.huaweicloud.com/repository/maven/huaweicloud-sdk-kunpeng-maven/</url>
</mirror>
EOF"
```

## 8. nodes.conf Configuration & Password Encryption Verification

### Verification Method

✅ **Correct Example**:
```bash
# Check if plaintext passwords exist (no encryption, no SSH verification)
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "bash ${DEVKIT_HOME}/encrypt-nodes-verify.sh --check"
# Expected: ALL_ENCRYPTED

# Safe display nodes.conf (passwords masked)
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "bash ${DEVKIT_HOME}/encrypt-nodes-verify.sh --mask"
# Expected: all ssh_pass values show as ***
```

### Expected Results
- `--check` outputs `ALL_ENCRYPTED` (no plaintext passwords)
- `--mask` output shows all `ssh_pass` values as `***`
- nodes.conf contains at least 1 target host entry
- All SSH connectivity verifications pass

## 9. Remote SSH Login to Target Servers Verification

### Verification Method

✅ **Correct Example**:
```bash
# Verify SSH from DevKit server to target server (using sshpass)
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "SSHPASS='<target_password>' sshpass -e ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -p 22 root@<target_ip> 'echo OK'"

# Or run encrypt-nodes-verify.sh which verifies SSH to all targets
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "bash ${DEVKIT_HOME}/encrypt-nodes-verify.sh"
```

### Expected Results
- SSH connection succeeds, outputs `OK`
- `encrypt-nodes-verify.sh` outputs `✅ All N target servers are reachable.`
- All target server SSH connectivity verifications pass
- sshpass is installed and available for non-interactive password authentication

### SSH Verification Failure Troubleshooting

❌ **Problem**: `Connection refused` / `Connection timeout` / `Host unreachable`

✅ **Solution**:
1. **Check target server security group inbound rules** (most common cause):
   - In Huawei Cloud console → target server's security group → add inbound rule
   - Protocol: TCP
   - Port: 22 (SSH)
   - Source: DevKit server EIP (i.e., the DevKit server's public IP)
2. **Check target server SSH service**: `systemctl status sshd`
3. **Check nodes.conf configuration**: confirm ssh_user/ssh_pass/target IP/port are correct
4. **Check if sshpass is installed**: `sshpass -V`
5. After fixing, re-run: `bash ${DEVKIT_HOME}/encrypt-nodes-verify.sh`

> **🔴 Security Group Configuration Reminder**: The DevKit server connects to target servers via its EIP. The target server's security group must allow inbound traffic on port 22 from the DevKit server's EIP. If not configured, SSH verification will report Connection refused/timeout errors.

## 10. Scan Execution Verification

### Verification Method

✅ **Correct Example**:
```bash
# Verify scan reports exist
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "stat ${DEVKIT_HOME}/report/"

# Check report naming convention
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "find ${DEVKIT_HOME}/report/ -maxdepth 1 -type d"
# Expected: <scan_mode>_<nodes_IP>_<timestamp> format
```

### Expected Results
- Scan reports exist under `${DEVKIT_HOME}/report/`
- Report directory naming format: `<scan_mode>_<nodes_IP>_<timestamp>`
- stmt mode generates CSV reports
- sbom mode generates HTML/JSON reports
- mvn_analyse mode generates HTML reports
- container_mig mode generates HTML/JSON reports
- Password check was performed before scanning (`--check` or `encrypt-nodes-verify.sh`)

## 11. Report Download Verification

### Verification Method

✅ **Correct Example**:
```bash
# Verify downloaded reports locally
stat ${LOCAL_DIR}/
# Expected: report files present
```

### Expected Results
- Local directory contains downloaded report files
- Remote directory structure is preserved locally
- Local save path is provided by the user (no default value)

## 12. Security Verification

### Verification Method

✅ **Correct Example**:
```bash
# Verify no plaintext password in chat output
# Check that DEVKIT_ECS_PASSWORD is never echoed
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "echo \${DEVKIT_ECS_PASSWORD:+set}"  # Only shows "set", not the value

# Verify nodes.conf passwords are encrypted
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "bash ${DEVKIT_HOME}/encrypt-nodes-verify.sh --check"
```

### Expected Results
- AK/SK displayed as `***` or placeholders in chat output and thinking process
- `DEVKIT_ECS_PASSWORD` displayed as `***` or `<your_password>` in chat output and thinking process
- nodes.conf `ssh_pass` displayed as `***` or `<encrypted_password>` in chat output and thinking process
- AI internal thinking/reasoning does not contain any actual password values
- `hcloud ECS BatchResetServersPassword` was not called
- paramiko only connects to the DevKit server, never to nodes.conf target servers

## 13. Full Workflow Verification

### Verification Checklist

| Step | Verification Command | Expected Result |
|------|----------------------|-----------------|
| hcloud Environment | `hcloud version` | Version ≥ 7.2.2 |
| Network Configuration | `hcloud VPC ListVpcs` | `devkit-vpc-*` exists |
| ECS Creation | `hcloud ECS ShowServer` | Status ACTIVE |
| EIP Binding | `hcloud ECS ListServersDetails` | Has public IP |
| SSH Login | `ssh ... "uname -m"` | Login succeeds |
| Script Upload | `ssh ... "ls ${DEVKIT_HOME}/*.sh"` | 3 scripts exist |
| DevKit Installation | `ssh ... "devkit version"` | Returns version number |
| sshpass Installation | `ssh ... "sshpass -V"` | Returns version number |
| Maven Installation | `ssh ... "mvn -v"` | 3.8.8 |
| Password Encryption | `encrypt-nodes-verify.sh --check` | ALL_ENCRYPTED |
| Remote SSH Verification | `SSHPASS=... sshpass -e ssh root@<target_ip> "echo OK"` | Outputs OK |
| Scan Execution | `ls ${DEVKIT_HOME}/report/` | Report files exist |
| Report Download | `ls ${LOCAL_DIR}/` | Reports downloaded |
| Security Check | Chat output review | No plaintext passwords |

## Common Issues Troubleshooting

### Q: hcloud not installed?

✅ **Solution**:
- Manual installation:
  ```bash
  curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-linux-amd64.tar.gz
  tar -xzf hcloudcli-linux-amd64.tar.gz
  chmod +x hcloud
  mv hcloud /usr/local/bin/
  ```

### Q: AK/SK not configured or invalid?

✅ **Solution**:

> **🔴 AI NEVER executes `hcloud configure set` on behalf of the user. AI only performs `hcloud configure list` existence checks. Credential configuration is the user's responsibility.**

When AK/SK is not configured, AI displays: "For security constraints, AK/SK cannot be received in conversation. Please configure AK/SK following the steps below:" and detects the current OS environment (Windows/Linux) to show the corresponding platform's configuration methods.

For complete AK/SK configuration steps (Windows/Linux environment variables, hcloud configure set, re-check flow), see [CLI Installation Guide §4 AK/SK Configuration](cli-installation-guide.md#4-aksk-configuration).

After configuration, AI re-checks with `hcloud configure list` (verification only) and tests with `hcloud ECS ListCloudServers --cli-region=${HUAWEI_REGION} --limit=1`.

### Q: No x86_64 flavors available?

✅ **Solution**:
- Switch to cn-north-4 / cn-east-3 / cn-south-1 / cn-southwest-2
- Query `hcloud ECS ListFlavors` to get available x86_64 flavors

### Q: CentOS 7.6 or Ubuntu 20.04 image not found?

✅ **Solution**:
- **🔴 MANDATORY**: Use **ECS Nova API** (`GET /v2.1/{project_id}/images/detail`) to query images. **NEVER use `hcloud IMS ListImages`** — it does not provide `HW_ARCH` metadata.
- Query endpoint: `https://ecs.{region}.myhuaweicloud.com/v2.1/{project_id}/images/detail`
- Apply 5-step filter: ① `metadata.HW_ARCH == "x86_64"` ② exclude GPU keywords (`gpu`/`with cuda`/`with tesla`/`with graphic`/`vroce`) ③ exclude bare metal/ARM (`baremetal`/`bms`/`arm`/`aarch64`/`kunpeng`/`ai`/`with uniagent`) ④ name contains OS pattern ⑤ prefer `__image_type == "gold"`
- Look for x86_64 image names containing "CentOS 7.6 64bit" or "Ubuntu 20.04 server 64bit"
- If no image passes all 5 filters, the OS may not have a compatible x86_64 non-GPU public image in that region — try the other OS option or a different region

### Q: ECS creation failed?

✅ **Solution**:
- Check AK/SK permissions and account balance

### Q: SSH login failed or connection refused?

✅ **Solution**:
- Check if security group has SSH inbound rule (port 22/tcp)
- If connection refused: security group has no SSH inbound rule — user must manually add SSH inbound rule (port 22/tcp) in Console. ICMP rule (0.0.0.0/0) is already auto-added
- Re-detect `DEVKIT_ECS_USER` / `DEVKIT_ECS_PASSWORD` environment variables (User→Machine level)
- Confirm `BatchResetServersPassword` was not called
- See [Security Rules](rules.md)

### Q: EIP not found?

✅ **Solution**:
- `DEVKIT_ECS_EIP` is obtained only from hcloud queries (not environment variables)
- Ensure ECS status is ACTIVE and floating IP is bound

### Q: DevKit installation failed?

✅ **Solution**:
- Check server network can access `kunpeng-repo.obs.cn-north-4.myhuaweicloud.com`
- Confirm `uname -m` returns x86_64
- Confirm OS is CentOS 7.6 or Ubuntu 20.04
- Verify wget/curl is available

### Q: Remote scan failed?

✅ **Solution**:
- Ensure nodes.conf is configured
- Run `encrypt-nodes-verify.sh --check` to confirm passwords are encrypted
- Confirm `encrypt-nodes-verify.sh` was run before scanning to encrypt passwords and verify SSH

### Q: nodes.conf SSH verification failed?

✅ **Solution**:
- Check ssh_user/ssh_pass/target IP/port
- Ensure target SSH service is running
- Check firewall rules
- **🔴 Security Group Configuration Reminder**: Add inbound rule in target server's security group (Protocol: TCP, Port: 22, Source: DevKit server EIP)
- Confirm sshpass is installed: `sshpass -V`
- After fixing, re-run `encrypt-verify`

### Q: Scan directory not provided?

✅ **Solution**:
- User must provide a valid path on the Kunpeng server

### Q: Plaintext passwords in nodes.conf?

✅ **Solution**:
- Run `bash ${DEVKIT_HOME}/encrypt-nodes-verify.sh` to encrypt and replace
- After encryption, run `bash ${DEVKIT_HOME}/encrypt-nodes-verify.sh --check` to confirm `ALL_ENCRYPTED`
- Use `bash ${DEVKIT_HOME}/encrypt-nodes-verify.sh --mask` to safely display nodes.conf

## External Reference Links

- [KooCLI Installation Guide](https://support.huaweicloud.com/cli/index.html)
- [DevKit CLI Installation Guide](https://www.hikunpeng.com/document/detail/zh/kunpengdevps/install/installguide/KunpengDevKitCli_0004.html)
- [System Migration CLI (stmt)](https://www.hikunpeng.com/document/detail/zh/kunpengdevps/portingadvisor/systemmigration/KunpengDevKitCli_0062.html)
- [System Migration CLI (sbom)](https://www.hikunpeng.com/document/detail/zh/kunpengdevps/portingadvisor/systemmigration/KunpengDevKitCli_0063.html)
- [System Migration CLI (mvn_analyse)](https://www.hikunpeng.com/document/detail/zh/kunpengdevps/portingadvisor/systemmigration/KunpengDevKitCli_0105.html)
- [System Migration CLI (container_mig)](https://www.hikunpeng.com/document/detail/zh/kunpengdevps/portingadvisor/systemmigration/KunpengDevKitCli_0150.html)
- [DevKit Download](https://www.hikunpeng.com/developer/devkit/downloadNew)
