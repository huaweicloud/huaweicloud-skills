# Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| `C01` | AK/SK not configured (also: SDK not installed) | Export `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK`; `pip install huaweicloudsdkbcs` |
| `C02` | Client initialization failed (IAM project/region resolution, transient credentials) | Verify the account has a project in the target region; retry with valid credentials |
| `U01` | Missing required input; for writes, `--confirm` missing | Fix the arguments; review the preview and re-run with `--confirm` |
| `U02` | Unsupported region, ambiguous `--name`, malformed body JSON, or unknown/mistyped body field | Use a supported region; fix the JSON per the [body file schemas](body-file-schemas.md) |
| `U03` | No instance found with the given `--name` | Verify the name with `list` first |
| `U04` | BCS API returned HTTP 401/403 | Attach the required read or write IAM policy |
| `B01` | Unexpected SDK/runtime failure; empty download (0 bytes) | Inspect the message; for downloads verify `--cert-type` and the body |
| `N03` | BCS API request failed (non-auth HTTP error) | Read the API message; fix inputs |