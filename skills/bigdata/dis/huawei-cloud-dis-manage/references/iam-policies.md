# DIS IAM Policies

Apply least privilege: grant the read-only policy for inspection skills and add
the management policy only when create/update/delete/scale/policy operations are
required. Replace `{region}` and `{project_id}` with the target values, or use
the `*` wildcard for all projects in the account.

## Read-only policy (inventory, monitoring, verification)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dis:*:list",
        "dis:*:show",
        "dis:*:get"
      ],
      "Resource": [
        "dis:*:*:*:stream/*",
        "dis:*:*:*:app/*"
      ]
    }
  ]
}
```

This permits `ListStreams`, `ShowStream`, `ListTransferTasks`,
`ShowTransferTask`, `ShowStreamMetrics`, `ShowPartitionMetrics`,
`ShowConsumerState`, `ListApp`, `ShowApp`, `ShowCheckpoint`, `ShowCursor`,
`ConsumeRecords`, `ListPolicies`, `ListTags`, `ShowStreamTags`, and
`ListResourcesByTags`.

## Management policy (create / update / delete / scale / policy / tag)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dis:stream:create",
        "dis:stream:delete",
        "dis:stream:update",
        "dis:stream:list",
        "dis:stream:show",
        "dis:stream:put",
        "dis:stream:get",
        "dis:transferTask:create",
        "dis:transferTask:delete",
        "dis:transferTask:list",
        "dis:transferTask:show",
        "dis:transferTask:start",
        "dis:transferTask:stop",
        "dis:metrics:get",
        "dis:app:create",
        "dis:app:delete",
        "dis:app:list",
        "dis:app:show",
        "dis:checkpoint:commit",
        "dis:checkpoint:delete",
        "dis:checkpoint:show",
        "dis:cursor:create",
        "dis:cursor:show",
        "dis:policy:create",
        "dis:policy:list",
        "dis:tag:create",
        "dis:tag:delete",
        "dis:tag:list",
        "dis:tag:show",
        "dis:resource:list"
      ],
      "Resource": [
        "dis:*:*:*:stream/*",
        "dis:*:*:*:app/*"
      ]
    }
  ]
}
```

If the IAM console reports that an action name is not recognized, grant
`dis:*:*` scoped to the target project as a fallback and narrow it after the
operation set is stable. Do not grant `*:*:*`.

## Cross-service permissions for dump tasks

Dump tasks use a DIS agency (`dis_admin_agency` or a user-created agency) to
write to the destination. Grant the agency only the destination it needs:

| Destination | Agency permission |
|-------------|-------------------|
| OBS | Object write permission on the staging/target bucket (`obs:object:PutObject`, `obs:bucket:ListBucket`) |
| DWS | DWS connection and table insert permissions for the configured database user; KMS decrypt for the encrypted password key |
| DLI | DLI table insert permission (`dli:table:insertInto`) for the target database/table, plus OBS staging write |
| MRS | MRS cluster access for non-Kerberos clusters and HDFS write on the target path, plus OBS staging write |
| CloudTable | CloudTable HBase/OpenTSDB write permission and OBS backup-bucket write |

The agency must be of type **Cloud service → DIS**, validity **Unlimited**, and
carry the appropriate policy for the destination project.

## Credential handling

- Read AK/SK from the KooCLI profile or environment variables; never hardcode
  them in scripts, documents, or command examples.
- Use `hcloud configure list` to inspect the active profile (it masks secrets).
- Never echo a DWS `user_password`, KMS key material, or `SendRecords` payloads
  that contain production data into logs or reports.
- For CI, prefer a temporary credential (STS token) with a short validity.