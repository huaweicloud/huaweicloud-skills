# IAM Permission Policies

Ensure the IAM user has the permissions required to perform CDN DNS resolution diagnosis.

## Minimum Required Permissions

| Permission | Description |
|------------|-------------|
| `cdn:domain:get` | Query domain details (ShowDomainDetailByName) |
| `cdn:domain:get` | Query IP attribution information (ShowIpInfo/v2, also covered by the CDN read-only query permission) |

> Note: ShowIpInfo/v2 is a read-only query interface of the CDN service, typically covered by `cdn:domain:get` or a CDN read-only policy. If the policy is fine-grained, ensure the read-only permission for IP information query is included.

## Policy Example

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cdn:domain:get"
      ],
      "Resource": "*"
    }
  ]
}
```

## Minimum Read-Only Custom Policy (Recommended)

To strictly restrict to read-only, use the following custom policy:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cdn:domain:get",
        "cdn:ip:info"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Deny",
      "Action": [
        "cdn:domain:update",
        "cdn:domain:delete",
        "cdn:domain:create",
        "cdn:domain:disable"
      ],
      "Resource": "*"
    }
  ]
}
```

## Notes

- This skill is **read-only diagnosis**; no write permissions are required
- If using a sub-account, ensure the sub-account has the above permissions
- If permission denied errors occur, contact the primary account administrator to grant permissions
- The permission statements do not include any write operation permissions (e.g., `cdn:domain:update`, `cdn:domain:delete`)
- `dns_resolve.py` is a local DNS query probe (A-record resolution via `dnspython`) and does not need IAM permissions; it performs unauthenticated network reads against the system DNS resolver
