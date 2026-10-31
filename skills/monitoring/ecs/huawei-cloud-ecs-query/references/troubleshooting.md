# Troubleshooting — huawei-cloud-ecs-query

常见问题与解决方案。

## 配置/认证类

### 配置文件不存在

**现象**：`错误: 配置文件不存在: ~/.huawei-ecs/config.yaml`

**解决**：按 SKILL.md「前置条件」章节创建配置文件，或使用 `--config <path>` 指定路径。

### 认证失败（401/403）

**现象**：`错误: 认证失败 (HTTP 401)…`（Token 认证获取 Token / AK/SK 鉴权时），或 `API 请求失败 (HTTP 403)`

**解决**：
1. 检查 `config.yaml` 中 AK/SK 是否正确（AK/SK 认证）
2. 检查 Token 认证的用户名/密码/Domain ID 是否正确
3. 确认账号具备 `ECS ReadOnlyAccess` 权限（见 `references/iam-policies.md`）

### 跨区域查询失败（Common.0018）

**现象**：使用 `--region cn-south-1` 切换区域时返回 `Common.0018: tenantId in token is not the same with in URL`

**原因**：`--region` 仅切换了 API 端点域名，`project_id` 仍指向配置中的原区域，导致 token 归属项目与 URL 路径项目不一致。

**解决**：
1. 在 `config.yaml` 的 `regions` 映射中配置目标区域对应的 `project_id`，例如：
   ```yaml
   regions:
     cn-south-1: "<cn-south-1 项目ID>"
   ```
2. 或使用命令行参数临时指定：`python scripts/ecs_query.py list-servers --region cn-south-1 --project-id <目标区域项目ID>`

### 提示需要 project_id

**现象**：`需要提供 project_id 配置`

**解决**：在华为云控制台「我的凭证」页面获取 Project ID，填入 `config.yaml` 或命令行参数。

## 网络类

### 连接超时/无法连接

**现象**：`错误: 无法连接到华为云 API 端点: ecs.cn-north-4.myhuaweicloud.com`

**解决**：
1. 检查网络能否访问公网（`curl -sI https://ecs.cn-north-4.myhuaweicloud.com`）
2. 检查 `region` 配置是否正确（如 cn-north-4 对应华北-北京四）
3. 若在内网/沙箱环境，确认有外网代理或已放通对应域名

## 查询类

### 查询结果为空

**现象**：`没有找到符合条件的云服务器实例。`

**解决**：
- 确认区域（region）内是否存在 ECS 实例
- 检查 `--status` / `--name` 过滤条件是否过严
- 确认账号的项目（project_id）与实例所在项目一致

### show-server 缺参数报错

**现象**：`错误: 请通过 --server-id 指定服务器ID`

**解决**：执行 `show-server` 时带上 `--server-id <实例ID>`。表格输出中 ID 列已截断（仅前 8 位），请使用 `list-servers --output json` 获取完整实例 ID。