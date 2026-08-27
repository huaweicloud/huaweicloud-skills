# IAM Permission Policies — huawei-cloud-kunpeng-source-code-migrate

IAM permissions required for provisioning a Kunpeng ECS instance on Huawei Cloud (Step 3d only). The SSH-only path (Step 3c) and local install path (Step 3a) do NOT require any IAM permissions — they use paramiko over SSH with user-provided credentials.

## Table of Contents

- [When IAM Permissions Are Required](#when-iam-permissions-are-required)
- [Minimum Required Permissions (Provisioning)](#minimum-required-permissions-provisioning)
  - [ECS Permissions](#ecs-permissions)
  - [VPC Permissions](#vpc-permissions)
  - [IMS Permissions](#ims-permissions)
  - [EIP Permissions](#eip-permissions)
  - [IAM Permissions](#iam-permissions)
- [Cleanup Permissions (Resource Deletion)](#cleanup-permissions-resource-deletion)
- [Recommended IAM Policy](#recommended-iam-policy)
- [Creating a Custom IAM Policy](#creating-a-custom-iam-policy)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

---

## When IAM Permissions Are Required

| Workflow Path | IAM Required? | Services Used |
|---------------|---------------|---------------|
| **Step 3a** — Local DevKit install | No | None (local execution only) |
| **Step 3c** — Existing remote server (SSH) | No | None (paramiko over SSH with user credentials) |
| **Step 3d** — Provision Kunpeng ECS on Huawei Cloud | **Yes** | ECS, VPC, IMS, EIP, IAM |

Only Step 3d (`provision_kunpeng_server.sh`) calls Huawei Cloud APIs via hcloud CLI and therefore requires IAM permissions. The permissions below are the **minimum set** needed to provision and later clean up the resources created by this skill.

---

## Minimum Required Permissions (Provisioning)

These permissions are called by `scripts/provision_kunpeng_server.sh` during ECS provisioning.

### ECS Permissions

| Action | hcloud CLI Command | API | Description |
|--------|--------------------|-----|-------------|
| `ecs:servers:create` | `hcloud ECS CreateServers` | POST /v1/{project_id}/cloudservers | Create the Kunpeng ECS instance |
| `ecs:servers:list` | `hcloud ECS ListServersDetails` | GET /v1/{project_id}/cloudservers/detail | Pre-flight auth check and list instances |
| `ecs:jobs:get` | `hcloud ECS ShowJob` | GET /v1/{project_id}/jobs/{job_id} | Poll async ECS creation job status |

### VPC Permissions

| Action | hcloud CLI Command | API | Description |
|--------|--------------------|-----|-------------|
| `vpc:vpcs:create` | `hcloud VPC CreateVpc` | POST /v1/{project_id}/vpcs | Create VPC for the ECS |
| `vpc:vpcs:get` | `hcloud VPC ShowVpc` | GET /v1/{project_id}/vpcs/{vpc_id} | Poll VPC status until ACTIVE |
| `vpc:subnets:create` | `hcloud VPC CreateSubnet` | POST /v1/{project_id}/vpcs/{vpc_id}/subnets | Create subnet within the VPC |
| `vpc:subnets:get` | `hcloud VPC ShowSubnet` | GET /v1/{project_id}/subnets/{subnet_id} | Poll subnet status until ACTIVE |
| `vpc:securityGroups:create` | `hcloud VPC CreateSecurityGroup` | POST /v1/{project_id}/security-groups | Create security group for SSH access |
| `vpc:securityGroupRules:create` | `hcloud VPC CreateSecurityGroupRule` | POST /v1/{project_id}/security-group-rules | Add inbound SSH rule (TCP 22) |

### IMS Permissions

| Action | hcloud CLI Command | API | Description |
|--------|--------------------|-----|-------------|
| `ims:images:list` | `hcloud IMS ListImages` | GET /v2/images | Find the EulerOS 2.0 ARM64 image ID |

### EIP Permissions

| Action | hcloud CLI Command | API | Description |
|--------|--------------------|-----|-------------|
| `eip:publicips:create` | `hcloud EIP CreatePublicip` | POST /v1/{project_id}/publicips | Create elastic public IP for SSH access |

### IAM Permissions

| Action | hcloud CLI Command | API | Description |
|--------|--------------------|-----|-------------|
| `iam:projects:list` | `hcloud IAM KeystoneListProjects` | GET /v3/projects | Resolve project_id for the target region |

> **Note:** `iam:projects:list` is needed because `ECS CreateServers` via `--cli-jsonInput` requires the `project_id` in the request path. The script fetches it by listing projects and filtering by region name.

---

## Cleanup Permissions (Resource Deletion)

After the migration assessment completes, the user is reminded to manually delete the provisioned resources (the AI never executes delete commands autonomously). To perform cleanup, the following additional permissions are needed:

| Action | hcloud CLI Command | API | Description |
|--------|--------------------|-----|-------------|
| `ecs:servers:delete` | `hcloud ECS DeleteServers` | POST /v1/{project_id}/cloudservers/delete | Delete the ECS instance |
| `eip:publicips:delete` | `hcloud EIP DeletePublicip` | DELETE /v1/{project_id}/publicips/{publicip_id} | Release the EIP |
| `vpc:subnets:delete` | `hcloud VPC DeleteSubnet` | DELETE /v1/{project_id}/vpcs/{vpc_id}/subnets/{subnet_id} | Delete the subnet |
| `vpc:securityGroups:delete` | `hcloud VPC DeleteSecurityGroup` | DELETE /v1/{project_id}/security-groups/{security_group_id} | Delete the security group |
| `vpc:vpcs:delete` | `hcloud VPC DeleteVpc` | DELETE /v1/{project_id}/vpcs/{vpc_id} | Delete the VPC |

> **⚠️ Cleanup is always manual.** The AI presents the delete commands as text but never executes them. The user must run them in their own terminal. See [prerequisites.md → Resource Cleanup Reminder](prerequisites.md#resource-cleanup-reminder).

---

## Recommended IAM Policy

The following custom IAM policy grants the minimum permissions needed for both provisioning (Step 3d) and cleanup. Attach this policy to the user or agency whose AK/SK is configured via `hcloud configure set`.

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:servers:create",
        "ecs:servers:list",
        "ecs:servers:delete",
        "ecs:jobs:get",
        "vpc:vpcs:create",
        "vpc:vpcs:get",
        "vpc:vpcs:delete",
        "vpc:subnets:create",
        "vpc:subnets:get",
        "vpc:subnets:delete",
        "vpc:securityGroups:create",
        "vpc:securityGroups:delete",
        "vpc:securityGroupRules:create",
        "ims:images:list",
        "eip:publicips:create",
        "eip:publicips:delete",
        "iam:projects:list"
      ]
    }
  ]
}
```
---

## Creating a Custom IAM Policy

### Via Huawei Cloud Console

1. Log in to the Huawei Cloud console → **IAM** → **Permissions** → **Policies** → **Create Custom Policy**
2. Set policy name: `KunpengDevKitProvisioning`
3. Set scope: **Project-level** (the resources are project-scoped)
4. Paste the JSON from [Recommended IAM Policy](#recommended-iam-policy) above
5. Click **OK** to create the policy
6. Assign the policy to the user or user group:
   - **IAM** → **Users** → select user → **Authorization** → add `KunpengDevKitProvisioning`
   - Or **IAM** → **User Groups** → select group → **Authorization** → add `KunpengDevKitProvisioning`

### Via hcloud CLI

```bash
# Create the custom policy (JSON content from above)
hcloud IAM CreatePolicy \
  --policy.name="KunpengDevKitProvisioning" \
  --policy.description="Minimum permissions for Kunpeng DevKit source code migration skill (provisioning + cleanup)" \
  --policy.scope="project" \
  --policy.policy='{"Version":"1.1","Statement":[{"Effect":"Allow","Action":["ecs:servers:create","ecs:servers:list","ecs:servers:delete","ecs:jobs:get","vpc:vpcs:create","vpc:vpcs:get","vpc:vpcs:delete","vpc:subnets:create","vpc:subnets:get","vpc:subnets:delete","vpc:securityGroups:create","vpc:securityGroups:delete","vpc:securityGroupRules:create","ims:images:list","eip:publicips:create","eip:publicips:delete","iam:projects:list"]}]}'
```

---

## Verification

After configuring IAM, verify each permission by running the corresponding read-only hcloud command. If any command returns `403 Forbidden`, the corresponding permission is missing.

```bash
# Set region (Guiyang 1 — the default for this skill)
REGION="cn-southwest-2"

# Verify ECS list permission
hcloud ECS ListServersDetails --cli-region=${REGION} --limit=1

# Verify VPC list permission (implicitly tests vpc:vpcs:get if any VPC exists)
hcloud VPC ListVpcs --cli-region=${REGION}

# Verify IMS list permission
hcloud IMS ListImages --cli-region=${REGION} --__imagetype=gold --__os_type=Linux --limit=1

# Verify IAM projects list permission
hcloud IAM KeystoneListProjects --cli-region=${REGION}
```

**Expected output:** Each command returns JSON with a valid response (HTTP 200).

**Failure indicators:**
- `403 Forbidden` — the action permission is missing from the IAM policy
- `401 Unauthorized` — AK/SK is invalid or expired; re-run `hcloud configure set`
- `配置文件中不存在` — hcloud is not configured; run `hcloud configure set --cli-region=${REGION} --cli-access-key=<AK> --cli-secret-key=<SK>`

---

## Troubleshooting

| Error | Cause | Resolution |
|-------|-------|------------|
| `403 Forbidden` on `ECS CreateServers` | Missing `ecs:servers:create` | Add the action to the custom policy |
| `403 Forbidden` on `VPC CreateVpc` | Missing `vpc:vpcs:create` | Add the action to the custom policy |
| `403 Forbidden` on `EIP CreatePublicip` | Missing `eip:publicips:create` | Add the action to the custom policy |
| `403 Forbidden` on `IAM KeystoneListProjects` | Missing `iam:projects:list` | Add the action to the custom policy (this is often overlooked) |
| `403 Forbidden` on `ECS DeleteServers` (during cleanup) | Missing `ecs:servers:delete` | Add the cleanup permissions to the policy |
| `401 Unauthorized` | Invalid/expired AK/SK | Re-run `hcloud configure set --cli-region=cn-southwest-2 --cli-access-key=<AK> --cli-secret-key=<SK>` |
| `hcloud: command not found` | hcloud CLI not installed | See [cli-installation-guide.md](cli-installation-guide.md) |
| Image not found | `ims:images:list` present but no EulerOS 2.0 ARM image in region | Verify the region has Kunpeng images: `hcloud IMS ListImages --cli-region=cn-southwest-2 --__imagetype=gold --__os_type=Linux` |

> **Tip:** If you only need to run the assessment on an **existing server** (Step 3c), no IAM permissions are needed at all — the skill uses paramiko over SSH with user-provided credentials.
