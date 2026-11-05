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

## Security notes

- Use the least-privilege policy that covers the intended capability group; do not grant
  `ECS FullAccess` when read-only diagnosis is enough.
- Never hardcode AK/SK in policies, scripts, or command lines — credentials are read from the
  environment or the hcloud profile only.
