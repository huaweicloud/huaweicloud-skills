# Troubleshooting

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| `No module named 'huaweicloudsdkbcs'` | SDK missing | `pip install huaweicloudsdkbcs` |
| `ERROR[C01]` | AK/SK not set | Set `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` |
| `ERROR[C02]` client initialization failed | IAM project/region resolution failed, region not authorized, or transient credentials | Check the account has a project in the target region and credentials are valid |
| `ERROR[U01]` confirmation required | `--confirm` missing on a write | Review the preview, then re-run with `--confirm` |
| `ERROR[U02]` invalid body file / region | Malformed JSON, unknown or mistyped field, or unsupported region | Fix the JSON per the [body file schemas](body-file-schemas.md); use a supported region |
| `ERROR[U03]` no instance named X | Name typo or wrong region | Verify with `list` first |
| `ERROR[U04]` HTTP 401/403 | Missing IAM permission | Attach `BCS ReadOnlyAccess` or the required write policy |
| Download size 0 | Empty response / wrong cert type | The script removes the empty file and exits with `ERROR[B01]`; verify `--cert-type` |
| `No operation_id returned` | Some APIs are synchronous | Verify the result with a read-only subcommand instead of polling |
| Polling timed out | Operation still running after `--timeout` | Re-check with `python3 scripts/bcs_manage.py op-record --operation-id=<id>` |
| `hcloud` reports unsupported service | Local KooCLI metadata cache lacks the BCS template | Use this SDK-mode skill instead. KooCLI can reach BCS only with the template cached: `hcloud BCS ListBlockchains --cli-region=cn-north-4`; this skill's equivalent is `python3 scripts/bcs_manage.py list --region=cn-north-4` |