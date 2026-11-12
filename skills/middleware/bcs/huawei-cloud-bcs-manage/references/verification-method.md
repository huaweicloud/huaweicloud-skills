# Verification Method

## Prerequisites

```bash
pip install huaweicloudsdkbcs
export HUAWEICLOUD_SDK_AK="<your-ak>"
export HUAWEICLOUD_SDK_SK="<your-sk>"
```

All commands below use the single entry point `scripts/bcs_manage.py`.

## Read-Only Verification

### 1. Argument parsing / help

```bash
python3 scripts/bcs_manage.py --help
python3 scripts/bcs_manage.py list --help
```

Expected: usage lists every read-only subcommand (`list`, `detail`, `nodes`,
`channels`, `members`, `notifications`, `flavors`, `quotas`, `status`,
`op-record`, `alerts`, `metrics`) and every write subcommand; only write
subcommands document `--confirm`.

### 2. Instance inventory

```bash
python3 scripts/bcs_manage.py list --region=cn-north-4
```

Expected: `Total BCS instances: N` plus a table with id, name, status, version,
service type, charging mode, cluster and creation time. If the account has no
instances, `No BCS instances found in this region.` is printed.

### 3. Structured output

```bash
python3 scripts/bcs_manage.py list --region=cn-north-4 --json
```

Expected: exactly one JSON object with `count` and `instances` on stdout.

### 4. Instance-scoped reads

Use an id from step 2:

```bash
python3 scripts/bcs_manage.py detail   --region=cn-north-4 --blockchain-id=<id>
python3 scripts/bcs_manage.py nodes    --region=cn-north-4 --blockchain-id=<id>
python3 scripts/bcs_manage.py channels --region=cn-north-4 --blockchain-id=<id>
python3 scripts/bcs_manage.py status   --region=cn-north-4 --blockchain-id=<id>
python3 scripts/bcs_manage.py op-record --region=cn-north-4 --blockchain-id=<id>
```

Expected: each command prints the corresponding section without a traceback.

### 5. Account-level reads

```bash
python3 scripts/bcs_manage.py members       --region=cn-north-4
python3 scripts/bcs_manage.py notifications --region=cn-north-4
python3 scripts/bcs_manage.py quotas        --region=cn-north-4
python3 scripts/bcs_manage.py flavors       --region=cn-north-4
```

### 6. Alerts and metrics

```bash
python3 scripts/bcs_manage.py alerts --region=cn-north-4 --blockchain-id=<id> \
  --type=active_alert --time-range=-1.-1.60 --max-points=10
python3 scripts/bcs_manage.py alerts --region=cn-north-4 --blockchain-id=<id> \
  --statistics --time-range=-1.-1.60
python3 scripts/bcs_manage.py metrics --region=cn-north-4 --blockchain-id=<id> \
  --metric-names=cpuUsage --max-points=10
python3 scripts/bcs_manage.py metrics --region=cn-north-4 --blockchain-id=<id> \
  --scope=node --entity-name=org-1 --max-points=10
```

Expected: `alerts` is bounded to the requested `--time-range`; `--statistics`
returns aggregated alert data. Metric subcommands use the BCS server-side
default window (the metric request models have no time-window field); passing
`--time-range` to them is accepted but prints a `WARNING` that the value is not
transmitted. `--max-points` bounds printed points in both cases. Instance
`metrics` without `--metric-names` queries the default first five metrics
(`cpuUsage`, `diskUsedRate`, `memUsedRate`, `sendBytesRate`, `recvBytesRate`).

### 7. Read error paths

```bash
# missing credentials
env -u HUAWEICLOUD_SDK_AK -u HUAWEICLOUD_SDK_SK python3 scripts/bcs_manage.py list
# unsupported region
python3 scripts/bcs_manage.py list --region=cn-east-3
# unknown instance name
python3 scripts/bcs_manage.py channels --region=cn-north-4 --name=does-not-exist
# client-init failure regression (SdkException must not escape as a traceback)
# Use a region the account has no IAM project in; cn-east-2 is the known case.
python3 scripts/bcs_manage.py list --region=cn-east-2
```

Expected: `ERROR[C01]`, `ERROR[U02]`, `ERROR[U03]` respectively, exit code 2,
no traceback. The last command must print `ERROR[C02]: ...` (not a Python
traceback) and exit 2 whenever IAM project/region resolution fails; when the
account is authorized in that region it simply lists instances.

## Write Verification

Verify parsing, preview and error paths **before** any real mutation.

### 8. Preview mode (no mutation)

```bash
python3 scripts/bcs_manage.py delete-channel --region=cn-north-4 \
  --blockchain-id=<id> --channel-id=<channel>
```

Expected: prints `=== IRREVERSIBLE OPERATION PREVIEW (delete-channel) ===` and
exits with code 2 without calling the API. This proves the confirmation gate
works.

### 9. Read-safe authenticated call (permission probe)

`list` confirms credentials and read permission without mutating anything:

```bash
python3 scripts/bcs_manage.py list --region=cn-north-4
```

Expected: a normal instance list (possibly empty), no `ERROR[C01]` / `U04`.

### 10. Missing credentials on a write

```bash
env -u HUAWEICLOUD_SDK_AK -u HUAWEICLOUD_SDK_SK python3 scripts/bcs_manage.py create-cert \
  --region=cn-north-4 --blockchain-id=<id> --org-name=<org> --user-name=testuser01
```

Expected: `ERROR[C01]`, exit code 2.

### 11. Invalid body file

```bash
printf '{"channels": ' > ./bad.json
python3 scripts/bcs_manage.py create-channels --region=cn-north-4 \
  --blockchain-id=<id> --body-file=./bad.json --confirm
```

Expected: `ERROR[U02]` invalid JSON, no API call.

### 12. Real mutation (only with user approval)

For each mutating test, use a disposable resource and confirm the target with
the user. Example certificate lifecycle on an existing instance:

```bash
# create → freeze → unfreeze a disposable user certificate
python3 scripts/bcs_manage.py create-cert --region=cn-north-4 \
  --blockchain-id=<id> --org-name=<org> --user-name=testuser01 --confirm
python3 scripts/bcs_manage.py freeze-cert --region=cn-north-4 \
  --blockchain-id=<id> --org-name=<org> --user-name=testuser01 --confirm
python3 scripts/bcs_manage.py unfreeze-cert --region=cn-north-4 \
  --blockchain-id=<id> --org-name=<org> --user-name=testuser01 --confirm
```

Expected: each call prints an operation summary; when an operation_id is
returned the script polls ListOpRecord until `finished`/`failed`/`stop`. If the
poll times out, re-check with the same entry point:

```bash
python3 scripts/bcs_manage.py op-record --region=cn-north-4 --operation-id=<operation_id>
```

### 13. Regression: SDK/parameter failures must not leak tracebacks

```bash
# client-init failure: region the account has no IAM project in (cn-east-2)
python3 scripts/bcs_manage.py create-instance --region=cn-east-2 \
  --body-file=./instance.json --confirm

# unknown field in an SDK request body
printf '{"name":"my-chain","unexpected_field":1}' > ./unknown.json
python3 scripts/bcs_manage.py create-instance --region=cn-north-4 \
  --body-file=./unknown.json --confirm
```

Expected: `ERROR[C02]` (or `ERROR[U04]` on 401/403) and `ERROR[U02]`
respectively, exit code 2, no Python traceback. The same behaviour applies to
every `CreateRequestBody` / `ChannelCreateInfo` / `UpdateInstanceRequestBody` /
`CfgRequestBody` / `QuitUnionFromMemberListRequestBody` body command.

The `update-instance` preview must accept the API contract's object array
(`node_orgs` is `list[NodeOrgs]`, each with `name`/`node_count`) without
stringifying it:

```bash
printf '{"node_orgs":[{"name":"org-2","node_count":2}],"is_delete_org":true}' > ./update_obj.json
python3 scripts/bcs_manage.py update-instance --region=cn-north-4 \
  --blockchain-id=<id> --body-file=./update_obj.json
```

Expected: `=== IRREVERSIBLE OPERATION PREVIEW (update-instance) ===` listing
`org-2(2 nodes)` and the delete-org impact note, exit code 2 (no `--confirm`),
no traceback.

### 14. Download verification

```bash
python3 scripts/bcs_manage.py download-sdk-config --region=cn-north-4 \
  --blockchain-id=<id> --body-file=./sdk_config.json --out=/tmp/sdk.zip
test -s /tmp/sdk.zip && echo OK
```

Expected: `Saved N bytes to /tmp/sdk.zip`, where N > 0, and the file mode is
`0600` (owner-only, certificates/SDK config carry key material):

```bash
test -s /tmp/sdk.zip && stat -c '%a' /tmp/sdk.zip
```

A 0-byte response is treated as failure: the script removes the empty file and
exits non-zero with `ERROR[B01]`.

### 15. JSON output mode

```bash
python3 scripts/bcs_manage.py update-instance --region=cn-north-4 \
  --blockchain-id=<id> --body-file=./update.json --confirm --json \
  | python3 -m json.tool >/dev/null && echo ONE_JSON_BLOCK
```

Expected: stdout holds exactly one parseable JSON block
(`{"response": …, "operation_record": …}`); the preview and progress lines are
written to stderr, so `--json | jq` works.

### 16. Cleanup

Delete any resource created for the test, and remove downloaded artifacts that
contain key material.

## Troubleshooting

| Error | Likely cause | Solution |
|-------|--------------|----------|
| `No module named 'huaweicloudsdkbcs'` | SDK missing | `pip install huaweicloudsdkbcs` |
| `ERROR[U01]` confirmation required | `--confirm` missing on a write | Review preview, re-run with `--confirm` |
| `ERROR[U02]` invalid body JSON / region | Malformed file, unknown/mistyped field, unsupported region | Fix JSON per SKILL.md schemas; use a supported region |
| `ERROR[U03]` no instance named X | Name typo or wrong region | Verify with `list` first |
| `ERROR[C01]` | AK/SK not set | Export `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` |
| `ERROR[C02]` client initialization failed | No IAM project in region / transient credentials | Verify the account has a project in the target region |
| Download size 0 | Empty response / wrong cert type | The script removes the empty file and exits `ERROR[B01]`; verify `--cert-type` |
| `ERROR[U04]` HTTP 403 | Missing IAM permission | Attach `BCS ReadOnlyAccess` or the required write policy |
| Operation `failed` | BCS rejected the request | Read `desc`/`message`; ask before retry |