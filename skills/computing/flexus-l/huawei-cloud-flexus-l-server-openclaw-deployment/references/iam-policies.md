# IAM Permission Policy Reference

This document describes the Huawei Cloud IAM permission policies required for the OpenClaw one-click deployment skill.

## Permission Requirements

### 1. Flexus L Instance Related Permissions

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Action": [
                "hcss:instance:create",
                "hcss:instance:list",
                "hcss:instance:get",
                "hcss:instance:delete"
            ],
            "Effect": "Allow",
            "Resource": "*"
        }
    ]
}
```

### 2. COC (Cloud Operations Center) Related Permissions

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Action": [
                "coc:script:create",
                "coc:script:execute",
                "coc:script:query",
                "coc:script:delete"
            ],
            "Effect": "Allow",
            "Resource": "*"
        }
    ]
}
```

### 3. IAM Related Permissions (Project ID Retrieval)

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Action": [
                "iam:project:list",
                "iam:project:get"
            ],
            "Effect": "Allow",
            "Resource": "*"
        }
    ]
}
```

## Recommended Policy Combination

Combine the above permissions into a complete custom policy:

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Action": [
                "hcss:instance:create",
                "hcss:instance:list",
                "hcss:instance:get",
                "hcss:instance:delete",
                "coc:script:create",
                "coc:script:execute",
                "coc:script:query",
                "coc:script:delete",
                "iam:project:list",
                "iam:project:get"
            ],
            "Effect": "Allow",
            "Resource": "*"
        }
    ]
}
```

## Permission Configuration Steps

1. Log in to Huawei Cloud console
2. Navigate to "IAM" -> "Users" -> Select target user
3. Click "Permissions" -> "Grant Permissions"
4. Select "Custom Policy" -> "Create Custom Policy"
5. Paste the above policy content and save
6. Grant the policy to the target user

## Precautions

- Follow the principle of least privilege and only grant necessary permissions
- Regularly review and update permission policies
- Ensure AK/SK are stored securely when using them, avoid hard-coding
