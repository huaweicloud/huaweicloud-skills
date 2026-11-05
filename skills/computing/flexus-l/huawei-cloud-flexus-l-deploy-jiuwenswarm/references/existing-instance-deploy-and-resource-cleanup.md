# Deploy on an Existing Instance & Resource Cleanup

This reference covers two flows:

1. **Deploying JiuwenSwarm onto an existing Flexus L instance** (skip instance creation)
2. **Cleaning up / releasing a deployed Flexus L instance** to stop billing

---

## 1. Deploy on an Existing Instance (在已有实例上部署)

If the Flexus L instance is **already created** (e.g. the user already has an instance running), you can skip the instance-creation phase entirely and deploy JiuwenSwarm directly onto it. This is useful when the user only wants to install the platform onto an existing server without creating a new one.

> ⚠️ **Requires customer confirmation before executing cloud operations!** Confirm the target instance (IP / ID), region, and that the instance is a Flexus L instance before proceeding.

### Steps (skip `create_instance.py`)

**1. Install dependencies** (COC remote install of Python 3.11+, Node.js 18.x, git, etc.)

```bash
python scripts/install_deps.py --ip <public_ip>
```

Or specify the instance directly:

```bash
python scripts/install_deps.py --instance-id <flexus_l_resource_id> --ecs-instance-id <ecs_id> --ip <public_ip>
```

**2. Deploy JiuwenSwarm service** (COC remote deployment)

```bash
python scripts/deploy_service.py --ip <public_ip>
```

**3. Verify deployment** (checks service status, port binding, HTTP health)

```bash
python scripts/verify_deployment.py --ip <public_ip>
```

**4. Configure model** (interactive)

```bash
python scripts/config_model.py --ip <public_ip> --interactive
```

**5. Configure message channel** (optional, interactive)

```bash
python scripts/config_channel.py --channel <xiaoyi|feishu|dingtalk> --ip <public_ip> --interactive
```

### Notes

- `install_deps.py`, `deploy_service.py`, `verify_deployment.py`, `config_model.py`, `config_channel.py` all accept `--ip <public_ip>` (auto-resolve instance info by IP) or `--instance-id` / `--ecs-instance-id` (specify directly).
- The instance must be a **Flexus L instance** (`hcss.l-instance`) for COC remote execution.
- Keep the customer confirmation step before any COC execution on the target instance.

---

## 2. Resource Cleanup (资源清理)

Deployed Flexus L instances continue to be billed (especially **包年包月 / prePaid** subscriptions). When the user no longer needs the JiuwenSwarm instance, clean it up to stop billing.

> ⚠️ **Requires customer confirmation before executing deletion!** Deleting an instance is irreversible and loses all data on it.

### Method 1: Release via Huawei Cloud Console (Recommended)

1. Login to [Flexus L Console](https://console.huaweicloud.com/smb/?/resource/list)
2. In the instance list, locate the JiuwenSwarm instance (or any instance to be released)
3. **Backup first (if needed)**: snapshot the system disk / download important data before releasing
4. Select the instance → click **更多 (More)** → **释放 (Release)** or **删除 (Delete)**
   - **prePaid (包年包月)**: click **退订 (Unsubscribe)** / **释放 (Release)** to stop the subscription and refund the remaining period
   - **postPaid (按需)**: click **删除 (Delete)** to release the instance directly
5. Confirm the release in the dialog; the instance enters "释放中 (Releasing)" and is then removed
6. Verify the instance is gone from the list; also release any **unbound EIP** and **unused security group** created for it if they are no longer needed
7. After release, confirm the instance is terminated to ensure no further billing

**Good practice**: Record which resources were created (instance ID, EIP, security group name, instance order ID) during deployment so cleanup is straightforward.

### Method 2: Unsubscribe a prePaid Instance

For prePaid (包年包月) instances:

1. Flexus L Console → instance details → **更多** → **退订 (Unsubscribe)**
2. Select the subscription items, choose a refund reason, and confirm
3. The instance is released after the unsubscribe takes effect

### Post-cleanup verification

- Confirm the instance no longer appears in the Flexus L instance list
- Confirm no billing item is still active for the instance in **费用中心 (Billing Center)**
- Release associated EIP / security group resources that are now unused