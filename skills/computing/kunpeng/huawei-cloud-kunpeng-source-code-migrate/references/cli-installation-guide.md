# CLI Installation Guide (hcloud / KooCLI)

This guide covers the complete installation, configuration, and verification of Huawei Cloud KooCLI (hcloud), which is required for the Kunpeng ECS server provisioning workflow.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Credential Configuration](#credential-configuration)
- [Verify Installation](#verify-installation)
- [Common hcloud Commands for ECS Provisioning](#common-hcloud-commands-for-ecs-provisioning)
- [Troubleshooting](#troubleshooting)
- [Security Best Practices](#security-best-practices)

---

## Overview

**hcloud (KooCLI)** is the command-line tool for Huawei Cloud. It provides access to Huawei Cloud APIs including ECS, VPC, EIP, and IAM services needed for server provisioning.

**Minimum version required:** 3.2.0

**Official documentation:** https://support.huaweicloud.com/productdesc-hcli/hcli_01.html

---

## Installation

### Linux (x86_64)

```bash
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-amd64.tar.gz"
tar -xzf huaweicloud-cli-linux-amd64.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/
```

### Linux (ARM64)

```bash
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-arm64.tar.gz"
tar -xzf huaweicloud-cli-linux-arm64.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/
```

### macOS

```bash
# Option 1: Homebrew
brew install hcloudcli

# Option 2: Direct download
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-mac-amd64.tar.gz"
tar -xzf huaweicloud-cli-mac-amd64.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/
```

### Windows

```powershell
# Download and extract
Invoke-WebRequest -Uri "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-windows-amd64.zip" -OutFile "huaweicloud-cli-windows-amd64.zip"
Expand-Archive huaweicloud-cli-windows-amd64.zip

# Add hcloud.exe to PATH (adjust path as needed)
$env:PATH += ";$PWD\huaweicloud-cli-windows-amd64"
```

> **Note:** On Windows, you may need to add hcloud.exe to your system PATH permanently via System Properties > Environment Variables.

---

## Credential Configuration

### Method 1: Command-Line Configuration (Recommended, All Platforms)

```bash
hcloud configure set --cli-region=cn-southwest-2 --cli-access-key=<your-ak> --cli-secret-key=<your-sk>
```

This method works on all platforms including Windows (MSYS2/Git Bash). Replace `<your-ak>` and `<your-sk>` with your actual Access Key ID and Secret Access Key.

> **⚠️ Platform note for Windows:** On Windows (MSYS2/Git Bash), `export HUAWEICLOUD_SDK_AK=...` and `$env:HUAWEICLOUD_SDK_AK = "..."` do NOT work reliably — the variables are invisible to hcloud. Always use `hcloud configure set --cli-access-key=... --cli-secret-key=...` instead.

### Method 2: Interactive Configuration

```bash
hcloud configure set
```

You will be prompted to enter:
- **cli-region**: `cn-southwest-2` (Guiyang 1)
- **cli-access-key**: Your Access Key ID
- **cli-secret-key**: Your Secret Access Key

> **⚠️ Security:** Do NOT provide AK/SK directly in the conversation. Always use command-line or interactive configuration.

### Method 3: Environment Variables (Linux/macOS Only)

```bash
export HUAWEICLOUD_SDK_AK=<your-access-key-id>
export HUAWEICLOUD_SDK_SK=<your-secret-access-key>
```

> **⚠️ This method does NOT work on Windows (MSYS2/Git Bash).** Use Method 1 instead.

### How to Obtain AK/SK

1. Log in to Huawei Cloud Console
2. Navigate to: My Credentials > Access Keys
3. Click "Create Access Key"
4. Download the credentials file (contains AK and SK)
5. Store securely — the SK is only shown once at creation time

---

## Verify Installation

### Check Version

```bash
hcloud version
# Expected output: hcloud version 3.x.x (>= 3.2.0)
```

### Test Authentication

```bash
# Test by listing ECS servers in the target region
hcloud ECS ListServersDetails --region=cn-southwest-2 --cli-output="cols=ServerId"
```

If authentication is successful, you will see a list of ECS server IDs (possibly empty if no servers exist).

### Test VPC Access

```bash
hcloud VPC ListVpcs --region=cn-southwest-2
```

---

## Common hcloud Commands for ECS Provisioning

The following hcloud commands are used by the provisioning script (`scripts/provision_kunpeng_server.sh`):

### VPC Operations

| Command | Description |
|---------|-------------|
| `hcloud VPC CreateVpc --region=<region> --vpc.name=<name> --vpc.cidr=<cidr>` | Create VPC |
| `hcloud VPC ShowVpc --region=<region> --vpc_id=<id>` | Get VPC details |
| `hcloud VPC DeleteVpc --region=<region> --vpc_id=<id>` | ⚠️ Delete VPC (**HIGH-RISK: AI MUST NOT auto-execute**) |
| `hcloud VPC ListVpcs --region=<region>` | List VPCs |

### Subnet Operations

| Command | Description |
|---------|-------------|
| `hcloud VPC CreateSubnet --region=<region> --subnet.vpc_id=<id> --subnet.name=<name> --subnet.cidr=<cidr> --subnet.gateway_ip=<ip> --subnet.dnsList.1=<dns1>` | Create Subnet |
| `hcloud VPC ShowSubnet --region=<region> --subnet_id=<id>` | Get Subnet details |
| `hcloud VPC DeleteSubnet --region=<region> --vpc_id=<vpc_id> --subnet_id=<id>` | ⚠️ Delete Subnet (**HIGH-RISK: AI MUST NOT auto-execute**) |

### Security Group Operations

| Command | Description |
|---------|-------------|
| `hcloud VPC CreateSecurityGroup --region=<region> --security_group.name=<name>` | Create Security Group (v3, no vpc_id) |
| `hcloud VPC CreateSecurityGroupRule/v2 --region=<region> --security_group_rule.security_group_id=<id> --security_group_rule.direction=ingress --security_group_rule.protocol=tcp --security_group_rule.port_range_min=<min> --security_group_rule.port_range_max=<max> --security_group_rule.remote_ip_prefix=<cidr>` | Add Rule (v2 API, uses port_range) |
| `hcloud VPC CreateSecurityGroupRule --region=<region> --security_group_rule.security_group_id=<id> --security_group_rule.direction=ingress --security_group_rule.protocol=tcp --security_group_rule.multiport=<port> --security_group_rule.remote_ip_prefix=<cidr> --security_group_rule.action=allow --security_group_rule.priority=1` | Add Rule (v3 API, uses multiport) |
| `hcloud VPC DeleteSecurityGroup --region=<region> --security_group_id=<id>` | ⚠️ Delete Security Group (**HIGH-RISK: AI MUST NOT auto-execute**) |

> **⚠️ Security:** Never use `0.0.0.0/0` as `remote_ip_prefix` for SSH rules. Always restrict to a specific IP or CIDR (e.g., `203.0.113.50/32`).

### EIP Operations

| Command | Description |
|---------|-------------|
| `hcloud EIP CreatePublicip --region=<region> --publicip.type=<type> --bandwidth.name=<name> --bandwidth.size=<size> --bandwidth.charge_mode=<mode> --bandwidth.share_type=<type>` | Create EIP |
| `hcloud VPC ListPublicips --region=<region>` | List EIPs |
| `hcloud VPC DeletePublicip --region=<region> --publicip_id=<id>` | ⚠️ Delete EIP (**HIGH-RISK: AI MUST NOT auto-execute**) |

> **Note:** EIP creation uses `hcloud EIP CreatePublicip` (NOT `hcloud VPC CreatePublicip`). The `--publicip.type` prefix is required.

### ECS Operations

| Command | Description |
|---------|-------------|
| `hcloud ECS CreateServers --region=<region> --server.name=<name> --server.imageRef=<id> --server.flavorRef=<flavor> --server.vpcid=<vpc_id> --server.nics.1.subnet_id=<subnet_id> --server.publicip.id=<eip_id> --server.root_volume.volumetype=<type> --server.root_volume.size=<size> --server.adminPass=<pass> --server.security_groups.1.id=<sg_id> --server.availability_zone=<az>` | Create ECS |
| `hcloud ECS ListServersDetails --region=<region>` | List ECS servers |
| `hcloud ECS ShowJob --region=<region> --job_id=<id>` | Check ECS creation job status |
| `hcloud ECS DeleteServers --region=<region> --servers.1.id=<id>` | ⚠️ Delete ECS (**HIGH-RISK: AI MUST NOT auto-execute**) |

> **Note:** All ECS CreateServers parameters MUST use the `--server.*` prefix. For example: `--server.name`, `--server.imageRef`, `--server.vpcid`, etc.

### IMS (Image) Operations

| Command | Description |
|---------|-------------|
| `hcloud IMS ListImages --region=<region> --__imagetype=gold --__os_type=Linux` | List public Linux images |
| `hcloud IMS ListImages --region=<region> --__imagetype=gold --__platform=HuaweiCloudEuler` | List Huawei Cloud EulerOS images |

> **Note:** IMS ListImages uses double-underscore parameters: `--__imagetype` (NOT `--imagetype`), `--__os_type`, `--__platform`.

> **⚠️ Important:** All hcloud parameters MUST use `--param=value` format (equals sign, no space). For example: `--region=cn-southwest-2`, NOT `--region cn-southwest-2`.

---

## Troubleshooting

### hcloud Command Not Found

**Problem:** `hcloud: command not found`

**Solution:**
1. Verify hcloud is installed: `which hcloud`
2. If installed but not in PATH, add it: `export PATH=$PATH:/path/to/hcloud`
3. Or reinstall following the installation steps above

### Authentication Failed

**Problem:** `authentication failed` or `unauthorized`

**Solution:**
1. Verify AK/SK are correct
2. Check if AK/SK have expired or been revoked
3. Re-run `hcloud configure` with correct credentials
4. Ensure the region is correct (cn-southwest-2 for Guiyang)

### Insufficient Permissions

**Problem:** `Forbidden` or `insufficient permissions`

**Solution:**
The IAM user needs the following permissions:
- `ECS FullAccess` — Create/manage ECS instances
- `VPC FullAccess` — Create/manage VPC, Subnet, Security Group
- `EIP FullAccess` — Create/manage Elastic IPs
- `IMS Access` — List images

Or use a more permissive policy like `AdministratorAccess` for testing.

### Region Not Found

**Problem:** `Region not found` or similar error

**Solution:**
1. Verify the region ID: `cn-southwest-2` (Guiyang 1)
2. List available regions: `hcloud IAM ListRegions`
3. Ensure the region is enabled for your account

### API Rate Limiting

**Problem:** `Too many requests` or rate limit error

**Solution:**
1. Wait a few seconds and retry
2. Reduce the frequency of API calls
3. hcloud has built-in retry logic for transient errors

### Parameter Format Error

**Problem:** `Invalid parameter` or similar error

**Solution:**
1. Ensure all parameters use `--param=value` format (equals sign)
2. Check parameter names against the API documentation
3. Use `--cli-output=json` for structured output

---

## Security Best Practices

1. **Never share AK/SK in conversation** — Use `hcloud configure` interactively
2. **Use IAM temporary credentials** when possible — Prefer agency delegation or temporary AK/SK
3. **Least privilege principle** — Grant only the minimum required permissions
4. **Rotate AK/SK regularly** — Recommended every 90 days
5. **Delete unused resources (USER RESPONSIBILITY)** — Clean up ECS, VPC, EIP when no longer needed. **⚠️ AI MUST NOT auto-execute delete commands.** User must manually execute cleanup commands after reviewing resource list.
6. **Monitor billing** — Check Huawei Cloud billing dashboard regularly
7. **Restrict Security Group rules** — Limit SSH access to specific IPs when possible
8. **Protect credential files** — Ensure hcloud config files have appropriate permissions (600)

> **🚫 HIGH-RISK: Resource Deletion Policy**
> - AI MUST NEVER auto-execute any `hcloud ... Delete*` commands
> - AI should provide cleanup commands as TEXT ONLY for user to execute manually
> - AI must list all resource IDs and warn about irreversibility before providing delete commands
> - Deletion is IRREVERSIBLE — once deleted, resources cannot be recovered

---

## Official Documentation

- [KooCLI Installation Guide](https://support.huaweicloud.com/cli/index.html)
- [KooCLI Command Reference](https://support.huaweicloud.com/cli/cli_01.html)
- [ECS API Reference](https://support.huaweicloud.com/api-ecs/ecs_02_0001.html)
- [VPC API Reference](https://support.huaweicloud.com/api-vpc/vpc_api01_0000.html)
