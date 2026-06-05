# Skill Verification Method

This document describes the verification methods and test steps for the OpenClaw one-click deployment skill.

## Verification Process

### Phase 1: Environment Preparation Verification

**Verification Items:**
- [ ] Python version >= 3.8
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Huawei Cloud AK/SK configured
- [ ] Network connectivity normal

**Verification Commands:**
```bash
# Check Python version
python --version

# Check dependency installation
python -c "from huaweicloudsdkcore.signer.signer import Signer; print('SDK OK')"
```

**Note: AK/SK can be provided via command-line arguments (`--ak` and `--sk`) or entered in interactive mode**

### Phase 2: Deployment Functionality Verification

**Verification Items:**
- [ ] Instance created successfully
- [ ] Instance status normal
- [ ] Instance specification meets expectations

**Verification Commands:**
```bash
# Deploy instance (use smaller specification for test environment)
python scripts/caller.py deploy --name test-openclaw --region cn-north-4 --ak <AK> --sk <SK>

# Verify instance status (via Huawei Cloud console or API)
```

**Expected Results:**
- Instance created successfully, status is "running"
- Instance specification is `hf.small.1.linux` (Beijing/Shanghai/Guangzhou) or `ahf.small.1.linux` (Guiyang)
- Disk configuration is 50GB EVS

### Phase 3: Model Installation Verification

**Verification Items:**
- [ ] UniAgent status is ONLINE
- [ ] Model installed successfully
- [ ] Model can be invoked normally

**Verification Commands:**
```bash
# Install model
python scripts/caller.py maas --resource-id <instance_id> --region-id cn-north-4 --model-params '{"provider":"huawei","api_key":"your_api_key","model_ids":["deepseek-v3.2"]}' --ak <AK> --sk <SK> --non-interactive

# Verify model status (via OpenClaw Web UI)
```

**Expected Results:**
- UniAgent status check passed
- Model installation task executed successfully
- Model displayed in OpenClaw model list

### Phase 4: Channel Installation Verification

**Verification Items:**
- [ ] Channel installed successfully
- [ ] Channel status normal
- [ ] Message sending and receiving normal

**Verification Commands:**
```bash
# Install channel
python scripts/caller.py channel --resource-id <instance_id> --region-id cn-north-4 --channel-list '[{"channel":"wecom","id":"xxx","secret":"xxx"}]' --ak <AK> --sk <SK> --non-interactive
```

**Expected Results:**
- Channel installation task executed successfully
- Channel displayed in OpenClaw channel list
- Can normally receive and send messages

### Phase 5: Web UI Access Verification

**Verification Items:**
- [ ] Security group rules configured correctly
- [ ] Web UI accessible normally
- [ ] Login function normal

**Verification Steps:**
1. Log in to Huawei Cloud console
2. Configure security group rules to open port 18789
3. Access `http://<public_ip>:18789`
4. Verify login page displays normally

## Common Issue Troubleshooting

### Issue 1: AK/SK Verification Failed

**Symptom:**
```
Error: AK/SK verification failed, please check if credentials are correct
```

**Troubleshooting Steps:**
1. Confirm AK/SK environment variables are set correctly
2. Confirm AK/SK have not expired
3. Confirm AK/SK have sufficient permissions

### Issue 2: UniAgent Status Abnormal

**Symptom:**
```
UniAgent status: OFFLINE
Please ensure UniAgent is started and online
```

**Troubleshooting Steps:**
1. Wait for instance to fully start (usually takes 5-10 minutes)
2. Check UniAgent status via Huawei Cloud console
3. Try restarting UniAgent service

### Issue 3: Model Installation Timeout

**Symptom:**
```
Error: Execution timeout, please check network connection or increase timeout duration
```

**Troubleshooting Steps:**
1. Increase timeout parameter `--timeout 1200`
2. Check instance network connection
3. Confirm model parameters are correct

## Automated Test Script

You can create the following test script to automate the verification process:

```bash
#!/bin/bash
echo "=== OpenClaw Deployment Verification ==="

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
| Credential Configuration | AK/SK provided via parameters or interactive input | Check if credentials are provided correctly |
| Instance Deployment | Instance created successfully, status running | Check permissions and network |
| Model Installation | Model installed successfully, can be invoked normally | Check UniAgent status and model parameters |
| Channel Installation | Channel installed successfully, can send and receive messages | Check channel configuration parameters |
