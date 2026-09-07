# Huawei CLI Output and Query

## 目标

让 `hcloud` 的返回结果：

- 稳定
- 易解析
- 易筛选
- 不把大量无关数据直接塞回对话

## 一、默认输出格式

### 推荐默认值

- 机器处理：`json`
- 人工浏览：`table`
- 管道拼值：`tsv`

如果返回结果后面还要被脚本或代码继续处理，默认强制：

```bash
--cli-output=json
```

## 二、`--cli-query`

`--cli-query` 基于 JMESPath。

典型用途：

- 只保留某些字段
- 只取前几项
- 做简单投影
- 降低结果体积

### 示例 1：只看第一条

```bash
--cli-query=items[0]
```

### 示例 2：只取部分字段

```bash
--cli-query=items[].{Name:name,Status:status}
```

### 示例 3：取数组中的某个值

```bash
--cli-query=servers[].id
```

## 三、默认输出策略

### 查询类

先这样想：

1. 用户真正要什么字段
2. 是不是只要摘要
3. 是不是只要 Top N

不要默认把整份原始 JSON 直接返回。

### 表格类

`table` 适合人工看，不适合后续再喂脚本。

如果已经选择 `table`：

- 可选 `--cli-output-num`
- 但不要把它当成后续自动处理输入

## 四、对 agent 的推荐规则

- 默认先 `json`
- 先用查询参数限制范围，再用 `--cli-query` 提炼
- 真需要表格给用户看时，再切换成 `table`
- 如果当前结果很大，优先汇总为：
  - 数量
  - 状态分布
  - 满足条件的候选项
  - Top N

## 五、高风险大输出 API

机器可读策略位于 `references/hcloud-output-policies.json`。运行 `hcloud_safe_exec.py` 时默认使用 `--output-mode=auto`，Agent 不需要先读完本文件或记住 API 名单，策略会在执行前自动命中。

当前重点保护以下类别：

- 镜像、规格和租户级列表：`IMS ListImages`、`ECS ListFlavors`、`ListFlavorSellPolicies`、`ListServersDetails`、DNS RecordSet、RMS/COC 全租户资源。
- 日志、审计和安全事件：LTS、CTS、CFW、RDS/DDS 日志以及日志/事件/history 家族。
- 时序数据：CES/AOM metric data。
- 账号明细：BSS、RMS、COC、SecMaster/HSS 列表和历史记录。
- 工作负载对象：CCI 全 namespace Pod、事件和指标，SWR tag/manifest 类列表。
- 文件和下载：CodeArts 文件/归档/diff/build log，以及数据库日志下载。

策略文件同时保留精确 operation 和家族规则：精确规则负责默认 `limit`、必需时间/范围参数和建议样本字段；家族规则负责保护以后新增但尚未逐项登记的日志、指标、账号记录和内容操作。未登记操作也受通用体积阈值保护。

### 输出模式

- `auto`：默认模式。小型普通 JSON 保持兼容；已知高风险结果直接摘要或落盘；未知 JSON 超过 12000 字符时自动摘要。
- `summary`：完整结果不进入对话，只返回顶层 key、数组路径/条数、Top N 样本、是否落盘及文件哈希。
- `file-only`：内容和下载响应只写入文件；对话不返回样本或顶层字符串值。没有指定路径时生成操作系统临时文件。
- `full`：已知高风险操作必须同时显式传入 `--allow-large-output`。Agent 默认不要使用。

无论哪种模式，成功解析 JSON 后都不会再把同一份 JSON 复制到 `stdout` 和 `parsed_json` 两个字段中。

### 推荐命令

普通查询直接使用 `auto`：

```bash
python3 scripts/hcloud_safe_exec.py \
  --service ECS \
  --operation ListFlavors \
  --arg=--cli-region=<region> \
  --arg=--project_id=<project-id> \
  --arg=--cli-output=json \
  --expect-json
```

策略会自动给 `ListFlavors` 添加默认 `limit=20`，并只向对话返回摘要。

需要完整数据做本地 join 时：

```bash
python3 scripts/hcloud_safe_exec.py \
  --service ECS \
  --operation ListFlavors \
  --arg=--cli-region=<region> \
  --arg=--project_id=<project-id> \
  --arg=--cli-output=json \
  --expect-json \
  --output-mode=file-only \
  --parsed-json-file=<parsed-json-file>
```

`--result-file` 保存完整结构化执行结果，`--parsed-json-file` 保存完整且已脱敏的 JSON 主体，`--raw-output-file` 保存完整且已脱敏的非 JSON stdout。Agent 后续也不要 `cat` 全量文件，使用 `jq`、短脚本或字段投影提取必要内容。

### 纠正和重试

如果返回 `OUTPUT_POLICY_REQUIRED`：

- 有 `corrected_command`：直接执行该安全命令。
- 有 `corrected_command_template`：把 `<required:...>` 替换成真实时间、范围或资源参数后执行。
- 不要原样重试失败命令。
- `OUTPUT_POLICY_REQUIRED` 是本地执行前门禁，不是华为云 API 故障。

建议摘要字段：

- `ListImages`：`id`、`name`、`status`、`visibility`、`__platform`、`__imagetype`、`os_version`、`min_disk`、`min_ram`、`created_at`。
- `ListFlavors`：`id`、`name`、`vcpus`、`ram`、`disk`、`os_extra_specs` 中和虚拟化、规格族、可用区相关的字段。
- `ListFlavorSellPolicies`：`flavor_id` / `flavor_name`、`availability_zone`、`sell_status`、`sell_mode`、`spot_options`、限制原因类字段。

## 六、推荐例子

### 1. 看配置项列表

```bash
hcloud configure list --cli-output=json
```

### 2. 看 ECS 规格前 20 条

```bash
hcloud ECS ListFlavors \
  --cli-region=cn-north-4 \
  --project_id=<project-id> \
  --limit=20 \
  --cli-output=json
```

### 3. 只看规格名和可用区

```bash
hcloud ECS ListFlavors \
  --cli-region=cn-north-4 \
  --project_id=<project-id> \
  --limit=20 \
  --cli-output=json \
  --cli-query=flavors[].{Name:name,AZ:os_extra_specs.ecsperformancetype}
```

上面的字段表达式只是示意，真实字段名应以当前返回体为准。

## 七、何时不要强上 `--cli-query`

以下情况不要先写复杂表达式：

- 还不知道返回体结构
- 当前 operation 帮助都拿不到
- 当前结果很可能是错误体而不是正常数据

此时先拿一版小样本原始 JSON，再决定 query。

## 八、结果落盘

当查询结果后面还要继续被脚本消费时，可以直接用包装脚本落盘：

```bash
python3 scripts/hcloud_safe_exec.py \
  --command-part=configure \
  --command-part=list \
  --arg=--cli-output=json \
  --expect-json \
  --result-file=/tmp/hcloud_safe_exec_result.json \
  --parsed-json-file=/tmp/hcloud_safe_exec_parsed.json
```

用途：

- `result-file`
  - 保存完整结构化执行结果
- `parsed-json-file`
  - 只保存解析后的 JSON 主体
