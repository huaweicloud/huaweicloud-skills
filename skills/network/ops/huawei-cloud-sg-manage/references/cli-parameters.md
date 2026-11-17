# huawei-cloud-sg-manage — CLI parameter reference

Verified against `hcloud VPC <Operation> --help` (KooCLI 7.2.12 / 7.3.12).
Common to all commands: `--cli-region` (required), `--project_id` (required by the API but
auto-filled from the authenticated profile when omitted), `--cli-output=json`.

Write operations expose `--dry_run=true` for a validation-only preview
(`CreateSecurityGroup/v3`, `CreateSecurityGroupRule/v3`, `UpdateSecurityGroup/v3`).
The two delete operations have no `--dry_run`; preview them with `ShowSecurityGroup/v3` /
`ShowSecurityGroupRule/v2` and require explicit user confirmation before executing.

### ListSecurityGroups/v3

| Parameter | Type | Required | Example |
| --------- | ---- | -------- | ------- |
| `--name.[N]` | array\<string\> | No | `--name.1=web-sg` |
| `--id.[N]` | array\<string\> | No | `--id.1=<sg-id>` |
| `--description.[N]` | array\<string\> | No | `--description.1=web` |
| `--enterprise_project_id` | string | No | `--enterprise_project_id=0` |
| `--limit` | integer | No | `--limit=100` (0-2000) |
| `--marker` | string | No | pagination marker |

### ListSecurityGroupRules/v3

| Parameter | Type | Required | Example |
| --------- | ---- | -------- | ------- |
| `--security_group_id.[N]` | array\<string\> | No | `--security_group_id.1=<sg-id>` |
| `--direction` | string | No | `--direction=ingress` |
| `--protocol.[N]` | array\<string\> | No | `--protocol.1=tcp` |
| `--action` | string | No | `--action=allow` |
| `--enabled` | boolean | No | `--enabled=true` |
| `--remote_ip_prefix` | string | No | `--remote_ip_prefix=10.0.0.0/8` |
| `--limit` | integer | No | `--limit=100` |

### ShowSecurityGroup/v3 / ShowSecurityGroupRule/v2

| Operation | Parameter | Type | Required |
| --------- | --------- | ---- | -------- |
| ShowSecurityGroup/v3 | `--security_group_id` | string | **Yes** |
| ShowSecurityGroupRule/v2 | `--security_group_rule_id` | string | **Yes** |

### CreateSecurityGroup/v3

| Parameter | Type | Required | Example |
| --------- | ---- | -------- | ------- |
| `--security_group.name` | string | **Yes** | `--security_group.name=web-sg` |
| `--security_group.description` | string | No | `--security_group.description=web-servers` |
| `--security_group.enterprise_project_id` | string | No | `--security_group.enterprise_project_id=0` |
| `--security_group.tags.[N].key` / `.value` | string | No | `--security_group.tags.1.key=env --security_group.tags.1.value=prod` |
| `--dry_run` | boolean | No | validation call only |

### CreateSecurityGroupRule/v3

| Parameter | Type | Required | Example |
| --------- | ---- | -------- | ------- |
| `--security_group_rule.security_group_id` | string | **Yes** | `--security_group_rule.security_group_id=<sg-id>` |
| `--security_group_rule.direction` | string | **Yes** | `--security_group_rule.direction=ingress` (ingress\|egress) |
| `--security_group_rule.protocol` | string | No | `--security_group_rule.protocol=tcp` (tcp\|udp\|icmp\|icmpv6\|any) |
| `--security_group_rule.ethertype` | string | No | `--security_group_rule.ethertype=IPv4` (IPv4\|IPv6) |
| `--security_group_rule.multiport` | string | No | `--security_group_rule.multiport=22,80` or `22-25` |
| `--security_group_rule.remote_ip_prefix` | string | No | `--security_group_rule.remote_ip_prefix=10.0.0.0/8` |
| `--security_group_rule.remote_group_id` | string | No | peer security group id (mutually exclusive with remote_ip_prefix) |
| `--security_group_rule.remote_address_group_id` | string | No | address group id (mutually exclusive with the two above) |
| `--security_group_rule.action` | string | No | `--security_group_rule.action=allow` (allow\|deny) |
| `--security_group_rule.priority` | integer | No | `--security_group_rule.priority=1` (1-65535, lower = higher priority) |
| `--security_group_rule.enabled` | boolean | No | `--security_group_rule.enabled=true` |
| `--security_group_rule.description` | string | No | optional label |

### UpdateSecurityGroup/v3

| Parameter | Type | Required | Example |
| --------- | ---- | -------- | ------- |
| `--security_group_id` | string | **Yes** | `--security_group_id=<sg-id>` |
| `--security_group.name` | string | No | `--security_group.name=new-name` |
| `--security_group.description` | string | No | `--security_group.description=new-desc` |
| `--dry_run` | boolean | No | `--dry_run=true` — validation-only preview, changes nothing |

### DeleteSecurityGroup/v3 / DeleteSecurityGroupRule/v3

| Operation | Parameter | Type | Required |
| --------- | --------- | ---- | -------- |
| DeleteSecurityGroup/v3 | `--security_group_id` | string | **Yes** |
| DeleteSecurityGroupRule/v3 | `--security_group_rule_id` | string | **Yes** |
