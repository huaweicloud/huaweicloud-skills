# IAM Policies for Huawei Cloud CTS

Least-privilege IAM policies for the operations performed by this skill (`huawei-cloud-cts-trace-management`).

## Query & Analyze (R3 — read-only)

Least privilege for query/analyze actions (`huawei_list_cts_trackers`, `huawei_list_cts_traces`,
`huawei_list_cts_operations`, `huawei_list_cts_notifications`, `huawei_list_cts_trace_resources`,
`huawei_analyze_cts_traces`, `huawei_analyze_cts_retention`):

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cts:tracker:list",
        "cts:trace:list",
        "cts:notification:list",
        "cts:operation:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```

> **Note:** This policy JSON uses the action pattern documented in the CTS API reference
> (`cts:tracker:list`, `cts:trace:list`, etc.). If your environment uses finer-grained actions,
> verify the exact action names on the IAM console (`cts:*` wildcard also works). The pre-defined
> system role `CTS ReadOnlyAccess` grants equivalent read-only access and is the simplest choice.

## Manage (R2/R1 — write)

For create/delete actions (`huawei_create_cts_tracker`, `huawei_create_cts_notification`,
`huawei_delete_cts_tracker`), add write permissions. The pre-defined `CTS Administrator` role
is the simplest option; the least-privilege alternative is:

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cts:tracker:create",
        "cts:tracker:delete",
        "cts:notification:create",
        "cts:tracker:list",
        "cts:trace:list",
        "cts:notification:list",
        "cts:operation:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## Related Permissions for Prerequisites

| Prerequisite | Required Permission |
|--------------|--------------------|
| OBS bucket for tracker log delivery | `obs:bucket:ListAllMyBuckets` / `obs:object:*` on the target bucket, or use a bucket the account already owns with proper CTS write grant |
| LTS log stream (long retention) | `lts:logstream:create`, `lts:logstream:list` in the region |
| SMN topic for notifications | `smn:topic:list` (read existing topic URN) |

## Security Notes

- **Never hardcode AK/SK** in scripts, commands, or documents. Credentials come from
  `hcloud configure` profile or the `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK`
  (or `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`) environment variables.
- Mask any AK/SK-like values in command output before reporting results.
- Delete/disable operations require explicit user confirmation (R1).