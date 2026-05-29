# IAM Permission Policies - JiuwenSwarm Deployment

## Permission Failure Handling Process (MUST)

When any command fails due to permission errors, follow this process:

1. **Read this document** - Read `references/iam_policies.md`
2. **Display required permissions** - Show users the required permission list and policy JSON from this file
3. **Guide authorization** - Guide users to create custom policies in the IAM console and grant permissions
4. **Pause execution** - Wait for user confirmation that permissions have been granted before continuing

---

## Basic Diagnostics (Read-only)

| API Action | Permission | Purpose |
|------------|------------|---------|
| iam:projects:list | List projects | Get Project ID for Region |
| ecs:servers:get | View instance details | Get Flexus L instance basic info |
| ecs:servers:list | List instances | List all ECS instances under account |
| rms:resources:list | List resources | Query Flexus L instance status and IP |
| coc:scripts:list | List scripts | View created COC scripts |
| coc:scriptJobs:get | View job details | Query COC script execution status |

## Advanced Operations (Requires additional authorization)

| API Action | Permission | Purpose |
|------------|------------|---------|
| coc:scripts:create | Create script | Create COC remote execution script |
| coc:scripts:execute | Execute script | Execute commands remotely on Flexus L instance |
| coc:scriptJobs:cancel | Cancel job | Cancel running COC task |
| ecs:servers:start | Start instance | Start Flexus L instance |
| ecs:servers:stop | Stop instance | Stop Flexus L instance |
| ecs:servers:reboot | Reboot instance | Reboot Flexus L instance |
| vpc:securityGroups:list | List security groups | View instance security group configuration |
| vpc:securityGroups:get | View security group | Check security group rules |

## Instance Creation (On-demand authorization)

| API Action | Permission | Purpose |
|------------|------------|---------|
| hcss:instances:create | Create Flexus L instance | Create new Flexus L instance |
| hcss:instances:get | View instance details | Get created instance info |
| hcss:instances:list | List instances | Confirm instance creation success |
| hcss:orders:get | View orders | Confirm order status |

---

## Minimum Permission Policy JSON

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:projects:list"
      ],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:servers:get",
        "ecs:servers:list",
        "ecs:servers:start",
        "ecs:servers:stop",
        "ecs:servers:reboot"
      ],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "rms:resources:list"
      ],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "coc:scripts:list",
        "coc:scripts:create",
        "coc:scripts:execute",
        "coc:scriptJobs:get",
        "coc:scriptJobs:cancel"
      ],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:securityGroups:list",
        "vpc:securityGroups:get"
      ],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "hcss:instances:get",
        "hcss:instances:list"
      ],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "hcss:orders:get"
      ],
      "Resource": ["*"]
    }
  ]
}
```

---

## Full Permission Policy JSON (Including instance creation)

Use the following policy if you need to create new Flexus L instances:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:projects:list"
      ],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:servers:get",
        "ecs:servers:list",
        "ecs:servers:start",
        "ecs:servers:stop",
        "ecs:servers:reboot"
      ],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "rms:resources:list"
      ],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "coc:scripts:list",
        "coc:scripts:create",
        "coc:scripts:execute",
        "coc:scriptJobs:get",
        "coc:scriptJobs:cancel"
      ],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:securityGroups:list",
        "vpc:securityGroups:get"
      ],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "hcss:instances:create",
        "hcss:instances:get",
        "hcss:instances:list"
      ],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "hcss:orders:get"
      ],
      "Resource": ["*"]
    }
  ]
}
```

---

## Steps to Create Custom Policy in IAM Console

1. Log in to Huawei Cloud Console
2. Go to **IAM (Identity and Access Management)**
3. Click left menu **Permission Management** > **Permission Policies**
4. Click **Create Policy**
5. Select **JSON** tab
6. Paste the policy JSON above
7. Enter policy name (e.g., `JiuwenSwarm-Deployment-Policy`)
8. Click **OK** to create policy
9. Go to **IAM (Identity and Access Management)** > **User Groups**
10. Select or create a user group
11. Click **Assign Policy**
12. Search and check the created policy
13. Click **OK** to complete authorization

---

## Permission Verification Command

After creating the policy, verify permissions with:

```bash
python scripts/prepare_env.py
```

Successful output should show all dependency modules checked successfully.
