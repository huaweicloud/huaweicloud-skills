# SMS 主机迁移 — 详细参考文档

> 本文件是 SKILL.md 的配套参考，包含详细的命令、脚本、错误目录和格式规范。

---

## A. SMS Agent 安装详细流程

### A.1 前置条件检查
```bash
whoami && sudo -n true 2>/dev/null && echo "sudo OK"
sudo test -w /root/ && echo "/root writable"
which rsync && rsync --version | head -1
uname -m  # 应为 x86_64
```

### A.2 Agent 安装
```bash
cd /root/ && tar xzf SMS-Agent.tar.gz -C /root/ && cd /root/SMS-Agent && bash ./startup.sh
```

### A.3 startup.sh 交互输入序列

**首次安装**（config 目录为空）：
```
y          ← 忽略 fstab 预检警告
y          ← 同意数据采集声明
<AK>       ← 华为云 AK
<SK>       ← 华为云 SK
<sms_domain>  ← 如 sms.ap-southeast-3.myhuaweicloud.com
0          ← 企业项目（0 = default）
```

**重启 Agent**（config 目录已有配置）：
```
y          ← 忽略 fstab 预检警告
y          ← 同意数据采集声明
<AK>       ← 华为云 AK
<SK>       ← 华为云 SK
y          ← 使用上次的 sms_domain（Y/N 确认，不是重新输入）
0          ← 企业项目
```

> ⚠️ 首次安装第 5 步输入 sms_domain 字符串；重启第 5 步输入 `y` 确认。传错会无限循环。

### A.4 非交互式安装（SSH 管道）
```bash
# 首次（通过临时文件传递凭据，避免 AK/SK 出现在进程参数中）
ssh -i key.pem user@ip 'sudo bash -c "cd /root/SMS-Agent && cat > /tmp/.sms_input << '\''EOF'\''
y
y
<AK>
<SK>
sms.ap-southeast-3.myhuaweicloud.com
0
EOF
bash ./startup.sh < /tmp/.sms_input && rm -f /tmp/.sms_input"'
# 重启
ssh -i key.pem user@ip 'sudo bash -c "cd /root/SMS-Agent && cat > /tmp/.sms_input << '\''EOF'\''
y
y
<AK>
<SK>
y
0
EOF
bash ./startup.sh < /tmp/.sms_input && rm -f /tmp/.sms_input"'
```

### A.5 验证 Agent 状态
```bash
ps -ef | grep linuxmain | grep -v grep
hcloud SMS ListServers --cli-region=<region>  # state=waiting, connected=true
```

---

## B. 迁移前检查清单

### B.1 网络连通性
- [ ] 源端与目的端私网路由联通 / 源端能访问 SMS 端点 / SSH 连接测试

### B.2 源端磁盘
- [ ] `lsblk` 列举所有磁盘，记录个数/大小/分区，与 Excel 核对，确认已挂载

### B.3 源端规格
- [ ] CPU < 80% / 可用内存 > 256MB / 磁盘 ≤ 23 / 记录 CPU/内存/OS 供对齐

### B.4 网络类型识别
- `VPN/专线` → 私网，不配 publicip，禁止挂载 EIP
- `EIP` → 公网，查询已有 EIP；禁止新建，没有则通知用户手动创建

---

## C. SMS API 详细命令

### C.1 安全组端口

| 迁移类型 | 需放通端口 | 用途 |
|---------|-----------|------|
| 文件级 | 22 | SSH（rsync over SSH） |
| 块级 | 22, 8899, 8900 | SSH + 控制 + 数据 |

```bash
# 检查
hcloud VPC ListSecurityGroupRules --cli-region=<region> --project_id=<pid> --security_group_id.1=<sg_id>
# 添加（以 8899 为例）
hcloud VPC CreateSecurityGroupRule --cli-region=<region> --security_group_rule.security_group_id=<sg_id> \
  --security_group_rule.direction=ingress --security_group_rule.protocol=tcp \
  --security_group_rule.multiport=8899 --security_group_rule.remote_ip_prefix=0.0.0.0/0 \
  --security_group_rule.action=allow --security_group_rule.ethertype=IPv4
```

### C.2 镜像选择
```bash
hcloud IMS ListImages --cli-region=<region> --__imagetype=gold --__os_type=Linux --__platform=Ubuntu
```
匹配源端 OS 版本取 id。禁止私有镜像。无匹配则停止通知用户。

### C.3 创建模板（CreateTemplate）

> ⚠️ **命名规则**：模板名使用固定名称，如 `AgentTemplate`（不带时间戳）

```bash
TIMESTAMP=$(date +%m%d)

hcloud SMS CreateTemplate --cli-region=<region> \
  --template.name=AgentTemplate \
  --template.region=<region> --template.projectid=<pid> \
  --template.availability_zone=<az> --template.vpc.id=<vpc_id> --template.vpc.cidr=<cidr> \
  --template.nics.1.id=<subnet_id> --template.nics.1.name=<subnet_name> --template.nics.1.cidr=<subnet_cidr> \
  --template.security_groups.1.id=<sg_id> --template.security_groups.1.name=<sg_name> \
  --template.flavor=<flavor> --template.volumetype=SAS --template.target_password='<pwd>' \
  --template.target_server_name=server-01_${TIMESTAMP} \
  --template.image_id=<image_id> --template.is_template=true
```

必填参数缺失后果：

| 参数 | 缺失后果 |
|------|---------|
| vpc.id + vpc.cidr | SMS.0007: NoneType 'vpc' |
| nics.1.id + name + cidr | SMS.6102 |
| security_groups.1.id + name | SMS.6102 |
| image_id | SMS.0007: vols_map NoneType |
| publicip.type + bandwidth_size（**仅 EIP 场景**；VPN/专线禁止传入） | SMS.6562 |
| is_template=true | 模板被级联删除 |
| target_password | ⚠️ 仅设中间 ECS 密码，全盘迁移后被源盘覆盖（见 G 节修复项 6） |

模板规则：镜像与源端 OS 一致（公有镜像）；安全组用已有默认组；规格 ≥ 源端；可用区取第一个

### C.4 创建任务（CreateTask）

> ⚠️ **ECS 命名**：`--target_server.name={hostname}_{MMDD}`

```bash
hcloud SMS CreateTask --cli-region=<region> \
  --name=MigrationTask-server-01_${TIMESTAMP} \
  --project_id=<pid> --project_name=SystemProject --region_id=<region> --region_name=<region> \
  --source_server.id=<src_id> --target_server.name=server-01_${TIMESTAMP} --target_server.vm_id="" \
  --type=MIGRATE_FILE --os_type=LINUX --vm_template_id=<tpl_id> --auto_start=true \
  --use_public_ip=false --syncing=false \
  --target_server.disks.1.disk_id=<src_disk_id> --target_server.disks.1.device_use=BOOT \
  --target_server.disks.1.name=/dev/nvme0n1 --target_server.disks.1.size=<bytes> --target_server.disks.1.used_size=<bytes> \
  --target_server.disks.1.physical_volumes.1.device_use=OS --target_server.disks.1.physical_volumes.1.file_system=ext4 \
  --target_server.disks.1.physical_volumes.1.index=0 --target_server.disks.1.physical_volumes.1.mount_point=/ \
  --target_server.disks.1.physical_volumes.1.name=<pv> --target_server.disks.1.physical_volumes.1.size=<bytes> \
  --target_server.disks.1.physical_volumes.1.used_size=<bytes> --target_server.disks.1.physical_volumes.1.uuid=<uuid>
```

### C.5 启动、轮询、割接
```bash
hcloud SMS UpdateTaskStatus --cli-region=<region> --task_id=<id> --operation=start
hcloud SMS ShowTask --cli-region=<region> --task_id=<id>
# READY→RUNNING→MIGRATE_FAIL/SYNCING/CUTOVER_READY
hcloud SMS UpdateTaskStatus --cli-region=<region> --task_id=<id> --operation=cutover  # 需用户确认
```

---

## D. 迁移后校验

- [ ] **🔴 源端无写操作**：对比迁移前后 df -h、数据库/日志大小、mtime
- [ ] 目的端规格一致（CPU/内存/磁盘）/ OS 版本一致 / 网络连通 / 应用启动

---

## E. 常见错误目录

| 错误 | 根因 | 修复 |
|------|------|------|
| 源端写操作 | 迁移中源端被写入 | 立即停止，回滚，重新迁移 |
| SMS.0515 | CreateTask 磁盘参数不完整 | 从 ShowServer 提取完整磁盘信息 |
| SMS.0007 vpc | 模板被删或 VPC 不完整 | 重建模板（vpc.id + vpc.cidr） |
| SMS.0007 vols_map | UEFI 源端未指定匹配镜像 | 模板指定匹配公有镜像 |
| SMS.6562 | 跨云私网不通，未配公网 IP | 模板加 publicip |
| SMS.6102 | 模板参数不完整 | 补全 name/cidr |
| SMS.7711 | 任务名含非法字符 | 字母+数字+下划线+连字符 |
| 源端 error | Agent 进错误态 | kill Agent，重启 startup.sh |
| 模板级联删除 | 删任务时模板一起删 | is_template=true，每次重建 |
| SSH port 22 | 安全组未放通 | 添加入向 TCP 22 |
| **迁移后无法登录** | 全盘迁移保留源端密码 | 修复脚本中 `chpasswd` 设预期密码 |
| **迁移后无法启动** | UEFI→BIOS + AWS 内核不兼容 | 见 G 节完整修复流程 |
| **net.ifnames=0 丢失** | 50-cloudimg-settings.cfg 覆盖 | 创建 99-net-ifnames.cfg 高优先级 |

---

## F. 输入格式

### F.1 JSON
```json
[{
  "id": "host-001",
  "source": {"hostname":"server-01","ip":"172.196.0.134","ssh_port":22,"username":"ubuntu","key_file":"server-01key.pem","region_id":"ap-southeast-1","os":"Ubuntu","os_type":"linux","firmware":"UEFI"},
  "target": {"hostname":"server-01","region_id":"ap-southeast-3","vpc_name":"vpc-agent-84346077","subnet_name":"subnet-migration","subnet_cidr":"192.168.3.0/24","migrate_to_existing":false},
  "network_type":"VPN","migration_type":"file",
  "sms": {"source_server_id":"","project_id":"","template_name":"AgentTemplate","task_name":"MigrationTask01","use_public_ip":false,"auto_start":true}
}]
```

### F.2 Excel 表（18 列）

| 列 | 名称 | 示例 | 列 | 名称 | 示例 |
|----|------|------|----|------|------|
| 1 | 源端主机名 | server-01 | 10 | 目的端主机名 | server-01 |
| 2 | 源端IP | 172.196.0.134 | 11 | 目的端区域 | ap-southeast-3 |
| 3 | SSH端口 | 22 | 12 | VPC名称 | vpc-agent-84346077 |
| 4 | 用户名 | ubuntu | 13 | 子网名称 | subnet-migration |
| 5 | 密钥文件 | server-01key.pem | 14 | 子网CIDR | 192.168.3.0/24 |
| 6 | 源端区域id | ap-southeast-1 | 15 | 是否已有主机 | 否 |
| 7 | 源端区域名 | Singapore | 16 | 已有主机名 | （空） |
| 8 | 源端OS | Ubuntu | 17 | 已有主机区域 | （空） |
| 9 | 网络类型 | VPN | 18 | 已有主机IP | （空） |

> Excel 路径：`obs://obs-zy-84346077/vmConfig/migration_hosts.xlsx`

---

## G. 迁移后修复 — 完整脚本（9 个修复项）

> 当迁移成功（MIGRATE_SUCCESS）但 ECS 不可达时执行。
> 判断标志：ECS ACTIVE + ARP 有 MAC + ping 不通 + SSH 超时
>
> ⚠️ **5 个叠加问题**：UEFI→BIOS + AWS内核不兼容 + 网络残留 + 密码不匹配 + grub.d覆盖

### G.1 停止 ECS + 卸载磁盘
```bash
hcloud ECS BatchStopServers --cli-region=<region> --os-stop.servers.1.id=<target_id> --os-stop.type=HARD
# 等待 SHUTOFF
hcloud ECS NovaDetachVolume --cli-region=<region> --server_id=<target_id> --volume_id=<disk_id>
```

### G.2 创建辅助 ECS

> ⚠️ 命名必须带时间戳：`helper_{MMDD}`
> ⚠️ 此处新建的 EIP 是规则 12 的唯一例外（helper 修复场景），修复完成后必须立即解绑并释放

```bash
TIMESTAMP=$(date +%m%d)
hcloud ECS CreateServers --cli-region=<region> \
  --server.name=helper_${TIMESTAMP} --server.imageRef=<image_id> --server.flavorRef=s6.large.05 \
  --server.vpcid=<vpc_id> --server.nics.1.subnet_id=<subnet_id> \
  --server.publicip.eip.iptype=5_bgp --server.publicip.eip.bandwidth.size=10 --server.publicip.eip.bandwidth.sharetype=PER \
  --server.root_volume.volumetype=GPSSD --server.root_volume.size=40 \
  --server.availability_zone=<az> --server.security_groups.1.id=<sg_id> --server.adminPass='Helper@2026'
# 创建后重启一次使密码生效
hcloud ECS BatchRebootServers --cli-region=<region> --reboot.servers.1.id=<helper_id> --reboot.type=SOFT
```

### G.3 挂载磁盘 + 执行修复
```bash
hcloud ECS NovaAttachVolume --cli-region=<region> --server_id=<helper_id> --volumeAttachment.volumeId=<disk_id>
# 磁盘挂载为 /dev/vdb
```

修复脚本（在辅助 ECS 上执行）：

```bash
sshpass -p 'Helper@2026' ssh root@<helper_eip> '
# 0. 挂载分区（先通过 lsblk 确认分区号，不同源端分区布局不同）
lsblk /dev/vdb -o NAME,SIZE,FSTYPE,MOUNTPOINT,PARTLABEL
mount /dev/vdb<root_part> /mnt                          # root 分区
mount /dev/vdb<boot_part> /mnt/boot 2>/dev/null         # boot 分区（如有）
mount /dev/vdb<efi_part> /mnt/boot/efi 2>/dev/null     # EFI 分区（如有）
# 根据 lsblk 输出确认 root/boot/efi 分区号，替换上方 <root_part>/<boot_part>/<efi_part>

# ============================================================
# 修复项 1: 安装 BIOS GRUB（UEFI→BIOS）
# ============================================================
# 创建 BIOS Boot Partition（GPT 上 i386-pc GRUB 需要）
parted /dev/vdb mkpart primary 8588MB 8589MB
parted /dev/vdb set <part_num> bios_grub on && partprobe /dev/vdb && sleep 2

# ============================================================
# 修复项 2: 替换 AWS 内核为华为云内核
# ============================================================
# AWS 内核（如 vmlinuz-7.0.0-1010-aws）在华为云虚拟硬件上不启动
# 从辅助 ECS 复制华为云 Ubuntu 内核
KERNEL_VER=$(ls /boot/vmlinuz-*generic | tail -1 | sed "s|/boot/vmlinuz-||")
cp /boot/vmlinuz-${KERNEL_VER} /mnt/boot/
cp /boot/initrd.img-${KERNEL_VER} /mnt/boot/
cp -a /lib/modules/${KERNEL_VER} /mnt/lib/modules/
# 验证新内核复制成功后再删除旧内核（在 update-grub 之后执行）
# （删除操作移至 update-grub 之后）

# ============================================================
# 修复项 3: 修复 netplan（DHCP + 正确网卡名）
# ============================================================
cat > /mnt/etc/netplan/50-cloud-init.yaml << "NP"
network:
    version: 2
    renderer: networkd
    ethernets:
        eth0: {dhcp4: true}
NP
chmod 600 /mnt/etc/netplan/50-cloud-init.yaml

# ============================================================
# 修复项 4: 防止 grub.d 覆盖 net.ifnames=0
# ============================================================
# 50-cloudimg-settings.cfg 会覆盖 GRUB_CMDLINE_LINUX_DEFAULT
# 创建 99- 开头的高优先级文件
mkdir -p /mnt/etc/default/grub.d/
cat > /mnt/etc/default/grub.d/99-net-ifnames.cfg << "GRUBD"
GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT net.ifnames=0 biosdevname=0"
GRUBD
# 同时直接修改 grub-default 确保生效
sed -i "s/^GRUB_CMDLINE_LINUX_DEFAULT=.*/GRUB_CMDLINE_LINUX_DEFAULT=\"net.ifnames=0 biosdevname=0\"/" /mnt/etc/default/grub 2>/dev/null

# ============================================================
# 修复项 5: 禁用 cloud-init 网络配置
# ============================================================
# cloud-init 用 DataSourceEc2Local 读 AWS 元数据，会覆盖 netplan
touch /mnt/etc/cloud/cloud-init.disabled
mkdir -p /mnt/etc/cloud/cloud.cfg.d/
cat > /mnt/etc/cloud/cloud.cfg.d/90-datasource.cfg << "DS"
datasource_list: [ None ]
DS
# 禁用 cloud-init networking 模块
cat > /mnt/etc/cloud/cloud.cfg.d/99-disable-network.cfg << "DN"
network: {config: disabled}
DN

# ============================================================
# 修复项 6: 设置 root 密码（⚠️ 用用户预期密码！）
# ============================================================
# 全盘迁移保留源端 /etc/shadow，target_password 被覆盖
# 必须在此重设为用户预期密码
chroot /mnt /bin/bash -c "echo \"root:<EXPECTED_PASSWORD>\" | chpasswd"

# ============================================================
# 修复项 9: 启用 SSH 密码登录
# ============================================================
sed -i "s/^#*PasswordAuthentication.*/PasswordAuthentication yes/" /mnt/etc/ssh/sshd_config
sed -i "s/^#*PermitRootLogin.*/PermitRootLogin yes/" /mnt/etc/ssh/sshd_config

# ============================================================
# 修复项 7+8: chroot 内更新 grub + 重建 initramfs
# ============================================================
mount --bind /dev /mnt/dev && mount --bind /proc /mnt/proc && mount --bind /sys /mnt/sys && mount --bind /run /mnt/run
cp /etc/resolv.conf /mnt/etc/resolv.conf

chroot /mnt /bin/bash -c "
  # 安装 BIOS GRUB（i386-pc，不受 Secure Boot 影响）
  grub-install --target=i386-pc /dev/vdb
  # 更新 grub 配置（会读取 99-net-ifnames.cfg）
  update-grub
  # 新内核已生效，安全删除 AWS 旧内核
  rm -f /boot/vmlinuz-*-aws /boot/initrd.img-*-aws 2>/dev/null
  # 重建 initramfs（使用新内核）
  update-initramfs -u -k all
  # 验证 netplan 语法
  netplan generate 2>&1 || true
"

# ============================================================
# 卸载
# ============================================================
umount /mnt/run /mnt/sys /mnt/proc /mnt/dev 2>/dev/null
umount /mnt/boot/efi 2>/dev/null
umount /mnt/boot 2>/dev/null
umount /mnt
'
```

### G.4 还原磁盘并启动
```bash
hcloud ECS NovaDetachVolume --cli-region=<region> --server_id=<helper_id> --volume_id=<disk_id>
hcloud ECS NovaAttachVolume --cli-region=<region> --server_id=<target_id> --volumeAttachment.volumeId=<disk_id> --volumeAttachment.device=/dev/vda
hcloud ECS BatchStartServers --cli-region=<region> --os-start.servers.1.id=<target_id>
```

### G.5 验证
```bash
# 等待 ECS ACTIVE
sleep 30
ping -c 3 <target_ip>
sshpass -p '<EXPECTED_PASSWORD>' ssh -o StrictHostKeyChecking=no root@<target_ip> \
  'echo "SSH OK: $(hostname)"; ip addr show; uname -r'
```

### G.6 修复项根因说明

| 修复项 | 根因 | 不修复后果 |
|--------|------|-----------|
| 1. BIOS GRUB | 源端 UEFI，华为云 ECS 用 BIOS | ECS 无法启动 |
| 2. 替换 AWS 内核 | AWS 内核（如 7.0.0-1010-aws）在华为云虚拟硬件不启动 | 启动到内核即 halt，串口无输出 |
| 3. netplan DHCP | 源端配 AWS 静态 IP + 网卡名 ens5 | 网卡无 IP |
| 4. 99-net-ifnames.cfg | 50-cloudimg-settings.cfg 覆盖 GRUB_CMDLINE | net.ifnames=0 丢失，网卡名不正确 |
| 5. 禁用 cloud-init 网络 | cloud-init 用 DataSourceEc2Local 覆盖 netplan | cloud-init 启动后网络配置被覆盖 |
| 6. 设置 root 密码 | 全盘迁移保留源端 /etc/shadow | 用户无法用预期密码登录 |
| 7. 更新 grub | 新内核需要 grub.cfg 入口 | grub 找不到新内核 |
| 8. 重建 initramfs | 新内核需要匹配的 initrd | 内核无法加载驱动 |
| 9. SSH 密码登录 | sshd_config 可能禁用密码登录 | 仅密钥可用，密码登录被拒 |

### G.7 Secure Boot 注意事项

华为云 ECS 可能启用 Secure Boot（Ubuntu 24.04 镜像）。此时：
- `grub-install --target=x86_64-efi` 生成**无签名** EFI 二进制 → Secure Boot 拒绝 → 静默 halt
- **解决方案 A**（推荐）：使用 `--target=i386-pc`（BIOS 模式），不受 Secure Boot 影响
- **解决方案 B**：chroot 内安装 `grub-efi-amd64-signed` 包（需 DNS 可用 + apt 源可达）
- **解决方案 C**：通过华为云控制台关闭 Secure Boot（需用户操作）

### G.8 排查流程（修复后仍不通时）

```
1. 查看串口控制台输出（hcloud ECS ShowServerRemoteConsole 或控制台 VNC）
   - 无输出 → GRUB 未安装成功
   - GRUB 提示但无内核加载 → grub.cfg 问题
   - 内核 panic → 内核不兼容或 initramfs 问题

2. 重新挂载到辅助 ECS 检查：
   - /boot/grub/grub.cfg 是否包含新内核
   - /boot/vmlinuz-*generic 是否存在
   - /lib/modules/ 是否有对应模块
   - /etc/default/grub.d/99-net-ifnames.cfg 是否存在

3. 网络排查（如能登录但网络不通）：
   - ip addr show → 确认网卡名和 IP
   - cat /etc/netplan/*.yaml → 确认 DHCP 配置
   - systemctl status systemd-networkd → 确认 networkd 运行
```

---

## H. 关键校验点（任务创建前）

1. 输入数据完整正确（源端/目的端与 Excel 一致）
2. 规格 ≥ 源端，镜像与源端 OS 一致（公有镜像）
3. 磁盘信息完整（磁盘数与 Excel 一致，从 Agent 获取分区信息）
4. 网络配置正确（EIP 场景确认已有 EIP；VPN 场景禁止挂载 EIP）
5. 源端写保护已建立
6. **ECS 命名带时间戳**：`{hostname}_{MMDD}`
7. 有疑问暂停询问用户

---

## I. 参考文档


- [SMS 迁移限制](https://support.huaweicloud.com/sms_faq/sms_faq_0007.html)
- [SMS API 参考](https://support.huaweicloud.com/api-sms/sms_api_0001.html)
- [设置迁移目的端](https://support.huaweicloud.com/qs-sms/sms3_02_0009.html)
