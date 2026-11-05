# Detailed Command Reference

> All commands below are written in their native, directly executable
> `hcloud <Service> <Operation> --key=value ...` form. At execution time wrap each one for quality
> reporting (reporting bypass only — the wrapped command is passed through unchanged):
> `skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- <hcloud command>`.
> Parameter names are taken from the authoritative `hcloud <Operation> --help` output; re-check with
> `hcloud DDS CreateInstance --help` / `hcloud DCS CreateInstance --help` before building a command.

## DDS CLI Commands

| Action | CLI Command |
|--------|-------------|
| List instances | `hcloud DDS ListInstances --cli-region={region} [--id={id}] [--name={name}] [--mode={mode}] [--datastore_type={type}] [--limit={n}] [--offset={n}]` |
| Create instance | `hcloud DDS CreateInstance --cli-region={region} --name={name} --region={region} --availability_zone={az} --datastore.type=DDS-Community --datastore.version={version} --datastore.storage_engine=wiredTiger --mode={mode} --flavor.{N}.type={node_type} --flavor.{N}.num={count} --flavor.{N}.spec_code={spec} --flavor.{N}.size={size} --flavor.{N}.storage=ULTRAHIGH --vpc_id={vpc_id} --subnet_id={subnet} --security_group_id={sg}` |
| Add read-only node | `hcloud DDS AddReadonlyNode --cli-region={region} --instance_id={id} --num={n} --spec_code={spec_code_rr}` |
| Add sharding node | `hcloud DDS AddShardingNode --cli-region={region} --instance_id={id} --type={mongos_shard} --num={n} --spec_code={spec} --volume.size={disk_gb_10_2000}` |
| Create manual backup | `hcloud DDS CreateManualBackup --cli-region={region} --backup.instance_id={id} --backup.name={name}` |
| Delete instance | `hcloud DDS DeleteInstance --cli-region={region} --instance_id={id}` |
| List flavors | `hcloud DDS ListFlavors --cli-region={region} [--engine_name={DDS-Community\|DDS-Enhanced}]` |
| List storage types | `hcloud DDS ListStorageType --cli-region={region}` |
| Show backup policy | `hcloud DDS ShowBackupPolicy --cli-region={region} --instance_id={id}` |
| Show entity config | `hcloud DDS ShowEntityConfiguration --cli-region={region} --instance_id={id} --entity_id={entity_id}` |

> Notes:
> - DDS `ListInstances`/`CreateInstance` `--mode` shares its name with a KooCLI system parameter. When prompted, answer `b` (target API parameter); in non-interactive environments prefix the command with `echo b |` (verified) or use `--cli-jsonInput`.
> - `--region` on `CreateInstance` is a **required body parameter**; KooCLI prints a harmless duplicate-parameter notice when `--cli-region` is also present.
> - `ShowEntityConfiguration` requires `--entity_id`: pass the instance ID for replica-set/single-node instances, or the group ID / node ID for cluster (sharding) instances.
> - `CreateInstance` disk parameters (issue #496-3): `hcloud DDS CreateInstance --help` marks `--flavor.{N}.size` and `--flavor.{N}.storage` as `optional`, but the API rejects a request without them. `--flavor.{N}.size` is the disk size in GB and **must be a multiple of 10**: 10–2000 GB for shard groups, config groups (exactly 20 GB) and replica sets, 10–1000 GB for a single node; mongos nodes do not select a disk, so the parameter is meaningless for them. `--flavor.{N}.storage` is `ULTRAHIGH` (SSD).
> - `AddReadonlyNode` `--spec_code` is **required** (issue #659-1) and must be a read-only spec code ending in `.rr`, e.g. `dds.mongodb.c6.large.4.rr`. Look it up first with `hcloud DDS ListFlavors --cli-region={region} --engine_name=DDS-Community` and pick a `.rr` entry. Not every product/region exposes a read-only flavor: measured on 2026-11-03, cn-north-4, cn-east-3 and cn-south-1 each offered 17 `.rr` flavors while ap-southeast-1 offered none. The flavor pool changes by region and over time, so never infer availability from a documented example — always run the `ListFlavors` query above first. When the region has no `.rr` flavor the call fails with `DBS.280434` ("The specifications are unavailable"), and the `DDS-Enhanced` engine returns `DBS.02000024` (not open to the public). Tell the user the capability is unavailable there instead of retrying with a non-`.rr` code.
> - `AddShardingNode` `--volume.size` is documented as `optional` by the CLI help but is required in practice when `--type=shard` (issue #659-2): it is the disk capacity applied to every newly added shard group, range 10–2000 GB. Omitting it fails with `DBS.280311` ("Invalid storage space"). It does not apply to `--type=mongos`.

## DCS CLI Commands

| Action | CLI Command |
|--------|-------------|
| List instances | `hcloud DCS ListInstances --cli-region={region} [--name={name}] [--instance_id={id}] [--status={status}] [--limit={n}] [--offset={n}]` |
| Show instance | `hcloud DCS ShowInstance --cli-region={region} --instance_id={id}` |
| Show node information | `hcloud DCS ShowNodesInformation --cli-region={region} --instance_id={id}` |
| Show IP whitelist | `hcloud DCS ShowIpWhitelist --cli-region={region} --instance_id={id}` |
| List ACL accounts | `hcloud DCS ListAclAccounts --cli-region={region} --instance_id={id}` |
| Delete instance | `hcloud DCS DeleteSingleInstance --cli-region={region} --instance_id={id}` |
| Restart instance | `hcloud DCS RestartOrFlushInstances --cli-region={region} --instances.{N}={id} --action={restart_soft_restart_flush}` |
| Create instance | `hcloud DCS CreateInstance --cli-region={region} --name={name} --engine={Redis\|Memcached} --engine_version={version} --capacity={gb} --spec_code={spec_code} --vpc_id={vpc_id} --subnet_id={subnet_id} --az_codes.1={az_code} [--security_group_id={sg}] --password={password}` — `--password` is **required by default** (when `--no_password_access` is `false` or unset) and may be omitted only with `--no_password_access=true`. It shares its name with a KooCLI system parameter — see the workaround note below. |
| Create custom template | `hcloud DCS CreateCustomTemplate --cli-region={region} --name={template_name} --template_id={source_template_id} --type={sys\|user} --params.{*} [--engine={engine}] [--engine_version={version}] [--cache_mode={mode}]` (the help notation `--params.{*}` is passed as key/value pairs, e.g. `--params.key1=value1`) |
| List config templates | `hcloud DCS ListConfigTemplates --cli-region={region} --type={sys\|user} [--engine={engine}] [--engine_version={version}] [--cache_mode={mode}] [--name={name}] [--template_id={id}] [--limit={n}] [--offset={n}]` |
| List flavors | `hcloud DCS ListFlavors --cli-region={region} [--engine={Redis\|Memcached}] [--engine_version={version}] [--cache_mode={mode}] [--capacity={gb}] [--spec_code={spec_code}]` |

```bash
# DCS instance creation — CLI is the primary path (the SDK table below is the fallback only).
# NOTE: `--password` shares its name with a KooCLI system parameter (same class of problem as
# DDS `--mode`). Interactive: type `b` (target API parameter) when prompted. Non-interactive /
# scripted (verified): prefix the command with `echo b |`, or pass the parameters through
# `--cli-jsonInput` together with `--project_id`. When `--no_password_access=true`, drop
# `--password` entirely — no prompt is triggered.
hcloud DCS CreateInstance --cli-region={region} \
  --name={name} --engine=Redis --engine_version=5.0 --capacity=1 \
  --spec_code={spec_code} --vpc_id={vpc_id} --subnet_id={subnet_id} \
  --az_codes.1={az_code} --password={password}
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DCS CreateInstance --cli-region={region} --name={name} --engine=Redis --engine_version=5.0 --capacity=1 --spec_code={spec_code} --vpc_id={vpc_id} --subnet_id={subnet_id} --az_codes.1={az_code} --password={password}
# Non-interactive alternative (answer `b` to the `--password` prompt; verified):
#   echo b | hcloud DCS CreateInstance --cli-region={region} --name={name} --engine=Redis --engine_version=5.0 --capacity=1 --spec_code={spec_code} --vpc_id={vpc_id} --subnet_id={subnet_id} --az_codes.1={az_code} --password={password}
# Fully non-interactive alternative (no prompt; verified — KooCLI requires `--project_id` on this path):
#   hcloud DCS CreateInstance --cli-region={region} --project_id={project_id} --cli-jsonInput=/tmp/dcs_create.json

# '--type' must match the source template: sys for a system template, user for a user template.
hcloud DCS CreateCustomTemplate --cli-region={region} \
  --name={template_name} --template_id={source_template_id} \
  --type=sys --params.timeout=300
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DCS CreateCustomTemplate --cli-region={region} --name={template_name} --template_id={source_template_id} --type=sys --params.timeout=300

hcloud DCS ListConfigTemplates --cli-region={region} --type=sys
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DCS ListConfigTemplates --cli-region={region} --type=sys
```

> Notes:
> - `hcloud DCS CreateInstance --help` marks `--az_codes.[N]`, `--capacity`, `--engine`, `--name`, `--spec_code`, `--subnet_id` and `--vpc_id` as **required** (`--cli-region`/`--project_id` are required by KooCLI itself). `--security_group_id` is required only when `--engine=Redis` with `--engine_version=3.0`, or when `--engine=Memcached`; Redis 4.0/5.0 instances use whitelist control instead. `--password` is optional in the CLI signature, but the request must carry it unless `--no_password_access=true`; the Redis password must be 8–32 characters containing at least three of uppercase, lowercase, digit and special characters.
> - `--password` on `hcloud DCS CreateInstance` collides with the KooCLI system parameter of the same name (verified on KooCLI 7.2.12): an inlined `--password=...` triggers the same-name parameter prompt (the CLI cannot tell whether it is the system parameter or the target-API parameter) and fails with `[USE_ERROR]EOF` when stdin is not a TTY. Interactive: answer `b` (target API parameter). Non-interactive (verified): prefix the command with `echo b |`, or pass the parameters through `--cli-jsonInput=<file>` together with `--project_id` — KooCLI itself points to `--cli-jsonInput` to avoid the interaction. With `--no_password_access=true` the parameter is not needed and no prompt appears.
> - Obtain `--spec_code` before creating: run `hcloud DCS ListFlavors --cli-region={region} --engine=Redis --capacity=1` (optionally `--cache_mode=single`) or read the spec name from the DCS console purchase page. Example value for a 1 GB single-replica Redis 5.0 instance: `redis.single.xu1.large.1`.
> - `ListConfigTemplates` `--type` is **required** and accepts exactly `sys` (system templates) or `user` (user templates) — **not** `system` (issue #496-2). `--engine`, `--engine_version` and `--cache_mode` are optional; when supplied they must form a consistent combination for the target engine/version/cache mode, otherwise the call is rejected with `DCS.4063`. When the values cannot be paired reliably, pass `--type` alone (for example `hcloud DCS ListConfigTemplates --cli-region={region} --type=sys`) and filter the returned JSON by `engine`/`engine_version`/`cache_mode` client-side.
> - `CreateCustomTemplate` requires `--name`, `--template_id`, `--type` and `--params.{*}`. `--type` must **match the source template** (issue #659-4): `sys` when `--template_id` points to a system template, `user` when it points to a user template. A mismatch fails with `DCS.4988` ("Query config param template data failed").
> - Existence pre-check for delete/query operations (issue #496-6): run `hcloud DCS ListInstances --cli-region={region} --instance_id={id}` (or `ShowInstance`) first; if the result is empty, report "instance {id} does not exist" and stop. Map API failures `DCS.002` (instance does not exist) and DDS `DBS.01010023` (instance not found) to that same clear message.
> - `RestartOrFlushInstances` `--action` accepts only `restart`, `soft_restart` or `flush` (issue #496-7); validate the value before calling, since an illegal value returns `DCS.001`.

## DCS SDK Operations (fallback)

> Use these only when the hcloud CLI cannot be used. The Python SDK does not read the encrypted AK/SK
> from the hcloud profile — set `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` (and the region) first.
> See `references/cli-installation-guide.md`.

| Action | SDK Method | Required Params |
|--------|------------|-----------------|
| Get node info | `show_nodes_information` | `instance_id` |
| List config templates | `list_config_templates` | `type` — **`sys` or `user`, never `system`** (issue #496-2). `engine` / `engine_version` / `cache_mode` are optional; pass them only as a consistent set, otherwise omit them and filter the returned templates client-side. A mismatched combination returns `DCS.4063`. |
| Create custom template | `create_custom_template` | `body` with `name`, `template_id`, `type` (**must match the source template**: `sys` for a system source template, `user` for a user source template — issue #659-4), `params`; `engine`, `engine_version`, `cache_mode` optional |
| Create instance | `create_instance` | `body` with `name`, `engine`, `engine_version`, `capacity`, `spec_code` (**required**, e.g. `redis.single.xu1.large.1`, from `ListFlavors` — issue #659-3), `vpc_id`, `subnet_id`, `az_codes`, `password` (**required unless `no_password_access=true`**; `DCS.4019` if it does not meet the complexity rules); `security_group_id` required for Redis 3.0 / Memcached |
