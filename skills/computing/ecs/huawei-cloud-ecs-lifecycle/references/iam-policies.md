# IAM Policies for Huawei Cloud ECS Lifecycle Management

Least-privilege IAM permissions required by this Skill. Authenticate with an IAM user (or agency)
that has exactly these permissions — no more.

## Built-in Roles (simplest)

| Operation Group | Built-in Role |
| ----------------- | --------------- |
| List / Show ECS instances | `ECS ReadOnlyAccess` |
| Create / Rename / Start / Stop / Reboot / Delete ECS | `ECS FullAccess` |
| Reinstall OS / Change OS / Resize (incl. batch resize) | `ECS FullAccess` |
| Create instances (network resources referenced) | `VPC ReadOnlyAccess` (to resolve VPC/subnet/SG) |

> If the account uses fine-grained policies, use the JSON below instead of built-in roles.

## Fine-grained Policy (least privilege)

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:servers:list",
        "ecs:servers:get"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:cloudServers:create",
        "ecs:cloudServers:delete",
        "ecs:cloudServers:reboot",
        "ecs:cloudServers:start",
        "ecs:cloudServers:stop",
        "ecs:cloudServers:update",
        "ecs:cloudServers:updateName"
      ],
      "Resource": "*"
    }
  ]
}
```

> **Note:** action names may vary slightly by region/version — verify against the IAM permission
> catalogue for the target project (`统一身份认证服务 → 权限`, filter by `ECS`).

### Change operations (reinstall OS / change OS / resize)

The policy JSON above covers the operations documented before issue #947. Reinstall OS, change OS and
resize are additional `cloudServers` mutations on the same resource. **Recommended way to grant them:
the built-in `ECS FullAccess` role** — the "Reinstall OS / Change OS / Resize" row in the built-in
role table above, at the same confidence level as the existing rows in this document. Reinstall and
change-OS additionally touch the server's keypair scope, and resize reads the flavor catalogue; the
built-in ECS full-access role is the broad-but-known option that covers them all.

If a fine-grained policy is required, the candidates below follow the same `ecs:cloudServers:*`
naming family used elsewhere in this file:

```json
{
  "Effect": "Allow",
  "Action": [
    "ecs:cloudServers:resize",
    "ecs:cloudServers:reinstall",
    "ecs:cloudServers:changeOs"
  ],
  "Resource": "*"
}
```

> **🛑 Status: NOT officially confirmed — catalogue check pending.** Only the built-in
> `ECS FullAccess` role is recommended for these operations (same framing as the existing rows in
> this document; per-action cataloguing was not performed). The three action names above are
> **candidates** derived from the `ecs:cloudServers:*` family already present in this document; they
> have **not** been verified against the IAM permission catalogue and must not be relied on in a
> production least-privilege policy before that check. Their exact spelling (and whether batch
> resize uses `ecs:cloudServers:resize` or a separate batch action) is unknown at the time of
> writing. Verify with the IAM permission catalogue for the target project
> (`统一身份认证服务 → 权限`, filter by `ECS`) — `hcloud IAM GetAuthorizationSchemaV5` can also be
> used when credentials for the IAM service are available.

**Confirmed vs. pending at a glance**

| Item | Status |
| ------ | -------- |
| Operations documented here exist in KooCLI 7.2.12 (`ReinstallServer*`, `ChangeServerOs*`, `ResizeServer`, `ResizePostPaidServer`, `BatchResizeServers`, `ListResizeFlavors`) | Confirmed by `--help` |
| Built-in role `ECS FullAccess` covers the change operations | Recommended built-in role (not per-action catalogued here) |
| `ecs:cloudServers:resize` / `:reinstall` / `:changeOs` | Pending IAM permission catalogue check |

## Credentials

- Credentials are read from the environment: any of
  `HUAWEI_ACCESS_KEY`/`HUAWEI_SECRET_KEY`, `HUAWEICLOUD_SDK_AK`/`HUAWEICLOUD_SDK_SK`, or the
  `hcloud` CLI profile (`hcloud configure set`).
- **Never hardcode AK/SK** in scripts or documentation.