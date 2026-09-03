# IAM Policies

## Least-Privilege Policy for Central Network Query

The following policy grants read-only access to Central Network resources in Cloud Connect.

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cc:centralNetworks:list",
        "cc:centralNetworks:get"
      ],
      "Resource": "*"
    }
  ]
}
```

## Explanation

| Permission | Scope | Commands Covered |
|------------|-------|-----------------|
| `cc:centralNetworks:list` | List operations | `ListCentralNetworks`, `ListCentralNetworkAttachments`, `ListCentralNetworkConnections` |
| `cc:centralNetworks:get` | Show/detail operations | `ShowCentralNetwork`, `ShowCentralNetworkErRouteTableAttachment`, `ShowCentralNetworkGdgwAttachment` |

## Assigning the Policy

1. Go to IAM → Policies → Create Custom Policy
2. Select JSON view, paste the policy above
3. Assign to the target user or group
