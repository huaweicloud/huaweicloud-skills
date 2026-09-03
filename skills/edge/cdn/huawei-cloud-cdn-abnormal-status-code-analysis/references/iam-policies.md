# IAM Permission Policies

Ensure the IAM user has the **read-only** permissions required to perform CDN
abnormal status-code diagnosis. This skill is read-only end to end; it never
requires write/delete permissions.

## Minimum Required Permissions

| Permission | Description |
|------------|-------------|
| `cdn:domain:get` | Query domain details, config, ownership/verify info |
| CDN statistics / log / bandwidth / top-N query scope | Read-only statistics, access-log download links, bandwidth calc, top-N, client stats, IP attribution |

The exact fine-grained action names for the statistics / log / bandwidth /
top-N sub-resources must be confirmed against the official Huawei Cloud IAM
permission reference for CDN
(https://support.huaweicloud.com/api-cdn/cdn-api-pdf.pdf). Do **not** fabricate
action names. The simplest correct grant is the system read-only policy below.

## Recommended System Policy (simplest read-only grant)

Attach the system policy **`CDN Domain Viewer`**
(display name "CDN Domain Viewer", description "Allow Query Domains") to the
IAM user. This is the official read-only CDN system policy and covers the
domain / configuration query scope this skill depends on.

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

> If a statistics / log / top-N query returns `CDN.0004` (permission / not in
> whitelist) or a 403, the read-only system scope is incomplete for that
> sub-resource — attach the broader CDN read-only system policy, or have the
> account administrator grant the confirmed fine-grained action after checking
> the official IAM reference. **Do not** elevate to any write action
> (`cdn:domain:update`, `cdn:domain:delete`, `cdn:cache:refresh`, …).

## Special Notes

- This skill is **read-only diagnosis**; the policy intentionally contains no
  write operation permissions.
- `ListBanUrl` / `ListAccessControlTask` require a separate 工单 (support
  ticket) whitelist ("not in the whitelist" / `CDN.0004`); they are still
  query-class GET operations, not write ops. If blocked, record the error and
  proceed; do **not** attempt to bypass.
- The Python log helper `scripts/fetch_cdn_log.py` performs an unauthenticated
  read-only HTTP download of a presigned CDN log link returned by
  `ShowLogs/v2`; it does **not** need IAM and accepts no credentials.
