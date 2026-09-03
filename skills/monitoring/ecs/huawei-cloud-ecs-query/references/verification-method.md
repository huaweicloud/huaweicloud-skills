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

### 2. 查询实例详情

```bash
python3 scripts/ecs_query.py show-server --server-id <server_id> --config config.yaml
```

| 检查项 | 预期结果 |
|--------|----------|
| server-id 必填 | 缺失时提示"请通过 --server-id 指定服务器ID" |
| 详情展示 | 含规格/镜像/IP/可用区等完整字段 |

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