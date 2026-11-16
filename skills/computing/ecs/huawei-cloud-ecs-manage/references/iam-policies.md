# IAM Policies — Least Privilege for huawei-cloud-ecs-manage

This skill requires IAM permissions on the ECS service (service prefix `ecs`) plus read-only
permissions on IMS (images), VPC (subnets / security groups), EIP (public IPs), KPS (keypairs) and
EVS (volumes), which the diagnosis flow cross-checks. Grant the **minimum** permissions per capability
group. All policies are region-scoped (ECS is a regional service; instances belong to a project).

The action names below follow the Huawei Cloud 「权限及授权项」 naming (`service:resource_type:action`)
and reuse only action names already verified in the official ECS/IMS/VPC/EVS permission catalogues
and in previously merged skills of this repository.

## 1. Query + Diagnose (R3, read-only)

Covers: `huawei_list_ecs_instances`, `huawei_get_ecs_instance`, `huawei_list_ecs_flavors`,
`huawei_list_ecs_images`, `huawei_list_ecs_quotas`, `huawei_diagnose_ecs_create_failure`,
`huawei_analyze_ecs_health`.

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:cloudServers:list",
        "ecs:cloudServers:get",
        "ecs:cloudServerFlavors:list",
        "ecs:cloudServerImages:list",
        "ecs:jobs:get",
        "ecs:serverVolumes:list",
        "ims:images:list",
        "vpc:subnets:list",
        "vpc:securityGroups:list",
        "vpc:publicIps:list",
        "evs:volumes:list",
        "kps:keypairs:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```

> - `ecs:cloudServers:list` covers `ListServersDetails` (instance lists) and also the quota
>   read (`ShowServerLimits`); `ecs:cloudServers:get` covers `ShowServer`.
> - `ims:images:list` is required by `huawei_list_ecs_images` / diagnosis step 3 (image check).
> - `vpc:subnets:list`, `vpc:securityGroups:list`, `vpc:publicIps:list` and `evs:volumes:list`
>   are required by diagnosis steps 4/6 and by `huawei_analyze_ecs_health`.
> - **Keypair check (diagnosis step 5)**: `hcloud KPS ListKeypairs` requires the KPS keypair
>   read permission `kps:keypairs:list` (Key Pair Service 「权限及授权项」). It is declared in
>   the policy JSON above; without it step 5 returns 403. The diagnosis flow degrades
>   gracefully: a 403 on step 5 is reported as "cannot verify keypair — check IAM permission",
>   not as a failure.

## 2. Manage (R2 — create / start / stop / restart)

Covers: `huawei_create_ecs_instance`, `huawei_start_ecs_instance`, `huawei_stop_ecs_instance`,
`huawei_restart_ecs_instance`.

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:cloudServers:create",
        "ecs:cloudServers:action",
        "ecs:cloudServers:list",
        "ecs:cloudServers:get",
        "ecs:cloudServerFlavors:list",
        "ecs:cloudServerImages:list",
        "ecs:jobs:get",
        "ims:images:list",
        "vpc:subnets:list",
        "vpc:securityGroups:list",
        "vpc:publicIps:list",
        "evs:volumes:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```

> `ecs:cloudServers:action` covers the start / stop / restart actions
> (`BatchStartServers`, `BatchStopServers`, `BatchRebootServers`). The write actions
> (`ecs:cloudServers:create`) should only be granted to accounts that really create instances.

## 3. Manage (R1 — delete)

Covers: `huawei_delete_ecs_instance`.

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:cloudServers:delete",
        "ecs:cloudServers:get",
        "ecs:cloudServers:list",
        "ecs:serverVolumes:list",
        "evs:volumes:list",
        "evs:volumes:delete",
        "vpc:publicIps:list",
        "vpc:publicIps:delete"
      ],
      "Resource": ["*"]
    }
  ]
}
```

> `huawei_delete_ecs_instance` uses `DeleteServers` path; the delete policy therefore declares:
> - `evs:volumes:delete` — required when `--delete_volume=true` (release bound volumes together);
>   skip this action if volume deletion is never used.
> - `vpc:publicIps:delete` — required when `--delete_publicip=true` (release bound EIP together);
>   `vpc:publicIps:list` covers the read side. Skip the delete action if EIP deletion is never used.

## 4. System policy alternative

For a read-only operator that only needs query + diagnosis, the predefined system policy
`ECS ReadOnlyAccess` (弹性云服务器只读权限) can be used instead of section 1 — it covers the ECS
read actions; IMS/VPC/EVS reads may still need their own read policies (`IMS ReadOnlyAccess`,
`VPC ReadOnlyAccess`, `EVS ReadOnlyAccess`) for the cross-service checks. The KPS keypair read used
by diagnosis step 5 (`kps:keypairs:list`) is likewise not part of `ECS ReadOnlyAccess`; grant that
action explicitly when the keypair check must not degrade to a permission warning.

## 5. Change operations (SKILL.md §5)

The change operations added for issue #931 act on an existing instance and therefore reuse the
read/action permissions above (`ecs:cloudServers:get` / `:list`, `ecs:cloudServers:action`, plus the
`vpc:publicIps:*` and `evs:*` reads the preflight checks need). The per-API write action names for
resize / reinstall / password reset / keypair / security group / NIC / volume attach-detach, and the
EIP bind-unbind pair, must be copied from the official **ECS** and **EIP** 「权限及授权项」
catalogues for the exact API before granting them: this document deliberately does not guess action
names that were not verified against a catalogue. If a change operation returns 403 while the read
actions work, that is the missing write action — look it up in the catalogue instead of widening the
policy to `ECS FullAccess`.

## 6. Batch operations, tags, VNC and enterprise projects (issue #1105)

Covers: `huawei_batch_start_ecs_by_tag`, `huawei_batch_stop_ecs_by_tag`,
`huawei_batch_reboot_ecs_by_tag`, `huawei_batch_tag_ecs`, `huawei_batch_untag_ecs`,
`huawei_get_ecs_vnc_console`, `huawei_change_ecs_enterprise_project`.

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:cloudServers:list",
        "ecs:cloudServers:get",
        "ecs:cloudServers:action",
        "ecs:serverTags:list",
        "ecs:serverTags:create",
        "ecs:serverTags:delete",
        "ecs:cloudServers:remoteConsole",
        "eps:enterpriseProjects:list",
        "eps:resources:migrate"
      ],
      "Resource": ["*"]
    }
  ]
}
```

> - Batch start/stop/reboot reuse `ecs:cloudServers:action` (same as the single-instance
>   `BatchStartServers` / `BatchStopServers` / `BatchRebootServers` calls).
> - Tag operations map to `ecs:serverTags:list|create|delete` (`ListServerTags`,
>   `BatchCreateServerTags`, `BatchDeleteServerTags`). Grant `create`/`delete` only when tag
>   changes are intended.
> - `ecs:cloudServers:remoteConsole` is required by `ShowServerRemoteConsole`; it returns a
>   temporary console URL, so grant it only to operators who may access the instance console.
> - Enterprise-project migration uses the EPS API, not an ECS API: `eps:enterpriseProjects:list`
>   (read/precheck) + `eps:resources:migrate` (the write). `--associated=true` migrates EVS/EIP too.
> - `huawei_batch_create_ecs_instances` / `prePaid` / `spot` creation reuse the create permission in
>   §2 (`ecs:cloudServers:create`); auto-pay orders additionally need the BSS order/pay actions
>   granted by your finance policy (see §7).

## 7. Account-balance precheck (BSS)

The create-failure diagnosis checks the account balance before reporting a capacity problem.
KooCLI 7.3.12 reports `Unsupported service: BSS`, so do **not** grant an `hcloud BSS` action — the
balance is read via the BSS OpenAPI / `huaweicloudsdkbss` SDK (`GET
/v2/accounts/customer-accounts/balances`, global endpoint) or the Billing Center console.

Relevant BSS permissions (official BSS 「权限及授权项」):
`bss:balance:view` for the balance read; when an auto-pay order is involved, the account also needs
the finance policy's order-pay action (commonly `bss:order:pay`, `bss:order:view`). This skill does
**not** purchase on the user's behalf — the balance check is diagnostic only.

## 8. Diagnosing 403 / 401 correctly

| Symptom | Meaning | Fix |
| ------- | ------- | --- |
| `403` + `not authorized`/`Forbidden` while other reads work | A specific action is missing | Grant the action from §1/§2/§6; never use `ECS FullAccess` as a shortcut |
| `401` / expired credentials / every call fails | Authentication, not authorization | Re-authenticate (`hcloud configure list`) or refresh AK/SK |
| Reads work, `create` fails `403` | `ecs:cloudServers:create` (or the BSS payment action for auto-pay) is missing | Grant that specific action |
| `Insufficient account balance` / arrears / failed order | Balance | Recharge in the Billing Center, then retry |

## Security notes

- Use the least-privilege policy that covers the intended capability group; do not grant
  `ECS FullAccess` when read-only diagnosis is enough.
- Never hardcode AK/SK in policies, scripts, or command lines — credentials are read from the
  environment or the hcloud profile only.
