# Huawei CLI Error Playbook

本文件记录 `hcloud` 路线里最常见的错误类型与处理方式。

## 一、错误处理总原则

先分类，再动作：

1. 先看错误类型
2. 再判断是上下文、网络、缓存、参数、还是服务端问题
3. 不要对同一个错误原样重试三次

## 二、常见错误类型

| 错误类型 | 常见含义 | 第一动作 |
|----------|----------|----------|
| `USE_ERROR` | 参数、region、service、operation、profile 使用有问题 | 回到 help、当前配置和参数构造 |
| `NETWORK_ERROR` | 网络连接、超时、重试耗尽 | 检查连通性、timeout、retry |
| `CLI_ERROR` | KooCLI 本地运行时或命令处理异常 | 查本机 KooCLI 版本和 `~/.hcloud/logs/` |
| `OPENAPI_ERROR` | 真实云服务 API 返回错误 | 看服务端语义和请求参数 |
| `APIE_ERROR` | API Explorer 元数据获取失败 | 检查 DNS、网络、meta cache、online/offline mode |
| `OUTPUT_POLICY_REQUIRED` | 本地大输出门禁拒绝了缺少范围或显式豁免的命令 | 执行纠正命令，或补齐纠正模板中的范围参数 |

## 三、按问题类型处理

### 0. 先看请求确定性，再决定是否重试

`hcloud_safe_exec.py` 的 `execution_semantics` 不替 Agent 判断业务完成，但会给出稳定边界：

| 字段 | 含义 |
| --- | --- |
| `request_outcome=succeeded` | 请求成功；mutation 仍需资源/job 回读 |
| `request_outcome=failed` | 有明确失败证据；按错误建议修正后再决定是否重试 |
| `request_outcome=outcome_unknown` | 连接、超时或运行时中断，mutation 可能已经到达云侧 |
| `retry_strategy=verify_before_retry` | 先查目标资源或 job，禁止原样重复提交 |

只读超时可在合理预算内重试；创建、修改、删除、绑定等 mutation 超时不能当作普通失败。明确的
KooCLI 参数错误或华为云 API 拒绝是已知失败，不应被误写为 transport ambiguity。

### 1. `OUTPUT_POLICY_REQUIRED`

这是 `hcloud_safe_exec.py` 在访问云 API 前触发的本地输出门禁，不是华为云服务故障。

- `missing_required_output_filters`：补齐 `corrected_command_template` 中的时间、范围或资源参数。
- `large_output_requires_explicit_override`：默认执行返回的 `corrected_command`，让结果摘要化。
- 真正需要完整结果时，把完整响应写到 `--result-file`、`--parsed-json-file` 或 `--raw-output-file`；不要把文件内容整体读回对话。
- 已知大输出若明确选择 `--output-mode=full`，还必须传 `--allow-large-output`。这属于显式审阅后的本地消费路径，不是 Agent 默认路径。
- 不要原样重试同一条被门禁拒绝的命令。

### 2. 提示缺少 `cli-region`

现象：

- `请输入cli-region`

动作：

1. 先看当前 profile 是否已有 region
2. 没有就显式加 `--cli-region=<region>`
3. 不要假设默认 region 总存在

### 3. 提示不支持的 service

现象：

- `不支持的服务名称`

动作：

1. 运行 `hcloud --help`
2. 确认服务名拼写
3. 如果当前走 offline mode，考虑元数据是否过旧

### 4. 提示不支持的 operation

现象：

- `不支持的operation`

动作：

1. 运行 `hcloud <service> --help`
2. 运行 `hcloud_operation_resolver.py --service <service> --operation <operation> --verify-help --pretty`，核对可用版本和本机默认版本
3. 确认 operation 名及 `Operation/vN` 是否真的存在
4. 如果不存在，先不要继续猜参数

### 5. `APIE_ERROR`

现象：

- `Failed to obtain API details`
- `Failed to obtain version list`
- `Failed to obtain service list`

典型原因：

- DNS 失败
- 网络不通
- live metadata 获取失败

动作：

1. 先判断是否只是 operation 级帮助失败
2. 回退到：
   - 本地 `~/.hcloud/metaRepo`
   - 当前 skill 的 `references/`
3. 必要时考虑：
   - `hcloud meta clear`
   - `hcloud meta download`
4. 如果当前环境根本不能联网，就不要继续依赖 live help

### 6. `NETWORK_ERROR`

现象：

- 连接超时
- 重试耗尽

动作：

1. 检查网络连通性
2. 适当增大：
   - `--cli-connect-timeout`
   - `--cli-read-timeout`
3. 必要时增加：
   - `--cli-retry-count`

### 7. `CLI_ERROR`

现象：

- 输出中出现 `[CLI_ERROR]`
- 命令还没到云服务 API，KooCLI 自身已经处理失败

典型原因：

- 本地 KooCLI 版本过旧或安装损坏
- 本地配置、插件、缓存或运行时状态异常
- 命令行解析、系统参数或本地文件访问在 KooCLI 内部失败

动作：

1. 先运行 `hcloud version` 记录版本。
2. 查看 `~/.hcloud/logs/` 下最近日志；旧安装也可能写到 `~/.hcloud/log/hcloud.log`。
3. 如果错误和元数据缓存相关，再考虑 `hcloud meta clear` 或 `hcloud meta download`。
4. 不要把 `CLI_ERROR` 直接归因到云服务业务参数；只有看到 `OPENAPI_ERROR` 或服务端错误码后，才进入服务端排查。

### 8. 参数不正确或重复

现象：

- `不正确的参数`
- `重复的参数`

动作：

1. 先看 `version_resolution.candidates`，确认当前 `/vN` 是否支持这些参数
2. 回看 `hcloud <service> <operation> --help`
3. 若解析器给出 `corrected_operation`，只读操作可使用纠正后的显式版本重试一次
4. 若是系统参数冲突，优先改成 `cli-*`
5. 若与 API 参数重名且难以处理，考虑转成 `--cli-jsonInput`

### 8.1 版本纠错边界

- 未显式指定版本的只读操作，如果首次失败明确属于 operation/参数/版本不匹配，`hcloud_safe_exec.py` 最多切换到另一个兼容版本重试一次。
- 显式指定但参数不兼容时，不先执行错误命令；输出 `corrected_operation` 和纠正命令，由 agent 重新审查。
- 创建、修改、删除等 mutation 不自动切换版本或重放，避免重复变更。
- 认证、权限、配额、region/project、网络和服务端业务错误不切换 API 版本，按原错误类型处理。
- 同一命令纠正后仍失败时停止，不循环试遍所有版本。

### 9. 空响应体

现象：

- 命令返回为空，看不出成功失败

动作：

1. 在原命令上补 `--debug`
2. 从状态码判断成功与否

空响应体也不能覆盖 `execution_semantics`：mutation 请求返回成功但没有资源终态时，仍按计划中的
Show/List/job 查询回读。

## 四、缓存与日志

### 元数据缓存

常见位置：

- `~/.hcloud/metaRepo/`

排查动作：

- 看本地是否已有缓存模板
- 遇到缓存损坏或版本不一致时，考虑 `hcloud meta clear`

### 日志

常见位置：

- `~/.hcloud/logs/`
- `~/.hcloud/log/hcloud.log`

用途：

- 看 `hcloud` 在当前机器上的执行轨迹
- 辅助分析命令为什么失败

## 五、推荐排查顺序

如果当前命令失败，默认按这个顺序排：

1. 当前上下文
   - profile
   - region
   - project
   - domain
2. 当前服务和 operation 是否真的存在
3. 当前参数是否真的被支持
4. 当前环境是否联网
5. 当前元数据缓存是否存在或过旧
6. 当前请求是否是服务端真实失败
