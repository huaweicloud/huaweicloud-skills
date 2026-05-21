# IAM权限策略 - 华为云OBS对象存储管理

本skill所需的IAM权限策略说明。

## 所需权限概览

| 操作 | IAM Action（旧版v3） | IAM Action（新版v5） | 描述 |
|------|----------------------|---------------------|------|
| 列出桶 | `obs:bucket:ListAllMyBuckets` | `obs:bucket:listAllMyBuckets` | 列出当前账号所有桶 |
| 获取桶存储信息 | `obs:bucket:GetBucketStorageInfo` | `obs:bucket:getBucketStorageInfo` | 获取桶容量和对象数 |
| 获取桶属性 | `obs:bucket:GetBucketMetadata` | `obs:bucket:getBucketMetadata` | 获取桶元数据 |
| 上传对象 | `obs:object:PutObject` | `obs:object:putObject` | 上传对象到桶 |
| 列出对象 | `obs:bucket:ListBucket` | `obs:bucket:listBucket` | 列出桶内对象 |
| 查询CES指标 | `ces:metric:get` | `ces:metric:get` | 查询CES监控指标 |

---

## 最低所需策略（JSON）

### 旧版IAM（v3接口 - 角色与策略授权）

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "obs:bucket:ListAllMyBuckets",
        "obs:bucket:GetBucketStorageInfo",
        "obs:bucket:GetBucketMetadata",
        "obs:object:PutObject",
        "obs:bucket:ListBucket",
        "ces:metric:get"
      ]
    }
  ]
}
```

### 新版IAM（v5接口 - 身份策略授权）

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "obs:bucket:listAllMyBuckets",
        "obs:bucket:getBucketStorageInfo",
        "obs:bucket:getBucketMetadata",
        "obs:object:putObject",
        "obs:bucket:listBucket",
        "ces:metric:get"
      ],
      "Resource": [
        "OBS:*:*:bucket:*",
        "CES:*:*:metric:*"
      ]
    }
  ]
}
```

---

## 资源级策略（推荐）

限制到特定桶，提高安全性：

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "obs:bucket:listAllMyBuckets",
        "obs:bucket:getBucketStorageInfo",
        "obs:bucket:getBucketMetadata",
        "obs:object:putObject",
        "obs:bucket:listBucket"
      ],
      "Resource": [
        "OBS:*:*:bucket:<BucketName>",
        "OBS:*:*:object:<BucketName>/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ces:metric:get"
      ],
      "Resource": [
        "CES:*:*:metric:*"
      ]
    }
  ]
}
```

---

## 只读策略

仅需查看桶信息和监控数据（不允许上传）：

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "obs:bucket:listAllMyBuckets",
        "obs:bucket:getBucketStorageInfo",
        "obs:bucket:getBucketMetadata",
        "obs:bucket:listBucket",
        "ces:metric:get"
      ],
      "Resource": [
        "OBS:*:*:bucket:*",
        "CES:*:*:metric:*"
      ]
    }
  ]
}
```

---

## 系统策略

可使用华为云预置的系统策略简化授权：

| 系统策略 | 包含权限 | 适用场景 |
|---------|---------|---------|
| `OBS OperateAccess` | 桶和对象读写（不含删除） | ✅ 推荐本skill使用 |
| `OBS ReadOnlyAccess` | 桶和对象只读 | 仅查看场景 |
| `OBS Administrator` | OBS全部权限 | ⚠️ 权限过大，不推荐 |
| `CES ReadOnlyAccess` | CES只读权限 | 查看监控指标 |

**推荐组合：** `OBS OperateAccess` + `CES ReadOnlyAccess`

> **⚠️ OBS OperateAccess说明**
>
> OBS OperateAccess包含桶和对象的读写权限，但**不包含删除权限**，
> 与本skill的"禁止删除"安全约束一致，推荐使用。

---

## 桶策略授权

除IAM策略外，也可通过桶策略（Bucket Policy）授权：

```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"ID": ["<IAMUserId>"]},
      "Action": [
        "obs:bucket:ListBucket",
        "obs:bucket:GetBucketStorageInfo",
        "obs:object:PutObject"
      ],
      "Resource": [
        "my-bucket",
        "my-bucket/*"
      ]
    }
  ]
}
```

---

## 策略最佳实践

1. **最小权限原则**：只授予所需最小权限，优先使用资源级策略
2. **禁止删除权限**：本skill禁止删除操作，策略中不应包含删除权限
3. **推荐OBS OperateAccess**：系统策略中OBS OperateAccess最匹配本skill需求
4. **CES数据访问**：查询监控指标需要CES ReadOnlyAccess
5. **定期审查**：定期检查IAM策略，确保无多余权限

---

## 官方文档

- [OBS IAM授权](https://support.huaweicloud.com/perms-cfg-obs/obs_40_0001.html)
- [创建IAM自定义策略](https://support.huaweicloud.com/usermanual-iam/iam_01_0605.html)
- [OBS桶策略配置](https://support.huaweicloud.com/usermanual-obs/obs_03_0123.html)
- [CES IAM授权](https://support.huaweicloud.com/api-ces/ces_03_0046.html)
