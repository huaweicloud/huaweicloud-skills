# 华为云 ECS API 参考文档

## API 端点

```
https://ecs.{region}.myhuaweicloud.com
```

## 认证方式

### 1. AK/SK 签名认证

使用 SDK-HMAC-SHA256 签名算法：

**请求头：**
```
Content-Type: application/json
X-Sdk-Date: {YYYYMMDDTHHMMSSZ}
host: ecs.{region}.myhuaweicloud.com
Authorization: SDK-HMAC-SHA256 Access={AK}, SignedHeaders=content-type;host;x-sdk-date, Signature={signature}
```

**签名计算步骤：**
1. 构建 Canonical Request
2. 对 Canonical Request 计算 SHA256 哈希
3. 构建 String to Sign: `SDK-HMAC-SHA256\n{date}\n{hash}`
4. 使用 SK 作为密钥，对 String to Sign 计算 HMAC-SHA256
5. 将结果作为 Signature

### 2. Token 认证

通过 IAM 获取 Token：

```
POST https://iam.{region}.myhuaweicloud.com/v3/auth/tokens
```

**请求体：**
```json
{
  "auth": {
    "identity": {
      "methods": ["password"],
      "password": {
        "user": {
          "name": "username",
          "password": "password",
          "domain": {"name": "domain_id"}
        }
      }
    },
    "scope": {
      "project": {"id": "project_id"}
    }
  }
}
```

**Token 从响应头 `X-Subject-Token` 获取，有效期 24 小时。**

**使用 Token 的请求头：**
```
X-Auth-Token: {token}
```

## API 接口

### 1. 查询云服务器详情列表

```
GET /v1/{project_id}/cloudservers/detail
```

**路径参数：**
| 参数 | 类型 | 必选 | 说明 |
|------|------|------|------|
| project_id | String | 是 | 项目ID |

**查询参数：**
| 参数 | 类型 | 必选 | 说明 |
|------|------|------|------|
| limit | Integer | 否 | 查询返回ECS数量限制（默认25，最大1000） |
| offset | Integer | 否 | 查询偏移量（默认1） |
| status | String | 否 | 按状态过滤 |
| name | String | 否 | 按名称过滤 |
| flavor | String | 否 | 按规格ID过滤 |

**响应参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| servers | Array | 云服务器详情列表 |
| count | Integer | 云服务器总数 |

### 2. 查询云服务器详情

```
GET /v1/{project_id}/cloudservers/{server_id}
```

**路径参数：**
| 参数 | 类型 | 必选 | 说明 |
|------|------|------|------|
| project_id | String | 是 | 项目ID |
| server_id | String | 是 | 云服务器ID |

**响应参数：**
返回单个云服务器的详细信息。

### 3. 服务器字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String | 服务器唯一标识 |
| name | String | 服务器名称 |
| status | String | 服务器状态 |
| addresses | Object | 网络地址信息 |
| flavor | Object | 规格信息（vcpus, ram, disk, name） |
| image | Object | 镜像信息 |
| created | String | 创建时间 |
| updated | String | 更新时间 |
| tenant_id | String | 租户ID |
| user_id | String | 用户ID |
| metadata | Object | 元数据（os_type, charging_mode, image_name, vpc_id等） |
| security_groups | Array | 安全组列表（name / id） |
| key_name | String | 密钥对名称 |
| tags | Array | 实例标签列表 |
| network_interfaces | Array | 网卡信息（含 subnet_id、association.public_ip_address） |
| locked | Boolean | 是否锁定 |
| OS-EXT-AZ:availability_zone | String | 可用区 |
| OS-EXT-STS:vm_state | String | 虚拟机状态 |
| OS-EXT-STS:power_state | Integer | 电源状态 |
| OS-EXT-STS:task_state | String | 任务状态 |
| enterprise_project_id | String | 企业项目ID |
| os-extended-volumes:volumes_attached | Array | 挂载的云硬盘附件列表（id / device / bootIndex） |

**metadata 关键字段：**

| metadata 字段 | 说明 |
|------|------|
| charging_mode | 计费模式："0"=按需计费、"1"=包年/包月、"2"=竞价计费 |
| image_name | 操作系统镜像名称 |
| os_type | 操作系统类型（Linux/Windows） |
| vpc_id | 所属虚拟私有云 VPC ID |

### 4. 增强查询接口（--detail/--full）

`list-servers` / `show-server` 使用 `--detail` 或 `--full` 时，脚本会额外调用以下只读接口补全运维字段：

**EVS 查询云硬盘详情列表**（补全系统盘/数据盘大小与类型）：

```
GET https://evs.{region}.myhuaweicloud.com/v2/{project_id}/cloudvolumes/detail?limit=1000&offset=...
```

| 响应字段 | 说明 |
|------|------|
| volumes[].id | 云硬盘ID |
| volumes[].size | 云硬盘大小（GB） |
| volumes[].volume_type | 云硬盘类型（GPSSD/SSD/SAS等） |

**VPC/EIP 查询弹性公网IP列表（v3）**（补全 EIP 带宽）：

```
GET https://vpc.{region}.myhuaweicloud.com/v3/{project_id}/eip/publicips?limit=100&offset=...
```

| 响应字段 | 说明 |
|------|------|
| publicips[].public_ip_address | 弹性公网IP地址 |
| publicips[].bandwidth.size | 带宽大小（Mbps） |
| publicips[].bandwidth.share_type | 带宽类型（PER/WHOLE） |

> **降级策略**：上述增强接口调用失败（如账号未授予 EVS/VPC 只读权限）时，脚本自动降级为仅展示 ECS 接口直返的挂载盘设备名与公网 IP 地址，不影响核心查询功能。

### 5. 多区域查询

`/v1/{project_id}/cloudservers/detail` 路径中的 `project_id` 必须与目标区域一致。使用 `--region` 切换区域时，需在 `config.yaml` 的 `regions` 映射中配置目标区域 `project_id`，或使用 `--project-id` 参数指定。

## 服务器状态值

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
| PAUSED | 暂停 |
| SUSPENDED | 挂起 |
| DELETED | 已删除 |

## 权限要求

使用此技能需要以下权限之一：
- ECS FullAccess（完全访问权限）
- ECS ReadOnlyAccess（只读权限，推荐）

## 参考链接

- [华为云 ECS API 参考](https://support.huaweicloud.com/api-ecs/)
- [API 签名指南](https://support.huaweicloud.com/devg-apisign/api-sign-provide01.html)
- [获取 AK/SK](https://support.huaweicloud.com/usermanual-iam/iam_02_0003.html)
