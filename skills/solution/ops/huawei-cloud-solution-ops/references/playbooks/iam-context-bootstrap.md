# IAM Context Bootstrap

## 目标

在真正执行华为云业务命令前，先把当前 CLI 上下文讲清楚。

这个 playbook 的目标不是立即调用某个 IAM API，而是先明确：

- 当前 profile
- 当前认证模式
- 当前 region
- 当前 project / domain 是否显式配置
- 当前是否具备继续执行条件

## 标准步骤

### 1. 先做上下文探查

```bash
python3 scripts/hcloud_context_inspect.py --pretty
```

读取重点：

- `current_profile_name`
- `profiles`
- `config.offline`
- `meta_repo`

### 2. 再看当前默认配置

```bash
hcloud configure show
```

如果需要更完整地看 profile 列表：

```bash
hcloud configure list --cli-output=json
```

## 默认判断规则

### 可以继续推进的情况

- 当前 profile 存在
- region 明确
- 当前任务只是查询类

### 需要补信息的情况

- region 缺失
- 任务需要 `project_id`，但当前 profile 中未显式配置
- 任务是全局服务，但 `domain_id` 也不明确

## 关于 IAM service 本身

如果当前环境能正常拿到 service 帮助，可以进一步运行：

```bash
hcloud IAM --help
```

用途：

- 确认当前 CLI 中 IAM service 是否可用
- 确认后续是否能走 IAM service 做补充发现

但当前 skill 的第一原则仍然是：

- 先讲清 CLI 上下文
- 再决定是否需要真实 IAM API

## 推荐输出

完成本 playbook 后，建议至少输出：

- 当前使用的 profile
- 当前使用的 region
- 当前是否显式配置了 project / domain
- 当前是否需要用户补 scope 信息

## 不要做的事

- 不要一上来就追问 AK/SK
- 不要在 profile 已经可用时忽略它
- 不要在上下文不明时直接开始高风险变更
