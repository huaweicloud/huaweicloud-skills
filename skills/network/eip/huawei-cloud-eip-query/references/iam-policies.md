# IAM Permission Policies

This skill is **read-only** — it only queries EIP resources and Cloud Eye monitoring
data. The following least-privilege policy covers its operations.

## Required Permissions

| API Action | Permission | Purpose |
| ------------ | ------------ | --------- |
| `vpc:publicIps:list` | List EIPs | `hcloud EIP ListPublicips/v2` |
| `vpc:publicIps:get` | Get EIP detail | `hcloud EIP ShowPublicip/v2` |
| `ces:metrics:list` | List metrics | `hcloud CES ListMetrics` |
| `ces:metricData:get` | Get metric data | `hcloud CES ShowMetricData` |

## Custom Policy (JSON)

Create a custom policy in IAM and attach it to the user / agency used by hcloud CLI:

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc:publicIps:list",
        "vpc:publicIps:get"
      ],
      "Resource": [
        "*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ces:metrics:list",
        "ces:metricData:get"
      ],
      "Resource": [
        "*"
      ]
    }
  ]
}
```

## Notes

- No write / destroy permissions are required. Do not add `vpc:publicIps:update`,
  `vpc:publicIps:delete`, `ceS:metricData:create`, or alarm mutation actions.
- If the account uses enterprise projects, scope the resource to the target project
  or keep `"Resource": ["*"]` for simplicity.
