# IAM Permissions Guide

## Required Permissions

This skill requires the following Huawei Cloud IAM permissions to manage Flexus L instances.

### HCSS (Flexus L Instance) Permissions

| Permission | Description | Actions |
|------------|-------------|---------|
| `hcss:lightInstance:create` | Create Flexus L instance | create-instance |
| `hcss:lightInstance:list` | List Flexus L instances | show-regions, show-images, show-specs |
| `hcss:lightInstance:get` | Get instance details | All operations |
| `hcss:lightInstance:renew` | Renew instance | renewal |
| `hcss:lightInstance:unsubscribe` | Unsubscribe instance | unsubscribe |

### BSS (Billing) Permissions

| Permission | Description | Actions |
|------------|-------------|---------|
| `bss:order:list` | List orders | renewal, unsubscribe |
| `bss:order:pay` | Pay orders | create-instance, renewal |
| `bss:refund:apply` | Apply refund | unsubscribe |

### IAM Permissions

| Permission | Description | Actions |
|------------|-------------|---------|
| `iam:project:list` | List projects | All operations |

---

## Minimum Policy Template

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "hcss:lightInstance:create",
        "hcss:lightInstance:list",
        "hcss:lightInstance:get",
        "hcss:lightInstance:renew",
        "hcss:lightInstance:unsubscribe",
        "bss:order:list",
        "bss:order:pay",
        "bss:refund:apply",
        "iam:project:list"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Setup Instructions

### Option 1: Use Built-in Policy

1. Go to **IAM Console** → **Policies**
2. Search for `HCSS FullAccess` policy
3. Assign to your user/role

### Option 2: Create Custom Policy

1. Go to **IAM Console** → **Policies** → **Create Custom Policy**
2. Select **JSON** format
3. Paste the policy template above
4. Name it (e.g., `FlexusLLifecyclePolicy`)
5. Assign to your user/role

---

## Permission Verification

To verify your permissions, run:

```bash
python3 scripts/flexus_lifecycle.py show-regions
```

If you see region list, permissions are correctly configured.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `403 Forbidden` | Missing permission | Add required IAM policy |
| `No project found` | Missing `iam:project:list` | Add IAM read permission |
| `Order creation failed` | Missing `bss:order:pay` | Add BSS permission |

For more details, see [Huawei Cloud IAM Documentation](https://support.huaweicloud.com/productdesc-iam/iam_01_0001.html).
