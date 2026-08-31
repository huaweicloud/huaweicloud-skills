---
name: huawei-cloud-ecs-dsh-deploy
description: |
  Huawei Cloud Flexus X Instance Deployment - DeepSeek Harness (dsh). ⚠️ Deployment involves actual charges, must confirm region/flavor/billing mode with user before execution.
  Triggers include: "部署DeepSeek Harness", "部署dsh", "部署DeepSeek智能体", "创建AI智能体服务器", "Deploy DeepSeek Harness", "Deploy dsh", "Create AI Agent Server", "Deploy AI Harness", "DeepSeek Harness", "dsh", "Flexus X", "ECS部署", "AI智能体".
triggers:
  - 部署DeepSeek Harness
  - 部署dsh
  - 部署DeepSeek智能体
  - 创建AI智能体服务器
  - Deploy DeepSeek Harness
  - Deploy dsh
  - Create AI Agent Server
  - Deploy AI Harness
  - DeepSeek Harness
  - dsh
  - Flexus X
  - ECS部署
  - AI智能体
tags: [DeepSeek Harness, dsh, AI Agent, Flexus Cloud Server X Instance, Deployment]
---

# Huawei Cloud Flexus X + DeepSeek Harness (dsh) One-Click Deployment

## ⚠️ Pre-Deployment Checklist (Highest Priority)

**This skill involves actual charges (creating Huawei Cloud Flexus X instance), must confirm with user before execution!**

**Required Confirmations:**
- Region (default: cn-north-4)
- Flavor (default: x1.2u.4g, 2 cores 4GB)
- Billing Mode (default: pay-as-you-go)

**Prohibited Actions:**
- ❌ Do NOT execute deployment before user explicitly confirms
- ❌ Do NOT use default config for deployment without asking user
- ❌ Do NOT assume user accepts default values
- ❌ **Do NOT fabricate or estimate prices** (e.g., "≈ ¥0.2-0.3/hour"); always refer users to the official pricing page

**Correct Process:**
1. Show user the default config (region, flavor, billing mode)
2. Inform users that for pricing, use the official price calculator: https://www.huaweicloud.com/pricing/calculator.html#/hecs
3. Ask if user confirms or needs modifications
4. Execute deployment only after user inputs `CONFIRM` (uppercase)

---

## Overview

This skill provides one-click deployment of **DeepSeek Harness (dsh)** — the open-source AI agent harness from DeepSeek AI — on Huawei Cloud Flexus X instances:

| Module | Description | Command |
| -------- | ------------- | --------- |
| **List Regions** | Show available regions | `python3 scripts/deploy_dsh.py --list-regions` |
| **Test Connection** | Verify AK/SK credentials | `python3 scripts/deploy_dsh.py --test` |
| **Deploy** | Purchase Flexus X instance and deploy dsh | `python3 scripts/deploy_dsh.py` |

### Components

| Component | Description | Port | Notes |
|------|------|------|------|
| **Node.js** | JavaScript runtime | - | Node.js 22 LTS, installed to /opt/nodejs/current |
| **@deepseek-ai/dsh** | DeepSeek Harness CLI | 3080 (loopback) | Official npm package, **dsh web** binds to 127.0.0.1 only |
| **Nginx** | Reverse proxy | 80 (loopback) | Local server proxy 80 → 127.0.0.1:3080 (public access does **not** use this port, see SSH tunnel below) |
| **systemd** | Service manager | - | **dsh.service** manages dsh lifecycle, auto-restart on failure |
| **UFW** | Firewall | - | Allows 22 (SSH)/80/443 (80/443 blocked by security group, not reachable from public) |

### Deployed Applications

| Application | Description | Port | Access URL |
|------|------|------|----------|
| **dsh Web UI** | AI agent harness web interface | 3080 (loopback) | http://127.0.0.1:3080 (**SSH tunnel required first**, see [Local Access Guide](#-local-access-guide-ssh-port-forwarding)) |

> ✅ **Important**: dsh `web` command intentionally binds to `127.0.0.1` only — the CLI rejects `--host 0.0.0.0`. **Remote access goes through an SSH local port-forwarding tunnel**: run `ssh -L 3080:127.0.0.1:3080 root@{public_ip}` on your machine, then open `http://127.0.0.1:3080`. Only port 22 needs to be open in the security group — dsh is never exposed to the public, which is more secure.

### Use Cases

1. **AI Agent Development** - Run and manage DeepSeek AI agent harness with a web UI
2. **Automation & Workflows** - Build multi-step agent workflows with the "everything is a plugin" architecture
3. **Development & Testing** - Quickly set up an AI agent development environment
4. **Team Collaboration** - Share agent workspaces across a team
5. **Multi-Region Deployment** - Provide nearby access for global users

### Important Notes

**⚠️ All scripts and environment check scripts are in the skill package. Must use skill `action=exec` for execution, do NOT run directly in shell.**

## Prerequisites

Before using this skill, ensure the following conditions are met:

### 1. Huawei Cloud Account

- Valid Huawei Cloud account
- Account has completed real-name authentication
- Account has sufficient balance or bound payment method

### 2. AK/SK Credentials

- Created Huawei Cloud access key (AK/SK)
- AK/SK has the following permissions:
  - `ECS`: Elastic Cloud Server management
  - `VPC`: Virtual Private Cloud management
  - `EIP`: Elastic Public IP management
  - `COC`: Cloud Operations Center management
- How to obtain: [Huawei Cloud Console](https://console.huaweicloud.com/) → My Credentials → Access Keys → Create Access Key

**Credential Configuration Methods:**

| Method | Description | Priority |
| -------- | ------------- | ---------- |
| **Environment Variables** | HW_ACCESS_KEY, HW_SECRET_KEY, HW_SECURITY_TOKEN | **Highest (Recommended)** |
| **Command Line Arguments** | --ak, --sk, --security-token | Lower (Accepted but not recommended) |

**Credential Types (By Recommendation Order):**

| Priority | Type | Parameters | Description |
| ------ | ---- | ---------- | ----------- |
| **First Choice** | **Temporary AK/SK** | Environment Variables + HW_SECURITY_TOKEN | Temporary credentials with security token, higher security |
| **Second Choice** | Permanent AK/SK | Environment Variables Only | Long-term access keys from Huawei Cloud Console |

> **Note:** Credentials are prioritized from environment variables; users are never asked to directly input AK/SK. However, if the user voluntarily provides credentials through other methods (e.g., conversation input, configuration files), credential parsing is still supported.

### 3. IAM Permissions

| Service | Policy | Required Actions |
| --------- | -------- | ------------------ |
| ECS | ECS FullAccess | ecs:* |
| VPC | VPC FullAccess | vpc:* |
| EIP | VPC FullAccess | vpc:publicIps:* |
| COC | COC FullAccess | coc:* |

> 📖 Detailed least-privilege policy: [IAM Policies](references/iam-policies.md)

### 4. Runtime Environment

- Python 3.8 or higher

**Required Dependencies:**

| Package | Version | Description |
|------|---------|------|
| requests | ≥2.31.0 | HTTP request library |
| huaweicloudsdkcore | ≥3.1.70 | Huawei Cloud SDK core library |
| huaweicloudsdkecs | ≥3.1.70 | Elastic Cloud Server SDK |
| huaweicloudsdkcoc | ≥3.1.70 | Cloud Operations Center SDK |

Install command:
```bash
pip install requests huaweicloudsdkcore huaweicloudsdkecs huaweicloudsdkcoc
```

### 5. Network Environment

- Ability to access Huawei Cloud API endpoints
- Required endpoints:
  - `ecs.{region}.myhuaweicloud.com`
  - `vpc.{region}.myhuaweicloud.com`
  - `iam.myhuaweicloud.com`
  - `coc.myhuaweicloud.com`

## ⚠️ Security Notes

### ⚠️ Security Execution Rules (Highest Priority)

| Rule | Description |
|------|------|
| 1 | All scripts must be executed through skill action=exec, **prohibited** from running directly in shell |
| 2 | **Prohibited** from printing script content or commands containing AK/SK/Token in conversation |
| 3 | **Prohibited** from creating temporary script files, prefer inline execution (python3 -c) |
| 4 | On execution failure, return only error message, **prohibited** from rewriting script or printing complete commands |
| 5 | AK/SK/Token must be passed through environment variables, **prohibited** from appearing in conversation |
| 6 | ⚠️ **Absolutely prohibited** from exposing, recording, or printing AK/SK/Token values in any form |

### ⚠️ Security Group Policy (Critical - Read Before Deployment)

**Deployment Strategy - Simple & Secure:**

| Setting | Value | Description |
|---------|-------|-----------|
| **Security Group Status** | Empty (no inbound rules) | Script only creates security group, does not add any rules |
| **Default Access** | All ports blocked | Before you configure rules, no IP can access the server |
| **Ports to Open** | **Only 22 (SSH)** | dsh Web UI is accessed via SSH tunnel; 80/443 do not need to be public |

**How to Configure After Deployment:**

1. Access [Huawei Cloud Console](https://console.huaweicloud.com/) → ECS → Security Groups
2. Find the security group named `sg-dsh`
3. **Manually** add an inbound rule: protocol TCP, port **22**, source IP = your public IP + `/32` suffix (e.g., `203.0.113.10/32`)
4. **Do not** add broad 80/443 rules — dsh is accessed only through the SSH tunnel; no other ports need to be exposed

> 💡 **Why Use Empty Security Group?** Security First - You have full control over which IPs can access the server. Only port 22 + SSH tunnel — dsh Web UI is never exposed publicly, so even an API key leak cannot be accessed from the internet.

**⚠️ AK/SK Security:** See [Prerequisites - AK/SK Credentials](#2-aksk-credentials). **Prohibited from exposing, recording, or printing AK/SK/Token values in any form.**

### ⚠️ dsh Security (Critical)

| Rule | Description |
|------|------|
| 1 | dsh binds to **127.0.0.1 only** — never force it to listen on 0.0.0.0 (CLI rejects it by design) |
| 2 | Remote access via **SSH local port forwarding**: run **ssh -L 3080:127.0.0.1:3080 root@{public_ip}** locally, then open http://127.0.0.1:3080 |
| 3 | DEEPSEEK_API_KEY is injected via systemd drop-in with **file mode 600** — never in the unit file, never in logs |
| 4 | API key is **optional** at deploy time; users can also set it later in the Web UI (Settings → Models) |
| 5 | dsh runs under a **dedicated system user** dsh (no-shell), not root |
| 6 | Production use **must** enable HTTPS (e.g. Let's Encrypt, via Nginx local proxy) |

### 🔐 SSL/TLS Verification

- 🔒 **SSL/TLS certificate verification is enabled by default** for all Huawei Cloud API requests (`verify=true`).
- The `HW_VERIFY_SSL` environment variable can override this — `HW_VERIFY_SSL=false` disables verification.
- ⚠️ **`HW_VERIFY_SSL=false` is for testing only.** Never disable SSL verification in production; it exposes AK/SK credentials and API traffic to man-in-the-middle attacks.

## Core Commands and Usage

> 💡 **Note**: When no operation options are provided, deployment operation is executed by default.

### Command Options

| Command/Option | Function | Description |
|-----------|------|------|
| `python3 scripts/deploy_dsh.py` | **Deploy** | Purchase Flexus X instance and deploy dsh |
| `python3 scripts/deploy_dsh.py --list-regions` | Show Available Regions | Show all available regions (19 regions) |
| `python3 scripts/deploy_dsh.py --test` | Test Connection | Verify AK/SK credentials |
| `python3 scripts/deploy_dsh.py --list-servers` | List Servers | Show all servers in specified region |
| `python3 scripts/deploy_dsh.py --delete <ID>` | Delete Server | Delete server by ID or name |
| `python3 scripts/deploy_dsh.py --status <ID>` | Check Status | Check deployment status by server ID |

### Global Parameters

> 💡 **Required Parameters**: `--ak`, `--sk` (or set `HW_ACCESS_KEY`, `HW_SECRET_KEY` environment variables)
> 💡 **Recommended Parameters**: `--security-token` (or set `HW_SECURITY_TOKEN` for temporary credentials)

### Execution Examples

**Example 1: List available regions**
```bash
python3 scripts/deploy_dsh.py --list-regions
```

**Example 2: Test AK/SK connection**
```bash
python3 scripts/deploy_dsh.py --test
```

**Example 3: Deploy with default settings (requires user confirmation)**
```bash
python3 scripts/deploy_dsh.py
```

**Example 4: Deploy with custom region and flavor**
```bash
python3 scripts/deploy_dsh.py --region cn-east-3 --flavor x1.4u.8g
```

**Example 5: List existing servers**
```bash
python3 scripts/deploy_dsh.py --list-servers --region cn-north-4
```

**Example 6: Check deployment status**
```bash
python3 scripts/deploy_dsh.py --status <server_id>
```

**Example 7: Delete a server**
```bash
python3 scripts/deploy_dsh.py --delete <server_id_or_name>
```

| Parameter | Description | Default |
| ----------- | ------------- | --------- |
| --region | Target region | cn-north-4 |
| --flavor | Instance flavor | x1.2u.4g |
| --name | Server name | Auto-generated |
| --password | Server password | Auto-generated |
| --charging-mode | Billing mode | postPaid |
| --bandwidth | EIP bandwidth (Mbps) | 100 |
| --volume-size | System disk (GB) | 40 |
| --coc-region | COC service region | cn-north-4 |
| --coc-timeout | COC script execution timeout (seconds) | 1800 |

### dsh Parameters

| Parameter | Description | Default |
| ----------- | ------------- | --------- |
| --dsh-port | dsh listening port (loopback only) | 3080 |
| --api-key | DEEPSEEK_API_KEY to pre-seed into the dsh service (optional) | Not set |

> 💡 The dsh port is bound to 127.0.0.1 only — access it locally via SSH tunnel (`ssh -L 3080:127.0.0.1:3080 root@{ip}`). No security group rule is needed for the dsh port itself.

### Advanced Parameters

> 💡 The following parameters are for advanced users, not needed for general scenarios

| Parameter | Description | Default |
| ----------- | ------------- | --------- |
| --project-id | Huawei Cloud project ID (optional) | Auto-fetched |
| --image | Image ID | Default Ubuntu 22.04 |
| --zone | Specify availability zone | Auto-select |
| --random-zone | Randomly select availability zone | Off |
| --no-eip | Do not create elastic public IP | Off |
| --auto-confirm | Skip interactive confirmation (use with caution!) | Off |

### Credential Configuration Examples

**Method 1: Using Environment Variables (First Choice - Strongly Recommended)**

```bash
python3 scripts/deploy_dsh.py
```

**Method 2: Using Command Line Arguments (Second Choice - Accepted)**

```bash
# Temporary credentials
python3 scripts/deploy_dsh.py \
  --ak <AK> --sk <SK> --security-token <TOKEN> \
  --region cn-north-4 \
  --flavor x1.2u.4g

# Permanent credentials
python3 scripts/deploy_dsh.py \
  --ak <AK> --sk <SK> \
  --region cn-north-4 \
  --flavor x1.4u.8g
```

### 🔒 Anti-Duplicate Deployment Mechanism

**System built-in lock file mechanism prevents duplicate deployments:**

- Lock file automatically created at deployment start: `dsh_deploy.lock`
- Lock file validity: 30 minutes (auto-expires)
- When lock file exists, new deployment automatically blocked
- Lock file path: system temp directory (`/tmp/dsh_deploy.lock` on Linux, `%TEMP%\dsh_deploy.lock` on Windows)

**⚠️ Important Notes:**
- ❌ **Do NOT run multiple deployment tasks simultaneously**
- ❌ **Duplicate deployments will create multiple servers, incurring double charges**
- Check if lock file was deleted after deployment failure

**Failure Handling:** On deployment failure, return failure reason and guide user to check console, no automatic retry or parameter modification

### 🚀 Domestic Mirror Acceleration

**Built-in domestic mirror acceleration for faster deployment:**

| Mirror Type | Mirror Source | Description |
|----------|--------|------|
| **Ubuntu APT** | USTC (mirrors.ustc.edu.cn) | System package updates |
| **npm registry** | npmmirror (registry.npmmirror.com) | @deepseek-ai/dsh install + Node.js binary download |
| **pip (local)** | Huawei Cloud (repo.huaweicloud.com) | Python dependency installation on the operator side |

**Mirror configuration location:** `scripts/coc_deploy.py` in `COMBINED_INSTALL_SCRIPT`

## Module Details

### Deploy DeepSeek Harness (dsh)

> ⏱️ **Deployment Time**: Entire process takes about **10 minutes** (server creation 3-5 minutes + software deployment 5-8 minutes), please be patient

> 💡 See [Credential Configuration Examples](#credential-configuration-examples) for deployment commands, and [Global Parameters](#global-parameters) for all parameters

**Deployment stages on the server (via COC script):**

| Stage | Operation | Description |
|------|------|------|
| 0 | Domestic Mirrors | Configure USTC APT mirror + npmmirror npm registry |
| 1 | Node.js 22 LTS | Install via official tarball (npmmirror mirror, fallback nodejs.org) |
| 2 | @deepseek-ai/dsh | npm install -g @deepseek-ai/dsh |
| 3 | Dedicated User | Create system user dsh, prepare DSH_HOME (/home/dsh/.dsh) |
| 4 | systemd Service | Write dsh.service (restart=on-failure, ProtectSystem, ReadWritePaths) |
| 5 | Nginx Reverse Proxy | 80 → 127.0.0.1:3080, WebSocket upgrade headers (loopback only) |
| 6 | Firewall | UFW allow 22/80/443 (80/443 blocked by security group, not reachable from public) |
| 7 | Start & Verify | Start dsh, wait for loopback HTTP 200, print deployment info |

## Available Regions

**Common Regions** (more regions run `--list-regions`):

| Region ID | Region Name | Supported Flexus X Instance Types |
| ----------- | ------------- | ------------- |
| cn-north-4 | North China-Beijing 4 | x1, x1e, x1i, x2e |
| cn-east-3 | East China-Shanghai 1 | x1, x1e, x1i, x2e |
| cn-south-1 | South China-Guangzhou | x1, x1e, x1i, x2e |
| ap-southeast-1 | China-Hong Kong | x1, x2e |
| ap-southeast-3 | Asia Pacific-Singapore | x1, x1e, x2e |

> 💡 Complete region list (19) run: `python3 scripts/deploy_dsh.py --list-regions`

## Output Format Specification

> ⛔ **CRITICAL — The SSH tunnel command MUST be output verbatim, never omitted, summarized, or paraphrased:**
>
> After deployment, the reply **MUST** include a copy-paste-ready SSH tunnel command line, with `{public_ip}` **replaced by the actual public IP** from the script output.
> For example, if the script outputs `Public IP: 121.36.x.x`, the reply must contain:
> ```
> ssh -L 3080:127.0.0.1:3080 root@121.36.x.x
> ```
> **NEVER** write only "please establish an SSH tunnel" without the full command — users need to copy-paste it; missing the command makes the Web UI inaccessible.

**After successful deployment, must return results in the following format:**

```
🎉 Deployment Successful!

| Item | Value |
|------|-----|
| Server Name | {server_name} |
| Public IP | {public_ip} |
| SSH Password | {password} |
| Region | {region_id} ({region_name}) |

🌐 Access URL (SSH tunnel required first):
- Run on your local machine (Windows PowerShell / macOS Terminal), replacing {public_ip} with the Public IP from the table above:
  ```
  ssh -L 3080:127.0.0.1:3080 root@{public_ip}
  ```
- Enter the SSH password (from the table above), keep the terminal window open
- Then open in your browser: http://127.0.0.1:3080

🔑 SSH Login: `ssh root@{public_ip}` (password: {password})

📦 Installed Components:
- Node.js 22 LTS ({node_version})
- @deepseek-ai/dsh ({dsh_version}, systemd service 'dsh')
- Nginx reverse proxy (80 → 127.0.0.1:{dsh_port}, loopback only)

📋 Post-deployment TODO:
1. Configure security group: Console → ECS → Security Groups → sg-dsh → Add inbound rule (TCP 22, source your_ip/32)
2. Establish SSH tunnel locally (see command above), then open Web UI: http://127.0.0.1:3080
3. In the Web UI: Settings → Models, enter your DeepSeek API key and save
4. Choose a workspace directory, then start a session

📖 [DeepSeek Harness GitHub](https://github.com/deepseek-ai/deepseek-harness) | [Flexus X Docs](https://support.huaweicloud.com/productdesc-flexusx/pd_01_0002.html)
```

**Variables:** `{server_name}` server name | `{public_ip}` public IP | `{password}` SSH password | `{region_id}`/`{region_name}` region | `{dsh_port}` dsh loopback port | `{node_version}` Node.js version | `{dsh_version}` dsh CLI version

## 🔐 Local Access Guide (SSH Port Forwarding)

> ⚠️ **You MUST follow this section after deployment**, otherwise the browser cannot open the dsh Web UI. dsh only listens on the server's loopback address `127.0.0.1:3080` — you need to establish an SSH tunnel on **your local machine** to forward local port 3080 to the server's 3080 port.

**How it works**: `ssh -L 3080:127.0.0.1:3080 root@{public_ip}` means — forward all traffic on your local `3080` port through the encrypted SSH channel to `127.0.0.1:3080` on the cloud server (where dsh runs). Data is fully encrypted, dsh Web UI is never exposed publicly, and only someone who can SSH can access it.

### Windows Users (PowerShell)

1. **Open PowerShell**: Press `Win` key → type `powershell` → Enter (or press `Win+X` → select "Windows PowerShell" / "Windows Terminal")
2. **Run the tunnel command** (replace `{public_ip}` with the public IP from the deployment output):
   ```powershell
   ssh -L 3080:127.0.0.1:3080 root@{public_ip}
   ```
3. **First-time fingerprint confirmation**: if prompted `Are you sure you want to continue connecting (yes/no)?`, type `yes` and press Enter
4. **Enter the password**: type the SSH password from the deployment output (characters are not displayed while typing — this is normal), press Enter
5. **Keep the window open**: once you see the remote shell prompt (e.g., `root@xxx:~#`), the tunnel is established. **Do not close this window**
6. **Open your browser**: visit `http://127.0.0.1:3080` to open the dsh Web UI

> 💡 Windows 10/11 **ships with** the OpenSSH client — no extra installation needed. If you get "'ssh' is not recognized", go to Settings → Apps → Optional Features → add "OpenSSH Client".

### macOS Users (Terminal)

1. **Open Terminal**: press `Command + Space` → type `Terminal` → Enter (or Finder → Applications → Utilities → Terminal)
2. **Run the tunnel command** (replace `{public_ip}` with the public IP from the deployment output):
   ```bash
   ssh -L 3080:127.0.0.1:3080 root@{public_ip}
   ```
3. **First-time fingerprint confirmation**: if prompted `Are you sure you want to continue connecting (yes/no)?`, type `yes` and press Enter
4. **Enter the password**: type the SSH password from the deployment output (characters are not displayed while typing — this is normal), press Enter
5. **Keep the window open**: once you see the remote shell prompt, the tunnel is established. **Do not close this window**
6. **Open your browser**: visit `http://127.0.0.1:3080` to open the dsh Web UI

> 💡 macOS ships with the OpenSSH client — no extra installation needed.

### Closing the Tunnel & Advanced Usage

| Scenario | Action |
|------|------|
| **Close the tunnel** | Press Ctrl+C in the PowerShell/Terminal window, or type exit and press Enter |
| **Forward only, no shell** | ssh -N -L 3080:127.0.0.1:3080 root@{public_ip} (-N runs no remote command; no shell prompt — recommended) |
| **macOS background** | ssh -f -N -L 3080:127.0.0.1:3080 root@{public_ip} (-f runs in background; stop with pkill -f "ssh -f -N" or killall ssh) |
| **Local port 3080 in use** | Use another local port: ssh -L 18080:127.0.0.1:3080 root@{public_ip}, then open http://127.0.0.1:18080 |
| **Passwordless login (recommended)** | Run ssh-copy-id root@{public_ip} (macOS/Linux) or use an SSH key in PowerShell for passwordless connections later |

> ⚠️ **Note**: after the tunnel is closed, `http://127.0.0.1:3080` becomes unreachable — this is normal; just re-run the tunnel command. After every machine reboot you must re-establish the tunnel.

## dsh Initial Setup

After establishing the SSH tunnel, open the dsh Web UI (`http://127.0.0.1:3080`):

| Setting | Description |
|--------|------|
| **API Key** | Go to Settings → Models, enter your DeepSeek API key and save (if not pre-seeded via --api-key) |
| **Workspace** | Choose a workspace directory to store sessions and artifacts |
| **Start Session** | Start a session in the web UI and the harness will respond |

> ⚠️ **Important**: dsh can read/write files and run commands — only port 22 should be open in the security group (source `your_ip/32`); dsh is accessed via SSH tunnel; never open 80/3080 to the public, never use `0.0.0.0/0`.

## Deployment Architecture

This skill uses **COC (Cloud Operations Center)** for secure deployment, replacing traditional SSH method:

```
┌─────────────────────────────────────────────────────────────┐
│                    Flexus Cloud Server X Instance                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Ubuntu 22.04 Server                    │    │
│  ├─────────────────────────────────────────────────────┤    │
│  │                                                     │    │
│  │   SSH tunnel ──► dsh (127.0.0.1:3080)              │    │
│  │   (port 22)       (loopback only)                   │    │
│  │                                                     │    │
│  │  ┌───────────────┐      ┌───────────────┐          │    │
│  │  │    Nginx      │      │    systemd    │          │    │
│  │  │   (port 80)   │      │  dsh.service  │          │    │
│  │  │   loopback    │      └───────┬───────┘          │    │
│  │  └───────────────┘              │                   │    │
│  │                                 ▼                   │    │
│  │                            dsh web (Node.js 22)     │    │
│  │                             user: dsh (no-shell)   │    │
│  │                             DSH_HOME: /home/dsh/.dsh│    │
│  └───────────┬──────────────────────┬──────────────────┘    │
│              │                      │                       │
│              │              ┌───────┴───────┐              │
│              │              │ Security Group │             │
│              │              │    sg-dsh     │             │
│              │              │ allow 22 /32  │             │
│              │              └───────┬───────┘             │
│              │                      │                      │
│              └──────────────────────┼──────────────────────┘
│                                     ▼                       │
│                           ┌─────────────┐                  │
│                           │    EIP      │  SSH only (22)   │
│                           └─────────────┘                  │
│                                     ▲                       │
│                                     │                       │
│                           ┌─────────┴─────────┐            │
│                           │  COC (Cloud       │           │
│                           │  Operations       │           │
│                           │  Center)          │           │
│                           │  Secure Script    │           │
│                           │  Execution        │           │
│                           └───────────────────┘            │
└─────────────────────────────────────────────────────────────┘

              ┌─────────────────────────────┐
              │  User machine (Windows/macOS) │
              │  ssh -L 3080:127.0.0.1:3080 root@{ip} │
              │  Browser → http://127.0.0.1:3080      │
              └─────────────────────────────┘
```

### Deployment Flow

| Stage | Operation | Description |
|------|------|------|
| 1 | Create Server | Create Flexus X instance via Huawei Cloud SDK |
| 2 | Configure Security Group | Create sg-dsh security group (empty rules, manual config needed) |
| 3 | Wait for UniAgent | Wait for COC UniAgent to come online |
| 4 | Create COC Script | Create installation script in Cloud Operations Center |
| 5 | Execute Script | Execute script on target instance via COC |
| 6 | Verify Deployment | Check dsh service and loopback port status |

### COC Deployment Advantages

Compared to SSH method, COC deployment has the following advantages:

| Feature | SSH Method | COC Method |
|------|---------|---------|
| **Security** | Requires open SSH port, security risk | Secure execution via Cloud Operations Center, no SSH port needed |
| **Permission Control** | Requires SSH password or key | Uses Huawei Cloud IAM permission control |
| **Audit Logs** | Requires manual logging | COC automatically records execution logs |
| **Batch Deployment** | Requires sequential SSH connections | Supports batch deployment of multiple servers |
| **Error Handling** | Requires manual processing | COC provides standardized error handling |

### Log Files

| File Path | Description |
|----------|------|
| /var/log/dsh-bootstrap.log | Deployment script execution log |
| /home/dsh/.dsh/ | dsh data directory (sessions, workspaces, artifacts) |
| /etc/systemd/system/dsh.service | dsh systemd unit file |
| /etc/systemd/system/dsh.service.d/10-credentials.conf | DEEPSEEK_API_KEY drop-in (mode 600, only if --api-key used) |
| /etc/nginx/conf.d/dsh.conf | Nginx reverse proxy config |

## File Structure

```
skills/huawei-cloud-ecs-dsh-deploy/
├── SKILL.md                    # English version
├── scripts/
│   ├── deploy_dsh.py           # Main deployment script
│   ├── pyproject.toml          # Dependency list
│   ├── huawei_cloud_ecs.py     # Huawei Cloud SDK wrapper
│   ├── coc_deploy.py           # COC deployment module (includes install script)
│   ├── config.py               # Configuration constants
│   ├── utils.py                # Utility functions
│   └── query_regions.py        # Region query helper
└── references/
    ├── acceptance-criteria.md     # Acceptance criteria
    ├── cli-installation-guide.md  # CLI installation guide (KooCLI & dependencies)
    ├── iam-policies.md            # IAM policies
    ├── verification-method.md     # Verification methods
    └── conversation-examples.md   # Natural-language conversation examples
```

## Error Handling

### Known Limitations

| Limitation | Description | Solution |
|------|------|----------|
| **dsh binds loopback only** | dsh web refuses --host 0.0.0.0 by design | Establish SSH tunnel locally: ssh -L 3080:127.0.0.1:3080 root@{ip}, then open http://127.0.0.1:3080 |
| **Status Check Method** | --status checks the server instance state; dsh health check requires the SSH tunnel | Verify by opening http://127.0.0.1:3080 after tunneling, or run curl http://127.0.0.1:3080 on the server |

### Common Errors

| Error Code | Description | Solution |
| ------------ | ------------- | ---------- |
| 401 Unauthorized | AK/SK invalid | Verify AK/SK is correct and valid |
| 403 Forbidden | Permission denied | Add required IAM policies |
| QuotaExceeded | Resource quota exceeded | Check ECS/VPC/EIP quotas |
| ServerLimitExceeded | Instance count limit | Release unused instances |
| FlavorNotFound | Flavor unavailable | Try other region or flavor |
| Timeout | Server creation timeout | Check actual status in console |
| Node.js < 22 | dsh requires Node.js >= 22 | Install script auto-installs Node 22 LTS |

## References

### Skill Reference Documents

- [Acceptance Criteria](references/acceptance-criteria.md) - Deployment verification standards
- [IAM Policies](references/iam-policies.md) - Permission configuration
- [Verification Methods](references/verification-method.md) - Skill verification
- [Conversation Examples](references/conversation-examples.md) - Dialog scenarios & response rules

### External References

- [DeepSeek Harness GitHub](https://github.com/deepseek-ai/deepseek-harness) - Official repository (default branch: master)
- [Flexus Cloud Server X Instance Documentation](https://support.huaweicloud.com/productdesc-flexusx/pd_01_0002.html) - Flexus X instance product documentation
- [AK/SK Authentication](https://support.huaweicloud.com/api-iam/iam_01_0001.html) - IAM authentication guide
