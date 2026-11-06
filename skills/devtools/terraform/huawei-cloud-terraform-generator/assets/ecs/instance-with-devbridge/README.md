# ECS with DevBridge SSH Tunnel Auto-Setup (B1: FunctionGraph Proxy)

## What This Template Does

Creates an ECS instance with **DevBridge SSH tunnel pre-installed and auto-starting on boot**, with **zero inbound security group rules** and **zero credentials in user_data**.

Supports **both Linux and Windows** — OS type is auto-detected from the image API:

| OS | Script | Tunnel Port | Auto-start | Connect via |
|----|--------|-------------|------------|-------------|
| Linux | bash + systemd | SSH 22 | systemd service | `ssh root@localhost -p <port>` |
| Windows | PowerShell + Scheduled Task | RDP 3389 | Windows Scheduled Task | Remote Desktop → `localhost:<port>` |

| Feature | Detail |
|---------|--------|
| Security Group | **No inbound rules** — all ingress denied by default |
| Egress | TCP 443 + TCP 80 + UDP 53 only |
| EIP | Assigned to ECS for outbound internet access |
| DevBridge | Auto-installed via cloud-init user_data on first boot |
| OS Detection | `data.huaweicloud_images_image` API query → `os` field → regex match |

## Architecture (B1: FunctionGraph Proxy)

```
Sandbox (before apply)
  └── ensures a DevBridge API Key exists (reuse an existing valid key, or
      create a new one via DevStage API using the sandbox's user-level AK/SK)

Terraform (provider auth uses user AK/SK — NOT written into any artifact)
  │
  ├── creates FunctionGraph function (holds ONLY the pre-created DevBridge
  │     API Key as EXISTING_API_KEY — NO AK/SK, NO DevStage call)
  ├── creates IAM agency (ECS can invoke the function)
  └── creates ECS (user_data has only function URN + region + project_id — NO credentials)
        │
        └── ECS boots
              → metadata service 169.254.169.254 (get agency STS) ← no user_data involved
              → invoke FunctionGraph (with STS)
              → function returns the pre-created DevBridge API Key (holds no AK/SK)
              → ECS sets up tunnel, encrypts key to disk
```

## Security Model

| Where | Contains AK/SK? | Contains DevBridge API Key? |
|-------|-----------------|---------------------------|
| user_data | **No** | **No** (fetched from function at runtime) |
| ECS metadata | **No** | **No** |
| tfstate (ECS) | **No** | **No** |
| tfstate (function) | **No** | Yes (revocable, tunnel-only scope) |
| FunctionGraph console | **No** | Yes (revocable, tunnel-only scope) |
| ECS local disk | No | Yes (encrypted, AES-256-GCM) |
| Cloud (after destroy) | No | No — function destroyed together with ECS/VPC |

**Key security property:** user AK/SK never enter user_data, ECS metadata, cloud-init logs, FunctionGraph user_data, or tfstate. They are used only for (a) the Terraform provider's apply-time authentication, and (b) creating the DevBridge API Key in the sandbox before apply. The FunctionGraph function holds only the revocable DevBridge API Key (tunnel-only scope), never AK/SK.

**FunctionGraph retention:** the function is kept until `terraform destroy` (it holds only the revocable DevBridge API Key, no AK/SK — see Security Model). No separate `-target` cleanup is needed or desired; keeping the function eliminates the Windows slow-boot race (there is no "destroy the function too early → ECS never gets the key" hazard).

## Prerequisites

1. **DevBridge API Key (pre-created in the sandbox)** — see `ecs-devbridge-option.md` Step 0. Reuse an existing valid sandbox key, or create one via DevStage API. The function never creates keys itself.
2. **DevStage development environment** — required only when creating a NEW key (not when reusing an existing sandbox key). Check via DevStage API: `GET /open-api-public/v2/devenvs`
3. **IAM permissions** — two modes:
   - **Custom role** (`use_custom_role = true`): needs IAM agency + custom role + FunctionGraph function creation permissions. Least privilege — ECS only gets `functiongraph:invokeFunction`.
   - **Predefined role** (`use_custom_role = false`, default): needs IAM agency + FunctionGraph function creation (no custom role creation). Uses `FunctionGraph Administrator` predefined role.
4. **FunctionGraph service** — available by default, no separate activation needed

## Cost

- FunctionGraph: **¥0** (free tier: 1 million invocations/month; this uses 1 invocation per ECS)
- EIP: ~¥0.02/hour
- No other additional cost

## How to Connect After Creation

```bash
# On your local machine (not the ECS):
devbridge auth login --api-key <same-api-key>
devbridge list                    # find the tunnel ID
devbridge connect <tunnel-id>     # establishes local port forwarding

# Linux ECS:
ssh root@localhost -p <port>      # port shown in connect output

# Windows ECS:
# Use Remote Desktop Connection → localhost:<port>
```

No security group changes needed. No public SSH/RDP port exposed.

## Files

| File | Purpose |
|------|---------|
| `main.tf` | FunctionGraph function, IAM role + agency, VPC, subnet, SG (no ingress), EIP, ECS with B1 user_data |
| `function_code.py` | FunctionGraph function code — returns the pre-created DevBridge API Key (no AK/SK, no DevStage call) |
| `variables.tf` | All variables (auth, network, ECS, EIP, agency) |
| `providers.tf` | Huawei Cloud + random provider configuration |