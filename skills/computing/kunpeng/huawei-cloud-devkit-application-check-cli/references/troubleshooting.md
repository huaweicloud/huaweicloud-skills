# Troubleshooting Guide

## Table of Contents

- [hcloud CLI Issues](#hcloud-cli-issues)
- [ECS Creation Issues](#ecs-creation-issues)
- [SSH Connection Issues](#ssh-connection-issues)
- [DevKit Installation Issues](#devkit-installation-issues)
- [nodes.conf Issues](#nodesconf-issues)
- [Scan Issues](#scan-issues)
- [Report Download Issues](#report-download-issues)

---

## hcloud CLI Issues

### Q: `hcloud: command not found`

**Cause**: KooCLI not installed or not in PATH

**Solution**:
```bash
# Check if hcloud is in PATH
which hcloud

# If not, add to PATH (Linux/macOS)
export PATH=$PATH:~/hcloud/

# Reinstall
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-linux-amd64.tar.gz
tar -xzf hcloudcli-linux-amd64.tar.gz
chmod +x hcloud
mv hcloud /usr/local/bin/
```

### Q: hcloud version too low (< 7.2.2)

**Cause**: Installed KooCLI version does not meet requirements

**Solution**:
```bash
# Upgrade KooCLI
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-linux-amd64.tar.gz
tar -xzf hcloudcli-linux-amd64.tar.gz
chmod +x hcloud
mv hcloud /usr/local/bin/

# Verify version
hcloud version
```

### Q: AK/SK authentication failed

**Cause**: AK/SK not configured, expired, or invalid

**Solution**:

> **🔴 AI NEVER executes `hcloud configure set` on behalf of the user. AI only performs `hcloud configure list` existence checks. Credential configuration is the user's responsibility.**

When AK/SK is not configured, AI displays: "For security constraints, AK/SK cannot be received in conversation. Please configure AK/SK following the steps below:" and detects the current OS environment (Windows/Linux) to show the corresponding platform's configuration methods.

For complete AK/SK configuration steps (Windows/Linux environment variables, hcloud configure set, re-check flow), see [CLI Installation Guide §4 AK/SK Configuration](cli-installation-guide.md#4-aksk-configuration).

After configuration, AI re-checks with `hcloud configure list` (verification only) and tests connectivity:

```bash
hcloud configure list
hcloud ECS ListCloudServers --cli-region=cn-north-4 --limit=1
```

### Q: Insufficient permissions (403 Unauthorized)

**Cause**: IAM user lacks required permissions

**Solution**:
1. Check if IAM policy includes required permissions (see [IAM Permission Policies](iam-policies.md))
2. Confirm AK/SK belongs to a user with permissions
3. Check if Region parameter is correct

---

## ECS Creation Issues

### Q: ECS creation timeout

**Cause**: Insufficient resources, quota limits, or network issues

**Solution**:
1. Check ECS quota: `hcloud ECS ListCloudServers --cli-region=${HUAWEI_REGION}`
2. Change availability zone or flavor
3. Check VPC/subnet status

### Q: EIP binding failed

**Cause**: Insufficient EIP quota or port not found

**Solution**:
1. Check EIP quota
2. Confirm ECS status is `ACTIVE`
3. Manually query port: `hcloud VPC ListPorts --cli-region=${HUAWEI_REGION} --device_id.1=${SERVER_ID}`

### Q: Security group rule not effective

**Cause**: Security group rule creation failed or delayed

**Solution**:
1. Verify security group rule: `hcloud VPC ListSecurityGroupRules --cli-region=${HUAWEI_REGION} --security_group_id=${SG_ID}`
2. Confirm port 22 is open
3. Check if source address is `0.0.0.0/0`

### Q: Duplicate DevKit ECS Created with Same Name

**Cause**: CreateServers output parsing failed, then CreateServers command was re-executed

**Solution**:
1. Query all devkit-ecs-* servers: `hcloud ECS ListServersDetails --cli-region=${HUAWEI_REGION}`
2. Filter by name to find duplicates
3. Keep one, delete the rest: `hcloud ECS DeleteServers --cli-region=${HUAWEI_REGION} --servers.1.id=<duplicate_server_id>`
4. Check and release orphaned EIPs: `hcloud EIP ListPublicips` to find EIPs with status=DOWN, `hcloud EIP DeletePublicip --publicip_id=<EIP_ID>` to release

---

## SSH Connection Issues

### Q: SSH authentication failed (AuthenticationException)

**Cause**: `DEVKIT_ECS_PASSWORD` environment variable value is incorrect

**Solution**:
1. Re-detect environment variables (User ? Machine level)
2. Confirm password complies with ECS password rules (8-26 characters, at least 3 character types)
3. Update environment variable:
   ```powershell
   [System.Environment]::SetEnvironmentVariable("DEVKIT_ECS_PASSWORD", "<correct_password>", "User")
   ```
4. **FORBIDDEN** to call `hcloud ECS BatchResetServersPassword`

### Q: SSH connection timeout

**Cause**: Security group has not opened port 22, EIP not bound, network unreachable

**Solution**:
1. Confirm security group inbound rule includes port 22
2. Confirm EIP is bound to ECS
3. Test network connectivity: `ping ${DEVKIT_ECS_EIP}`

### Q: paramiko connection refused

**Cause**: ECS not started or SSH service not running

**Solution**:
1. Confirm ECS status is `ACTIVE`
2. View instance status via ECS console
3. Restart ECS instance

---

## DevKit Installation Issues

### Q: DevKit download failed

**Cause**: Network issue or download URL unreachable

**Solution**:
1. Confirm DevKit ECS can access the internet
2. Check if download URL is correct
3. Manually download and upload to DevKit ECS

### Q: DevKit installation script execution failed

**Cause**: OS incompatible, insufficient disk space, missing dependencies

**Solution**:
1. Confirm OS is CentOS 7.6 or Ubuntu 20.04
2. Check disk space: `df -h /home`
3. Check dependencies: `yum install -y wget tar` (CentOS) or `apt install -y wget tar` (Ubuntu)

### Q: `devkit version` command not found

**Cause**: DevKit not properly installed or PATH not configured

**Solution**:
```bash
# Check DevKit installation directory
ls ${DEVKIT_HOME}/DevKit/

# Manually add to PATH
export PATH=${DEVKIT_HOME}/DevKit/DevKit-Sys-Mig-CLI-26.1.RC1-Linux-x86-64:$PATH

# Verify
devkit version
```

### Q: Maven installation failed

**Cause**: JDK not installed or network issue

**Solution**:
1. Check JDK: `java -version`
2. Manually install Maven:
   ```bash
   bash ${DEVKIT_HOME}/install_devkit.sh --check-maven
   ```
3. Verify: `mvn -v`

---

## nodes.conf Issues

### Q: nodes.conf contains plaintext password

**Cause**: User filled in plaintext password during configuration

**Solution**:
```bash
# Encrypt and replace
ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "bash ${DEVKIT_HOME}/encrypt-nodes-verify.sh"
```

### Q: SSH verification to target server failed

**Cause**: Target server password incorrect, SSH service not running, network unreachable

**Solution**:
1. Confirm target server IP, port, username, password are correct
2. Confirm target server SSH service is running
3. Confirm DevKit ECS can access target server
4. Fix nodes.conf and re-run:
   ```bash
   ssh ${DEVKIT_ECS_USER}@${DEVKIT_ECS_EIP} "bash ${DEVKIT_HOME}/encrypt-nodes-verify.sh"
   ```

### Q: SSH verification still fails after password encryption

**Cause**: Plaintext password before encryption does not match actual password

**Solution**:
1. Update nodes.conf with the correct plaintext password
2. Delete verified host records: `find /tmp -name devkit_nodes_verified_hosts -delete`
3. Re-run the encryption verification script

---

## Scan Issues

### Q: Scan command execution failed

**Cause**: nodes.conf configuration error, target server unreachable, DevKit not properly installed

**Solution**:
1. Confirm Step 7 is complete (nodes.conf configuration + encryption + SSH verification)
2. Confirm DevKit is properly installed: `devkit version`
3. Check if scan parameters are correct
4. View scan log for detailed error information

### Q: mvn_analyse scan failed

**Cause**: Maven not installed, pom.xml path incorrect, Maven repository does not exist

**Solution**:
1. Confirm Maven is installed: `mvn -v`
2. Confirm pom.xml path is correct
3. Confirm Maven repository exists and is accessible
4. If Maven needs to be installed: `bash ${DEVKIT_HOME}/install_devkit.sh --check-maven`

### Q: container_mig scan failed

**Cause**: Image package path incorrect, Dockerfile path incorrect

**Solution**:
1. Confirm `--image` parameter points to a valid image package
2. Confirm `--dockerfile` parameter points to a valid Dockerfile (if provided)
3. Check if image package format is supported

### Q: Report directory name not renamed

**Cause**: `rename_reports_to_eip` function execution failed

**Solution**:
1. Check directory names under `${DEVKIT_HOME}/report/`
2. Confirm nodes.conf contains target IP
3. Manually rename or re-run scan

---

## Report Download Issues

### Q: SFTP download failed

**Cause**: Local path does not exist, network issue, insufficient permissions

**Solution**:
1. Confirm local directory exists and has write permission
2. Confirm report file exists on DevKit ECS
3. Check network connectivity

### Q: Downloaded report file incomplete

**Cause**: Scan not completed or report generation interrupted

**Solution**:
1. Confirm scan completed successfully
2. Check file list under `${DEVKIT_HOME}/report/`
3. Re-execute scan and download

---

## Related Documents

- [Security Rules](rules.md) ? Password management and security constraints
- [DevKit Operations Workflow](devkit-operations-workflow.md) ? Operation workflow
- [IAM Permission Policies](iam-policies.md) ? Permission configuration
- [Verification Method](verification-method.md) ? Installation verification
