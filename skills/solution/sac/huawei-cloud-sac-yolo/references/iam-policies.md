# IAM Policies — huawei-cloud-sac-yolo

IAM configuration required to deploy the YOLO training platform.

Reference: <https://support.huaweicloud.com/yolo-aislt/yolo_04.html>

## Basic operations (read-only)

| API Action | Permission | Purpose |
| ------------ | ----------- | --------- |
| ecs:servers:get | View ECS instance details | Check instance status |
| ecs:servers:list | List ECS instances | Verify deployment |
| vpc:vpcs:get | View VPC details | Verify network |
| vpc:subnets:get | View subnet details | Verify network |
| vpc:securityGroups:get | View security group | Verify security rules |
| eip:publicips:get | View EIP details | Verify public access |
| evs:volumes:get | View EVS volume | Verify storage |
| cbr:vaults:get | View backup vault | Verify backup |

## Deployment operations (additional authorization required)

| API Action | Permission | Purpose |
| ------------ | ----------- | --------- |
| ecs:servers:create | Create ECS instance | Provision GPU instance |
| ecs:servers:delete | Delete ECS instance | Cleanup |
| vpc:vpcs:create | Create VPC | Network infrastructure |
| vpc:vpcs:delete | Delete VPC | Cleanup |
| vpc:subnets:create | Create subnet | Network infrastructure |
| vpc:subnets:delete | Delete subnet | Cleanup |
| vpc:securityGroups:create | Create security group | Security rules |
| vpc:securityGroups:delete | Delete security group | Cleanup |
| eip:publicips:create | Create EIP | Public access |
| eip:publicips:delete | Delete EIP | Cleanup |
| evs:volumes:create | Create EVS volume | Storage disks |
| evs:volumes:delete | Delete EVS volume | Cleanup |
| cbr:vaults:create | Create backup vault | Backup |
| cbr:vaults:delete | Delete backup vault | Cleanup |
| rfs:stacks:create | Create RFS stack | Solution deployment |
| rfs:stacks:delete | Delete RFS stack | Cleanup |

## Minimum-privilege policy JSON (read-only)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:servers:get",
        "ecs:servers:list",
        "vpc:vpcs:get",
        "vpc:subnets:get",
        "vpc:securityGroups:get",
        "eip:publicips:get",
        "evs:volumes:get",
        "cbr:vaults:get"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## Minimum-privilege policy JSON (deployment)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:servers:*",
        "vpc:vpcs:*",
        "vpc:subnets:*",
        "vpc:securityGroups:*",
        "eip:publicips:*",
        "evs:volumes:*",
        "cbr:vaults:*",
        "rfs:stacks:*"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## Account Requirements

- If using the **initial registered account** (the account created when
  first registering with Huawei Cloud), no additional IAM preparation
  is needed.
- If using an **IAM user**, confirm the user is in the `admin` user
  group. If not, grant the relevant permissions and complete the steps
  below.

## Create rf_admin_trust Agency (Optional)

The `rf_admin_trust` agency is required by the Resource Formation Service
(RFS) to deploy the solution on behalf of the user. If it already exists,
skip creation.

### Step-by-step

1. Go to the Huawei Cloud console, hover over the account name, and open
   **Unified Identity Authentication**.
2. Navigate to **Agencies** and search for `rf_admin_trust`.
3. If the agency exists, no further action is needed.
4. If it does not exist:
   - Click **Create Agency**.
   - **Agency name**: `rf_admin_trust`
   - **Agency type**: Cloud service
   - **Cloud service**: `RFS`
   - Click **Complete**.
5. Click **Authorize Now**.
   - Search for and select the **Tenant Administrator** policy.
   - Click **Next**.
6. Set the **minimum authorization scope** to **All resources**.
   - Click **OK**.

### Agency configuration summary

| Field | Value |
| ------- | ------- |
| Agency name | `rf_admin_trust` |
| Agency type | Cloud service |
| Cloud service | RFS |
| Policy | Tenant Administrator |
| Authorization scope | All resources |

## Permission Failure Handling

If any Terraform or CLI command fails due to insufficient IAM permissions,
follow this process:

1. **Identify the error**: Look for `Unauthorized` or `Forbidden` in the
   command output.
2. **Read this document**: Review the required permissions listed above.
3. **Present to the user**: Show the required permission list and the
   Custom Policy JSON.
4. **Guide the user**:
   - Go to the Huawei Cloud console → **IAM** → **Policies** → **Create Custom Policy**.
   - Paste the Custom Policy JSON from the appropriate section above.
   - Assign the policy to the IAM user or user group used for deployment.
   - If the `rf_admin_trust` agency is missing, follow the
     "Create rf_admin_trust Agency" steps above.
5. **Pause execution**: Wait for the user to confirm that permissions
   have been granted before retrying the failed command.
