---
name: huawei-cloud-ecs-query
description: 查询华为云ECS弹性云服务器信息。仅用于查询，不包含创建/删除/规格变更等写操作。当用户需要查看华为云ECS实例列表、实例详情、实例状态时使用。支持AK/SK和Token两种认证方式，支持表格和JSON两种输出格式，支持多区域查询。触发场景：用户要求"查询云服务器列表"、"查看ECS实例详情"、"ECS运行状态"、"列出ECS"、"查看服务器状态"，或请求中带 update/修改/创建/删除 ECS 以外的只读查询意图时（如查 flavor、可用区、镜像等 ECS 属性）使用。写操作请求（创建、删除、规格变更、开机/关机）请使用其他技能。
---

# 华为云 ECS 查询技能

## 概述

本技能用于查询华为云弹性云服务器（ECS）的信息，包括：
- **查询实例列表**：列出所有ECS实例的基本信息
- **查询实例详情**：获取单个ECS实例的详细配置信息
- **查询实例状态**：查看ECS实例的运行状态

支持两种认证方式（AK/SK 签名认证 和 Token 认证），两种输出格式（表格 和 JSON），以及多区域查询。

## 前置条件

### 1. 安装 Python 依赖

```bash
pip install requests pyyaml
```

### 2. 获取认证凭证

**方式一：AK/SK 认证（推荐）**
- 登录华为云控制台 → 右上角用户名 → "我的凭证" → "访问密钥" → 新增访问密钥
- 保存 AK（Access Key ID）和 SK（Secret Access Key）
- 同时需要获取 Project ID（项目ID）：在"我的凭证"页面查看

**方式二：Token 认证**
- 需要华为云账号的用户名、密码
- 需要账号的 Domain ID（租户ID，在"我的凭证"页面查看）
- 需要Project ID

### 3. 配置文件

创建配置文件 `~/.huawei-ecs/config.yaml`（或通过 `--config` 参数指定路径）：

```yaml
# 认证方式：aksk 或 token
auth_method: aksk

# AK/SK 认证配置
ak: "your-access-key-id"
sk: "your-secret-access-key"
project_id: "your-project-id"

# Token 认证配置（当 auth_method 为 token 时使用）
# username: "your-username"
# password: "your-password"
# domain_id: "your-domain-id"

# 默认区域
region: "cn-north-4"

# 输出格式：table 或 json
output_format: "table"
```

## 工作流

当用户请求查询 ECS 信息时，按以下流程执行：

1. **识别查询类型**：确定用户需要的是实例列表（list）、实例详情（show）还是实例状态（status）
2. **确认认证配置**：检查 `~/.huawei-ecs/config.yaml` 是否存在；若缺失，提示用户先完成配置（参考"前置条件"章节）
3. **执行查询**：根据查询类型运行对应命令（参考"核心命令"章节）
   - 列表 → `list-servers`（可加 `--status`/`--name` 过滤）
   - 详情 → `show-server`
   - 状态 → `server-status`
4. **格式化输出**：默认表格输出；用户要求 JSON 时用 `--output json`
5. **处理错误**：API 请求失败时，根据错误信息提示用户检查网络、区域或权限（参考"注意事项"与 `references/troubleshooting.md`）

## 核心命令

### hcloud CLI 等价命令（推荐）

本技能脚本通过华为云 API 直连实现查询。若环境中已安装 hcloud CLI（KooCLI）并完成 `hcloud configure`，可使用以下等价命令快速查询：

```bash
# 查询实例列表
hcloud ECS ListServersDetails --cli-region=cn-north-4 --limit=25

# 查询单个实例详情
hcloud ECS ShowServer --cli-region=cn-north-4 --server_id=<server_id>

# 查询实例状态（结合 --cli-query 过滤）
hcloud ECS ListServersDetails --cli-region=cn-north-4 --status=ACTIVE
```

CLI 安装与认证方式参考 `references/cli-installation-guide.md`。

### 脚本命令

#### 查询实例列表

```bash
python scripts/ecs_query.py list-servers --config config.yaml
```

可选参数：
- `--region`：指定区域（如 cn-north-4, cn-east-3, ap-southeast-1）
- `--output`：输出格式（table 或 json）
- `--limit`：返回数量限制（默认25）
- `--offset`：页码偏移（默认1）
- `--status`：按状态过滤（ACTIVE, SHUTOFF, BUILD, ERROR 等）
- `--name`：按名称过滤
- `--flavor`：按规格ID过滤

#### 查询实例详情

```bash
python scripts/ecs_query.py show-server --server-id <server_id> --config config.yaml
```

> **获取 server_id 指引**：若不知道实例 ID，先运行 `python scripts/ecs_query.py list-servers --config config.yaml`（或 `hcloud ECS ListServersDetails --cli-region=<region>`），从结果中复制目标实例的 ID 列。

#### 查询实例状态

```bash
python scripts/ecs_query.py server-status --server-id <server_id> --config config.yaml
```

> **获取 server_id 指引**：同上，先用 `list-servers` 获取实例 ID。

## 输出说明

### 表格格式

实例列表以表格形式展示，包含以下列：
| 列名 | 说明 |
|------|------|
| ID | 服务器ID |
| Name | 服务器名称 |
| Status | 运行状态 |
| Flavor | 规格类型 |
| vCPU | 虚拟CPU核数 |
| RAM(MB) | 内存大小 |
| Private IP | 私有IP地址 |
| Public IP | 弹性公网IP |
| Created | 创建时间 |
| AZ | 可用区 |

### 状态说明

| 状态值 | 含义 |
|--------|------|
| ACTIVE | 运行中 |
| SHUTOFF | 已关机 |
| BUILD | 创建中 |
| ERROR | 故障 |
| REBOOT | 重启中 |
| HARD_REBOOT | 强制重启中 |
| MIGRATING | 迁移中 |
| RESIZE | 规格变更中 |
| VERIFY_RESIZE | 规格变更验证中 |

## API 参考

详细API接口说明请参考 `references/api-reference.md`。

## 排障

- **配置文件缺失**：按"前置条件"章节创建 `~/.huawei-ecs/config.yaml`
- **认证失败**：检查 AK/SK 或 Token 配置是否正确，账号是否具备 ECS 只读权限
- **连接失败**：检查网络是否能访问 `ecs.{region}.myhuaweicloud.com`
- 更多排障指引见 `references/troubleshooting.md`

## 注意事项

1. **安全提醒**：配置文件包含敏感凭证信息，请妥善保管，不要提交到版本控制系统
2. **网络要求**：需要能访问华为云API端点（`ecs.{region}.myhuaweicloud.com`）
3. **权限要求**：使用的账号/IAM用户需要具备 ECS 只读权限（ECS ReadOnlyAccess），详细策略见 `references/iam-policies.md`
4. **区域支持**：华为云有多个区域，常见区域包括：
   - cn-north-4（华北-北京四）
   - cn-north-1（华北-北京一）
   - cn-east-3（华东-上海一）
   - cn-south-1（华南-广州）
   - ap-southeast-1（中国-香港）
   - ap-southeast-2（亚太-新加坡）
5. **AK/SK 签名**：使用 SDK-HMAC-SHA256 签名算法，与华为云官方签名规范一致