# IAM Policies — Least Privilege for huawei-cloud-ecs-manage

This skill requires IAM permissions on the ECS service (service prefix `ecs`) plus read-only
permissions on IMS (images), VPC (subnets / security groups), EIP (public IPs) and EVS (volumes),
which the diagnosis flow cross-checks. Grant the **minimum** permissions per capability group.
All policies are region-scoped (ECS is a regional service; instances belong to a project).

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
        "evs:volumes:list"
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
> - **Keypair check (diagnosis step 5)**: the keypair read permission name differs between the
>   ECS Nova keypair API and the KPS (Key Pair Service) API. If `hcloud KPS ListKeypairs` returns
>   a 403, ask the IAM admin to grant the documented keypair read permission from the ECS/KPS
>   「权限及授权项」 pages (do not guess the action name). The diagnosis flow degrades gracefully:
>   a 403 on step 5 is reported as "cannot verify keypair — check IAM permission", not as a failure.

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
        "evs:volumes:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```

> `huawei_delete_ecs_instance` uses `DeleteServers` path; `--delete_volume=true` additionally
> requires EVS delete permission (`evs:volumes:delete`) — grant it only when the user explicitly
> wants volume deletion together with the instance.

## 4. System policy alternative

For a read-only operator that only needs query + diagnosis, the predefined system policy
`ECS ReadOnlyAccess` (弹性云服务器只读权限) can be used instead of section 1 — it covers the ECS
read actions; IMS/VPC/EVS reads may still need their own read policies (`IMS ReadOnlyAccess`,
`VPC ReadOnlyAccess`, `EVS ReadOnlyAccess`) for the cross-service checks.

## Security notes

- Use the least-privilege policy that covers the intended capability group; do not grant
  `ECS FullAccess` when read-only diagnosis is enough.
- Never hardcode AK/SK in policies, scripts, or command lines — credentials are read from the
  environment or the hcloud profile only.