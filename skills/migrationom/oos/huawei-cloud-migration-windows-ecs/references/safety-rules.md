# Windows迁移安全规则

## 1. 源端安全要求

### 1.1 WinRM安全配置

| 规则 | 要求 | 说明 |
|------|------|------|
| WinRM认证 | Basic或Kerberos | 禁止使用Negotiate匿名认证 |
| WinRM加密 | 生产环境使用HTTPS(5986) | 测试环境可使用HTTP(5985) |
| WinRM超时 | 连接超时30s，操作超时300s | 防止长时间挂起 |
| 最大Shell内存 | 1024MB-2048MB | 防止内存耗尽 |
| 并发Shell限制 | 最大5个并发Shell | 防止资源滥用 |

### 1.2 Windows账户安全

| 规则 | 要求 |
|------|------|
| 迁移账户 | 必须属于Administrators组 |
| 密码复杂度 | 至少8位，包含大小写字母、数字、特殊字符 |
| 密码传输 | 通过安全渠道传递，不在日志中记录 |
| UAC | 迁移期间可临时降低，迁移后恢复 |

### 1.3 防火墙规则

迁移期间需要开放的端口（迁移完成后可关闭）：

```powershell
# 仅对迁移工具IP开放（推荐）
$MigrationToolIP = "x.x.x.x"

# WinRM
netsh advfirewall firewall add rule name="WinRM-HTTP-Migration" dir=in action=allow protocol=TCP localport=5985 remoteip=$MigrationToolIP

# VSS（块级迁移需要）
netsh advfirewall firewall add rule name="VSS-Migration" dir=in action=allow protocol=TCP localport=135 remoteip=$MigrationToolIP
```

## 2. 数据安全

### 2.1 迁移数据保护

| 规则 | 要求 |
|------|------|
| 数据传输 | SMS使用HTTPS加密传输 |
| 数据校验 | 迁移后自动校验数据完整性 |
| 源端数据 | 迁移不修改源端数据（只读） |
| 增量同步 | 支持增量同步，减少数据传输量 |

### 2.2 敏感信息处理

- **禁止**在日志、配置文件、报告中记录明文密码
- **禁止**在控制台输出源端或目标ECS的完整密码
- 密码通过环境变量或加密配置文件传递
- 迁移完成后清理临时凭证文件

### 2.3 磁盘安全

| 规则 | 要求 |
|------|------|
| 源端磁盘 | 迁移前检查磁盘健康状态 |
| 目标磁盘 | 确保目标ECS磁盘容量 >= 源端已用空间 |
| VSS快照 | 块级迁移使用VSS快照，确保数据一致性 |
| 分区对齐 | 保持源端分区结构 |
| 文件系统 | 源端文件系统必须为 **NTFS**（不支持 FAT32/exFAT） |
| 磁盘类型 | 源端必须为**基本磁盘**（Basic Disk），不支持动态磁盘迁移 |
| 分区可用空间 | 分区 > 600MB → 可用 ≥ 320MB；分区 < 600MB → 可用 ≥ 40MB |
| 磁盘数量 | 源端磁盘数量 ≤ 23 块（含系统盘和数据盘） |
| RAID | 源端不能使用 RAID 磁盘阵列 |
| 加密磁盘 | 源端磁盘不能启用 BitLocker 加密 |
| 系统卷位置 | 系统卷必须位于磁盘 1 |
| GPT 分区 | GPT 分区磁盘目标容量需比源端大 1GB |
| 源端磁盘变更 | 磁盘调整后无法增量同步，需重启 Agent |
| 共享文件系统 | 源端不能使用共享文件系统 |
| ZRAM | 源端不能使用 ZRAM 压缩内存 |
| AD/多节点数据库 | 源端不能为 AD 域控或多节点数据库 |

### 2.4 资源利用率约束

| 规则 | 要求 | 说明 |
|------|------|------|
| CPU 利用率 | < 80% | 迁移时源端 CPU 利用率需低于 80% |
| 可用内存 | > 256MB | 源端可用内存需大于 256MB |
| 磁盘空间 | 系统盘剩余 ≥ 1GB | Agent 安装临时空间 |

## 3. 网络安全

### 3.1 安全组规则

**目标ECS安全组**应包含以下规则：

| 优先级 | 方向 | 协议 | 端口 | 源地址 | 说明 |
|--------|------|------|------|--------|------|
| 100 | ingress | TCP | 3389 | 管理IP | RDP远程管理 |
| 110 | ingress | TCP | 5985 | 管理IP | WinRM HTTP |
| 120 | ingress | TCP | 5986 | 管理IP | WinRM HTTPS |
| 200 | ingress | TCP | 80 | 业务来源IP/32 | HTTP（按需，禁0.0.0.0/0） |
| 210 | ingress | TCP | 443 | 业务来源IP/32 | HTTPS（按需，禁0.0.0.0/0） |
| 300 | egress | All | All | 0.0.0.0/0 | 出站流量 |

**注意**: 迁移完成后，关闭5985/5986端口，仅保留业务所需端口。

### 3.3 SMS Agent 通信端口

**源端 Windows 安全组**需放通以下端口（Agent 与 SMS 服务通信）：

| 端口 | 协议 | 用途 | 方向 |
|------|------|------|------|
| 22 | TCP | SSH（Linux Agent 管理） | ingress |
| 8899 | TCP | SMS 控制通道 | ingress |
| 8900 | TCP | SMS 数据传输通道 | ingress |
| 443 | TCP | SMS API（HTTPS） | egress |

> **注意**: Windows Agent 通过 8899（控制）和 8900（数据）端口与 SMS 服务通信。
> 源端安全组必须放通这两个端口，否则 Agent 无法注册和传输数据。

### 3.2 网络隔离

- 源端和目标ECS建议在不同网段
- 迁移工具通过公网或VPN连接源端
- 目标ECS创建在指定VPC/子网中
- 迁移完成后配置适当的网络ACL


### 3.4 安全组放通规则（最小权限，强制）

**入方向禁止 `0.0.0.0/0` / `::/0`**：引擎代码层硬拒绝（`core/target_provider.py::_FORBIDDEN_CIDRS`）；
`sg_source_cidrs` 含全网段直接配置报错；复用已有安全组时，含入向 `0.0.0.0/0` 一律拒绝。

放通 = 最小权限，四个维度缺一不可：

| 维度 | 要求 |
|------|------|
| 端口最小化 | 仅放迁移必需端口 `22,8899,8900`（`sms_task.sg_ports`），不放开全端口 |
| 来源最小化 | 仅放源端 IP/32（公网=源端公网IP/32，私网=源端内网IP/32，`sms_task.sg_source_cidrs`） |
| 方向最小化 | 仅添加入向目标规则，不触碰其他规则；出向默认放行 |
| 生命周期最小化 | 迁移完成 `release` 回收安全组/EIP；迁移端口用后即关，仅留业务端口 |

业务端口（如 RDP 3389）确需开放时：单端口 + 管理 IP/32，禁止 `0.0.0.0/0`：

```bash
hcloud VPC CreateSecurityGroupRule --direction ingress --protocol tcp \
  --port 3389 --remote-ip <管理IP>/32
```

> **WinRM 传输**：HTTP(5985) 为明文，`AllowUnencrypted=true` 仅限内网/测试环境；生产优先 HTTPS(5986)。

## 4. 操作安全

### 4.1 迁移前检查清单

- [ ] 源端Windows版本受支持（2008/2008R2/2012/2012R2/2016/2019/2022/2025/Win7/8.1/10/11 64位）
- [ ] 源端文件系统为NTFS（不支持FAT32/exFAT）
- [ ] 源端磁盘为基本磁盘（不支持动态磁盘迁移）
- [ ] 源端分区可用空间满足要求（>600MB→≥320MB；<600MB→≥40MB）
- [ ] 源端磁盘数量 ≤ 23 块
- [ ] 源端 CPU 利用率 < 80%
- [ ] 源端可用内存 > 256MB
- [ ] 源端未使用 RAID 磁盘阵列
- [ ] 源端未启用 BitLocker 加密
- [ ] 源端系统卷位于磁盘 1
- [ ] 源端未使用共享文件系统 / ZRAM
- [ ] 源端不是 AD 域控或多节点数据库
- [ ] 已根据系统版本选择正确的Agent版本（2012+→Python3 GUI；2008/7→Python2 CLI）
- [ ] WinRM已正确配置并可连接
- [ ] .NET Framework版本满足要求
- [ ] VSS服务正常运行
- [ ] 源端磁盘空间充足（至少2GB剩余）
- [ ] 源端无未完成的Windows更新
- [ ] 源端无运行中的关键服务（或已安排停机窗口）
- [ ] 目标region支持Windows镜像
- [ ] 目标VPC/子网/安全组已准备
- [ ] hcloud CLI已配置正确的AK/SK
- [ ] AK/SK具有足够的IAM权限

### 4.2 迁移中安全规则

- **禁止**在迁移过程中修改源端数据
- **禁止**在迁移过程中重启源端服务器
- **禁止**在迁移过程中修改目标ECS配置
- 监控迁移进度，发现异常及时处理
- 迁移日志实时上传到OBS备份

### 4.3 迁移后安全规则

- [ ] 验证目标ECS可正常启动
- [ ] 验证RDP可连接
- [ ] 验证数据完整性
- [ ] 修改目标ECS管理员密码
- [ ] 配置目标ECS安全组（关闭迁移端口）
- [ ] 卸载源端SMS Agent
- [ ] 清理SMS中的源端注册信息
- [ ] 更新DNS/负载均衡指向新ECS

## 5. 权限要求

### 5.1 hcloud AK/SK权限

迁移所需的最小IAM权限：

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sms:*:*",
        "ecs:servers:*",
        "ecs:serverGroups:*",
        "evs:volumes:*",
        "vpc:*:*",
        "vpc:securityGroups:*",
        "vpc:publicIps:*",
        "ims:images:list",
        "iam:projects:list"
      ],
      "Resource": "*"
    }
  ]
}
```

### 5.2 源端Windows权限

- 迁移账户必须是Administrators组成员
- 需要以下Windows权限：
  - `SeRemoteShutdownPrivilege` - 远程关机
  - `SeBackupPrivilege` - 备份文件
  - `SeRestorePrivilege` - 恢复文件
  - `SeSecurityPrivilege` - 安全日志访问

## 6. 风险控制

### 6.1 回滚方案

| 场景 | 回滚方式 |
|------|----------|
| 迁移前 | 无需回滚，源端未修改 |
| 数据同步中 | 停止任务，删除目标ECS，源端不受影响 |
| Cutover前 | 停止任务，保留目标ECS但不切换流量 |
| Cutover后 | 保留源端服务器，可回切流量到源端 |
| 验证失败 | 保留源端和目标ECS，人工排查 |

### 6.2 并发控制

- 单个源端同时只允许一个迁移任务
- 同一VPC内并发创建ECS不超过10个
- 批量迁移建议并发数不超过5
- 每个迁移任务独立超时控制

### 6.3 资源限制

| 资源 | 限制 |
|------|------|
| 单次迁移最大磁盘数 | 23 块 |
| 单块磁盘最大容量 | 无限制（Windows 块级迁移） |
| 源端最大总容量 | 无限制（Windows） |
| 最大源端服务器数 | 1000 台/租户 |
| 最大并发任务数 | 200 |
| 迁移超时时间 | 默认2小时，最大24小时 |
| Cutover超时 | 默认30分钟，最大2小时 |
| GPT 分区磁盘 | 目标容量需比源端大 1GB |
| 字符集编码 | cp437 / cp936 |
| SSH 密钥类型 | ssh-rsa / rsa-sha2-256 / rsa-sha2-512 |
