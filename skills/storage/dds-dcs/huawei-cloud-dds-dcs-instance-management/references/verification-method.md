# Verification Method

## 1. CLI Command Verification

Verify that each hcloud command produces valid output:

```bash
# Test DDS ListInstances
hcloud DDS ListInstances --cli-region=cn-north-4 --limit=1
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DDS ListInstances --cli-region=cn-north-4 --limit=1

# Test DCS ListInstances
hcloud DCS ListInstances --cli-region=cn-north-4 --limit=1
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DCS ListInstances --cli-region=cn-north-4 --limit=1

# Test DDS ListFlavors
hcloud DDS ListFlavors --cli-region=cn-north-4 --engine_name=DDS-Community
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DDS ListFlavors --cli-region=cn-north-4 --engine_name=DDS-Community
```

Expected: Returns valid JSON with instance/flavor data, not an error.

## 2. SDK Verification

Verify SDK imports and basic connectivity:

```bash
python3 -c "
from huaweicloudsdkdcs.v2 import DcsClient
from huaweicloudsdkdds.v3 import DdsClient
print('SDK packages available ✓')
"
```

SDK calls also need their own credentials (`HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` /
`HUAWEICLOUD_SDK_REGION`); the encrypted AK/SK in `~/.hcloud/config.json` is not
readable by the Python SDK. See `references/cli-installation-guide.md` (issue #496-5).

## 3. Pre-flight Validation

Run these checks **before** executing an operation, so the skill reports an actionable
message instead of a raw API error code (issue #496-6, issue #496-7).

### 3.1 Existence check (before delete/query)

Every delete or per-instance query must first prove that the instance exists in
`{region}`.

```bash
# DDS — use before DeleteInstance / ShowEntityConfiguration / ShowBackupPolicy
hcloud DDS ListInstances --cli-region={region} --id={instance_id}

# DCS — use before DeleteSingleInstance / ShowNodesInformation
hcloud DCS ListInstances --cli-region={region} --instance_id={instance_id}
hcloud DCS ShowInstance --cli-region={region} --instance_id={instance_id}
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DDS ListInstances --cli-region={region} --id={instance_id}
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DCS ListInstances --cli-region={region} --instance_id={instance_id}
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DCS ShowInstance --cli-region={region} --instance_id={instance_id}
```

- Empty result set (no instance matching the id) → report `instance {instance_id} not
  found` and stop; do not call the mutating API.
- Otherwise continue with the requested operation.

Raw error codes that this check prevents from reaching the user:

| Raw error | Meaning | Raised by |
|-----------|---------|-----------|
| `DBS.01010023` | DDS instance not found | `hcloud DDS DeleteInstance` with an unknown `--instance_id` |
| `DCS.002` | DCS instance does not exist | `hcloud DCS DeleteSingleInstance` / `hcloud DCS ShowInstance` / SDK `show_nodes_information` with an unknown instance id |
| `DCS.001` | Invalid `action` value | `hcloud DCS RestartOrFlushInstances` with an unsupported `--action` (see 3.2) |

### 3.2 Parameter validation (before create/restart)

DDS `CreateInstance` — confirm every item below is present before executing. The list
is cross-checked against `hcloud DDS CreateInstance --help` (required) plus issue
#496-3 (API-required in practice):

| Parameter | Notes |
|-----------|-------|
| `--name` | 4–64 chars, must start with a letter |
| `--mode` | `ReplicaSet` / `Sharding` / `Single`; shares its name with a KooCLI system parameter, so prefer `--cli-jsonInput` or pipe the answer |
| `--datastore.type` | `DDS-Community` |
| `--datastore.version` | `3.4` / `4.0` / `4.2` / `4.4` / `5.0` |
| `--datastore.storage_engine` | `wiredTiger` |
| `--region` | Target region ID |
| `--availability_zone` | Availability zone ID |
| `--vpc_id` | VPC ID |
| `--subnet_id` | Subnet ID |
| `--security_group_id` | Security group ID |
| `--flavor.[N].type` | `mongos` / `shard` / `config` / `replica` / `single` |
| `--flavor.[N].num` | Node count, e.g. `replica` = 3, 5 or 7 |
| `--flavor.[N].spec_code` | Flavor code, obtained from `hcloud DDS ListFlavors` |
| `--flavor.[N].size` | Disk size in GB, a multiple of 10 |
| `--flavor.[N].storage` | Disk type, `ULTRAHIGH` (SSD) |

If any item is missing, list the missing parameters together with an example value and
stop instead of executing. `--flavor.[N].size` and `--flavor.[N].storage` are marked
optional by `hcloud DDS CreateInstance --help` but are required by the DDS API in
practice — a missing value fails with a raw parameter error (issue #496-3).

DCS `RestartOrFlushInstances` — `--action` accepts only these values (source:
`hcloud DCS RestartOrFlushInstances --help`):

| `--action` | Meaning |
|-----------|---------|
| `restart` | Force restart |
| `soft_restart` | Soft restart, restarts the process only |
| `flush` | Clear data (Redis 4.0 / Redis 5.0 only) |

```bash
hcloud DCS RestartOrFlushInstances --cli-region={region} --instances.1={instance_id} --action={restart|soft_restart|flush}
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DCS RestartOrFlushInstances --cli-region={region} --instances.1={instance_id} --action={restart|soft_restart|flush}
```

For any other value (for example `force_restart`), report `action '{value}' is invalid;
allowed values: restart / soft_restart / flush` and stop, instead of letting the API
return `DCS.001` (issue #496-7).

### 3.3 DCS CLI path verification

Confirm the CLI exposes the DCS operations before documenting or executing them
(static check, no credentials required):

```bash
hcloud DCS CreateInstance --help
hcloud DCS CreateCustomTemplate --help
hcloud DCS ListConfigTemplates --help
hcloud DCS RestartOrFlushInstances --help
```

Resolve the mandatory `--spec_code` of `hcloud DCS CreateInstance` from the flavor list
(`--spec_code` is a required parameter of that operation):

```bash
hcloud DCS ListFlavors --cli-region={region} --engine=Redis --engine_version=5.0 --cache_mode=single
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DCS ListFlavors --cli-region={region} --engine=Redis --engine_version=5.0 --cache_mode=single
```

#### `--password` naming conflict (same class as DDS `--mode`)

`--password` is an API parameter of `hcloud DCS CreateInstance`, but it shares its name
with a KooCLI system parameter — the same class of conflict as `--mode` on
`hcloud DDS CreateInstance`. When it is inlined on the command line, KooCLI asks whether
`password` is the KooCLI system parameter (a), the target API parameter (b), or both (c);
in a non-interactive environment (no TTY, i.e. the agent case) the command aborts with
`[USE_ERROR]EOF` before the request is even built. Use one of the following three forms
instead (all verified against KooCLI 7.2.12 with `--dryrun`):

```bash
# Form 1 — answer the prompt with `b` (target API parameter); works in shell pipelines
echo b | hcloud DCS CreateInstance --cli-region={region} --name={name} --engine=Redis --engine_version=5.0 --capacity=1 --spec_code={spec_code} --vpc_id={vpc_id} --subnet_id={subnet_id} --az_codes.1={az_code} --password={complex_password}

# Form 2 — pass the body through a JSON input file (no prompt; `--project_id` is required on this path)
hcloud DCS CreateInstance --cli-region={region} --project_id={project_id} --cli-jsonInput=/tmp/dcs_create.json
# /tmp/dcs_create.json:
# {"body":{"name":"{name}","engine":"Redis","engine_version":"5.0","capacity":1,"spec_code":"{spec_code}","vpc_id":"{vpc_id}","subnet_id":"{subnet_id}","az_codes":["{az_code}"],"password":"{complex_password}"}}

# Form 3 — no password at all: set --no_password_access=true and omit --password
hcloud DCS CreateInstance --cli-region={region} --name={name} --engine=Redis --engine_version=5.0 --capacity=1 --spec_code={spec_code} --vpc_id={vpc_id} --subnet_id={subnet_id} --az_codes.1={az_code} --no_password_access=true
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DCS CreateInstance --cli-region={region} --name={name} --engine=Redis --engine_version=5.0 --capacity=1 --spec_code={spec_code} --vpc_id={vpc_id} --subnet_id={subnet_id} --az_codes.1={az_code} --password={complex_password}
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DCS CreateInstance --cli-region={region} --project_id={project_id} --cli-jsonInput=/tmp/dcs_create.json
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DCS CreateInstance --cli-region={region} --name={name} --engine=Redis --engine_version=5.0 --capacity=1 --spec_code={spec_code} --vpc_id={vpc_id} --subnet_id={subnet_id} --az_codes.1={az_code} --no_password_access=true
```

Parameter sources (`ctx/help/DCS_CreateInstance.txt`): `--password` is optional, but the
request must contain it when `no_password_access` is `false` or unset (8–32 characters,
at least three of lowercase / uppercase / digit / special; a non-compliant value is
rejected with `DCS.4019`); `--no_password_access` is an optional boolean that defaults to
`false`. When Form 1 is run through the reporting wrapper, feed the answer to the whole
pipeline (`echo b | skill-quality-cli run --skill-name ... -- hcloud DCS CreateInstance ...`).

## 4. Mutating Operation Safety

Before executing any mutating operation:

1. Always confirm with the user
2. Use `--dryrun` or parameter validation first (when available)
3. Recommend creating a backup before destructive operations
4. Run the existence and parameter checks in section 3 first.

## 5. End-to-End Test

Deployment analysis:

```bash
# Collect DDS deployment info (--mode prompts; answer `b` / use `echo b |` in CI)
hcloud DDS ListInstances --cli-region=cn-north-4 --datastore_type=DDS-Community
echo b | hcloud DDS ListInstances --cli-region=cn-north-4 --mode=ReplicaSet

# Collect DCS security info
hcloud DCS ListInstances --cli-region=cn-north-4
hcloud DCS ShowIpWhitelist --cli-region=cn-north-4 --instance_id={instance_id}
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DDS ListInstances --cli-region=cn-north-4 --datastore_type=DDS-Community
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DDS ListInstances --cli-region=cn-north-4 --mode=ReplicaSet
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DCS ListInstances --cli-region=cn-north-4
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DCS ShowIpWhitelist --cli-region=cn-north-4 --instance_id={instance_id}
```

## 6. Quality Reporting (CLI) Verification

```bash
# 6.1 CLI install (idempotent) + PATH export
export PATH="$HOME/.local/bin:$PATH"
bash scripts/ensure_cli.sh
command -v skill-quality-cli   # or ~/.local/bin/skill-quality-cli

# 6.2 Wrapper mode — hcloud command run + automatic quality report
skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management \
  -- hcloud DDS ListInstances --cli-region=cn-north-4 --limit=1

# 6.3 Manual single-step report (fire-and-forget; output/exit unchanged)
skill-quality-cli report --skill-name huawei-cloud-dds-dcs-instance-management --status success

# 6.4 E2E real delivery through the bundled carrier (must print [quality-report] OK trace_id=...)
printf '{"session_id":"verify-dds-dcs","trigger_type":"workflow"}' > /tmp/qcfg.json
SKILL_QUALITY_REPORT_VERBOSE=1 python3 scripts/cli/cli_entry.py --no-auto-upgrade \
  report --skill-name huawei-cloud-dds-dcs-instance-management --status success --json /tmp/qcfg.json 2>&1 | tail -1
```

Expected: step 6.4 prints `[quality-report] OK trace_id=<id>` (HTTP 200 from the quality endpoint);
steps 6.2/6.3 complete with their normal output/exit codes unchanged (reporting never blocks or
alters hcloud results).
