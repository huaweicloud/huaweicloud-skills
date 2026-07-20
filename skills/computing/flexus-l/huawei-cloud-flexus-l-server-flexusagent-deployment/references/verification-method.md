# Skill Verification Method

This document describes the verification methods and test steps for the FlexusAgent one-click deployment skill.

## Verification Flow

### Phase 1: Environment Preparation Verification

**Verification Items:**
- [ ] Python version >= 3.8
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Huawei Cloud AK/SK configured
- [ ] Network connectivity is normal

**Verification Commands:**
```bash
# Check Python version
python --version

# Check dependency installation
python -c "from huaweicloudsdkcore.signer.signer import Signer; print('SDK OK')"
```

**Note: AK/SK can be provided via command-line arguments (`--ak`, `--sk`, and `--security-token`) or entered in interactive mode.**

### Phase 2: Deployment Function Verification

**Verification Items:**
- [ ] Instance created successfully
- [ ] Instance status is normal
- [ ] Instance specifications meet expectations

**Verification Commands:**
```bash
# Deploy instance (using a smaller spec for testing is recommended)
python scripts/caller.py deploy --name test-flexusagent --region cn-north-4 --ak <AK> --sk <SK> --security-token <Token> --non-interactive

# Verify instance status (via Huawei Cloud console or API)
```

**Expected Results:**
- Instance created successfully, status is "running".
- Instance spec is `hf.xlarge.1.linux` (Beijing/Shanghai/Guangzhou) or `ahf.xlarge.1.linux` (Guiyang).
- Disk configuration is 50GB EVS.

### Phase 3: Administrator Password Change Verification

**Verification Items:**
- [ ] UniAgent status is ONLINE
- [ ] Administrator password change task executed successfully
- [ ] COC task execution completed

**Verification Commands:**
```bash
# Change admin password
python scripts/caller.py passwd --resource-id <instance_id> --region-id cn-north-4 --admin-password <string> --ak <AK> --sk <SK> --security-token <Token> --non-interactive
```

**Expected Results:**
- UniAgent status check passed.
- Administrator password change task executed successfully.
- COC task execution completed (a prompt will follow: Administrator login email super@dify.com).

### Phase 4: MaaS Model Integration Verification

**Verification Items:**
- [ ] FlexusAgent login successful
- [ ] MaaS plugin installed and configured successfully
- [ ] Models can be called normally

**Verification Commands:**
```bash
# Integrate MaaS model
python scripts/caller.py maas --flexusagent-base-url http://<IP>:80 --flexusagent-email <email> --flexusagent-password <password> --maas-api-key <api_key> --non-interactive

# Verify model status (via FlexusAgent Web UI)
```

**Expected Results:**
- FlexusAgent login successful.
- Model integration flow shows "✓ Plugin installation and credential configuration completed".
- Models appear in the FlexusAgent model list.


## Troubleshooting

### Problem 1: AK/SK Verification Failed

**Symptoms:**
```
Error: AK/SK verification failed, please check if the credentials are correct
```

**Troubleshooting Steps:**
1. Confirm AK/SK environment variables are correctly set.
2. Confirm AK/SK have not expired.
3. Confirm AK/SK have sufficient permissions.

### Problem 2: UniAgent Status Abnormal

**Symptoms:**
```
UniAgent Status: OFFLINE
Please ensure UniAgent is started and online
```

**Troubleshooting Steps:**
1. Wait for the instance to fully start (usually takes 5-10 minutes).
2. Check UniAgent status via Huawei Cloud console.
3. Try restarting the UniAgent service.

### Problem 3: Administrator Password Change Timeout

**Symptoms:**
```
Error: Execution timed out, please check network connection or increase timeout
```

**Troubleshooting Steps:**
1. Increase the timeout parameter `--timeout 1200`.
2. Check the instance's network connection.

### Problem 4: MaaS Integration Failed

**Symptoms:**
```
Error: Login failed: Email or password incorrect
```

**Troubleshooting Steps:**
1. Confirm the FlexusAgent Web UI address is correct.
2. Confirm the administrator email and password are correct.
3. Confirm the MaaS API Key is valid.

## Automated Test Script

You can create the following test script to automate the verification flow:

```bash
#!/bin/bash
echo "=== FlexusAgent Deployment Verification ==="

echo ""
echo "1. Checking Python version..."
python --version

echo ""
echo "2. Checking SDK installation..."
python -c "from huaweicloudsdkcore.signer.signer import Signer; print('SDK OK')"

echo ""
echo "=== Verification completed ==="
```

## Verification Matrix

| Verification Item | Success Criteria | Failure Handling |
|--------|----------|----------|
| Environment Preparation | Python >= 3.8, dependencies installed successfully | Check Python version, reinstall dependencies |
| Credential Configuration | AK/SK provided via parameters or interactive input | Check if credentials are correctly provided |
| Instance Deployment | Instance created successfully, status running | Check permissions and network |
| Admin Password Change | Password change successful, login successful with new password (email: super@dify.com) | Check UniAgent status and password parameters |
| MaaS Integration | Model integration successful, callable normally | Check login info and API Key |
