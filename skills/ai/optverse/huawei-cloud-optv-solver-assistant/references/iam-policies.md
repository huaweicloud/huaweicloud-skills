# IAM Policies - OptVerse Solver Assistant

## Overview

This document lists the required IAM permissions for the OptVerse Solver Assistant skill.

## 1. OptVerse Permissions

### 1.1 Read Operations (Required)

| API Action | Permission | Purpose |
|------------|-----------|---------|
| optverse:chats:list | List chats | View conversation history |
| optverse:chats:get | Get chat detail | Retrieve conversation content |
| optverse:artifacts:list | List artifacts | View generated artifacts per stage |
| optverse:file:download | Download file | Download artifacts for user review |

### 1.2 Write Operations (Required)

| API Action | Permission | Purpose |
|------------|-----------|---------|
| optverse:chats:create | Create chat | Submit requirement analysis and confirmations |
| optverse:file:upload | Upload file | Upload requirement/data files |
| optverse:chats:publish | Publish chat | Publish assistant as reusable asset |

### 1.3 Optional Operations

| API Action | Permission | Purpose |
|------------|-----------|---------|
| optverse:chats:cancel | Cancel chat | Cancel in-progress SSE stream |
| optverse:chats:delete | Delete chat | Clean up test conversations |
| optverse:chats:update | Update chat | Rename or modify conversation |

## 2. IAM Token Permissions (if using token approach)

| API Action | Permission | Purpose |
|------------|-----------|---------|
| iam:tokens:create | Create IAM token | Obtain X-Auth-Token for API calls |

## 3. Minimal Policy JSON

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "optverse:chats:create",
        "optverse:chats:list",
        "optverse:chats:get",
        "optverse:chats:publish",
        "optverse:chats:cancel",
        "optverse:file:upload",
        "optverse:file:download",
        "optverse:artifacts:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## 4. Permission Failure Handling

When any command fails due to permission errors:

1. Check the error message for the specific permission required
2. Review the policy JSON above
3. Guide the user to create a custom policy in IAM Console:
   - Navigate to IAM Console → Permissions → Policies → Create Custom Policy
   - Paste the minimal policy JSON above
   - Assign the policy to the IAM user
4. Wait for user confirmation before retrying

## 5. Security Notes

- The `create_chat.py` script uses IAM token authentication (requires IAM username/domain/password).
- No credentials are logged or printed in full
