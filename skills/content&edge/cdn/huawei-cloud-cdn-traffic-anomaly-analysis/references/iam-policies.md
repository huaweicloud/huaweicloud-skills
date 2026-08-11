# IAM Permission Policies

Ensure the IAM user has the required permissions to perform CDN traffic analysis.

## Minimum Required Permissions

| Permission | Description |
|------------|-------------|
| `cdn:domain:list` | List CDN domains |
| `cdn:domain:get` | Get domain details |
| `cdn:statistics:get` | Get traffic/bandwidth statistics |
| `cdn:billing:get` | Get billing mode information |

## Policy Example

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cdn:domain:list",
        "cdn:domain:get",
        "cdn:statistics:get",
        "cdn:billing:get"
      ],
      "Resource": "*"
    }
  ]
}
```

## Notes

- This skill is **read-only**, no write permissions required
- If using a sub-account, ensure the sub-account has the above permissions
- If permission denied errors occur, contact the account administrator to grant permissions
