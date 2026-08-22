# Troubleshooting - Kunpeng DevKit WebUI Mode Installation

This document covers common issues and solutions during DevKit installation.

## Table of Contents

- [1. hcloud Not Installed or Not Configured](#1-hcloud-not-installed-or-not-configured)
- [2. Python SDK or paramiko Not Installed](#2-python-sdk-or-paramiko-not-installed)
- [3. ECS Creation Failed](#3-ecs-creation-failed)
- [4. KMS Key Creation or Encryption Failed](#4-kms-key-creation-or-encryption-failed)
- [5. KMS Decryption Failed](#5-kms-decryption-failed)
- [6. paramiko SSH Connection Failed](#6-paramiko-ssh-connection-failed)
- [7. Kunpeng Flavor or Image Selection Error](#7-kunpeng-flavor-or-image-selection-error)
- [8. Architecture or OS Incompatible](#8-architecture-or-os-incompatible)
- [9. Insufficient Disk Space](#9-insufficient-disk-space)
- [10. expect Not Installed](#10-expect-not-installed)
- [11. Required Dependencies Missing](#11-required-dependencies-missing)
- [12. Installation Package Download Failed](#12-installation-package-download-failed)
- [13. Port Conflict](#13-port-conflict)
- [14. Firewall Blocking](#14-firewall-blocking)
- [15. Service Startup Failed](#15-service-startup-failed)
- [16. Installation Interrupted by SSH Disconnect](#16-installation-interrupted-by-ssh-disconnect)
- [17. EIP Binding Failed](#17-eip-binding-failed)
- [18. Reference Documents](#18-reference-documents)

---

## 1. hcloud Not Installed or Not Configured

### Symptoms

```
hcloud: command not found
```

### Solution

```bash
bash skills/hcloud-cli/scripts/install.sh
export PATH="$PATH:$HOME/.local/bin"
echo "y" | hcloud version
```

See [cli-installation-guide.md](cli-installation-guide.md).

---

## 2. Python SDK or paramiko Not Installed

### Symptoms

```
ModuleNotFoundError: No module named 'huaweicloudsdkecs'
ModuleNotFoundError: No module named 'paramiko'
```

### Solution

```bash
# Auto-use China mirror when system timezone is UTC+8 (faster in CN region; auto-detected via Python)
PIP_INDEX=$(python3 -c "import time;print('-i https://mirrors.huaweicloud.com/repository/pypi/simple' if -(time.timezone)//3600==8 else '')")
pip install $PIP_INDEX huaweicloudsdkcore huaweicloudsdkecs huaweicloudsdkkms paramiko
```

---

## 3. ECS Creation Failed

### Symptoms

```
ECS creation failed (job status: 2)
```

### Common Causes

| Cause | Solution |
|-------|----------|
| Insufficient quota | Apply for ECS quota in the Huawei Cloud console |
| Image ID does not exist | Re-query the image list and confirm the aarch64 image ID |
| Flavor unavailable | The region does not support this flavor; use another Kunpeng flavor |
| VPC/subnet mismatch | Ensure the VPC and subnet are in the same region |
| Password does not meet requirements | Password must be 8-26 characters, including uppercase, lowercase, digits, and special characters |

---

## 4. KMS Key Creation or Encryption Failed

### Symptoms

```
403 Forbidden when calling KMS API
Key creation failed
```

### Common Causes

| Cause | Solution |
|-------|----------|
| KMS permission missing | Add `kms:kms:create`, `kms:kms:encrypt`, `kms:kms:decrypt` to IAM policy |
| KMS quota exceeded | Delete unused KMS keys or request quota increase |
| Region mismatch | Ensure Python SDK KMS client uses the same region as the ECS |

### Solution

```bash
# Verify KMS access via Python SDK
python3 -c "
from huaweicloudsdkkms.v2 import KmsClient
from huaweicloudsdkcore.auth.credentials import BasicCredentials
# ... (construct client with same region as ECS) ...
print('KMS OK')
"
```

---

## 5. KMS Decryption Failed

### Symptoms

```
ERROR: KMS decryption failed
```

### Common Causes

| Cause | Solution |
|-------|----------|
| KMS key already deleted | KMS key was scheduled for deletion; cannot decrypt. Re-create ECS. |
| Wrong cipher_text | Ensure the exact `kms_cipher_text` from Phase 1 is used |
| Wrong key_id | Ensure the exact `kms_key_id` from Phase 1 is used |
| Region mismatch | KMS client region must match the region where the key was created |

---

## 6. paramiko SSH Connection Failed

### Symptoms

```
ERROR: SSH connection to <EIP> failed
AuthenticationException
```

### Common Causes

| Cause | Solution |
|-------|----------|
| Security group port 22 not open | Open port 22 in the security group (see ecs-creation-guide.md §7) |
| EIP not bound | Verify EIP is bound to the ECS via `hcloud EIP ShowPublicip` |
| ECS not ACTIVE | Wait for ECS to become ACTIVE before attempting SSH |
| Password incorrect | Verify KMS decryption returned the correct password |
| SSH service not running | ECS may still be initializing; wait 30s and retry |
| Host key verification | paramiko uses `AutoAddPolicy` by default; no manual action needed |

### Solution

1. Verify security group port 22 is open
2. Verify EIP is bound: `hcloud EIP ShowPublicip --cli-region=$REGION --publicip_id=$EIP_ID`
3. Wait 30s for SSH service to start after ECS becomes ACTIVE
4. Re-run `create_ecs_and_setup_devkit.py install`

---

## 7. Kunpeng Flavor or Image Selection Error

### Symptoms

ECS created successfully but architecture is x86_64, or DevKit installation reports architecture incompatibility.

### Solution

- **Flavor**: Must select a Kunpeng flavor starting with `k` (kc1/kx1), do not select x86 flavors like c6/c7
- **Image**: Must select an aarch64/ARM64 architecture image

---

## 8. Architecture or OS Incompatible

### Compatibility List

| OS | Version | Package Manager |
|----|---------|----------------|
| CentOS | 7.6 | yum |
| Ubuntu | 18.04 | apt |

---

## 9. Insufficient Disk Space

```bash
df -h /
yum clean all
```

---

## 10. expect Not Installed

```bash
yum install -y expect
```

---

## 11. Required Dependencies Missing

Dependencies are installed automatically by [install_devkit_webui.sh](../scripts/install_devkit_webui.sh), which handles both `yum` and `apt-get` package managers. If a dependency is reported missing after installation, check the install log at `/tmp/devkit_install.log` and install the missing package manually with the appropriate package manager.

---

## 12. Installation Package Download Failed

```bash
curl -I "https://kunpeng-repo.obs.cn-north-4.myhuaweicloud.com/Kunpeng%20DevKit/Kunpeng%20DevKit%2026.1.RC1/DevKit-All-26.1.RC1-Linux-Kunpeng.tar.gz"
wget -c "<URL>" -O DevKit-All-26.1.RC1-Linux-Kunpeng.tar.gz
```

---

## 13. Port Conflict

```bash
lsof -i :8086
lsof -i :8002
```

---

## 14. Firewall Blocking

```bash
firewall-cmd --permanent --add-port=8086/tcp
firewall-cmd --permanent --add-port=8002/tcp
firewall-cmd --reload
```

---

## 15. Service Startup Failed

```bash
systemctl status devkit_nginx --no-pager -l
systemctl status gunicorn_framework --no-pager -l
systemctl status gunicorn_plugin --no-pager -l
tail -100 /opt/DevKit/logs/nginx_error.log
```

---

## 16. Installation Interrupted by SSH Disconnect

The `install_devkit_webui.sh` script runs `nohup` in the background, so SSH disconnect should not interrupt the installation. If it does:

```bash
# Reconnect via paramiko and check status
python scripts/create_ecs_and_setup_devkit.py install \
  --region $REGION --eip $EIP --kms-key-id $KID --kms-cipher-text-file $CT_FILE
```

---

## 17. EIP Binding Failed

| Cause | Solution |
|-------|----------|
| ECS status is not ACTIVE | Wait for ECS creation to complete |
| Incorrect port_id | Obtain the correct port_id via `hcloud VPC ListPorts --cli-region=$REGION --device_id.1=$SERVER_ID` |
| Insufficient EIP quota | Apply for EIP quota in the console |

---

## 18. Reference Documents

- [CLI Installation Guide](cli-installation-guide.md)
- [ECS Creation Guide](ecs-creation-guide.md)
- [SSH Connection Guide](ssh-connection-guide.md)
- [IAM Permission Policies](iam-policies.md)
