# Verification Method — huawei-cloud-ecs-query

各查询操作的验证方法。

## 环境准备

| 检查项 | 方法 |
|--------|------|
| Python 依赖 | `python3 -c "import requests, yaml; print('OK')"` 返回 OK |
| 配置文件 | `~/.huawei-ecs/config.yaml` 存在且含有效 AK/SK（或 token 配置） |
| 网络连通 | `curl -sI https://ecs.cn-north-4.myhuaweicloud.com` 返回 200/302 |

## 查询操作验证

### 1. 查询实例列表

```bash
python3 scripts/ecs_query.py list-servers --config config.yaml
```

| 检查项 | 预期结果 |
|--------|----------|
| 命令退出码 | 0 |
| 表格输出 | 含 ID/Name/Status/Flavor/vCPU 等列 |
| JSON 输出 | `--output json` 返回合法 JSON |

```bash
python3 scripts/ecs_query.py list-servers --detail --config config.yaml
```

| 检查项 | 预期结果 |
|--------|----------|
| 增强表格 | 含 System Disk / Data Disks / Security Group / VPC/Subnet / Image / KeyPair / Tags / EIP(BW) / Billing 列 |
| 系统盘列 | 显示大小（GB）与类型（如 80G (GPSSD)） |
| EIP(BW) 列 | 显示公网 IP 及带宽（Mbps） |
| Billing 列 | 按需计费 / 包年包月 / 竞价计费 |
| 降级场景 | 账号无 EVS/VPC 权限时，相关列显示挂载盘设备名/公网 IP，命令仍正常退出 |

### 2. 查询实例详情

```bash
python3 scripts/ecs_query.py show-server --server-id <server_id> --config config.yaml
```

| 检查项 | 预期结果 |
|--------|----------|
| server-id 必填 | 缺失时提示"请通过 --server-id 指定服务器ID" |
| 详情展示 | 含规格/镜像/IP/可用区等完整字段 |
| 默认字段 | 含安全组/VPC ID/子网 ID/镜像名称/密钥对/计费模式 |

```bash
python3 scripts/ecs_query.py show-server --server-id <server_id> --full --config config.yaml
```

| 检查项 | 预期结果 |
|--------|----------|
| 系统盘行 | 显示大小/类型/挂载点（如 80G (GPSSD) @/dev/vda） |
| 数据盘行 | 显示数据盘大小/类型列表（无数据盘时显示"无"） |
| EIP带宽行 | 显示公网 IP 与带宽（如 1.2.3.4 (10Mbps)） |

### 3. 查询实例状态

```bash
python3 scripts/ecs_query.py server-status --server-id <server_id> --config config.yaml
```

| 检查项 | 预期结果 |
|--------|----------|
| 状态列 | 显示 status 及中文说明（如 ACTIVE（运行中）） |
| 附加字段 | VM状态/电源状态/可用区/更新时间 |

### 4. hcloud CLI 等价命令（若已安装）

```bash
hcloud ECS ListServersDetails --cli-region=cn-north-4 --limit=5
```

| 检查项 | 预期结果 |
|--------|----------|
| 返回结构 | JSON 含 `servers` 数组 |
| 退出码 | 0 |

## 错误码对照

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| HTTP 401/403 | AK/SK 无效或权限不足 | 检查认证配置与 `ECS ReadOnlyAccess` 授权 |
| 连接超时 | 网络无法访问 ECS 端点 | 检查网络与 region 配置 |
| 配置文件缺失 | 未创建 config.yaml | 按 SKILL.md 前置条件创建 |