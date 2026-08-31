# Acceptance Criteria

## Overview

This document defines the acceptance criteria for this skill, used to determine if the deployment is successful.

## Functional Acceptance Criteria

### 1. ECS Instance Creation

| Acceptance Item | Standard | Verification Method |
|-----------------|----------|---------------------|
| Instance Status | ACTIVE | Query ECS status |
| Correct Flavor | x1.2u.4g or user-specified (minimum 2 cores 4GB) | Query instance details |
| Correct Image | Ubuntu 22.04 Server 64-bit (x86_64) | Query image information |
| System Disk | 40GB+ SAS | Query disk information |

### 2. Network Configuration

| Acceptance Item | Standard | Verification Method |
|-----------------|----------|---------------------|
| EIP Binding | Bound with public IP | Query EIP status |
| Security Group | sg-dsh created | Query security group list |
| Security Group Status | **Empty security group** after deployment (no inbound rules) | Query security group rules |
| Manual Configuration Verification | Port **22** rule (SSH) added manually by user in console | Huawei Cloud console verification |
| Rule Format | All inbound rules source IP are `your_ip/32` | Check security group rules |
| **No 0.0.0.0/0** | **Absolutely no 0.0.0.0/0 inbound rules allowed** | Security group rules audit |
| **Only Port 22 Open** | **Only TCP 22 is allowed from your_ip/32; no 80/443/3080 rules** | Security group rules audit |

### 3. DeepSeek Harness (dsh) Deployment

| Acceptance Item | Standard | Verification Method |
|-----------------|----------|---------------------|
| Node.js | Node.js 22 LTS installed | Check `node -v` |
| dsh CLI | @deepseek-ai/dsh installed globally | Check `dsh -V` |
| dsh Service | systemd service `dsh` enabled and running | Check `systemctl status dsh` |
| dsh Loopback Port | Port 3080 (default) responding on 127.0.0.1 | Check `curl http://127.0.0.1:3080` |
| Nginx Reverse Proxy | Nginx installed, config passes `nginx -t` (loopback only) | Check `nginx -t` and `systemctl status nginx` |
| Web UI via SSH Tunnel | After `ssh -L 3080:127.0.0.1:3080 root@<public_ip>`, `curl http://127.0.0.1:3080` returns HTTP 200/302 | Local machine verification |
| Auto-restart | systemd Restart=on-failure policy enabled | Check `systemctl cat dsh` |
| Dedicated User | System user `dsh` created, DSH_HOME owned by it | Check `id dsh` and DSH_HOME permissions |
| Service Logs | Deployment logs normal | Check /var/log/dsh-bootstrap.log |
| Data Directory | DSH_HOME created (default /home/dsh/.dsh) | Check directory existence |

### 4. Security

| Acceptance Item | Standard | Verification Method |
|-----------------|----------|---------------------|
| Loopback Binding | dsh binds to 127.0.0.1 only (no public exposure) | Check `ss -tlnp \| grep 3080` |
| No Hardcoded Credentials | No AK/SK in code or scripts | Code review |
| API Key Handling | DEEPSEEK_API_KEY only via systemd drop-in (mode 600), never logged | Code review + check /etc/systemd/system/dsh.service.d/ |
| npm Registry | npmmirror registry configured for China acceleration | Check `npm config get registry` |

## Performance Acceptance Criteria

| Acceptance Item | Standard |
|-----------------|----------|
| Deployment Time | < 15 minutes |
| API Response Time | < 3 seconds |
| Page Load Time | < 5 seconds |

## Security Acceptance Criteria

| Acceptance Item | Standard | Verification Method |
|-----------------|----------|---------------------|
| SSH Access Restriction | Security group is empty, must **manually add** `your_ip/32` to access port 22, **no 0.0.0.0/0** | Check security group rules |
| dsh Web Access | dsh accessed via **SSH tunnel** (`ssh -L 3080:127.0.0.1:3080 root@<public_ip>` → `http://127.0.0.1:3080`); **no public 80/3080 rules** | Check security group rules + local tunnel verification |
| **No 0.0.0.0/0 Rules** | **Absolutely prohibit any 0.0.0.0/0 inbound rules** (including user manually added) | Security group rules audit |
| **CIDR Range Restriction** | All inbound rules must use `/32` (single IP), prohibit `/24, /16, /0` and other broad ranges | Security group rules audit |
| **Empty Security Group Policy** | Script only creates empty security group, does not automatically add any inbound rules | Code review |
| **User Manual Configuration** | After deployment, guide user to manually configure security group in Huawei Cloud console | Check deployment output |
| COC Deployment | Use Cloud Operations Center for secure deployment | Check deployment method |
| UniAgent Status | UniAgent online and available | Check COC resource status |
| No Hardcoded Credentials | No AK/SK in code | Code review |
| Password Complexity | Comply with password policy (8-26 characters, containing uppercase, lowercase, numbers, special characters) | Check auto-generated password |
| User Confirmation Mechanism | User must confirm before creating resources | Test deployment flow |
| No Automatic Retry | No automatic retry or parameter switching on failure | Code review |

## Acceptance Test Cases

### Test Case 1: Default Configuration Deployment

**Preconditions**:
- Valid AK/SK
- Project ID and region information

**Steps**:

✅ **Correct Example**:
```bash
python3 deploy_dsh.py \
  --ak AKEXAMPLE123456 \
  --sk SKEXAMPLE789012 \
  --project-id PROJECT123456 \
  --region cn-north-4
```

**Expected Result**:
- All acceptance items passed
- dsh Web UI accessible at `http://127.0.0.1:3080` (after `ssh -L 3080:127.0.0.1:3080 root@<public_ip>`)
- dsh service running on 127.0.0.1:3080 (loopback only)

### Test Case 2: Custom Configuration Deployment

**Preconditions**:
- Valid AK/SK
- Custom server flavor

**Steps**:

✅ **Correct Example**:
```bash
python3 deploy_dsh.py \
  --ak AKEXAMPLE123456 \
  --sk SKEXAMPLE789012 \
  --project-id PROJECT123456 \
  --region cn-north-4 \
  --flavor x1.4u.8g \
  --name my-dsh-server \
  --dsh-port 3080
```

**Expected Result**:
- Server flavor matches custom configuration
- dsh accessible normally

### Test Case 3: Deployment with API Key Pre-seed

**Preconditions**:
- Valid AK/SK
- DeepSeek API key

**Steps**:

✅ **Correct Example**:
```bash
python3 deploy_dsh.py \
  --ak AKEXAMPLE123456 \
  --sk SKEXAMPLE789012 \
  --project-id PROJECT123456 \
  --region cn-north-4 \
  --api-key sk-xxxxxxxxxxxx
```

**Expected Result**:
- DEEPSEEK_API_KEY injected via systemd drop-in (file mode 600)
- API key never appears in deployment logs

### Test Case 4: Deployment Failure Rollback

**Preconditions**:
- Invalid AK/SK (simulate authentication failure)

**Steps**:

❌ **Error Example**:
```bash
python3 deploy_dsh.py \
  --ak INVALID_AK \
  --sk INVALID_SK \
  --project-id PROJECT123456 \
  --region cn-north-4
```

**Expected Result**:
- Returns clear error message
- No resource residue (or cleaned up)

### Test Case 5: Empty Security Group Verification (Critical Security Test)

**Preconditions**:
- Valid AK/SK
- Know your public IP (can get from https://api.ipify.org)

**Steps**:

✅ **Correct Example - Manual Configuration After Deployment**:
```bash
python3 deploy_dsh.py \
  --ak AKEXAMPLE123456 \
  --sk SKEXAMPLE789012 \
  --project-id PROJECT123456 \
  --region cn-north-4
```

**Operations in Huawei Cloud console after deployment**:
1. Navigate to ECS → Security Groups → `sg-dsh`
2. Add inbound rule: TCP port 22, source IP `your_ip/32` (required for SSH tunnel)

**Expected Result**:
- Security group `sg-dsh` created but **has no inbound rules** (only necessary outbound rules)
- Deployment output clearly prompts user to manually configure security group in Huawei Cloud console
- After user manually adds the rule, all inbound rules source_ip are only `your_ip/32`
- **No 0.0.0.0/0 inbound rules exist**
- **Only port 22 is open; no 80/443/3080 rules** (dsh accessed via SSH tunnel)

### Test Case 6: Manual Security Group Configuration Verification (Security Boundary)

**Preconditions**:
- Deployment completed (Test Case 5)

**Verification Steps**:

✅ **Verify in Huawei Cloud console**:
- Navigate to ECS → Security Groups → `sg-dsh` → Rules List
- Confirm all inbound rules are `your_ip/32`
- Confirm port 22 (SSH) is open
- **No 0.0.0.0/0 rules**
- **No broad CIDR rules like /24 /16 /0**
- **No 80/443/3080 inbound rules** (not needed — SSH tunnel only)

❌ **Absolutely prohibited configuration**:
- Using `0.0.0.0/0` as source IP
- Using `your_ip/24` or `your_ip/16` and other broad ranges
- Opening unnecessary ports (such as 1-65535, or 80/3080 to public)

**Expected Result**:
- SSH can successfully login from your IP: `ssh root@<public_ip>`
- SSH tunnel works: `ssh -L 3080:127.0.0.1:3080 root@<public_ip>` then `curl http://127.0.0.1:3080` returns 200/302
- Cannot access any port from other IPs (blocked by security group)

## Acceptance Report Template

```markdown
# Acceptance Report

## Basic Information
- Skill Name: huawei-cloud-ecs-dsh-deploy
- Test Time: 2026-08-18 10:00:00
- Tester: TestUser

## Acceptance Results
| Item | Result | Notes |
|------|--------|-------|
| ECS Instance Creation | PASS | |
| Network Configuration | PASS | |
| dsh Deployment | PASS | |
| Nginx Reverse Proxy | PASS | |
| Security Check | PASS | |
| Performance Test | PASS | |

## Summary
- Passed: 6 items
- Failed: 0 items
- Conclusion: PASSED
```
