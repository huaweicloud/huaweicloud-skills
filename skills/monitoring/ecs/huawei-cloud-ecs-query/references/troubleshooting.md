# Troubleshooting — huawei-cloud-ecs-query

常见问题与解决方案。

## 配置/认证类

### 配置文件不存在

**现象**：`错误: 配置文件不存在: ~/.huawei-ecs/config.yaml`

**解决**：按 SKILL.md「前置条件」章节创建配置文件，或使用 `--config <path>` 指定路径。

### 认证失败（401/403）

**现象**：`API 请求失败 (HTTP 401)` 或 403

**解决**：
1. 检查 `config.yaml` 中 AK/SK 是否正确（AK/SK 认证）
2. 检查 Token 认证的用户名/密码/Domain ID 是否正确
3. 确认账号具备 `ECS ReadOnlyAccess` 权限（见 `references/iam-policies.md`）

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

**解决**：执行 `show-server` 时带上 `--server-id <实例ID>`，实例 ID 可通过 `list-servers` 获得。