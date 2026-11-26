# Provisioning checks

Use the main workflow in `../../SKILL.md`; pitfalls and failure handling are centralized in `../gotchas.md` G07–G12. When preparing creation, find the operation and dependencies in `commands.md`, then use current versioned help.

## ECS sales and dependencies

Query the target flavor/AZ with `ECS/ListFlavors`. Retain `id`, CPU, memory and relevant `os_extra_specs`.

| Check | Rule |
| --- | --- |
| Sales status | `cond:operation:az` is target-AZ status; `cond:operation:status` is regional status. Precedence follows G08. `normal/promotion`: commercial; `abandon`: retired; `sellout`: sold out; `obt/obt_sellout`: beta. |
| Billing | `cond:operation:charge`: `period` for prepaid, `demand` for pay-per-use; the documented absent-field default supports both. |
| Further sales evidence | `ListFlavorSellPolicies`: retain flavor, AZ, `sell_mode`, `sell_status` and account restrictions. |
| Dependencies | Check project/region, quota, image architecture/status/minimum disk, disk support, subnet membership/status/free IPs, security-group access/rules and login method. |

Source: [ECS extension fields](https://support.huaweicloud.com/api-ecs/zh-cn_topic_0020212656.md). Stop on evidenced incompatibility, sold-out status or permission restrictions; disclose unresolved conditions.

## Login selection

Use an existing suitable key pair when authorized; verify the user can use its private key without reading it. Prepaid ECS key login requires associated fields such as `server.metadata.op_svc_userid` under current help. For password login, follow G12 before preparing the request.

## Unsubscribe and stop using

Guide the user through the console; do not generate or execute unsubscribe/delete commands.

- Prepaid: Cost Center → Orders → Unsubscriptions (or Unsubscriptions and Returns).
- Pay-per-use: the resource's service console → delete after backup/migration.

Before submission, check account, resource, related resources, refund, fees and destination against the console preview and [official rules](https://support.huaweicloud.com/usermanual-billing/unsubscription_topic_2000010.md).
