# Linked Resource Queries (跨产品关联资源联动查询)

Read-only queries that link an ECS instance to its cross-product resources: attached EVS
volumes and snapshots, VPC/subnet topology, security groups and rules, and bound EIPs.

All operations here are **read-only** — they never create, modify, or delete a resource, and
they are safe to run without user confirmation. Resolve the instance first with
`ListServersDetails` / `ShowServer`, then reuse the returned IDs:

- `server_id` — from `ShowServer` / `ListServersDetails`
- `metadata.vpc_id` — the VPC the instance belongs to
- `security_groups[].name` — security-group **names only** (map them to IDs before querying)
- NIC `port_id`s — from `addresses`; this is the join key between an ECS instance and an EIP

Every command uses `--cli-region=cn-north-4` as the example region; replace it with the
authenticated account's region (or rely on the CLI profile default). `--project_id` is
auto-resolved by KooCLI from the credentials.

## 1. Attached EVS volumes (挂载的云硬盘)

```bash
hcloud ECS ListServerVolumeAttachments --cli-region=cn-north-4 --server_id=6a2f0b1c-8d4e-4f3a-9b7c-1d2e3f4a5b6c
hcloud EVS ListVolumes --cli-region=cn-north-4 --server_id=6a2f0b1c-8d4e-4f3a-9b7c-1d2e3f4a5b6c
```

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region |
| `--project_id` | Yes (auto) | string | Project ID |
| `--server_id` | Yes | string | Server ID; `ListVolumes --server_id` filters to the server's attached volumes |
| `--limit` / `--offset` | No | integer | Pagination for `ListVolumes` |

`ListServerVolumeAttachments` returns the attachment records from the ECS side;
`ListVolumes --server_id` returns the EVS volume objects. Cross-check both for the full picture.

## 2. EVS volume detail and snapshots (云硬盘详情与快照)

```bash
hcloud EVS ShowVolume --cli-region=cn-north-4 --volume_id=b3f0c2a4-5d6e-4f70-9a1b-2c3d4e5f6a7b
hcloud EVS ListSnapshots --cli-region=cn-north-4 --volume_id=b3f0c2a4-5d6e-4f70-9a1b-2c3d4e5f6a7b
hcloud EVS ShowSnapshot --cli-region=cn-north-4 --snapshot_id=c4a1d3b5-6e7f-4f80-8b2c-3d4e5f6a7b8c
```

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region |
| `--project_id` | Yes (auto) | string | Project ID |
| `--volume_id` | Yes (ShowVolume) / No (ListSnapshots filter) | string | Volume ID (UUID) |
| `--snapshot_id` | Yes (ShowSnapshot) | string | Snapshot ID (UUID) |

## 3. VPC / subnet topology (实例所在 VPC / 子网)

```bash
hcloud VPC ShowVpc/v3 --cli-region=cn-north-4 --vpc_id=2a4f8b3c-9d0e-4f1a-8b3c-4d5e6f7a8b9c
hcloud VPC ListSubnets --cli-region=cn-north-4 --vpc_id=2a4f8b3c-9d0e-4f1a-8b3c-4d5e6f7a8b9c
hcloud VPC ShowSubnet --cli-region=cn-north-4 --subnet_id=5b0c2d4e-6f7a-4f80-9c4d-5e6f7a8b9c0d
```

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region |
| `--project_id` | Yes (auto) | string | Project ID |
| `--vpc_id` | Yes (ShowVpc/v3 / ListSubnets) | string | VPC ID (UUID), from `ShowServer` `metadata.vpc_id` |
| `--subnet_id` | Yes (ShowSubnet) | string | Subnet ID (UUID) returned by `ListSubnets`; never an `addresses` key |

The server's `vpc_id` comes from `ShowServer` under `metadata.vpc_id`, not from
`security_groups`. The keys of `addresses` are also the instance's **`vpc_id`**, not a subnet ID —
passing an `addresses` key to `VPC ShowSubnet --subnet_id` fails with `VPC.0216` /
`SYS.0404 The resource could not be found`. To locate the instance's subnet, call
`VPC ListSubnets --vpc_id=<vpc_id>`, then match the instance's private IPv4 address (from
`addresses`) against each subnet's CIDR; pass that subnet's `id` to `ShowSubnet` only when its
detail is needed.

> Always specify the API version on `ShowVpc` as `ShowVpc/v3`. Without the version suffix KooCLI
> prints a `ShowVpc有多个版本...` notice as the first stdout line before the JSON, which breaks
> pure JSON parsing (`json.loads` raises `JSONDecodeError`); `ShowVpc/v3` emits JSON only.

## 4. Security groups and rules (关联安全组及规则)

```bash
hcloud VPC ListSecurityGroups/v3 --cli-region=cn-north-4
hcloud VPC ShowSecurityGroup/v3 --cli-region=cn-north-4 --security_group_id=6d1e3f5a-7b8c-4f90-8d5e-6f7a8b9c0d1e
hcloud VPC ListSecurityGroupRules/v3 --cli-region=cn-north-4 --security_group_id.1=6d1e3f5a-7b8c-4f90-8d5e-6f7a8b9c0d1e
```

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region |
| `--project_id` | Yes (auto) | string | Project ID |
| `--security_group_id` | Yes (ShowSecurityGroup) | string | Security group ID (UUID) |
| `--security_group_id.1` | No (rules filter) | string | Indexed filter to limit rules to one security group |

`ShowServer` returns only `security_groups[].name`. Call `ListSecurityGroups/v3` first to build a
name → ID map, then use the matching `id` with `ShowSecurityGroup/v3` / `ListSecurityGroupRules/v3`.

## 5. Bound EIP (绑定的弹性公网IP)

```bash
hcloud EIP ListPublicips/v2 --cli-region=cn-north-4 --port_id.1=7e2f4a6b-8c9d-4f10-9e6f-7a8b9c0d1e2f
hcloud EIP ShowPublicip/v2 --cli-region=cn-north-4 --publicip_id=8f3a5b7c-9d0e-4f20-8a7b-9c0d1e2f3a4b
```

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region |
| `--project_id` | Yes (auto) | string | Project ID |
| `--port_id.1` | No | string | NIC port ID (UUID) used to find the EIP bound to the server |
| `--publicip_id` | Yes (ShowPublicip) | string | EIP ID (UUID) |

The EIP-to-ECS association key is the NIC `port_id` (from `ShowServer` `addresses`), **not**
`server_id`. If the instance has no bound EIP, the list is empty — report that the instance is
not bound to a public IP.

## Permission requirements

| Query group | Built-in role |
| ------------- | --------------- |
| EVS volumes / snapshots | `EVS ReadOnlyAccess` |
| VPC / subnets / security groups | `VPC ReadOnlyAccess` |
| EIP | `EIP ReadOnlyAccess` |

See `references/iam-policies.md` for the fine-grained `List*` / `Show*` action list.