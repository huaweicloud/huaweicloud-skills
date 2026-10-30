# CLI命令参考

## 1. hcloud SMS 命令

### 1.1 源端管理

```bash
# 注册源端（Windows）
hcloud SMS CreateServer --name "my-win-server" --ip 10.0.0.1 --os-type WINDOWS \
    --region-id cn-north-4 --project-id <project_id>

# 查看源端列表
hcloud SMS ListServers --state ONLINE

# 查看源端详情
hcloud SMS ShowServer --id <server_id>

# 刷新源端磁盘信息
hcloud SMS PutDiskInfo --server-id <server_id>

# 删除源端注册
hcloud SMS DeleteServer --id <server_id>
```

### 1.2 迁移任务

```bash
# 创建迁移任务（Windows使用MIGRATE_BLOCK）
hcloud SMS CreateTask --server-id <server_id> --name "win-migration" \
    --type MIGRATE_BLOCK --region-id cn-north-4 --project-id <project_id> \
    --auto-start true

# 查看任务列表
hcloud SMS ListTasks --state MIGRATING

# 查看任务详情
hcloud SMS ShowTask --id <task_id>

# 查看任务进度
hcloud SMS ShowTaskProgress --id <task_id>

# 启动任务
hcloud SMS StartTask --id <task_id>

# 停止任务
hcloud SMS StopTask --id <task_id>

# 暂停任务
hcloud SMS PauseTask --id <task_id>

# 恢复任务
hcloud SMS ResumeTask --id <task_id>

# 执行Cutover
hcloud SMS CutOverTask --id <task_id>

# 删除任务
hcloud SMS DeleteTask --id <task_id>

# 查看任务状态
hcloud SMS ShowTaskStatus --id <task_id>
```

### 1.3 源端模板

```bash
# 创建源端模板
hcloud SMS CreateTemplate --name "win-template" --os-type WINDOWS

# 查看模板列表
hcloud SMS ListTemplates
```

## 2. hcloud ECS 命令

```bash
# 创建ECS（Windows）
hcloud ECS CreateServer --name "my-ecs" --flavor s6.large.2 \
    --image-id <windows_image_id> --vpc-id <vpc_id> --subnet-id <subnet_id> \
    --security-group-id <sg_id> --admin-pass '<密码>' \
    --public-ip eip

# 查看ECS列表
hcloud ECS ListServers

# 查看ECS详情
hcloud ECS ShowServer --id <server_id>

# 查看ECS规格
hcloud ECS ListFlavors --availability-zone cn-north-4a

# 停止ECS
hcloud ECS StopServer --id <server_id>

# 启动ECS
hcloud ECS StartServer --id <server_id>

# 删除ECS
hcloud ECS DeleteServer --id <server_id>
```

## 3. hcloud IMS 命令

```bash
# 查看公共Windows镜像
hcloud IMS ListImages --imagetype gold --os-type Windows

# 查看镜像详情
hcloud IMS ShowImage --id <image_id>
```

## 4. hcloud VPC 命令

```bash
# 创建VPC
hcloud VPC CreateVpc --name "migration-vpc" --cidr 192.168.0.0/16

# 创建子网
hcloud VPC CreateSubnet --vpc-id <vpc_id> --name "migration-subnet" \
    --cidr 192.168.0.0/24 --gateway-ip 192.168.0.1

# 创建安全组
hcloud VPC CreateSecurityGroup --name "migration-sg" --vpc-id <vpc_id>

# 添加安全组规则
hcloud VPC CreateSecurityGroupRule --security-group-id <sg_id> \
    --direction ingress --protocol tcp --port 3389 --remote-ip <管理IP>/32

# 创建EIP
hcloud EIP CreatePublicip --bandwidth-size 5 --bandwidth-name "migration-eip"
```

## 5. WinRM 常用命令（在源端Windows执行）

```powershell
# 检查WinRM配置
winrm get winrm/config

# 检查监听器
winrm enumerate winrm/config/listener

# 测试WinRM连接
Test-WSMan -ComputerName localhost -Port 5985

# 查看服务状态
Get-Service WinRM

# 查看SMS Agent服务
Get-Service SMSAgentService

# 查看VSS状态
Get-Service VSS
vssadmin list writers

# 查看磁盘信息
Get-Disk
Get-Volume
Get-PSDrive

# 查看系统信息
systeminfo
Get-ComputerInfo
```

## 6. 迁移引擎脚本命令（当前入口）

引擎真实入口为 `scripts/windows_migration/` 下的 Python 脚本（详见 `scripts/windows_migration/README.md`）：

```bash
cd scripts/windows_migration/

# 迁移前置检查（环境变量是否齐备）
python3 preflight_check.py --scenario public

# Phase A：部署 Agent 并注册源端（自动含源端清理；单台/批量）
python3 unified_migrate.py --scenario public --config config/migrate.yaml
python3 unified_migrate.py --scenario private --batch env --workers 10

# Phase B：SMS 控制面（目标编排→建任务→同步→割接→回收）
python3 sms_task.py discover --config config/migrate.yaml
python3 sms_task.py prepare-target --config config/migrate.yaml
python3 sms_task.py create --yes && python3 sms_task.py start --yes
python3 sms_task.py wait --config config/migrate.yaml        # 轮询至 SUCCESS
python3 sms_task.py sync --yes && python3 sms_task.py cutover --yes
python3 sms_task.py cleanup --yes && python3 sms_task.py release --resource-type <eip|sg> --resource-id <id> --yes

# 环境清理（源端+代理）与 Agent 恢复
python3 cleanup_environment.py --config config/migrate.yaml --yes
python3 agent_recover.py --scenario public --config config/migrate.yaml
```

退出码与引擎一致：`0`=成功 `1`=失败 `2`=配置错误 `130`=中断。变更类操作默认交互确认（`--yes` 跳过）。
