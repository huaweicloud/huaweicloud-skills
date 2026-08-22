# IAM Permission Policies - Kunpeng DevKit WebUI Mode

IAM permissions required for creating Kunpeng ECS and installing DevKit.

## Table of Contents

- [Minimum Required Permissions](#minimum-required-permissions)
  - [ECS Permissions](#ecs-permissions)
  - [VPC Permissions](#vpc-permissions)
  - [IMS Permissions](#ims-permissions)
  - [EIP Permissions](#eip-permissions)
  - [KMS Permissions](#kms-permissions)
- [Recommended IAM Policy](#recommended-iam-policy)
- [Verification](#verification)

## Minimum Required Permissions

### ECS Permissions

| Action | API | Description |
|--------|-----|-------------|
| `ecs:servers:create` | POST /v1/{project_id}/cloudservers | Create ECS instances (Python SDK) |
| `ecs:servers:get` | GET /v1/{project_id}/cloudservers/{server_id} | Query ECS details |
| `ecs:servers:list` | GET /v1/{project_id}/cloudservers/detail | List ECS instances (resolve IP to ID) |
| `ecs:jobs:get` | GET /v1/{project_id}/jobs/{job_id} | Query async job status |
| `ecs:flavors:get` | GET /v1/{project_id}/cloudservers/flavors | Query ECS flavors |

### VPC Permissions

| Action | API | Description |
|--------|-----|-------------|
| `vpc:vpcs:list` | GET /v1/{project_id}/vpcs | List VPCs (hcloud CLI) |
| `vpc:vpcs:get` | GET /v1/{project_id}/vpcs/{vpc_id} | Get VPC details |
| `vpc:subnets:list` | GET /v1/{project_id}/subnets | List subnets (hcloud CLI) |
| `vpc:subnets:get` | GET /v1/{project_id}/subnets/{subnet_id} | Get subnet details |
| `vpc:securityGroups:list` | GET /v1/{project_id}/security-groups | List security groups |
| `vpc:securityGroupRules:create` | POST /v1/{project_id}/security-group-rules | Create security group rules |
| `vpc:ports:list` | GET /v1/{project_id}/ports | List ports for EIP binding (hcloud CLI) |

### IMS Permissions

| Action | API | Description |
|--------|-----|-------------|
| `ims:images:list` | GET /v2/images | List images (hcloud CLI) |
| `ims:images:get` | GET /v2/images/{image_id} | Get image details |

### EIP Permissions

| Action | API | Description |
|--------|-----|-------------|
| `eip:publicips:create` | POST /v1/{project_id}/publicips | Create EIP (hcloud CLI) |
| `eip:publicips:update` | PUT /v1/{project_id}/publicips/{publicip_id} | Bind/unbind EIP (hcloud CLI) |
| `eip:publicips:get` | GET /v1/{project_id}/publicips/{publicip_id} | Get EIP details |

### KMS Permissions

Required for encrypting and storing the ECS password securely via Python SDK.

| Action | API | Description |
|--------|-----|-------------|
| `kms:kms:create` | POST /v1.0/{project_id}/kms/create | Create KMS key (Python SDK) |
| `kms:kms:encrypt` | POST /v1.0/{project_id}/kms/encrypt | Encrypt ECS password (Python SDK) |
| `kms:kms:decrypt` | POST /v1.0/{project_id}/kms/decrypt | Decrypt ECS password for SSH (Python SDK) |
| `kms:kms:scheduleDeletion` | POST /v1.0/{project_id}/kms/schedule-key-deletion | Schedule KMS key deletion (Python SDK) |
| `kms:kms:list` | GET /v1.0/{project_id}/kms/list-keys | List KMS keys (Python SDK) |

---

## Recommended IAM Policy

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:servers:create",
        "ecs:servers:get",
        "ecs:servers:list",
        "ecs:jobs:get",
        "ecs:flavors:get",
        "vpc:vpcs:list",
        "vpc:vpcs:get",
        "vpc:subnets:list",
        "vpc:subnets:get",
        "vpc:securityGroups:list",
        "vpc:securityGroupRules:create",
        "vpc:ports:list",
        "ims:images:list",
        "ims:images:get",
        "eip:publicips:create",
        "eip:publicips:update",
        "eip:publicips:get",
        "kms:kms:create",
        "kms:kms:encrypt",
        "kms:kms:decrypt",
        "kms:kms:scheduleDeletion",
        "kms:kms:list"
      ]
    }
  ]
}
```

---

## Verification

After configuring IAM, verify permissions:

```bash
hcloud ECS ListServersDetails --cli-region=cn-north-4
hcloud VPC ListVpcs --cli-region=cn-north-4
hcloud IMS ListImages --cli-region=cn-north-4 --__imagetype=gold --status=active
```

If any command returns `403 Forbidden`, the corresponding permission is missing.

KMS permissions can be verified via Python SDK:

```bash
python3 -c "
from huaweicloudsdkkms.v2 import KmsClient
from huaweicloudsdkcore.auth.credentials import BasicCredentials
# ... (construct client) ...
print('KMS OK')
"
```
