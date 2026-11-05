# IAM Policies

This skill needs the following least-privilege IAM permissions for the OBS batch
desensitization flow and the optional FunctionGraph automation path.

## OBS (batch list / download / upload)

| Action | Resource | Purpose |
| -------- | ---------- | --------- |
| `obs:bucket:ListBucket` | `arn:aws:s3:::<bucket>` | List objects (obsutil `ls`) |
| `obs:object:List` | `arn:aws:s3:::<bucket>` | Enumerate objects under a prefix |
| `obs:object:GetObject` | `arn:aws:s3:::<bucket>/*` | Download source images |
| `obs:object:PutObject` | `arn:aws:s3:::<bucket>/*` | Upload desensitized results |

Example policy for the source/target buckets:

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "obs:bucket:ListBucket",
        "obs:object:List",
        "obs:object:GetObject",
        "obs:object:PutObject"
      ],
      "Resource": [
        "obs:*:*:*:source-bucket",
        "obs:*:*:*:source-bucket/*",
        "obs:*:*:*:target-bucket",
        "obs:*:*:*:target-bucket/*"
      ]
    }
  ]
}
```

> If source and target are the same bucket, only that one bucket needs to be granted.

## FunctionGraph (optional `setup-trigger` automation)

Required only when the user asks to create the automatic desensitization pipeline
(`setup-trigger` sub-command):

| Action | Resource | Purpose |
| -------- | ---------- | --------- |
| `functiongraph:function:create` | `functiongraph:*:*:function:*` | Create the auto-desensitization function |
| `functiongraph:function:get` | `functiongraph:*:*:function:*` | Confirm the created function |
| `functiongraph:trigger:create` | `functiongraph:*:*:*:*` | Create the OBS trigger |
| `functiongraph:trigger:get` | `functiongraph:*:*:*:*` | Confirm the trigger |
| `obs:bucket:ListBucket` + `obs:object:GetObject`/`PutObject` | the watched bucket | The function code reads/writes OBS when triggered |

Example:

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "functiongraph:function:create",
        "functiongraph:function:get",
        "functiongraph:trigger:create",
        "functiongraph:trigger:get"
      ],
      "Resource": "*"
    }
  ]
}
```

## Notes

- The image desensitization itself runs **locally** with Pillow — no additional compute IAM
  permission is required for the `list`/`process` flow.
- The FunctionGraph function code reads and writes OBS with the OBS AK/SK supplied through its
  environment variables (`OBS_ENDPOINT`, `OBS_AK`, `OBS_SK`). Those variables must be configured
  on the function if you use `setup-trigger`; they are never echoed by this skill.
- If the FunctionGraph create call fails with `FSS.0403`, the executing IAM user lacks
  `functiongraph:function:create` — grant that action and retry.
