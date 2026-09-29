---
name: huawei-cloud-sms-migration-assistant
description: migrate hosts to Huawei cloud end-to-end, including reading the host information from a given obs path, confirm with the user on the to-be migrated hosts, perform migration pre-check, start up the sms agent, create sms migration tasks, read and expand 'MIGRATION_REFERENCE.md' if encounter error during the migration, monitor the tasks and report to the user once the full data replication is completed.
---

# huawei-cloud-sms-migration-assistant

## 概述

辅助华为云 SMS（Server Migration Service）主机迁移操作。
主要步骤如下：
1. **高危操作禁止列表** — 牢记迁移过程中绝对不能执行的操作
2. **迁移前检查** — 网络连通性、源端资源水位、磁盘/OS 兼容性
3. **API 迁移流程** — hcloud CLI + SMS API 完整流程
4. **迁移后启动修复** — 如果源端使用UEFI，需要使用helper ecs把内核替换成BIOS、网络配置、密码注入
5. **迁移后校验** — 目的端与源端一致性比对

6. **常见错误与修复** — 实战踩坑（SMS.0515/SMS.0007/SMS.6562 等）
如果迁移中遇到报错，首先参考 `references/MIGRATION_REFERENCE.md`错误目录，以及解决方案

---

## 核心原则

**在不修改任何源端信息的情况下，将源端数据原封不动地安全复制到目的端。**

1. **源端保护第一** — 源端严格只读，禁止任何增删改
2. **数据完整性** — 源端所有数据完整复制到目的端
3. **严格按输入创建目的端** — 不允许偏差或改动
4. **源端业务不变** — 迁移过程中源端业务状态保持不变
5. **命名规则强制** — 所有新创建的目的端 ECS 必须按 `{hostname}_{MMDD}` 命名

---

## 最关键风险点：源端保护

> **迁移过程中，源端必须严格只读。任何增删改操作都会导致致命后果。**

- **禁止**：数据库写入、文件上传/修改/删除、日志清空/新增、配置变更、应用重启、软件安装、用户添加/修改、权限变更、磁盘分区调整
- **后果**：源端业务瘫痪 + 迁移失败 + 目的端数据不一致 + 无法恢复
- **Agent 必须**：定期检查源端磁盘/数据库/日志大小，发现任何变化立即停止迁移、回滚、通知用户

---

## 一、禁止执行的高危操作

### 级别一：数据丢失或迁移失败（绝对禁止）

#### 源端保护

| 编号 | 禁止操作 |
|------|---------|
| **01** | 迁移中对源端**任何增删改** |
| **02** | 迁移中源端**磁盘调整** |
| **03** | 关闭源端 **SMS-Agent** |
| **04** | 关闭源端 **IO 监控** |
| **05** | 割接后**源端新增数据** | 

#### 目的端保护

| 编号 | 禁止操作 |
|------|---------|
| 06 | 目的端**切换操作系统** |
| 07 | 目的端**重装系统** |
| 08 | 目的端**磁盘操作** |
| 09 | 未完成时**系统重装/切换** |
| 10 | 割接前**目的端新增数据** |

#### 其他关键操作

| 编号 | 禁止操作 |
|------|---------|
| 11 | 未完成时**删除迁移任务** |
| **12** | **禁止创建/新建 EIP**（任何阶段），需 EIP 时**用户在控制台手动创建**，你只用已有 EIP。**例外**：迁移后修复流程中创建 helper ECS 的临时 EIP 允许由 Agent 创建，修复完成后必须立即释放 |
| **12a** | 网络类型**非 EIP**（VPN/专线）时**禁止新建 EIP、禁止给目的端 ECS 挂载/绑定 EIP**；模板中**禁止传入任何 `--template.publicip.*` 参数**；迁移后**必须检查并释放 SMS 自动创建的 EIP** |
| **13** | **禁止对你在的主机里记录的华为云AK/SK 做增删改操作** |

### 级别二：迁移问题或额外成本

| 编号 | 禁止操作 |
|------|---------|
| 14 | CPU 占用率 ≥ 80% 启动迁移 |
| 15 | 可用内存 ≤ 256MB 启动迁移 |
| 16 | 磁盘 > 23 块 |
| 17 | Linux 磁盘 > 16TB |
| 18 | 同时迁移 > 200 台 |
| 19 | 单用户 > 1000 台 |
| 20 | BitLocker 加密 Windows |
| 21 | AD 域控制器/多节点数据库 |
| 22 | RAID 磁盘阵列 |
| 23 | LVM 嵌套系统 |
| 24 | LVM 精简卷 |
| 25 | 安全组开放 0.0.0.0/0 |
| 26 | 安全组开放非必需端口 |
| 27 | 使用**私有镜像**而非公有镜像 |
| 28 | 目的端规格 **<** 源端（缩容） |

### 级别三：需注意

| 编号 | 注意事项 |
|------|---------|
| 29 | OS/应用 License 可能失效（SID/MAC 变化） |
| 30 | 网卡配置可能需手动调整 |
| 31 | GPU 服务器需重装驱动 |
| 32 | 共享文件系统不会被迁移 |
| 33 | 未挂载/未初始化磁盘不会被迁移 |
| 34 | 临时磁盘迁移完成后自动删除 |

---

## 二、迁移前检查

```
1. 迁移前检查     →  python3 scripts/pre_migration_check.py --input migration_hosts.json
```

---

## 三、SMS Agent 安装

```bash
### 源端安装。如果以下目录里已有SMS Agent, 跳过安装步骤，请勿重复安装。
cd /root/SMS-Agent && bash ./startup.sh
### 交互输入：y / y / <AK> / <SK> / sms_domain / 0
```

如果是首次安装，第 5 步输入 sms_domain 字符串；重启输入 `y` 确认。传错会无限循环。

详细交互序列、非交互式安装、验证方法见 `references/MIGRATION_REFERENCE.md` A 节。

---

## 四、SMS API 迁移流程

### 4.1 流程概览

```
1. 解析 'migration_hosts.json' → 源端信息 vs 目的端信息
2. 查询目的端资源（VPC/子网/安全组/规格/镜像）
3. 创建模板（CreateTemplate）— 含 target_password
4. 创建任务（CreateTask）— 三个关键参数！
5. 启动（UpdateTaskStatus --operation=start）
6. 轮询（ShowTask）→ MIGRATE_SUCCESS
7. （跳过）割接（--operation=cutover）— 不允许割接或者删除源端主机。任务停留在割接前这一步，直到用户手动启动割接
8. 迁移后启动修复（第七节）— 如果主机无法启动，进行修复
9. 迁移后校验
```
如果删除任务，在下一次重建任务前要先重建迁移Template模版

输入数据严格性：必须按 'migration_hosts' JSON 创建目的端，禁止修改或猜测。有疑问**先问用户**。

### 4.2 网络类型与 EIP 规则

| Excel 网络类型 | 模板配置 | EIP 规则 |
|---------------|---------|---------|
| VPN/专线 | 私网，**模板中不传任何 `--template.publicip.*` 参数** | **禁止新建 EIP、禁止挂载 EIP**（12a）；迁移后检查并释放 SMS 自动创建的 EIP |
| EIP | 公网，配 public eip | 查询已有 EIP 挂载；**禁止新建**（12），没有通知用户手动创建 |

> ⚠️ **VPN/专线 网络类型 EIP 规则（强制，违反即违规）**
>
> 当 `migration_hosts` 中网络类型为 **VPN/专线** 时：
>
> 1. **创建模板（CreateTemplate）时禁止传入 `--template.publicip.type` / `--template.publicip.bandwidth_size` 等任何 publicip 参数** — SMS 服务会据此自动创建 EIP 并绑定到目的端 ECS，违反 VPN 网络类型不允许公网访问的安全要求
> 2. **迁移完成后（MIGRATE_SUCCESS 后），必须检查每台目的端 ECS 是否被绑定了浮动 IP** — 即使模板未配 publicip，SMS 在跨云迁移场景下仍可能自动创建 EIP 用于中间传输
> 3. **如发现目的端 ECS 有浮动 IP，必须立即解绑并释放**：
>    ```bash
>    # 解绑 EIP
>    hcloud EIP DisassociatePublicips --cli-region=<region> --publicip_id=<eip_id> 
>    # 释放 EIP
>    hcloud EIP DeletePublicip --cli-region=<region> --publicip_id=<eip_id>
>    ```
> 4. **此规则适用于迁移全生命周期**：模板创建、任务执行、迁移后修复、清理阶段，任何阶段发现 VPN 场景下有 EIP 都必须清理
> 5. **根因**：VPN/专线网络类型的主机通过私网与内网通信，公网 EIP 暴露攻击面，违反网络安全隔离要求

### 4.3 创建模板（CreateTemplate）— 关键必填参数

| 参数 | 缺失后出现错误码 |
|------|---------|
| vpc.id + vpc.cidr | SMS.0007 |
| nics.1.id + name + cidr | SMS.6102 |
| security_groups.1.id + name | SMS.6102 |
| image_id（与源端 OS 一致，公有镜像） | SMS.0007 vols_map |
| publicip.type + bandwidth_size（**仅 EIP 场景**；VPN/专线场景禁止传入） | SMS.6562 |
| is_template=true | 模板被级联删除 |
| **target_password** | 见下方说明 |

**`target_password` 的真相**：该参数设置 SMS 创建中间 ECS 时的密码。但全盘迁移完成后，源盘的 `/etc/shadow` 会覆盖中间 ECS 的密码 — **最终迁移盘上的密码是源端的，不是 `target_password` 设的值**。因此必须在迁移后修复脚本中重新设置密码（见第七节修复项 6）。

完整命令见 `references/MIGRATION_REFERENCE.md` C.3 节。

### 4.4 创建任务（CreateTask）— 三个关键参数缺一不可

| 参数 | 作用 | 不加后果 |
|------|------|---------|
| `--syncing=false` | 跳过增量同步 | 80% 报 vols_map NoneType |
| `--use_public_ip=false` | 私网连接 Agent | 80% 报 exception 22 |
| `--target_server.disks.1.disk_id=<src_disk_id>` | 磁盘映射 | vols_map None |

磁盘信息来源：`hcloud SMS ShowServer` 返回的 disks。

**新建的目的端ECS 命名**：`--target_server.name={hostname}_{MMDD}`（见如下命名规则）。

**所有通过 SMS API 或修复流程创建的 ECS，命名格式：**

```
{hostname}_{MMDD}
```

| 示例 | 说明 |
|------|------|
| `server-01_0824` | server-01 在 2026-08-24 创建 |
| `server-02_0824` | server-02 在 2026-08-24创建 |

**规则：**
- `{hostname}` = Excel/JSON 中目的端主机名（如 `server-01`）
- 时间戳 = 创建时刻的 `date +%m%d`
- **辅助 ECS 也带时间戳**：`helper_{MMDD}`
- **禁止**使用 `ecs-boot-fix`、`helper-ecs` 等无时间戳名称
- 上传到 OBS 的文件名带更详细时间戳{YYYYMMDD_HHMMSS}
- SMS任务名称可以不带时间戳，用源端主机名命名任务即可

完整命令见 `references/MIGRATION_REFERENCE.md` C.4 节。

### 4.5 任务状态流转

```
READY → RUNNING → MIGRATE_FAIL / SYNCING / CUTOVER_READY
子任务：CREATE_CLOUD_SERVER → SSL_CONFIG → ATTACH_AGENT_IMAGE → FORMAT_DISK_LINUX_FILE → MIGRATE_LINUX_FILE
```

---

## 五、迁移后校验

- [ ] **源端无写操作**：对比迁移前后 df -h、数据库/日志大小、mtime
- [ ] 目的端规格一致（CPU/内存/磁盘）/ OS 版本一致 / 网络连通 / 应用启动
- [ ] **VPN/专线场景：目的端 ECS 无浮动 IP**（见 4.2 节 EIP 规则）

> 详细校验命令见 `references/MIGRATION_REFERENCE.md` D 节。

---

## 六、常见错误速查

| 错误 | 一句话修复 |
|------|-----------|
| SMS.0515 | 从 ShowServer 提取完整磁盘信息传入 CreateTask |
| SMS.0007 vpc | 重建模板（vpc.id + vpc.cidr） |
| SMS.0007 vols_map | 模板指定与源端 OS 匹配的公有镜像 |
| SMS.6562 | 模板加 publicip.type=5_bgp（**仅 EIP 场景**；VPN 场景见 4.2 节） |
| SMS.6102 | 补全 nics/security_groups 的 name/cidr |
| 源端 error | kill Agent，重启 startup.sh（重启输入序列） |

> 完整错误目录见 `references/MIGRATION_REFERENCE.md` E 节。

---

## 七、迁移后启动修复

> **MIGRATE_SUCCESS 不代表 ECS 可用。** AWS Ubuntu 迁移到华为云后通常遇到 **5 个叠加问题**：

| # | 问题 | 根因 | 不修复后果 |
|---|------|------|-----------|
| 1 | **源端使用UEFI, 华为云只支持BIOS，ECS启动不匹配** | AWS 用 UEFI，华为云 ECS 用 BIOS | ECS 完全无法启动 |
| 2 | **AWS 内核不兼容** | 源端内核（如 `vmlinuz-7.0.0-1010-aws`）在华为云虚拟硬件上不启动 | 启动到内核即 halt，无日志 |
| 3 | **网络配置残留** | netplan 配 AWS 静态 IP + 网卡名 ens5；cloud-init 用 DataSourceEc2Local | 网卡无 IP，SSH 不通 |
| 4 | **root 密码不是预期值** | 全盘迁移保留源端 `/etc/shadow`，`target_password` 被覆盖 | 无法登录 |
| 5 | **grub.d 覆盖内核参数** | `50-cloudimg-settings.cfg` 覆盖 `GRUB_CMDLINE_LINUX_DEFAULT`，`net.ifnames=0` 丢失 | 网卡名不正确 |

### 判断标志
ECS ACTIVE + ARP 有 MAC + ping 不通 + SSH 超时 → 需要修复

### 修复流程（9 步）

| 步骤 | 操作 |
|------|------|
| 1 | 停止目的端 ECS（HARD） |
| 2 | 卸载系统盘（NovaDetachVolume） |
| 3 | 创建辅助 ECS（同 VPC），命名 `helper_{MMDD}`，创建后重启一次使密码生效 |
| 4 | 挂载迁移磁盘到辅助 ECS（/dev/vdb） |
| 5 | **执行修复脚本**（见下方 9 个修复项） |
| 6 | 卸载磁盘 → 挂载回目的端 /dev/vda → 启动 ECS |
| 7 | 验证：ping + SSH + `ip addr show` |
| 8 | **如仍不通**：检查串口控制台输出，区分 GRUB 错误 vs 内核 panic |
| 9 | 确认可登录后，设置 root 密码为用户预期值 |

### 修复脚本核心（Step 5）— 9 个修复项

在辅助 ECS 上 chroot 到迁移磁盘执行：

| # | 修复项 | 具体操作 |
|---|--------|---------|
| 1 | **安装 BIOS GRUB** | 创建 bios_grub 分区 + `grub-install --target=i386-pc /dev/vdb` |
| 2 | **替换 AWS 内核** | 从辅助 ECS 复制 `vmlinuz-*generic` + `initrd.img-*generic` + `/lib/modules/*generic` 到迁移盘；更新 grub |
| 3 | **修复 netplan** | 写 `eth0: {dhcp4: true}`；加 `net.ifnames=0` 内核参数 |
| 4 | **创建 99-net-ifnames.cfg** | 在 `/etc/default/grub.d/` 创建高优先级文件，防止 `50-cloudimg-settings.cfg` 覆盖 |
| 5 | **禁用 cloud-init 网络配置** | 禁用 `DataSourceEc2Local`；设 `datasource_list: [None]` 或直接禁用 cloud-init |
| 6 | **设置 root 密码** | `echo 'root:<expected_password>' | chpasswd`（**必须用用户预期密码**） |
| 7 | **更新 grub** | `update-grub`（注意：只更新 grub.cfg，不重装 bootloader） |
| 8 | **重建 initramfs** | `update-initramfs -u -k all` |
| 9 | **启用 SSH 密码登录** | `PasswordAuthentication yes` + `PermitRootLogin yes` in sshd_config |

> 完整脚本见 `references/MIGRATION_REFERENCE.md` G 节。

### Secure Boot 注意事项

华为云 ECS 可能启用 Secure Boot（Ubuntu 24.04 镜像）。此时：
- `grub-install` 生成**无签名** EFI 二进制，Secure Boot 会拒绝 → 静默 halt
- **解决**：安装 `grub-efi-amd64-signed` 包（需 chroot 内 DNS 可用），或通过华为云控制台关闭 Secure Boot
- BIOS 模式（i386-pc）不受 Secure Boot 影响，优先使用 BIOS GRUB

### 修复项根因

| 修复项 | 不修复后果 |
|--------|-----------|
| BIOS GRUB | ECS 无法启动（UEFI 引导写入的磁盘在 BIOS ECS 上不工作） |
| 替换 AWS 内核 | ECS 启动到内核即 halt，串口无输出 |
| netplan DHCP | 网卡无 IP |
| 99-net-ifnames.cfg | `net.ifnames=0` 被 50-cloudimg 覆盖，网卡名不正确 |
| 禁用 cloud-init 网络 | cloud-init 用 AWS DataSource 覆盖 netplan |
| 设置 root 密码 | 全盘迁移保留源端密码，用户无法用预期密码登录 |
| SSH 密码登录 | 仅密钥登录可用，用户无法用密码登录 |

---

## 八、迁移完成后清理策略

> **不要删除华为云控制台上的 SMS 迁移任务和模板。**

| 资源 | 迁移完成后 |
|------|-----------|
| 辅助 ECS | 可删除 |
| **目的端 EIP（VPN/专线场景）** | **必须解绑并释放** — SMS 可能自动创建，迁移后必须清理（见 4.2 节） |
| 源端 SMS Agent | 可卸载，卸载前询问用户是否卸载.如果用户回答否，保留SMS Agent |
| **SMS 迁移任务** | **不删除** |
| **SMS 模板** | **不删除** |

---

## 九、完整迁移流程速查

```
1. 安装 SMS Agent（源端）
   └─ startup.sh：y / y / AK / SK / sms_domain / 0

2. 获取源端信息
   └─ ListServers → source_server_id
   └─ ShowServer → disk_id, disk_size, pv_uuid, pv_size

3. 创建模板（CreateTemplate）
   └─ 必填：vpc.id + cidr + nics + security_groups + image_id + publicip + is_template + target_password
   └─ target_password 全盘迁移后会被源盘覆盖，需在修复脚本中重设

4. 创建任务（CreateTask）— 三个关键参数！
   └─ --syncing=false / --use_public_ip=false / --disks.1.disk_id=<src_disk_id>
   └─ ECS 命名：{hostname}_{MMDD}

5. 启动任务（UpdateTaskStatus --operation=start）

6. 轮询状态（ShowTask）→ MIGRATE_SUCCESS

7. 如果主机无法ping通，迁移后修复（第七节）
   └─ BIOS GRUB + 替换内核 + netplan(DHCP) + 99-net-ifnames.cfg + 禁用cloud-init + 设密码 + SSH

8. 清理（第八节）
   └─ 删辅助 ECS
   └─ 不删 SMS 任务和模板
   └─ VPN/专线场景：检查并释放目的端 ECS 的 EIP（见 4.2 节）

9. 检查目的端ECS是否根据ECS命名规则进行命名，如果不是，重新根据命名规则修改目的端ECS名称

```

---

## 十、前置条件

- Python 3.6+ / hcloud CLI 已配置 AK/SK 和 region
- 迁移前检查需能访问源端网络 / 迁移后校验需能访问目的端网络
- 目的端 VPC/子网/安全组信息从 Excel 表获取
- **任何疑问必须先问用户，确认无误再创建迁移任务**

---

## 文件结构

```
sms-migration-assistant/
├── SKILL.md                          ← 本文件（流程概览 + 禁止操作 + 关键参数）
├── references/
│   └── MIGRATION_REFERENCE.md        ← 详细命令、脚本、错误目录、格式规范
├── scripts/
│   ├── pre_migration_check.py        ← 迁移前检查
│   └── post_migration_check.py       ← 迁移后校验
  
```
# Example

input: migration_hosts.json
源端主机名: server-01
源端主机内网IP: 172.196.0.134
源端系统盘大小: 8GB
源端数据盘大小: 0 (如果为0，或者没有这个输入，不需要创建额外数据盘）
端口号： 22
用户名： ubuntu
Key文件名: server-01key.pem
源端区域id: ap-southeast-1
源端区域名: Singapore
源端OS: ubuntu
网络类型: VPN
目的端主机名: server-01-{时间戳}
目的端系统盘大小: 40GB (目的端系统盘至少要和源端系统盘一样或者比它大）
目的端数据盘大小: 0
目的端区域id: ap-southeast-3
目的端VPC名: vpc-agent-84346077
目的端子网名: subnet-migration
目的端子网CIDR: 192.168.3.0/24
是否迁移至已有主机?: 否

migration template:
Name: AgentMigration
Region/Project: ap-southeast-3
Migration Method: File-level
Network: Private
Target Server: create new
Start Target Upon Launch: Yes

server template:
Template Name: AgentTemplate
Region/Project: ap-southeast-3
AZ: AZ1
Disk: General purpose SSD
VPC: vpc-agent-84346077
Subnet: subnet-migration
Security group: sg-agent-84346077
