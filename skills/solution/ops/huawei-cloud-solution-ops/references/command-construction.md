# Huawei CLI Command Construction

## 目标

把 `hcloud` 命令构造成：

- 可发现
- 可复现
- 可审查
- 可在大结果和复杂 body 下稳定工作

## 一、先发现 service 和 operation

### 0. 本地 meta cache 发现

```bash
python3 scripts/hcloud_meta_lookup.py --service=ECS --pretty
```

用途：

- 优先看本地有没有 operation 摘要和 detail cache
- 降低对 live help 的依赖

### 1. service 发现

```bash
hcloud --help
```

用途：

- 确认当前 CLI 支持哪些服务

### 2. operation 发现

```bash
hcloud <service> --help
```

用途：

- 确认当前 service 下有哪些 operation

### 3. 参数发现

```bash
hcloud <service> <operation> --help
```

用途：

- 确认参数列表和位置

注意：

- 这一步可能依赖 live metadata
- 如果失败，不要直接瞎猜参数

### 4. 多 API 版本选择

同一个 operation 可能同时提供 V2、V3，且各版本参数并不相同。不要把“不写版本时的默认版本”理解为所有参数都能在该版本使用。

如果 agent 最终要直接执行 `hcloud`，先让本地解析器根据参数生成显式版本命令：

```bash
python3 scripts/hcloud_operation_resolver.py \
  --service VPC \
  --operation ListSecurityGroups \
  --param vpc_id=<vpc-id> \
  --arg=--cli-region=ap-southeast-1 \
  --emit-command
```

这个例子会选择支持 `vpc_id` 的 `ListSecurityGroups/v2`。多版本命令最终统一写成 `Operation/vN`，便于审查和失败纠正。普通小查询的 `--emit-command` 输出直接 `hcloud`；命中大输出策略时，输出会自动改成包装显式版本 operation 的 `hcloud_safe_exec.py --output-mode=auto`，避免 Agent 从命令生成阶段绕过摘要和落盘门禁。使用 `hcloud_safe_exec.py` 或 `hcloud_resource_query.py` 时不必单独调用解析器，它们会执行同样的预解析。

解析成功后同时读取 `request_contract`：它给出 method、path、顶层参数、位置、类型和必填信息。若
`body_shape_confidence=top_level_only`，表示本地 KooCLI catalog 没有证明嵌套 body 结构，不能据此猜测
`.1` 或点号参数。

## 二、查询类命令的默认形态

推荐默认骨架：

```bash
hcloud <service> <operation> \
  --cli-region=<region> \
  --cli-output=json
```

这里的 `<operation>` 在本地 catalog 能解析出版本时应为显式的 `<operation>/vN`。

然后再追加：

- 项目级服务需要的 `project_id`
- 过滤条件
- `limit`
- `--cli-query`

大列表、日志/事件、时序指标、全租户记录和文件/下载内容不要直接执行裸 `hcloud`。用 `hcloud_safe_exec.py` 的默认 `--output-mode=auto`，由 `references/hcloud-output-policies.json` 自动添加分页、要求时间/范围参数，并把 Agent 输出收敛成摘要或文件。只有已经通过服务端过滤且确定是小结果的普通查询，才适合直接执行显式版本的 `hcloud Service Operation/vN ...`。

如果本地门禁返回 `OUTPUT_POLICY_REQUIRED`，优先执行 `corrected_command`；返回的是 `corrected_command_template` 时，先补齐 `<required:...>`，再执行一次。不要把同一条不安全命令原样重试。

### 推荐例子

```bash
hcloud ECS ListFlavors \
  --cli-region=cn-north-4 \
  --project_id=<project-id> \
  --limit=20 \
  --cli-output=json
```

## 三、变更类命令的默认形态

推荐先做预执行：

```bash
hcloud <service> <operation> \
  --cli-region=<region> \
  --dryrun
```

然后再切到真实执行。

适用操作：

- 创建
- 修改
- 删除
- 启停
- 批量动作

### ECS 创建类额外护栏

ECS 创建类任务在 dry-run 前先校验 `cli-jsonInput`：

```bash
python3 scripts/hcloud_ecs_create_plan.py \
  --json-input-file=<path-to-json> \
  --operation=CreateServers \
  --region=<region> \
  --pretty
```

只有当 `validation.errors` 为空时，才使用输出里的 `commands.safe_exec` 进入 dry-run。

如果真实提交返回 `job_id`，继续使用：

```bash
python3 scripts/hcloud_ecs_wait_job.py \
  --job-id=<job-id> \
  --region=<region> \
  --project-id=<project-id> \
  --pretty
```

在 job 到达终态之前，不要宣称创建完成。

### 通用 `cli-jsonInput` 本地预检

非 ECS 专用请求在 JSON 写好后先运行：

```bash
python3 scripts/hcloud_request_preflight.py \
  --service=<SERVICE> \
  --operation=<Operation或Operation/vN> \
  --json-input-file=<path-to-json> \
  --project-id=<仅当path未写入JSON时使用> \
  --pretty
```

该脚本不会运行 hcloud、导入 SDK model 或访问云端。它先复用 operation resolver 确定唯一 API
版本，再校验 KooCLI 的 `path/query/body/formData/header/cookie` 外层结构和顶层参数位置；本机存在
对应官方 SDK 时，再静态校验同一 API 版本的有限深度嵌套 required/type 证据。

- `success=false`：先修正明确的 JSON、位置、必填字段或类型错误，不生成或执行 dry-run/submit。
- `validation_status=partial`：SDK 不存在、版本 schema 不存在或深层 schema 截断；请求仍可进入 dry-run，
  但不能声称参数已经完整验证。
- `SDK_UNKNOWN_FIELD`：只告警，不自动删除字段；已安装 SDK 可能落后于 live API，应查 skeleton、help
  或官方文档。
- 同一 request 位置不能一部分写入 JSON、另一部分用直接 API 参数传入。`project_id` 已放在
  `path` 时，不再重复传 `--project-id`。

通用 `hcloud_change_plan.py` 和 `hcloud_service_change_plan.py` 收到 `--json-input-file` 时会自动附带
`request_preflight`。预检只证明本地请求形状，不替代 dry-run、区域产品类型、配额、价格、权限、依赖和
变更后的资源/业务验证。

## 四、复杂参数优先 `--cli-jsonInput`

当遇到以下情况时，不要手拼长命令：

- body 很大
- 嵌套结构很多
- 有 `path` / `query` / `body` 多位置参数
- 当前 shell 长度或转义会变得脆弱

### 推荐路径

1. 先尝试 `--skeleton`
2. 如果可用，再生成骨架后编辑 JSON
3. 用 `--cli-jsonInput=<file>` 执行

### 推荐 JSON 结构

```json
{
  "path": {},
  "query": {},
  "body": {}
}
```

只保留真正需要的 key，不要强行保留空位置。

### 用官方 SDK 元数据补充嵌套结构

当 resolver 的 `request_contract` 只到顶层，且本机安装了对应官方 SDK 时，可以静态读取有限深度的
request schema：

```bash
python3 scripts/hcloud_sdk_catalog.py \
  --service=ECS \
  --operation=DeleteServers \
  --schema-depth=3 \
  --pretty
```

该命令只解析 SDK 源码中的 model 类型，不导入 model、不调用云 API，也不执行 mutation。将
`request_schema` 作为字段名、嵌套对象、数组元素类型和 required 证据，再写 `--cli-jsonInput`；如果
schema 仍显示 `truncated`、`available=false` 或与 hcloud help 冲突，停止猜测并继续查官方文档。

优先让 `hcloud_request_preflight.py` 组合 resolver 与 SDK 证据；只有需要查看完整 schema 来源或排查
预检证据时，再直接运行 `hcloud_sdk_catalog.py`。

## 五、查询类输出稳定化

默认建议：

- 机器处理：`--cli-output=json`
- 人眼快速浏览：`--cli-output=table`
- 纯值拼接：`--cli-output=tsv`

如果要继续让代码或脚本消费结果，默认坚持 `json`。

## 六、推荐统一包装脚本

### 用结构化方式执行 service/operation

```bash
python3 scripts/hcloud_safe_exec.py \
  --service ECS \
  --operation ListFlavors \
  --arg=--cli-region=cn-north-4 \
  --arg=--project_id=<project-id> \
  --arg=--limit=20 \
  --expect-json \
  --pretty
```

如果需要把结果保存到文件：

```bash
python3 scripts/hcloud_safe_exec.py \
  --command-part=configure \
  --command-part=list \
  --arg=--cli-output=json \
  --expect-json \
  --result-file=/tmp/hcloud_safe_exec_result.json \
  --parsed-json-file=/tmp/hcloud_safe_exec_parsed.json
```

### 用通用方式执行系统命令

```bash
python3 scripts/hcloud_safe_exec.py \
  --command-part=configure \
  --command-part=list \
  --arg=--cli-output=json \
  --expect-json \
  --pretty
```

## 七、参数构造的实用规则

- 系统参数统一优先用 `cli-*`
- 参数值里有特殊字符时要明确引用
- 同类冲突参数不要新旧混用
- 若出现重复参数冲突，优先改成 `cli-*` 新参数名
- 如果当前 operation 帮助拿不到，不要凭印象补 body 字段

## 八、对于长结果的默认做法

不要直接把原始大结果全部返回给用户。

默认做法：

1. 先限制数量
2. 再用 `--cli-query` 提炼
3. 再汇总为用户关心的结论

例如：

- 只要实例名和状态
- 只要前 20 条
- 只要满足某个 tag 的资源
