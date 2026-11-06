# Deploy Instance with DevBridge — Best Practices

## Overview

This document describes best practices for deploying ECS instances with DevBridge SSH tunnel auto-setup using the B1 (FunctionGraph proxy) architecture.

> **Architecture status:** this document reflects the **current** design, where the DevBridge
> API Key is **pre-created in the sandbox before apply** and the FunctionGraph function only
> **forwards** that key. The function holds **no AK/SK** and does **not** call DevStage API.
> (An older design had the function call DevStage API with AK/SK in its env vars — that has been
> superseded; see `ecs-devbridge-option.md` Part 3A for the authoritative flow.)

## Architecture: B1 (FunctionGraph Proxy)

```
Sandbox (before apply) → create (or reuse) a DevBridge API Key via DevStage API
                         using the sandbox's user-level AK/SK. Persist to disk.

Terraform apply        → writes that key into the FunctionGraph function's user_data
                         (as EXISTING_API_KEY) + IAM agency + ECS.

ECS (at boot)          → metadata service (agency STS) → invoke FunctionGraph
                         → receive the pre-created DevBridge API Key
                         → install DevBridge CLI + create tunnel
```

Key flow for B1 mode:

1. The DevBridge API Key already exists in the sandbox before `terraform apply`.
2. Terraform writes **only that key** into the function's `user_data` (`EXISTING_API_KEY`).
3. The ECS obtains agency STS credentials from the metadata service, invokes the function, and receives the key back.
4. The ECS installs DevBridge and creates the SSH/RDP tunnel.

## Why B1?

The original "self-create" approach passed user AK/SK directly into ECS cloud-init user_data as
plaintext. This exposed credentials to anyone with read access to ECS user_data (console, API,
metadata), cloud-init logs, and Terraform state.

B1 solves this by moving the key hand-off into a FunctionGraph function:

- The user's AK/SK are used **only in the sandbox** (to pre-create the key) and for the Terraform
  provider's apply-time authentication. They **never enter** ECS user_data, ECS metadata,
  cloud-init logs, or tfstate.
- The ECS receives only a **revocable, tunnel-only** DevBridge API Key — not an AK/SK.
- The FunctionGraph function holds **no AK/SK** — it only returns the pre-created key.

This is strictly stronger than the old "AK/SK in function env vars" design: there are now **no AK/SK
in any Terraform artifact**, only a revocable DevBridge API Key (which cannot touch OBS/ECS/RDS).

## Security Best Practices

### 1. Security Group: Zero Inbound

The template creates a security group with `delete_default_rules = true` and only egress rules:

- TCP 443 (HTTPS — DevBridge tunnel, DevStage API, package downloads)
- TCP 80 (HTTP — package repository fallback)
- UDP 53 (DNS — name resolution)

No inbound rules are created. SSH/RDP access is exclusively through the DevBridge tunnel.

### 2. Credential Isolation

| Layer | Has user AK/SK? | Has DevBridge API Key? |
|-------|-----------------|----------------------|
| user_data (B1) | No | No (received at runtime) |
| ECS metadata | No | No |
| tfstate (ECS) | No | No |
| tfstate (function `user_data`) | No | Yes (revocable, tunnel-only) |
| ECS local disk | No | Yes (encrypted at rest by setup script) |
| Sandbox `~/.huawei/devbridge/config.yaml` | No | Yes (reused across creations) |

**Only sensitive value in tfstate** is the DevBridge API Key — revocable and tunnel-only. No AK/SK,
no security token ever lands in tfstate, user_data, or cloud-init logs.

### 3. IAM Least Privilege

Two modes are supported via the `use_custom_role` variable:

- **`use_custom_role = true`**: Creates a custom IAM role with only `functiongraph:invokeFunction` permission. The ECS agency cannot access any other cloud service. Requires IAM custom role creation permission.
- **`use_custom_role = false` (current default)**: Uses a predefined role (`FunctionGraph Administrator` by default, configurable via `predefined_role_name`). Broader permissions but works without IAM custom role creation permission. Use this if the user's AK/SK doesn't have IAM role creation permission (e.g., a sub-user with limited permissions).

Regardless of mode, the function's behavior is identical — it only returns the pre-created key.

### 4. State File Protection

- The `devbridge_api_key` variable is marked `sensitive = true` (masked in plan output)
- `.gitignore` must include `terraform.tfstate*` and `terraform.tfvars`
- For production: use a remote backend with encryption (OBS + KMS)

### 5. Function Lifecycle: Keep Until `terraform destroy`

The FunctionGraph function is kept until the full `terraform destroy`, and is destroyed together
with the other resources. **Do NOT run a separate `-target` destroy on the function.**

The function's `user_data` holds only a revocable DevBridge API Key (no AK/SK), so there is no
high-risk credential requiring urgent removal. Keeping the function also eliminates the Windows
slow-boot race: there is no "destroy the function too early → the ECS never gets the key → the tunnel
never appears" hazard, and no timing rule to obey.

## Cost

| Resource | Cost |
|----------|------|
| FunctionGraph | ¥0 (free tier: 1M invocations/month; uses 1 per ECS) |
| EIP | ~¥0.02/hour |
| ECS | Standard ECS pricing |
| IAM agency/role | ¥0 |

No additional cost for the B1 architecture vs. a standard ECS deployment.

## Limitations

1. **DevBridge API Key in tfstate** — the function's `user_data` contains the DevBridge API Key, which is stored in tfstate. This value is revocable and tunnel-only (it cannot touch OBS/ECS/RDS), so the risk is bounded, but it still requires tfstate protection (`.gitignore` + remote backend for production).
2. **DevBridge API Key lifecycle** — the key persists after `terraform destroy`. Clean up via DevStage API `DELETE /open-api-public/v1/relay/api-key/{id}`.
3. **Boot time** — cloud-init takes 1-3 minutes to complete the tunnel setup after `terraform apply` finishes.
4. **IAM role resource** — `huaweicloud_identity_role` is used to create a custom role. If the Terraform provider version doesn't support this resource, fall back to a predefined role (`use_custom_role = false`) or create the role manually.