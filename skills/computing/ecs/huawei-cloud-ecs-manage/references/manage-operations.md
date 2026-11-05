# Manage Operations (Change & Maintenance)

Covers the ECS **change / maintenance** operations that go beyond instance lifecycle
(create / start / stop / restart / delete), plus the **mandatory asynchronous job polling**
that must follow every write operation.

Addresses issue **#931** (8 missing high-frequency change-operation classes → 11 actions) and
issue **#921** (`ShowJob` polling guidance missing for the asynchronous Manage write operations).

> **Dual-form rule** — every `hcloud` command below is shown twice: the bare command and the
> identical payload wrapped with
> `skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- ...` for quality reporting.
> Bare `hcloud` invocations are not allowed in this skill.
> Run `hcloud <Service> <Operation> --help` before constructing any command; every parameter
> name in this document was verified against **KooCLI 7.2.12** with
> `hcloud <Service> <Operation> --help --cli-region=cn-north-4`.

> **Write markers** — every write command block starts with a comment line
> `# [W] 写操作 (WRITE): ...` stating the effect and the risk gate.

## 0. Risk levels and confirmation gates

| Level | Meaning | Gate |
| ----- | ------- | ---- |
| R3 | Read-only | Auto-execute |
| R2 | Change, recoverable with extra work | Show the full command + target, ask for explicit confirmation, then execute |
| R1 | Change that destroys a binding or data and cannot be undone by re-running the command | Show impact + evidence from a read-only pre-check, require explicit confirmation, then execute |

| Action | hcloud operation(s) | Risk |
| ------ | ------------------- | ---- |
| `huawei_resize_ecs_instance` | ECS `ResizeServer` | R2 |
| `huawei_reinstall_ecs_os` | ECS `ReinstallServerWithCloudInit` | R2 (system disk content is lost — warn explicitly) |
| `huawei_reset_ecs_password` | ECS `ResetServerPassword` | R2 |
| `huawei_replace_ecs_keypair` | ECS `NovaCreateKeypair` (+ `NovaDeleteKeypair`) | R2 for create, **R1** for deleting the old keypair |
| `huawei_bind_ecs_eip` | EIP `AssociatePublicips` | R2 |
| `huawei_unbind_ecs_eip` | EIP `DisassociatePublicips` | **R1** (the EIP/private-IP binding is released) |
| `huawei_change_ecs_security_group` | ECS `NovaAssociateSecurityGroup` / `NovaDisassociateSecurityGroup` | R2 (may cut off management access — warn) |
| `huawei_add_ecs_nic` | ECS `NovaAttachInterface` / `BatchAddServerNics` | R2 |
| `huawei_remove_ecs_nic` | ECS `NovaDetachInterface` / `BatchDeleteServerNics` | **R1** (the port and its private IP are destroyed) |
| `huawei_attach_ecs_volume` | ECS `AttachServerVolume` | R2 |
| `huawei_detach_ecs_volume` | ECS `DetachServerVolume` | R2 (unmount inside the guest OS first) |

R1/R2 rules inherited from `SKILL.md`: never chain writes, never modify an instance the user did
not explicitly name, and never echo credentials (AK/SK, passwords, tokens) or the private key
returned by `NovaCreateKeypair`.

## 1. Async job polling (mandatory after every write) — issue #921

The ECS Manage write operations are **asynchronous**: the API returns a `job_id` immediately and
the real work continues in the background. Reporting success right after the command returns is
therefore wrong. Skipping the poll produces these 4 wrong conclusions:

| # | Wrong conclusion | What is really happening |
| - | ---------------- | ------------------------ |
| 1 | "Instance created" | The instance is still `BUILD`; provisioning may still end in `ERROR` — create must be confirmed against `ShowServer` until `ACTIVE` |
| 2 | "Instance stopped" | The guest-OS shutdown is still running; the instance may still be reachable |
| 3 | "Instance deleted" | The instance can still sit in the recycle bin and is still returned by `ShowServer` |
| 4 | No progress feedback | A large instance can take minutes to build; without polling the user sees neither progress nor a timeout |

### 1.1 Standard flow (apply after EVERY write)

```text
1. Pre-check (R3) + preview the exact command, get explicit user confirmation   (R2/R1 gate)
2. Execute the hcloud write operation
3. Read job_id from the response
4. Poll ECS ShowJob until status is SUCCESS or FAIL
5. For create only: additionally poll ECS ShowServer until status is ACTIVE
6. Report the final result: job status + final instance status (+ error_msg on failure)
```

Step 4 — poll the job result:

```bash
# Repeat until status is SUCCESS or FAIL. Suggested interval 10 s (30 s after the first 2 minutes),
# overall timeout 15 minutes. Any other status means "still running" — keep polling.
hcloud ECS ShowJob --cli-region={region} --job_id={job_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ShowJob --cli-region={region} --job_id={job_id}
```

Step 5 — create only: confirm the instance itself reached `ACTIVE`:

```bash
hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
```

### 1.2 Which operations return a `job_id`

| Action | hcloud operation | Poll after the job succeeds |
| ------ | ---------------- | --------------------------- |
| `huawei_create_ecs_instance` | ECS `CreatePostPaidServers` | `ShowJob` → `ShowServer` until `ACTIVE` |
| `huawei_start_ecs_instance` | ECS `BatchStartServers` | `ShowJob` → `ShowServer` until `ACTIVE` |
| `huawei_stop_ecs_instance` | ECS `BatchStopServers` | `ShowJob` → `ShowServer` until `SHUTOFF` |
| `huawei_restart_ecs_instance` | ECS `BatchRebootServers` | `ShowJob` → `ShowServer` until `ACTIVE` |
| `huawei_delete_ecs_instance` | ECS `DeleteServers` | `ShowJob` → `ShowServer` confirms the instance is gone (or reports it is still in the recycle bin) |
| `huawei_resize_ecs_instance` | ECS `ResizeServer` | `ShowJob` → `ShowServer` until `ACTIVE` |
| `huawei_reinstall_ecs_os` | ECS `ReinstallServerWithCloudInit` | `ShowJob` → `ShowServer` until `ACTIVE` |
| `huawei_reset_ecs_password` | ECS `ResetServerPassword` | `ShowJob` |
| `huawei_add_ecs_nic` / `huawei_remove_ecs_nic` | ECS NIC operations | `ShowJob` (NIC/batch operations also return a job) |
| `huawei_bind_ecs_eip` / `huawei_unbind_ecs_eip` | EIP `AssociatePublicips` / `DisassociatePublicips` | Usually no job — verify with `ECS ShowServer` (addresses); poll as in §1 if a `job_id` is returned |
| `huawei_attach_ecs_volume` / `huawei_detach_ecs_volume` | ECS `AttachServerVolume` / `DetachServerVolume` | Verify with `ECS ListServerVolumeAttachments`; poll as in §1 if a `job_id` is returned |

`ShowJob` on a job that never existed returns an error, so always take `job_id` from the response
of the write operation that was just executed — never invent one.

### 1.3 Reporting format

```text
Result: <SUCCESS|FAIL>
Job:    <job_id> -> <status>
Target: <server_id> -> <final instance status from ShowServer>
Detail: <error_code/error_msg from the job or from ShowServer fault block, on FAIL>
```

Never print "done" while the job status is anything other than `SUCCESS`, and never print
"created" until `ShowServer` reports `ACTIVE`.

## 2. `huawei_resize_ecs_instance` — change the instance flavor

Purpose: change the vCPU/memory flavor of an existing instance (vertical scaling).
Operation: ECS `ResizeServer`. Risk: **R2**.

| Parameter | Req. | Notes |
| --------- | ---- | ----- |
| `--server_id` | required | Target instance ID |
| `--resize.flavorRef` | required | Target flavor ID — must be in the resize-support list |
| `--dry_run` | optional | `true` only pre-checks the request (no resize performed) |
| `--resize.mode` | optional | `withStopServer` — resize a running instance (auto power-off, resize, power-on) |
| `--resize.dedicated_host_id` | optional | Target dedicated host (DeH instances only) |
| `--resize.cpu_options.hw:cpu_threads` | optional | `1` = disable hyper-threading, `2` = enable |
| `--resize.extendparam.isAutoPay` | optional | `true`/`false` — auto-pay for yearly/monthly billing |

Pre-flight, no change is made:

```bash
hcloud ECS ResizeServer --cli-region={region} --server_id={server_id} --resize.flavorRef={flavor_id} --dry_run=true
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ResizeServer --cli-region={region} --server_id={server_id} --resize.flavorRef={flavor_id} --dry_run=true
```

Real resize:

```bash
# [W] 写操作 (WRITE): changes the instance flavor (power cycle with --resize.mode=withStopServer) — R2: preview + explicit confirmation required
hcloud ECS ResizeServer --cli-region={region} --server_id={server_id} --resize.flavorRef={flavor_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ResizeServer --cli-region={region} --server_id={server_id} --resize.flavorRef={flavor_id}
```

Then poll (§1): `ShowJob` until `SUCCESS`/`FAIL`, then `ShowServer` until `ACTIVE`.

Failure / degradation:

- `--dry_run=true` fails first in most cases — report the returned `error_code`/`error_msg` and do
  not send the real request.
- The target flavor must be supported for the current flavor and the current AZ; if not, the job
  fails — fall back to querying the resize-support list and picking another flavor.
- If the instance is running and `--resize.mode` was omitted, the request can be rejected; re-run
  the preview with `--resize.mode=withStopServer` and warn the user about the induced reboot.
- Yearly/monthly instances need `--resize.extendparam.isAutoPay` — otherwise the order stays
  unpaid and the resize never starts.

## 3. `huawei_reinstall_ecs_os` — reinstall the operating system

Purpose: reinstall the OS of an existing instance. Operation: ECS `ReinstallServerWithCloudInit`.
Risk: **R2** — everything on the system disk is destroyed; warn the user explicitly and confirm.

| Parameter | Req. | Notes |
| --------- | ---- | ----- |
| `--server_id` | required | Target instance ID |
| `--os-reinstall.adminpass` | optional | New login password (never echo it back) |
| `--os-reinstall.keyname` | optional | Keypair name used for the new OS |
| `--os-reinstall.userid` | optional | User ID — **required when `--os-reinstall.keyname` is supplied** |
| `--os-reinstall.mode` | optional | `withStopServer` — reinstall a running instance (auto power-off, reinstall) |
| `--os-reinstall.metadata.user_data` | optional | cloud-init user data (base64) |
| `--os-reinstall.metadata.__system__cmkid` | optional | CMK ID for encrypted system disk |
| `--os-reinstall.metadata.__system__encrypted` | optional | System disk encryption flag (`0`/`1`) |

```bash
# [W] 写操作 (WRITE): reinstalls the OS, destroying all data on the system disk — R2: preview + explicit confirmation required
hcloud ECS ReinstallServerWithCloudInit --cli-region={region} --server_id={server_id} --os-reinstall.keyname={key_name} --os-reinstall.userid={user_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ReinstallServerWithCloudInit --cli-region={region} --server_id={server_id} --os-reinstall.keyname={key_name} --os-reinstall.userid={user_id}
```

Then poll (§1): `ShowJob` until `SUCCESS`/`FAIL`, then `ShowServer` until `ACTIVE`.

⚠️ **Two hard facts verified with `--help`:**

- `ECS ReinstallServer` is **not** a KooCLI operation — the CLI rejects it and points to
  `ReinstallServerWithCloudInit` / `ReinstallServerWithoutCloudInit`. Never write it.
- This interface has **no image parameter at all** — it reinstalls with the instance's **original
  image**. Do not invent an image parameter for it (verified: the full `Params:` list of
  `ReinstallServerWithCloudInit` contains only `--server_id` plus the OS-reinstall fields
  listed above). To move to a different image, create a new instance instead.

Failure / degradation: if reinstall fails, the instance normally stays in `ERROR`; report the
`fault` block from `ShowServer` and do not retry blindly — verify the keypair/`userid` combination
first (`keyname` without `userid` is rejected by the API).

## 4. `huawei_reset_ecs_password` — reset the instance login password

Purpose: reset the login password of an existing instance. Operation: ECS `ResetServerPassword`.
Risk: **R2**.

| Parameter | Req. | Notes |
| --------- | ---- | ----- |
| `--server_id` | required | Target instance ID |
| `--reset-password.new_password` | required | New password — must satisfy the complexity rules |
| `--reset-password.is_check_password` | optional | Boolean: check the password complexity |

```bash
# [W] 写操作 (WRITE): resets the instance login password — R2: preview + explicit confirmation required
hcloud ECS ResetServerPassword --cli-region={region} --server_id={server_id} --reset-password.new_password={new_password}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ResetServerPassword --cli-region={region} --server_id={server_id} --reset-password.new_password={new_password}
```

Then poll (§1): `ShowJob` until `SUCCESS`/`FAIL`.

Failure / degradation: a rejected password is a complexity failure — re-ask the user instead of
retrying the same value; never echo the password in the report or in the command preview.
Always pass the password through a shell variable/environment indirection so it is not written
into shell history or logs.

## 5. `huawei_replace_ecs_keypair` — replace the login keypair

Purpose: create a new keypair, and retire the old one. Operations: ECS `NovaCreateKeypair`
(+ ECS `NovaDeleteKeypair`). Risk: **R2** for creation, **R1** for deleting the old keypair.

Step 1 — inspect the keypairs that already exist (read-only):

```bash
hcloud KPS ListKeypairs --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud KPS ListKeypairs --cli-region={region}
```

Step 2 — create the replacement keypair:

| Parameter | Req. | Notes |
| --------- | ---- | ----- |
| `--keypair.name` | required | Name of the new keypair |
| `--keypair.public_key` | optional | Import an existing public key instead of generating a pair |
| `--keypair.type` | optional | `ssh` or `x509` (micro-version 2.2) |
| `--keypair.user_id` | optional | Owner user ID of the keypair |

```bash
# [W] 写操作 (WRITE): creates a new keypair (the returned private key is shown once) — R2: preview + explicit confirmation required
hcloud ECS NovaCreateKeypair --cli-region={region} --keypair.name={key_name}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS NovaCreateKeypair --cli-region={region} --keypair.name={key_name}
```

Step 3 — retire the old keypair (irreversible):

| Parameter | Req. | Notes |
| --------- | ---- | ----- |
| `--keypair_name` | required | Name of the keypair to delete |

```bash
# [W] 写操作 (WRITE) — IRREVERSIBLE: deletes a keypair — R1: verify it is unused by every instance, then explicit confirmation
hcloud ECS NovaDeleteKeypair --cli-region={region} --keypair_name={old_key_name}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS NovaDeleteKeypair --cli-region={region} --keypair_name={old_key_name}
```

⚠️ **Verified limitation — binding a keypair to an *existing* instance:**

`NovaUpdateServer` accepts only `--server_id` plus `--server.name` / `--server.description`; it has
**no key-name parameter**, and the ECS operation list contains no other keypair write operation
(only `NovaCreateKeypair` / `NovaDeleteKeypair` / `NovaListKeypairs` / `NovaShowKeypair`).
Therefore `huawei_replace_ecs_keypair` is defined as:

1. create the new keypair (above), then
2. install the new **public key** on the running instance over the existing login path
   (for example by appending it to `~/.ssh/authorized_keys` after `huawei_reset_ecs_password`), and
3. delete the old keypair only after the new key is proven to work.

For a **new** instance the new keypair is used directly at creation time via
`--server.key_name={key_name}` (see `SKILL.md` §3). Do not claim that the create-keypair call
itself changed the login key of a running instance.

Failure / degradation:

- `NovaCreateKeypair` returns the private key **once** — capture it for the user immediately, never
  store it in the report, and never re-query it (only the public key can be read back).
- Deleting an old keypair that is still referenced by another instance breaks future logins —
  list the keypairs, ask which instances use it, and confirm before the R1 delete.

## 6. `huawei_bind_ecs_eip` — bind an EIP to the instance

Purpose: associate an existing elastic public IP with an instance NIC port.
Operation: **EIP** `AssociatePublicips`. Risk: **R2**.

⚠️ **Service ownership verified:** binding/unbinding public IPs belongs to the **EIP** service.
There is no `AssociatePublicips` operation under service `VPC` (KooCLI answers
`不支持的operation:AssociatePublicips`). Always use `EIP`.

Pre-check (read-only) — get the target NIC port ID:

```bash
hcloud ECS ListServerInterfaces --cli-region={region} --server_id={server_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ListServerInterfaces --cli-region={region} --server_id={server_id}
```

| Parameter | Req. | Notes |
| --------- | ---- | ----- |
| `--publicip_id` | required | ID of the EIP to bind |
| `--publicip.associate_instance_type` | required | `PORT` (also accepts `NATGW`, `VPN`, `ELB`) — use `PORT` for ECS |
| `--publicip.associate_instance_id` | required | The **port ID** of the instance NIC when `associate_instance_type=PORT` |

```bash
# [W] 写操作 (WRITE): binds an EIP to an instance NIC port — R2: preview + explicit confirmation required
hcloud EIP AssociatePublicips --cli-region={region} --publicip_id={publicip_id} --publicip.associate_instance_type=PORT --publicip.associate_instance_id={port_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud EIP AssociatePublicips --cli-region={region} --publicip_id={publicip_id} --publicip.associate_instance_type=PORT --publicip.associate_instance_id={port_id}
```

Verify by re-running `ListServerInterfaces` or `ShowServer` and confirming the new public address
appears; if the response carries a `job_id`, poll it as described in §1.

Failure / degradation:

- `associate_instance_id` must not be empty and both `associate_instance_type` /
  `associate_instance_id` must be sent together, otherwise the binding is not created.
- A dual-stack (IPv6) public IP cannot be re-bound to a different instance.
- One EIP can serve only one port — if the EIP is already bound, unbind it first (R1, §7).

## 7. `huawei_unbind_ecs_eip` — unbind an EIP from the instance

Purpose: release the association between a public IP and an instance port.
Operation: **EIP** `DisassociatePublicips`. Risk: **R1** — the instance loses public
connectivity the moment the call succeeds.

| Parameter | Req. | Notes |
| --------- | ---- | ----- |
| `--publicip_id` | required | ID of the EIP to unbind; the EIP record itself is kept |

Find the EIP currently bound to the port (read-only):

```bash
hcloud EIP ListPublicips/v2 --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud EIP ListPublicips/v2 --cli-region={region}
```

```bash
# [W] 写操作 (WRITE) — connectivity loss: unbinds an EIP from the instance — R1: verify the EIP belongs to the target, then explicit confirmation
hcloud EIP DisassociatePublicips --cli-region={region} --publicip_id={publicip_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud EIP DisassociatePublicips --cli-region={region} --publicip_id={publicip_id}
```

Failure / degradation: warn that any session reachable only through that public IP (SSH, RDP,
business traffic) is cut immediately; if the user is connected through it, agree on another access
path first. On error, re-list the public IPs and re-confirm the `--publicip_id` — do not retry
against a guessed ID.

## 8. `huawei_change_ecs_security_group` — change the security groups of an instance

Purpose: add or remove a security group on an instance.
Operations: ECS `NovaAssociateSecurityGroup` / ECS `NovaDisassociateSecurityGroup`.
Risk: **R2** — a wrong change can cut off management access.

⚠️ Both interfaces take the **security group name**, not its ID.

| Parameter | Req. | Notes |
| --------- | ---- | ----- |
| `--server_id` | required | Target instance ID |
| `--addSecurityGroup.name` | required (add) | Security group **name** to add; applies to the NICs configured on the instance |
| `--removeSecurityGroup.name` | required (remove) | Security group **name** to remove |

```bash
# [W] 写操作 (WRITE): adds a security group to the instance — R2: preview + explicit confirmation required
hcloud ECS NovaAssociateSecurityGroup --cli-region={region} --server_id={server_id} --addSecurityGroup.name={sg_name}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS NovaAssociateSecurityGroup --cli-region={region} --server_id={server_id} --addSecurityGroup.name={sg_name}
```

```bash
# [W] 写操作 (WRITE): removes a security group from the instance — R2: preview + explicit confirmation required
hcloud ECS NovaDisassociateSecurityGroup --cli-region={region} --server_id={server_id} --removeSecurityGroup.name={sg_name}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS NovaDisassociateSecurityGroup --cli-region={region} --server_id={server_id} --removeSecurityGroup.name={sg_name}
```

Then poll (§1) if the response carries a `job_id`; otherwise verify the effective groups with
`ShowServer`.

Failure / degradation: if the group is the last one, the instance keeps its default group — removing
the group that carries the inbound SSH/RDP rule locks the user out; state this before confirming.
Security group **IDs** are rejected here (the field is a name) — look the name up with
`VPC ListSecurityGroups/v2` first, and check group IDs first if you only have an ID. An instance
accepts a limited number of security groups, so a full list fails — remove one before adding another.

## 9. `huawei_add_ecs_nic` — add a NIC (network interface) to the instance

Purpose: attach an extra network interface to an instance.
Operations: ECS `NovaAttachInterface` (single, by network/port) or ECS `BatchAddServerNics`
(batch, with subnet/security-group/IP control). Risk: **R2**.

### 9a. Single interface — ECS `NovaAttachInterface`

| Parameter | Req. | Notes |
| --------- | ---- | ----- |
| `--server_id` | required | Target instance ID |
| `--interfaceAttachment.net_id` | optional | Network (subnet) ID — ignored when `port_id` is given |
| `--interfaceAttachment.port_id` | optional | Pre-created port ID — **`net_id` and `port_id` cannot both be passed** |
| `--interfaceAttachment.fixed_ips.1.ip_address` | optional | Fixed IP address inside the subnet (index starts at 1) |

```bash
# [W] 写操作 (WRITE): attaches a new network interface to the instance — R2: preview + explicit confirmation required
hcloud ECS NovaAttachInterface --cli-region={region} --server_id={server_id} --interfaceAttachment.net_id={subnet_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS NovaAttachInterface --cli-region={region} --server_id={server_id} --interfaceAttachment.net_id={subnet_id}
```

### 9b. Batch NICs — ECS `BatchAddServerNics`

| Parameter | Req. | Notes |
| --------- | ---- | ----- |
| `--server_id` | required | Target instance ID |
| `--nics.1.subnet_id` | optional | Subnet for the new NIC (index starts at 1) |
| `--nics.1.port_id` | optional | Pre-created port ID |
| `--nics.1.ip_address` | optional | Fixed IP; omitted = auto-allocated |
| `--nics.1.security_groups.1.id` | optional | Security group **ID** for the new NIC |
| `--nics.1.ipv6_enable` | optional | Enable the IPv6 address on the NIC |
| `--nics.1.ipv6_bandwidth.id` | optional | IPv6 shared-bandwidth ID |
| `--nics.1.efi_enable` | optional | Enable vRoCE on the NIC — secondary NICs only, not the primary NIC |

```bash
# [W] 写操作 (WRITE): adds one or more NICs to the instance — R2: preview + explicit confirmation required
hcloud ECS BatchAddServerNics --cli-region={region} --server_id={server_id} --nics.1.subnet_id={subnet_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS BatchAddServerNics --cli-region={region} --server_id={server_id} --nics.1.subnet_id={subnet_id}
```

Then poll (§1): NIC operations are asynchronous — `ShowJob` until `SUCCESS`/`FAIL`, then verify the
new interface with `ListServerInterfaces`.

Failure / degradation: `net_id` + `port_id` together is rejected; a subnet with no free IPs fails
the allocation (check the subnet before retrying); `efi_enable` on the primary NIC is not
supported.

## 10. `huawei_remove_ecs_nic` — remove a NIC from the instance

Purpose: detach an extra network interface.
Operations: ECS `NovaDetachInterface` (single, by port) or ECS `BatchDeleteServerNics` (batch).
Risk: **R1** — the port and its private IP are destroyed.

Pre-check (read-only) — list the interfaces and pick the right port:

```bash
hcloud ECS ListServerInterfaces --cli-region={region} --server_id={server_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ListServerInterfaces --cli-region={region} --server_id={server_id}
```

### 10a. Single interface — ECS `NovaDetachInterface`

| Parameter | Req. | Notes |
| --------- | ---- | ----- |
| `--server_id` | required | Target instance ID |
| `--port_id` | required | NIC port ID — requesting the **primary NIC returns HTTP 403** |

```bash
# [W] 写操作 (WRITE) — IRREVERSIBLE: detaches a NIC and destroys its port/IP — R1: verify the port is not the primary NIC, then explicit confirmation
hcloud ECS NovaDetachInterface --cli-region={region} --server_id={server_id} --port_id={port_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS NovaDetachInterface --cli-region={region} --server_id={server_id} --port_id={port_id}
```

### 10b. Batch NICs — ECS `BatchDeleteServerNics`

| Parameter | Req. | Notes |
| --------- | ---- | ----- |
| `--server_id` | required | Target instance ID |
| `--nics.1.id` | required | Port ID of the NIC to delete (index starts at 1) |

```bash
# [W] 写操作 (WRITE) — IRREVERSIBLE: batch-deletes NICs and their ports/IPs — R1: verify every port ID first, then explicit confirmation
hcloud ECS BatchDeleteServerNics --cli-region={region} --server_id={server_id} --nics.1.id={port_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS BatchDeleteServerNics --cli-region={region} --server_id={server_id} --nics.1.id={port_id}
```

Then poll (§1): `ShowJob` until `SUCCESS`/`FAIL`, then re-run `ListServerInterfaces`.

Failure / degradation: HTTP 403 means the port is the **primary** NIC — it cannot be detached;
report this instead of retrying. Removing a NIC that carries the default route or the bound EIP
cuts connectivity; check the EIP binding before confirming.

## 11. `huawei_attach_ecs_volume` — attach a data disk

Purpose: attach an existing EVS data volume to an instance.
Operation: ECS `AttachServerVolume`. Risk: **R2**.

| Parameter | Req. | Notes |
| --------- | ---- | ----- |
| `--server_id` | required | Target instance ID |
| `--volumeAttachment.volumeId` | required | Volume ID (UUID) to attach |
| `--dry_run` | optional | `true` only pre-checks the request (no attach performed) |
| `--volumeAttachment.device` | optional | Mount point, e.g. `/dev/vdb` (KVM) or `/dev/sdb` (XEN); XEN requires it |
| `--volumeAttachment.count` | optional | Number of volumes (for batch attach of new volumes) |
| `--volumeAttachment.volume_type` | optional | Volume type for newly created volumes |
| `--volumeAttachment.hw:passthrough` | optional | SCSI passthrough flag |

Pre-flight, no change is made:

```bash
hcloud ECS AttachServerVolume --cli-region={region} --server_id={server_id} --volumeAttachment.volumeId={volume_id} --dry_run=true
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS AttachServerVolume --cli-region={region} --server_id={server_id} --volumeAttachment.volumeId={volume_id} --dry_run=true
```

Real attach:

```bash
# [W] 写操作 (WRITE): attaches a data volume to the instance — R2: preview + explicit confirmation required
hcloud ECS AttachServerVolume --cli-region={region} --server_id={server_id} --volumeAttachment.volumeId={volume_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS AttachServerVolume --cli-region={region} --server_id={server_id} --volumeAttachment.volumeId={volume_id}
```

Verify with the attachment list:

```bash
hcloud ECS ListServerVolumeAttachments --cli-region={region} --server_id={server_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ListServerVolumeAttachments --cli-region={region} --server_id={server_id}
```

Failure / degradation: the volume must exist and be unattached; a duplicate `--volumeAttachment.device`
mount point is rejected — pick the next free letter; attach succeeds at the API level but the disk
still needs partitioning/formatting/mounting **inside the guest OS**, which this CLI cannot do —
say so explicitly in the report.

## 12. `huawei_detach_ecs_volume` — detach a data disk

Purpose: detach an EVS data volume from an instance. Operation: ECS `DetachServerVolume`.
Risk: **R2** (data on the volume is preserved, but an unclean unmount can corrupt it).

| Parameter | Req. | Notes |
| --------- | ---- | ----- |
| `--server_id` | required | Target instance ID |
| `--volume_id` | required | Volume ID to detach |
| `--delete_flag` | optional | `0` (default) = normal detach, `1` = force detach of a data disk |

```bash
# [W] 写操作 (WRITE): detaches a data volume from the instance — R2: unmount inside the guest OS first, then preview + explicit confirmation
hcloud ECS DetachServerVolume --cli-region={region} --server_id={server_id} --volume_id={volume_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS DetachServerVolume --cli-region={region} --server_id={server_id} --volume_id={volume_id}
```

Then poll (§1) if a `job_id` is returned, and verify with `ListServerVolumeAttachments`.

Failure / degradation:

- The volume must be unmounted in the guest OS first — detaching a mounted disk risks data loss and
  can fail while the device is busy.
- `--delete_flag=1` is a **force** detach and is only valid for data disks; never use it on a
  system disk and never use it to "make it work" without telling the user.
- A system disk cannot be detached; the operation is for data volumes.

## 13. Common error handling

| Symptom | Likely cause | Action |
| ------- | ------------ | ------ |
| HTTP 400 on any change | Malformed payload — usually an index/name mismatch (e.g. security group ID instead of name, both `net_id` and `port_id`) | Re-read the parameter table and `--help`; fix the payload; do not retry unchanged |
| HTTP 403 on NIC removal | The `--port_id` is the primary NIC | Report it; choose another port |
| HTTP 403 / 404 on EIP bind | The `--publicip_id` does not exist or is not in this region/project | Re-list with `EIP ListPublicips/v2` and re-confirm |
| HTTP 409 | The resource is in a state that forbids the change (volume in use, instance busy) | Poll `ShowServer`/`ShowJob`, let the instance settle, then re-preview |
| Job status `FAIL` | The asynchronous operation failed | Show `error_code`/`error_msg` from the job and the instance `fault` block; stop — do not auto-retry |
| `Unsupported operation` | A non-existent operation name was used (e.g. `ECS ReinstallServer`) | Use the operation names in this document, all verified with `--help` |
| `APIGW.0301` / 401 | Credentials invalid or expired | This is an environment problem, not a skill defect — re-authenticate before retrying |

Never auto-retry a write. A failed write is reported with the raw error, and a new attempt requires
a fresh preview and a fresh confirmation.

## 14. Coverage map

| Issue | Requirement | Section |
| ----- | ----------- | ------- |
| #921 | Mandatory async polling after every write; `ShowJob` until `SUCCESS`/`FAIL`; `ShowServer` until `ACTIVE` for create; report the final status | §1 (plus a "then poll (§1)" note in every write section) |
| #921 | The 4 wrong conclusions caused by skipping the poll | §1 table |
| #931 ① | Spec change — `huawei_resize_ecs_instance` | §2 |
| #931 ② | OS reinstall — `huawei_reinstall_ecs_os` | §3 |
| #931 ③ | Password reset — `huawei_reset_ecs_password` | §4 |
| #931 ④ | Keypair replacement — `huawei_replace_ecs_keypair` | §5 |
| #931 ⑤ | EIP bind/unbind — `huawei_bind_ecs_eip` / `huawei_unbind_ecs_eip` | §6, §7 |
| #931 ⑥ | Security group change — `huawei_change_ecs_security_group` | §8 |
| #931 ⑦ | NIC add/remove — `huawei_add_ecs_nic` / `huawei_remove_ecs_nic` | §9, §10 |
| #931 ⑧ | Volume attach/detach — `huawei_attach_ecs_volume` / `huawei_detach_ecs_volume` | §11, §12 |
| #931 | R2 preview + confirm for every change (R1 for irreversible unbind/delete) | §0 + the `[W]` marker in every command block |
