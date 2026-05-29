# Permission Guide

## Required IAM Permissions

### Minimum Required Permissions

| Service | Policy | Actions | Description |
| --------- | -------- | --------- | ------------- |
| **HCSS** | `HCSS FullAccess` | `hcss:*:*` | Flexus L instance management |
| **BSS** | `BSS Administrator` | `bss:*:*` | Billing and subscription management |
| **IAM** | `IAM ReadOnlyAccess` | `iam:projects:list` | Get project ID by region |

### Custom Policy (Recommended)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "hcss:lightInstances:create"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bss:renewal:create",
        "bss:unsubscribe:create"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:projects:list"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Failure Handling

| Error Code | Cause | Solution |
| ------------ | ------- | ---------- |
| `401` | Invalid AK/SK | Verify AK/SK is correct and active |
| `403` | Insufficient permissions | Add required policies to user/role |
| `APIGW.0101` | API not found | Check if service is enabled in region |
| `APIGW.0301` | Authentication failed | Check AK/SK or token validity |

### Common Permission Issues

1. **"Permission denied" when creating instance**
   - Ensure `HCSS FullAccess` policy is attached
   - Check if Flexus L service is enabled in the region

2. **"Cannot get project ID"**
   - Ensure `IAM ReadOnlyAccess` policy is attached

## How to Grant Permissions

1. Login to [Huawei Cloud Console](https://console.huaweicloud.com/)
2. Go to **Identity and Access Management** → **Users**
3. Select the user → **Authorize**
4. Add required policies:
   - `HCSS FullAccess`
   - `BSS Administrator`
   - `IAM ReadOnlyAccess`
5. Click **OK** to save
