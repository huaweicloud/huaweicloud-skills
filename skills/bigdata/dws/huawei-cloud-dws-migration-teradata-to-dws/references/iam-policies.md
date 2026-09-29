# IAM Policies - Teradata to DWS Migration

本 skill 在辅助场景下调用 DWS / OBS 只读查询接口（云服务信息确认），数据迁移本身通过数据库连接执行。所需权限如下。

## Read-only Query Permissions

| API Action | Permission | Purpose |
|------------|------------|---------|
| dws:clusters:get | View cluster details | Get cluster connection endpoint and status |
| dws:clusters:list | List clusters | Confirm cluster exists, get project_id / cluster_id |
| obs:bucket:ListAllMyBuckets | List OBS buckets | Confirm OBS bucket availability before `--method obs` |
| obs:object:ListObjects | List OBS objects | Verify exported files in OBS temp directory |

## KooCLI Corresponding Commands

| Permission | hcloud Command |
|------------|----------------|
| dws:clusters:list | `hcloud DWS ListClusters --cli-region=<region> --project_id=<pid>` |
| dws:clusters:get | `hcloud DWS ListClusterDetails --cli-region=<region> --project_id=<pid> --cluster_id=<cid>` |
| obs:bucket:ListAllMyBuckets | `hcloud obs ls` |

## Minimum Permission Policy JSON

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dws:clusters:get",
        "dws:clusters:list",
        "obs:bucket:ListAllMyBuckets",
        "obs:object:ListObjects"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## Database Account Permissions

| Database | Required Permission | Purpose |
|----------|--------------------|---------|
| Teradata（源端） | SELECT | 只读数据访问（禁止任何写操作） |
| DWS（目标端） | CREATE、INSERT、SELECT | 建表、导入数据、校验 |

> 源端 Teradata 连接必须以只读方式建立；详细禁止项见 `references/forbidden-operations.md`。

## Permission Failure Handling

1. 当任何命令因权限错误失败时，读取本文档
2. 向用户展示所需权限列表与策略 JSON
3. 引导用户在 IAM 控制台创建自定义策略并授权
4. 暂停执行，等待用户确认权限已授予

## Common Permission Errors

| Error Code | Meaning | Solution |
|------------|---------|----------|
| 403 | Insufficient permissions | Check if the IAM user has the above permissions |
| 401 | Authentication failed | Check AK/SK configuration or IAM Token validity |
| DWS.0001 | DWS API error | Check cluster status and project_id |