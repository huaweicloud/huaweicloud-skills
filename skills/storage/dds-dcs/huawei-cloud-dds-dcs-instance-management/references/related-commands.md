# Detailed Command Reference

## DDS CLI Commands

| Action | CLI Command |
|--------|-------------|
| List instances | `hcloud DDS ListInstances --cli-region={region} [--id={id}] [--name={name}] [--mode={mode}] [--datastore_type={type}] [--limit={n}] [--offset={n}]` |
| Create instance | `hcloud DDS CreateInstance --cli-region={region} --name={name} --region={region} --availability_zone={az} --datastore.type=DDS-Community --datastore.version={version} --datastore.storage_engine=wiredTiger --mode={mode} --flavor.{N}.type={node_type} --flavor.{N}.num={count} --flavor.{N}.spec_code={spec} --subnet_id={subnet} --security_group_id={sg}` |
| Add read-only node | `hcloud DDS AddReadonlyNode --cli-region={region} --instance_id={id} --num={n}` |
| Add sharding node | `hcloud DDS AddShardingNode --cli-region={region} --instance_id={id} --type={mongos_shard} --num={n} --spec_code={spec}` |
| Create manual backup | `hcloud DDS CreateManualBackup --cli-region={region} --backup.instance_id={id} --backup.name={name}` |
| Delete instance | `hcloud DDS DeleteInstance --cli-region={region} --instance_id={id}` |
| List flavors | `hcloud DDS ListFlavors --cli-region={region} [--engine_name={type}]` |
| List storage types | `hcloud DDS ListStorageType --cli-region={region}` |
| Show backup policy | `hcloud DDS ShowBackupPolicy --cli-region={region} --instance_id={id}` |
| Show entity config | `hcloud DDS ShowEntityConfiguration --cli-region={region} --instance_id={id} --entity_id={entity_id}` |

> Notes:
> - DDS `ListInstances`/`CreateInstance` `--mode` shares its name with a KooCLI system parameter. When prompted, answer `b` (target API parameter); in non-interactive environments prefix the command with `echo b |` (verified) or use `--cli-jsonInput`.
> - `--region` on `CreateInstance` is a **required body parameter**; KooCLI prints a harmless duplicate-parameter notice when `--cli-region` is also present.
> - `ShowEntityConfiguration` requires `--entity_id`: pass the instance ID for replica-set/single-node instances, or the group ID / node ID for cluster (sharding) instances.

## DCS CLI Commands

| Action | CLI Command |
|--------|-------------|
| List instances | `hcloud DCS ListInstances --cli-region={region} [--name={name}] [--instance_id={id}] [--status={status}] [--limit={n}] [--offset={n}]` |
| Show instance | `hcloud DCS ShowInstance --cli-region={region} --instance_id={id}` |
| Show IP whitelist | `hcloud DCS ShowIpWhitelist --cli-region={region} --instance_id={id}` |
| List ACL accounts | `hcloud DCS ListAclAccounts --cli-region={region} --instance_id={id}` |
| Delete instance | `hcloud DCS DeleteSingleInstance --cli-region={region} --instance_id={id}` |
| Restart instance | `hcloud DCS RestartOrFlushInstances --cli-region={region} --instances.{N}={id} --action={restart_soft_restart_flush}` |

## DCS SDK Operations

| Action | SDK Method | Required Params |
|--------|------------|-----------------|
| Get node info | `show_nodes_information` | `instance_id` |
| List config templates | `list_config_templates` | `type` (sys/user), `engine` (Redis/Memcached), `engine_version`, `cache_mode` (missing required params → DCS.4063) |
| Create custom template | `create_custom_template` | `body` with name, engine, cache_mode (+ type/user, engine_version, template_id) |
| Create instance | `create_instance` | `body` with name, engine, capacity, vpc_id, subnet_id |