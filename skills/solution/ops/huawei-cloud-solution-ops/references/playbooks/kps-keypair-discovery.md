# KPS Keypair Discovery Playbook

## 目标

在 ECS 创建或 SSH 登录场景里，先确认密钥对 discovery 路径。

## 适用场景

- 创建 ECS 前确认 keypair
- 用户要求复用现有 SSH keypair
- 用户想排查实例登录方式

## 当前环境约束

当前机器已经验证到：

- `KPS` 在服务目录里存在
- 当前机器没有 `KPS` 的本地 template cache
- service help fallback 仍然受 `APIE_ERROR` 限制

因此：

- 当前 playbook 主要负责方法论和风险约束
- 不应伪装成已经稳定掌握了全部 KPS operation 参数

## 标准步骤

### 1. 上下文确认

```bash
python3 scripts/hcloud_context_inspect.py --pretty
```

### 2. KPS cache discovery

```bash
python3 scripts/hcloud_meta_lookup.py --service=KPS --allow-help-fallback --pretty
```

### 3. 在 ECS readiness 中回答的问题

- 是否已有可复用 keypair
- keypair 是不是在目标 region 内
- 用户是想走密码登录还是密钥登录

## 当前建议

如果当前环境下还拿不到 KPS operation 细节：

- 不要直接生成真实 keypair 创建命令
- 先把 ECS 创建模板中的 `key_name` 留为占位
- 在交付里明确指出“需要在可用元数据或现网确认后替换”
