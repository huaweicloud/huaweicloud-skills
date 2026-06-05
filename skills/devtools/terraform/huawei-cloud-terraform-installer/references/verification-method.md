# Terraform Installer Skill Verification Method

## Prerequisites

- **Python 3.6+** - Required for running the installation script

## Test Environment

| Item | Value |
|------|-------|
| Test Machine OS | Ubuntu 22.04.5 LTS |
| Test Machine Spec | s6.small.1 (1vCPU, 1GB) |
| Test Machine Public IP | 1.92.158.126 |
| Security Group | Allow SSH only from local IP (120.46.211.126) |
| Login Method | Password login (root/Test@123456) |
| Test Region | cn-north-4 (North China-Beijing 4) |

## Test Cases

### 1. Check Function (--check)

**Purpose**: Verify that `--check` parameter correctly detects Terraform installation status

**Steps**:
```bash
# Not installed state
python3 install_terraform.py --check
# Expected output: [ERROR] Terraform not installed

# Installed state
python3 install_terraform.py --check
# Expected output: [SUCCESS] Terraform installed: vX.X.X
```

### 2. Binary Installation Method (Default)

**Purpose**: Verify binary download installation works correctly

**Steps**:
```bash
python3 install_terraform.py
```

**Expected Results**:
- Successfully download Terraform binary
- Successfully install HuaweiCloud Provider
- Successfully configure terraformrc
- terraform init test passes

### 3. Specify Version Installation (--version)

**Purpose**: Verify that specific version can be installed

**Steps**:
```bash
python3 install_terraform.py --version 1.8.0
terraform version
# Expected: Terraform v1.8.0
```

### 4. Uninstall Function (--uninstall)

**Purpose**: Verify uninstall function completely cleans up all files

**Steps**:
```bash
python3 install_terraform.py --uninstall
```

**Expected Results**:
- Delete /usr/local/bin/terraform
- Delete ~/.terraformrc
- Clean up ~/.terraform.d/providers

### 5. Provider Initialization Test

**Purpose**: Verify terraform init works correctly after installation

**Steps**:
```bash
mkdir /tmp/tf-test && cd /tmp/tf-test
cat > main.tf << 'EOF'
terraform {
  required_providers {
    huaweicloud = {
      source  = "huaweicloud/huaweicloud"
      version = "1.90.0"
    }
  }
}
EOF
terraform init
```

**Expected Result**: terraform init succeeds

## Test Execution Methods

### Automated Test Script

```bash
#!/bin/bash
# Complete test workflow

echo "=== Test 1: --check (not installed) ==="
python3 install_terraform.py --check

echo "=== Test 2: Binary Installation ==="
python3 install_terraform.py

echo "=== Test 3: Verify Installation ==="
terraform version

echo "=== Test 4: --check (installed) ==="
python3 install_terraform.py --check

echo "=== Test 5: Uninstall ==="
python3 install_terraform.py --uninstall

echo "=== Test 6: Specify Version ==="
python3 install_terraform.py --version 1.8.0 --uninstall
python3 install_terraform.py --version 1.8.0
terraform version

echo "=== Tests Complete ==="
```

### Remote Testing (via SSH)

```bash
# Upload script
scp install_terraform.py root@<EIP>:/tmp/

# Execute test
ssh root@<EIP> 'python3 /tmp/install_terraform.py'
```

## Acceptance Criteria

| Test Item | Pass Criteria |
|-----------|---------------|
| --check (not installed) | Output [ERROR] Terraform not installed |
| --check (installed) | Output [SUCCESS] Terraform installed |
| Binary installation | Installation succeeds, terraform version works |
| --version X.X.X | Specified version installed successfully |
| --uninstall | All files cleaned up |
| terraform init | Initialization succeeds using local Provider |

---

*Document created: 2026-05-25*
