# ECS Change Operations (Reinstall OS / Change OS / Resize)

> **Issue #947 correction.** Issue #947 proposes `hcloud ECS ReinstallOs` and
> `hcloud ECS ResizeServer / ChangeServerFleet`. Verified against KooCLI **7.2.12**:
> `ReinstallOs` and `ChangeServerFleet` **do not exist** — both return
> `[USE_ERROR]不支持的operation:<name>`. `ResizeServer` does exist. This document maps each
> requested capability to the operation names that are actually available, and every operation
> and parameter name below was verified by running
> `hcloud ECS <Operation> --help --cli-region=cn-north-4` on KooCLI 7.2.12.

## Operation Name Mapping

| Issue-suggested name | Real KooCLI operation | Note |
| ---------------------- | ----------------------- | ------ |
| `ReinstallOs` | `ReinstallServerWithCloudInit` | Invalid in KooCLI 7.2.12 (`[USE_ERROR]不支持的operation:ReinstallOs`). Use this variant to reinstall the current image with Cloud-Init / user-data injection. |
| `ReinstallOs` | `ReinstallServerWithoutCloudInit` | Same reinstall capability without Cloud-Init user-data injection (no `--os-reinstall.metadata.user_data`). |
| `ReinstallOs` (new image) | `ChangeServerOsWithCloudInit` / `ChangeServerOsWithoutCloudInit` | Switching to a *different* OS image is a distinct operation; `--os-change.imageid` is required. |
| `ChangeServerFleet` | *no such operation* | Invalid in KooCLI 7.2.12 (`[USE_ERROR]不支持的operation:ChangeServerFleet`). Changing the flavor ("规格") is `ResizeServer` / `ResizePostPaidServer` (single server) or `BatchResizeServers` (batch). |
| `ResizeServer` | `ResizeServer` | Exists and is verified; see the section below. |

## Prerequisites & Sequence

1. **Resolve the target server** — you need `server_id` (UUID). If unknown, list first:
   `hcloud ECS ListServersDetails --cli-region={region} --name={name}`.
2. **Reinstall / change OS requires the server to be stopped.** Stop it first with
   `BatchStopServers`, then wait until `ShowServer` reports `status` = `SHUTOFF`. Alternatively,
   both reinstall and change-OS accept `--os-reinstall.mode=withStopServer` /
   `--os-change.mode=withStopServer`, which lets the operation run against a powered-on server
   (the service stops it, applies the change, and starts it again).
3. **Changing the OS image also changes the login credentials.** Supply `--os-change.adminpass`
   (password) or `--os-change.keyname` (keypair). When `keyname` is used, `userid` is required.
4. **Resize can run while powered on** with `--resize.mode=withStopServer` (the service stops,
   resizes, and restarts the server). Without it, the server must already be stopped.
5. **Find allowed target flavors before resizing** with `ListResizeFlavors` (see below) — not every
   flavor is a legal resize target for a given instance.
6. **All change operations below are mutating and billable.** Present the exact command to the user
   and wait for explicit confirmation before executing.

Recommended sequence for an OS change (stop first — do **not** also pass `mode=withStopServer`):

```bash
hcloud ECS ListServersDetails --cli-region={region} --name={name}
hcloud ECS BatchStopServers --cli-region={region} --os-stop.servers.1.id={server_id} --os-stop.type=SOFT
hcloud ECS ShowServer --cli-region={region} --server_id={server_id}      # wait for status = SHUTOFF
hcloud ECS ReinstallServerWithCloudInit --cli-region={region} --server_id={server_id} \
  --os-reinstall.adminpass={admin_pass}
hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
```

> Alternative: skip the `BatchStopServers` step and pass
> `--os-reinstall.mode=withStopServer` (or `--os-change.mode=withStopServer`) instead, which lets the
> service stop, apply the change, and start the server again. Use **one** approach, not both.

Recommended sequence for a resize:

```bash
hcloud ECS ListResizeFlavors --cli-region={region} --instance_uuid={server_id}
hcloud ECS ResizeServer --cli-region={region} --server_id={server_id} \
  --resize.flavorRef={flavor_id} --resize.mode=withStopServer
hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
```

## Reinstall OS with Cloud-Init

### Purpose

Reinstall the server's current operating system, with the option to inject Cloud-Init user data and
to switch the login credential (password or keypair).

### Confirmation

> **Confirmation required before execution.** Reinstalling destroys all data on the system disk.
> Back up first and get explicit user confirmation.

### Command

```bash
hcloud ECS ReinstallServerWithCloudInit --cli-region={region} --server_id={server_id} \
  --os-reinstall.mode=withStopServer --os-reinstall.adminpass={admin_pass}
```

With keypair authentication and injected user data:

```bash
hcloud ECS ReinstallServerWithCloudInit --cli-region={region} --server_id={server_id} \
  --os-reinstall.keyname={key_name} --os-reinstall.userid={user_id} \
  --os-reinstall.metadata.user_data={base64_user_data}
```

### Parameters

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region, agent fills automatically |
| `--project_id` | Yes (auto) | string | Project ID, auto-resolved by KooCLI from the credentials |
| `--server_id` | Yes | string | Server ID (UUID) |
| `--os-reinstall.adminpass` | No | string | Initial login password of the administrative account |
| `--os-reinstall.keyname` | No | string | Keypair name |
| `--os-reinstall.userid` | No | string | User ID; required when `keyname` is passed |
| `--os-reinstall.mode` | No | string | `withStopServer` — allow the reinstall on a powered-on server (auto stop/start) |
| `--os-reinstall.metadata.user_data` | No | string | User data injected during the reinstall (Cloud-Init) |
| `--os-reinstall.metadata.__system__cmkid` | No | string | CMK ID for encryption; used together with `__system__encrypted` (36 bytes) |
| `--os-reinstall.metadata.__system__encrypted` | No | string | Encryption flag: `0` = not encrypted, `1` = encrypted |

> `ReinstallServerWithCloudInit` has **no** `--dry_run` parameter in KooCLI 7.2.12.

### Post-execution verification

Read the instance back and confirm the server returns to an active/stopped state:

```bash
hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
```

Expect `status` to settle on `ACTIVE`; `image.id` still identifies the
installed image, and `metadata`/`key_name` reflect the new credential if one was supplied.

## Reinstall OS without Cloud-Init

### Purpose

Reinstall the server's current operating system without Cloud-Init user-data injection.

### Confirmation

> **Confirmation required before execution.** Reinstalling destroys all data on the system disk.

### Command

```bash
hcloud ECS ReinstallServerWithoutCloudInit --cli-region={region} --server_id={server_id} \
  --os-reinstall.mode=withStopServer --os-reinstall.adminpass={admin_pass}
```

### Parameters

Identical to `ReinstallServerWithCloudInit` **except** that `--os-reinstall.metadata.user_data` is
not accepted.

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region, agent fills automatically |
| `--project_id` | Yes (auto) | string | Project ID, auto-resolved by KooCLI |
| `--server_id` | Yes | string | Server ID (UUID) |
| `--os-reinstall.adminpass` | No | string | Initial login password of the administrative account |
| `--os-reinstall.keyname` | No | string | Keypair name |
| `--os-reinstall.userid` | No | string | User ID; required when `keyname` is passed |
| `--os-reinstall.mode` | No | string | `withStopServer` — allow the reinstall on a powered-on server |
| `--os-reinstall.metadata.__system__cmkid` | No | string | CMK ID for encryption |
| `--os-reinstall.metadata.__system__encrypted` | No | string | Encryption flag: `0` = not encrypted, `1` = encrypted |

> `ReinstallServerWithoutCloudInit` has **no** `--dry_run` parameter in KooCLI 7.2.12.

### Post-execution verification

```bash
hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
```

Same check as above: wait for `status` to settle (`ACTIVE`), and confirm the instance is reachable
with the credential set during the reinstall.

## Change OS with Cloud-Init

### Purpose

Switch the server to a **different** OS image (for example an upgraded distribution or a different
OS), with the option to inject Cloud-Init user data and to set new login credentials.

### Confirmation

> **Confirmation required before execution.** Changing the OS image destroys all data on the system
> disk and changes the login credentials. Confirm the target image ID with the user first.

### Command

```bash
hcloud ECS ChangeServerOsWithCloudInit --cli-region={region} --server_id={server_id} \
  --os-change.imageid={image_id} --os-change.adminpass={admin_pass}
```

Yearly/monthly (包年/包月) server with automatic payment:

```bash
hcloud ECS ChangeServerOsWithCloudInit --cli-region={region} --server_id={server_id} \
  --os-change.imageid={image_id} --os-change.keyname={key_name} --os-change.userid={user_id} \
  --os-change.isAutoPay=true
```

### Parameters

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region, agent fills automatically |
| `--project_id` | Yes (auto) | string | Project ID, auto-resolved by KooCLI |
| `--server_id` | Yes | string | Server ID (UUID) |
| `--os-change.imageid` | Yes | string | ID (UUID) of the new image to switch to |
| `--os-change.adminpass` | No | string | Initial login password of the administrative account |
| `--os-change.keyname` | No | string | Keypair name |
| `--os-change.userid` | No | string | User ID; required when `keyname` is used |
| `--os-change.mode` | No | string | `withStopServer` — allow the change on a powered-on server |
| `--os-change.isAutoPay` | No | string | `true` = auto-pay the order; `false` = pay manually (yearly/monthly servers) |
| `--os-change.metadata.user_data` | No | string | User data injected during the change (Cloud-Init) |
| `--os-change.metadata.__system__cmkid` | No | string | CMK ID for encryption |
| `--os-change.metadata.__system__encrypted` | No | string | Encryption flag: `0` = not encrypted, `1` = encrypted |

> `ChangeServerOsWithCloudInit` has **no** `--dry_run` parameter in KooCLI 7.2.12.

### Post-execution verification

```bash
hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
```

`image.id` must equal `{image_id}` after the operation completes, and `status` must settle on
`ACTIVE`.

## Change OS without Cloud-Init

### Purpose

Switch the server to a different OS image without Cloud-Init user-data injection.

### Confirmation

> **Confirmation required before execution.** Changing the OS image destroys all data on the system
> disk and changes the login credentials.

### Command

```bash
hcloud ECS ChangeServerOsWithoutCloudInit --cli-region={region} --server_id={server_id} \
  --os-change.imageid={image_id} --os-change.adminpass={admin_pass}
```

### Parameters

Identical to `ChangeServerOsWithCloudInit` **except** that `--os-change.metadata.user_data` is not
accepted.

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region, agent fills automatically |
| `--project_id` | Yes (auto) | string | Project ID, auto-resolved by KooCLI |
| `--server_id` | Yes | string | Server ID (UUID) |
| `--os-change.imageid` | Yes | string | ID (UUID) of the new image to switch to |
| `--os-change.adminpass` | No | string | Initial login password of the administrative account |
| `--os-change.keyname` | No | string | Keypair name |
| `--os-change.userid` | No | string | User ID; required when `keyname` is used |
| `--os-change.mode` | No | string | `withStopServer` — allow the change on a powered-on server |
| `--os-change.isAutoPay` | No | string | `true` = auto-pay the order; `false` = pay manually (yearly/monthly servers) |
| `--os-change.metadata.__system__cmkid` | No | string | CMK ID for encryption |
| `--os-change.metadata.__system__encrypted` | No | string | Encryption flag: `0` = not encrypted, `1` = encrypted |

> `ChangeServerOsWithoutCloudInit` has **no** `--dry_run` parameter in KooCLI 7.2.12.

### Post-execution verification

```bash
hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
```

Confirm `image.id` equals `{image_id}` and `status` is `ACTIVE`.

## Resize Server (ResizeServer)

### Purpose

Change the flavor ("规格", e.g. vCPU/memory) of a single ECS server. This is the operation that
replaces the issue's `ChangeServerFleet` suggestion.

### Confirmation

> **Confirmation required before execution.** Resizing changes billing and may restart the server.
> Check the target flavor with `ListResizeFlavors` and confirm with the user first.

### Command

```bash
hcloud ECS ResizeServer --cli-region={region} --server_id={server_id} \
  --resize.flavorRef={flavor_id} --resize.mode=withStopServer
```

Pre-check only, without changing anything (`--dry_run` is supported by this operation):

```bash
hcloud ECS ResizeServer --cli-region={region} --server_id={server_id} \
  --resize.flavorRef={flavor_id} --dry_run=true
```

### Parameters

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region, agent fills automatically |
| `--project_id` | Yes (auto) | string | Project ID, auto-resolved by KooCLI |
| `--server_id` | Yes | string | Server ID (UUID) |
| `--resize.flavorRef` | Yes | string | Target flavor ID; query allowed targets with `ListResizeFlavors` |
| `--resize.mode` | No | string | `withStopServer` — allow resizing a powered-on server (auto stop, resize, start) |
| `--dry_run` | No | boolean | `true` = pre-check only (required params, request format); returns 202 if the check passes without executing the change |
| `--resize.extendparam.isAutoPay` | No | string | `true` = auto-pay the order; `false` = pay manually; only effective for yearly/monthly billing |
| `--resize.dedicated_host_id` | No | string | New dedicated host ID (only for servers on a dedicated host) |
| `--resize.cpu_options.hw:cpu_threads` | No | integer | CPU hyper-threading: `1` = disabled, `2` = enabled; must not exceed the target flavor's `hw:cpu_threads` |

### Post-execution verification

```bash
hcloud ECS ListResizeFlavors --cli-region={region} --instance_uuid={server_id}
hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
```

`flavor.id` must equal `{flavor_id}` after the resize job completes, and `status` must be `ACTIVE`.
The server may pass through `RESIZE` while the job is running.

## Resize Post-Paid Server (ResizePostPaidServer)

### Purpose

Change the flavor of a single pay-per-use (按需) server through the dedicated pay-per-use resize
operation.

### Confirmation

> **Confirmation required before execution.** Resizing changes billing. Confirm the target flavor
> with the user first.

### Command

```bash
hcloud ECS ResizePostPaidServer --cli-region={region} --server_id={server_id} \
  --resize.flavorRef={flavor_id} --resize.mode=withStopServer
```

### Parameters

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region, agent fills automatically |
| `--project_id` | Yes (auto) | string | Project ID, auto-resolved by KooCLI |
| `--server_id` | Yes | string | Server ID (UUID) |
| `--resize.flavorRef` | Yes | string | Target flavor ID |
| `--resize.mode` | No | string | `withStopServer` — allow resizing a powered-on server |
| `--dry_run` | No | boolean | `true` = pre-check only, do not execute the change |
| `--resize.cpu_options.hw:cpu_threads` | No | integer | CPU hyper-threading: `1` = disabled, `2` = enabled |

> Unlike `ResizeServer`, this operation does **not** expose `--resize.dedicated_host_id` or
> `--resize.extendparam.isAutoPay` in KooCLI 7.2.12 (pay-per-use servers have no order to pay).

### Post-execution verification

```bash
hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
```

Confirm `flavor.id` equals `{flavor_id}` and `status` settles on `ACTIVE`.

## Batch Resize Servers (BatchResizeServers)

### Purpose

Change the flavor of several servers in one request.

### Confirmation

> **Confirmation required before execution.** Resizing changes billing for every listed server.
> List the affected `server_id`s in the confirmation prompt.

### Command

```bash
hcloud ECS BatchResizeServers --cli-region={region} --resize.flavorRef={flavor_id} \
  --resize.servers.1.id={server_id_1} --resize.servers.2.id={server_id_2} \
  --resize.mode=withStopServer
```

### Parameters

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region, agent fills automatically |
| `--project_id` | Yes (auto) | string | Project ID, auto-resolved by KooCLI |
| `--resize.flavorRef` | Yes | string | Target flavor for all listed servers |
| `--resize.servers.[N].id` | Yes | string | Server IDs, indexed form (`--resize.servers.1.id={server_id}`) |
| `--resize.mode` | No | string | Resize mode (for example `withStopServer`) |
| `--resize.cpu_options.hw:cpu_threads` | No | integer | CPU hyper-threading: `1` = disabled, `2` = enabled |
| `--resize.promotion.id` | No | string | Promotion/offer ID |
| `--resize.promotion.type` | No | string | Promotion/offer type |

> `BatchResizeServers` has **no** `--dry_run` parameter in KooCLI 7.2.12.

### Post-execution verification

Verify each server individually:

```bash
hcloud ECS ShowServer --cli-region={region} --server_id={server_id_1}
```

`flavor.id` must equal `{flavor_id}` for every server in the batch.

## List Allowed Resize Flavors (ListResizeFlavors)

### Purpose

Query the flavors a given server is allowed to be resized to. Run this **before** any resize so the
`--resize.flavorRef` value is a legal target.

### Confirmation

None — this is a read-only query.

### Command

```bash
hcloud ECS ListResizeFlavors --cli-region={region} --instance_uuid={server_id}
```

By source flavor instead of instance:

```bash
hcloud ECS ListResizeFlavors --cli-region={region} --source_flavor_id={flavor_id}
```

### Parameters

| Parameter | Required | Type | Description |
| ----------- | ---------- | ------ | ------------- |
| `--cli-region` | Yes (auto) | string | Region, agent fills automatically |
| `--project_id` | Yes (auto) | string | Project ID, auto-resolved by KooCLI |
| `--instance_uuid` | No | string | Server ID (UUID) whose resize targets are queried; at least one of `instance_uuid`, `source_flavor_id`, `source_flavor_name` must be provided |
| `--source_flavor_id` | No | string | Source flavor ID of the server to resize |
| `--source_flavor_name` | No | string | Source flavor name of the server to resize |
| `--limit` | No | integer | Maximum flavors per page (default 1000) |
| `--marker` | No | string | Pagination marker: ID of the last flavor of the previous page |
| `--sort_dir` | No | string | Sort direction: `asc` (default) or `desc` |
| `--sort_key` | No | string | Sort field: `flavorid` (default), `sort_key`, `name`, `memory_mb`, `vcpus`, `root_gb` |

### Post-execution verification

The returned flavor list contains the candidate `--resize.flavorRef` values. After the resize,
re-run this query together with `ShowServer` to confirm the instance now reports the new `flavor.id`.
An empty `flavors` list is a valid response and means no compatible resize target was returned for
that instance/source flavor.

## Verifying a Change Operation

Every change operation is verified by reading the instance back:

```bash
hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
```

| Change | Field to check in `ShowServer` |
| -------- | -------------------------------- |
| Reinstall OS | `status` settles on `ACTIVE` (or `SHUTOFF`) and the instance boots with the credential set during the reinstall |
| Change OS | `image.id` equals the requested `--os-change.imageid`, `status` = `ACTIVE` |
| Resize | `flavor.id` equals the requested `--resize.flavorRef`, `status` = `ACTIVE`; `ListResizeFlavors` lists the target beforehand |

> Change operations are asynchronous: `ShowServer` may first report a transitional state
> (for example `RESIZE` while a resize job runs, or `BUILD` while the server is being rebuilt)
> before settling. Re-read until the state is stable.
