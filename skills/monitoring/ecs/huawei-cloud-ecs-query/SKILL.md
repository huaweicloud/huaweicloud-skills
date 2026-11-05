---
name: huawei-cloud-ecs-query
description: 查询华为云ECS弹性云服务器信息。仅用于查询，不包含创建/删除/规格变更等写操作。当用户需要查看华为云ECS实例列表、实例详情、实例状态时使用。支持AK/SK和Token两种认证方式，支持表格和JSON两种输出格式，支持多区域查询，支持 --detail/--full 增强输出（补全系统盘/数据盘大小类型、安全组、VPC/子网、镜像名称、密钥对、标签、EIP带宽、计费模式等运维字段）。触发条件：用户要求"查询云服务器列表"、"查看ECS实例详情"、"ECS运行状态"、"列出ECS"、"查看服务器状态"，或请求中带 update/修改/创建/删除 ECS 以外的只读查询意图时（如查 flavor、可用区、镜像等 ECS 属性）使用。写操作请求（创建、删除、规格变更、开机/关机）请使用其他技能。
---

# 华为云 ECS 查询技能

## 概述

本技能用于查询华为云弹性云服务器（ECS）的信息，包括：
- **查询实例列表**：列出所有ECS实例的基本信息
- **查询实例详情**：获取单个ECS实例的详细配置信息
- **查询实例状态**：查看ECS实例的运行状态

支持两种认证方式（AK/SK 签名认证 和 Token 认证），两种输出格式（表格 和 JSON），以及多区域查询。

`list-servers` / `show-server` 支持 `--detail` 或 `--full` 参数，可补全以下关键运维字段：

| 字段 | 说明 |
|------|------|
| 系统盘 | 大小（GB）与类型（如 GPSSD/SSD）以及挂载点 |
| 数据盘 | 数据盘列表（大小/类型/挂载点） |
| 安全组 | 实例所属安全组名称列表 |
| VPC/子网 | 实例所属 VPC ID 与子网 ID |
| 镜像名称 | 实例操作系统镜像名称（metadata.image_name） |
| 密钥对 | 实例登录密钥对名称 |
| 标签 | 实例标签列表 |
| EIP带宽 | 弹性公网 IP 及带宽大小（Mbps，来自 VPC/EIP 接口） |
| 计费模式 | 按需/包年包月/竞价（metadata.charging_mode） |

## 前置条件

### 1. 安装 Python 依赖

> **⚠️ Mandatory: every `hcloud` command in this skill MUST be wrapped with `skill-quality-cli run --skill-name huawei-cloud-ecs-query -- ` — bare `hcloud` calls are strictly forbidden.**
> Similarly, every script execution MUST be wrapped with the same `skill-quality-cli run --skill-name huawei-cloud-ecs-query -- ` prefix (e.g. `skill-quality-cli run --skill-name huawei-cloud-ecs-query -- python scripts/ecs_query.py list-servers ...`) — bare `python scripts/ecs_query.py` invocations are forbidden. Bootstrapping exception: `ensure_cli.sh` / `install_cli.sh` may be executed bare during initial setup when `skill-quality-cli` is not yet installed.

```bash
skill-quality-cli run --skill-name huawei-cloud-ecs-query -- pip install requests pyyaml
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

# 多区域查询（可选）：
# 使用 --region 切换到其他区域时，需要同时提供目标区域对应的 project_id。
# 推荐在此维护 区域 → 项目ID 映射；也可在命令行用 --project-id 临时指定。
# regions:
#   cn-north-4: "your-project-id-for-cn-north-4"
#   cn-south-1: "your-project-id-for-cn-south-1"

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
   - 需要完整运维字段时 → 追加 `--detail` 或 `--full`
4. **格式化输出**：默认表格输出；用户要求 JSON 时用 `--output json`；需要增强字段时用 `--detail`/`--full`
5. **处理错误**：API 请求失败时，根据错误信息提示用户检查网络、区域或权限（参考"注意事项"与 `references/troubleshooting.md`）

## 核心命令

### hcloud CLI 等价命令（推荐）

本技能脚本通过华为云 API 直连实现查询。若环境中已安装 hcloud CLI（KooCLI）并完成 `hcloud configure`，可使用以下等价命令快速查询：

```bash
# 查询实例列表
skill-quality-cli run --skill-name huawei-cloud-ecs-query -- hcloud ECS ListServersDetails --cli-region=cn-north-4 --limit=25

# 查询单个实例详情
skill-quality-cli run --skill-name huawei-cloud-ecs-query -- hcloud ECS ShowServer --cli-region=cn-north-4 --server_id=<server_id>

# 查询实例状态（结合 --cli-query 过滤）
skill-quality-cli run --skill-name huawei-cloud-ecs-query -- hcloud ECS ListServersDetails --cli-region=cn-north-4 --status=ACTIVE
```

CLI 安装与认证方式参考 `references/cli-installation-guide.md`。

### 脚本命令

#### 查询实例列表

```bash
skill-quality-cli run --skill-name huawei-cloud-ecs-query -- python scripts/ecs_query.py list-servers --config config.yaml
```

可选参数：
- `--region`：指定区域（如 cn-north-4, cn-east-3, ap-southeast-1）。**跨区域查询时**，该区域对应的 `project_id` 需在 config.yaml 的 `regions` 映射中配置，或使用 `--project-id` 参数指定，否则 `--region` 仅切换 API 域名、`project_id` 仍指向原区域，会报 `Common.0018` 错误
- `--project-id`：指定目标区域的项目ID（多区域查询时与 `--region` 配套使用）
- `--output`：输出格式（table 或 json）
- `--limit`：返回数量限制（默认25）
- `--offset`：页码偏移（默认1）
- `--status`：按状态过滤（ACTIVE, SHUTOFF, BUILD, ERROR 等）
- `--name`：按名称过滤
- `--flavor`：按规格ID过滤
- `--detail` / `--full`：展示完整运维字段（系统盘/数据盘大小类型、安全组、VPC/子网、镜像名称、密钥对、标签、EIP带宽、计费模式）。两者等价，`--full` 是 `--detail` 的别名

```bash
# 查询实例列表（完整运维字段）
skill-quality-cli run --skill-name huawei-cloud-ecs-query -- python scripts/ecs_query.py list-servers --detail --config config.yaml
```

> **增强字段说明**：系统盘/数据盘大小与类型来自 EVS `ListVolumes` 接口、EIP带宽来自 VPC/EIP `ListPublicips/v3` 接口。当查询账号未授予 EVS/VPC 只读权限时，这些列自动降级为仅展示挂载盘设备名与公网 IP 地址，不影响其余字段与整体查询。

#### 查询实例详情

```bash
python scripts/ecs_query.py show-server --server-id <server_id> --config config.yaml
```

```bash
# 查询实例详情（完整运维字段）
skill-quality-cli run --skill-name huawei-cloud-ecs-query -- python scripts/ecs_query.py show-server --server-id <server_id> --full --config config.yaml
```

> **获取 server_id 指引**：表格输出中 ID 列会被截断（仅显示前 8 位），复制完整 ID 请使用 `python scripts/ecs_query.py list-servers --output json --config config.yaml`，从 JSON 输出的 `servers[].id` 字段获取完整 server_id（或 `hcloud ECS ListServersDetails --cli-region=<region>`）。
>
> **增强字段说明**：`--detail`/`--full` 模式下 `show-server` 额外展示系统盘/数据盘的大小与类型（EVS 接口）以及 EIP 带宽（VPC/EIP 接口）；未启用 `--detail`/`--full` 时，详情仍展示安全组/VPC/子网/镜像名称/密钥对/计费模式等 ECS 直接返回字段。

#### 查询实例状态

```bash
python scripts/ecs_query.py server-status --server-id <server_id> --config config.yaml
```

> **获取 server_id 指引**：同上，使用 `list-servers --output json` 获取完整 ID。

## Parameter Confirmation

| 参数 | 必需 | 说明 | 示例 |
|------|------|------|------|
| config | 否 | 配置文件路径（默认 `~/.huawei-ecs/config.yaml`） | `--config config.yaml` |
| region | 否 | 目标区域（默认取配置文件 `region`） | `--region cn-south-1` |
| project-id | 否 | 目标区域对应的项目ID（多区域查询时与 `--region` 配套） | `--project-id <cn-south-1项目ID>` |
| output | 否 | 输出格式（table / json，默认 table） | `--output json` |
| limit | 否 | list-servers 返回数量限制（默认25） | `--limit 50` |
| offset | 否 | list-servers 页码偏移（默认1） | `--offset 2` |
| status | 否 | list-servers 按状态过滤 | `--status ACTIVE` |
| name | 否 | list-servers 按名称过滤 | `--name web-01` |
| flavor | 否 | list-servers 按规格ID过滤 | `--flavor s3.small.1` |
| detail | 否 | list-servers/show-server 展示完整运维字段 | `--detail` |
| full | 否 | list-servers/show-server 展示完整运维字段（--detail 别名） | `--full` |
| server-id | 是（show-server/server-status） | 云服务器ID（先用 `list-servers --output json` 获取） | `--server-id <server_id>` |

## KooCLI Command Format Standard

当使用 hcloud CLI（KooCLI）等价命令时，遵循标准格式：

```
hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]
```

- Service 名称使用大写开头（如 `ECS`），Operation 使用 PascalCase（如 `ListServersDetails`、`ShowServer`）
- 所有命令必须携带 `--cli-region=<region>` 区域参数
- hcloud CLI 底层使用 `--cli-region` 指定区域，与脚本的 `--region` 参数含义一致

## 输出说明

### 表格格式

实例列表默认以简洁表格形式展示，包含以下列：
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

使用 `--detail`（或 `--full`）后，表格额外追加以下列：
| 列名 | 说明 |
|------|------|
| System Disk | 系统盘大小/类型/挂载点（EVS 接口补全） |
| Data Disks | 数据盘列表（大小/类型/挂载点，EVS 接口补全） |
| Security Group | 安全组名称 |
| VPC/Subnet | VPC ID / 子网 ID（截断显示） |
| Image | 镜像名称（metadata.image_name） |
| KeyPair | 密钥对名称 |
| Tags | 实例标签 |
| EIP(BW) | 公网 IP 及带宽大小（Mbps，VPC/EIP 接口补全） |
| Billing | 计费模式（按需/包年包月/竞价） |

> **注意**：表格模式下 ID 列会截断显示（仅前 8 位），如需完整 ID（如用作 `--server-id`），请使用 `--output json` 输出。

### 详情输出

`show-server` 详情默认展示核心配置字段及 ECS 接口直返的运维字段（系统盘/数据盘挂载点、安全组、VPC/子网、镜像名称、密钥对、计费模式、标签），若 API 返回挂载的云硬盘信息（`os-extended-volumes:volumes_attached`），会一并展示“挂载云硬盘”（设备名 + 云硬盘ID）。使用 `--detail`/`--full` 时，额外补全系统盘/数据盘的大小与类型（EVS 接口）及 EIP 带宽（VPC/EIP 接口，含带宽大小 Mbps）。查看云硬盘的性能等更详细信息，请使用云硬盘（EVS）相关技能。

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

## Reference Documents

- `references/api-reference.md` — ECS API 接口与字段说明、认证流程
- `references/cli-installation-guide.md` — Python 环境与 hcloud CLI 安装、认证配置
- `references/iam-policies.md` — 所需 IAM 权限策略
- `references/troubleshooting.md` — 常见错误与排障指引
- `references/acceptance-criteria.md` — 验收标准
- `references/verification-method.md` — 各查询操作验证方法

## 排障

- **配置文件缺失**：按"前置条件"章节创建 `~/.huawei-ecs/config.yaml`
- **认证失败**：`错误: 认证失败 (HTTP xxx)…`，检查 AK/SK 或 Token 配置是否正确，账号是否具备 ECS 只读权限
- **跨区域查询失败（Common.0018）**：`--region` 切换区域时 `project_id` 也必须指向目标区域；请在 config.yaml 的 `regions` 映射中配置，或使用 `--project-id` 指定
- **连接失败**：检查网络是否能访问 `ecs.{region}.myhuaweicloud.com`；`--detail`/`--full` 模式还会访问 `evs.{region}.myhuaweicloud.com` 与 `vpc.{region}.myhuaweicloud.com`
- **使用 --detail 时系统盘/数据盘/EIP带宽显示为空**：账号缺少 EVS 或 VPC 只读权限，或增强接口调用失败；相关列已自动降级为挂载盘设备名/公网IP地址，可忽略
- 更多排障指引见 `references/troubleshooting.md`

## 注意事项

1. **安全提醒**：配置文件包含敏感凭证信息，请妥善保管，不要提交到版本控制系统
2. **网络要求**：需要能访问华为云API端点（`ecs.{region}.myhuaweicloud.com`）
3. **权限要求**：使用的账号/IAM用户需要具备 ECS 只读权限（ECS ReadOnlyAccess），详细策略见 `references/iam-policies.md`；使用 `--detail`/`--full` 补全系统盘/数据盘大小类型与 EIP 带宽时，还需具备 EVS（EVS ReadOnlyAccess）与 VPC（VPC ReadOnlyAccess）只读权限，未授权时相关字段自动降级展示且不影响查询
4. **区域支持**：华为云有多个区域，常见区域包括：
   - cn-north-4（华北-北京四）
   - cn-north-1（华北-北京一）
   - cn-east-3（华东-上海一）
   - cn-south-1（华南-广州）
   - ap-southeast-1（中国-香港）
   - ap-southeast-2（亚太-新加坡）
5. **AK/SK 签名**：使用 SDK-HMAC-SHA256 签名算法，与华为云官方签名规范一致
6. **敏感凭据安全声明**：本技能仅支持 ECS 实例信息**只读**查询，**不支持查看/重置云服务器登录密码、密钥对等敏感凭据**，相关操作请在华为云控制台完成
7. **费用/配额边界声明**：本技能仅支持 ECS 实例信息**只读**查询，**不支持账单/费用/配额等 BSS（费用中心）类查询**，相关查询请使用费用中心或 BSS 类技能
8. **磁盘信息边界**：默认模式下 `show-server` 详情展示 API 返回的挂载云硬盘 ID/设备名；`--detail`/`--full` 模式通过 EVS `ListVolumes` 接口补全系统盘/数据盘的大小与类型。查询云硬盘的性能、加密等扩展信息请使用云硬盘（EVS）相关技能
9. **写操作统一拒绝**：对于创建、删除、启停（开机/关机）、规格变更、迁移、重装系统等 ECS **写操作**请求，本技能**统一拒绝**，并使用统一话术引导用户：
   > “抱歉，本技能仅支持 ECS 实例信息只读查询，不支持该写操作。请在华为云控制台完成，或使用对应的 ECS 管理类技能。”