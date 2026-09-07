# EVS Volume Readiness Playbook

## 目标

确认云硬盘创建、挂载或扩容后的云侧状态，并区分云侧挂载成功和 ECS 内文件系统可用。

## 适用场景

- 创建 EVS 云硬盘
- 挂载到 ECS
- 扩容或变更磁盘类型
- 创建、查询或删除快照

涉及 ECS 内部格式化、挂载和写入测试时，先读取 `ecs-ssh-access-readiness.md`。没有 COC 时，必须通过已验证 SSH key、reset password 可用通道，或对可替换资源执行重装/重建纳管后再做机内动作。

## 标准检查

0. 命名和幂等键：

- 用户没有给数据盘名称时，用稳定的业务语义名，例如 `disk-<workload>-data`。不要用每轮随机名，也不要因为挂载到某台 ECS 就默认改成 `<server>-data`，除非用户明确要求主机级命名。
- 用户只说“大一点的数据盘”或“应用数据放那里”但没有指定容量时，结合现有系统盘大小、业务目标、配额、可售规格和成本风险推断容量。若推断而非用户明示，最终要说明“我按这些依据选择了该容量/类型，可调整”。
- 创建前按候选名称和目标 ECS attachment 查询既有云硬盘。若已有满足容量/类型要求的数据盘挂载到目标 ECS，优先修复机内挂载，不要再创建重复盘。

1. 查询 EVS 列表入口：

```bash
python3 scripts/hcloud_resource_discovery.py \
  --service EVS \
  --operation ListVolumes \
  --region=<region> \
  --project-id=<project-id> \
  --limit=20 \
  --pretty
```

2. 对云硬盘 JSON 结果做云侧验收：

```bash
python3 scripts/hcloud_resource_verify.py \
  --service EVS \
  --json-file=<safe-exec-result.json> \
  --target-id=<volume-id> \
  --expect-status IN-USE \
  --expect-bound-to=<server-id> \
  --require-match \
  --pretty
```

## 验收字段

- Volume ID
- 名称
- `status`
- 容量和类型
- 可用区
- attachment 中的 ECS ID / device

## ECS 内部验收

如果用户目标包括“格式化为 ext4 并挂载到 `/data`”，云侧 `in-use` 仍不等于任务完成。还必须通过 SSH、远程命令或等价通道验证：

- `lsblk` 能看到目标设备
- 文件系统类型符合预期
- `df -h` 能看到挂载点
- 写入测试文件成功

没有 ECS 内部执行能力时，只能声明“云硬盘已挂载到云侧目标”，不能声明“文件系统已经可用”。

### 远程执行缺口处理

- 先检查是否存在已验证可用的 SSH 凭据、远程命令/COC、或创建时可注入的 cloud-init。只要当前任务是已有 ECS 的后置挂载，cloud-init 通常不能补救，除非允许重装/重建。
- 如果 COC 在当前 region 不支持或返回权限错误，不要继续尝试同一 COC 路径超过一次。
- 对创建、部署、配置、验收类任务，若云盘已经挂到目标 ECS 但缺机内执行通道，按纳管阶梯走：
  1. 查 ECS `key_name`，寻找本地保存的 private key；若 keypair 由 KPS 托管，尝试 `KPS ExportPrivateKey`。只有实际 `ssh -i` 成功才算可用。
  2. key 不可用时，`ShowResetPasswordFlag` 确认 ECS 支持重置密码。
  3. 生成一次性强密码，调用 `ResetServerPassword`；密码只用于本轮 SSH，不在最终回复展示。
  4. 只为受限来源 CIDR 添加临时 TCP 22 入站规则，例如用户给定管理员 IP、当前执行环境 `/32`、VPN/办公网或跳板机来源。
  5. 用 `sshpass` 依次尝试 root 和镜像默认用户。若 `Permission denied` 且 user_data/sshd 显示 `PasswordAuthentication no`，不要重复重置密码。
  6. 登录成功后执行幂等挂载脚本。
  7. 验收 `df -h /data`、`findmnt /data`、`touch /data/test_write.txt`。
  8. 删除临时 SSH 入站规则；若无法删除，最终输出临时规则 ID 和原因。
- 若 key 不可用、托管私钥不存在、密码登录被系统策略拒绝且 COC 不可用：
  - 对本轮新建、演示或可替换部署资源，不要停在云侧挂载；创建/导出任务专用 keypair 后，用 `ReinstallServerWithCloudInit` 注入 key 和 `/data` 挂载脚本。只有需要换镜像时才用 `ChangeServerOsWithCloudInit`；只有实例身份/EIP/ELB 绑定无需保留时才同名重建。
  - 对明确已有且需保留数据的业务 ECS，不能宣称 `/data` 完成，只能给出云侧挂载事实和需要的最小执行通道。

### 幂等机内挂载脚本要点

- 优先用设备实际 UUID 写 `/etc/fstab`，不要直接写易变化的 `/dev/vdX`。
- 如果目标挂载点已挂载，先确认它是否就是目标新盘；不要格式化已经挂载且可能含数据的盘。
- 如果目标盘已有文件系统，跳过 `mkfs`；只有 `blkid` 查不到文件系统时才格式化。
- 验收脚本至少输出：
  - `lsblk -f`
  - `findmnt /data`
  - `df -h /data`
  - `touch /data/test_write.txt && rm -f /data/test_write.txt`

### 同名/既有磁盘

- 若已经存在符合目标命名或验收要求的云硬盘并已挂载到目标 ECS，优先修复和验证这块盘，不要创建新的重复数据盘。
- 只有用户明确要求新增更大容量，或现有盘容量/类型不满足目标，才创建新盘；创建后仍必须完成机内挂载验收。

## 最终输出

成功时给出 volume ID、状态、容量、挂载目标和 ECS 内部验收结果。失败时明确停在云侧挂载、系统识别、格式化还是挂载点阶段。
