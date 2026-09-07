# FunctionGraph Readiness Playbook

## 目标

帮助用户创建、查询或排查 FunctionGraph 函数前，先明确运行时、代码包、依赖、agency/xrole、触发器、日志、测试事件和调用边界。函数创建和触发器配置通常跨 IAM、APIG、OBS、CTS、LTS、SMN、Kafka 等服务，不能只看一个函数状态。

## 适用场景

- 用户要部署 Python/Node/Java/Go 函数。
- 用户要用 OBS、APIG、定时器、CTS、LTS、SMN、Kafka 等触发函数。
- 用户要用 Custom Image 函数运行 SWR 镜像。
- 用户要排查函数调用失败、触发器不生效、日志为空或权限不足。

## 标准只读检查

1. 查询函数列表：

```bash
python3 scripts/hcloud_resource_discovery.py \
  --service FunctionGraph \
  --operation ListFunctions \
  --region=<region> \
  --pretty
```

2. 查询函数配置：

```bash
python3 scripts/hcloud_resource_query.py \
  --service FunctionGraph \
  --operation ShowFunctionConfig \
  --region=<region> \
  --param function_urn=<function_urn> \
  --pretty
```

3. 查询触发器：

```bash
python3 scripts/hcloud_resource_query.py \
  --service FunctionGraph \
  --operation ListFunctionTriggers \
  --region=<region> \
  --param function_urn=<function_urn> \
  --pretty
```

4. 查询日志详情：

```bash
python3 scripts/hcloud_resource_query.py \
  --service FunctionGraph \
  --operation ShowLtsLogDetails \
  --region=<region> \
  --param function_urn=<function_urn> \
  --pretty
```

## 创建前检查

函数创建或更新前至少确认：

- 函数名、runtime、handler、memory、timeout、package。
- 代码来源：inline、zip、OBS、jar、Custom Image/SWR。
- 依赖包和依赖版本。
- agency/xrole 是否能访问 OBS、VPC、SWR、LTS、目标下游服务。
- 是否需要 VPC、subnet、security group、VPC endpoint。
- 是否启用 LTS 日志和异步调用状态日志。
- 触发器类型、事件格式、权限和重试语义。
- 是否会产生公网入口、下游费用或高并发成本。

## 触发器要点

| 触发器 | 必查项 |
| --- | --- |
| TIMER | cron/rate 表达式、时区、触发状态、幂等性。 |
| APIG | API 分组、认证方式、域名、后端超时、错误码。 |
| OBS | bucket、事件类型、prefix/suffix、对象权限、循环触发风险。 |
| CTS | trace 事件范围、审计延迟、过滤条件。 |
| LTS | log group/stream、日志格式、触发条件。 |
| SMN/Kafka/DMS | topic/consumer、重试、死信、消息格式。 |

## 风险边界

- `InvokeFunction` 会真实调用函数，可能触发下游写操作或费用；不要当成只读查询。
- `CreateFunction`、`UpdateFunctionCode`、`UpdateFunctionConfig`、`CreateFunctionTrigger`、`EnableLtsLogs` 都是写操作，必须二次确认。
- 不在最终输出中展示用户代码里的密钥、环境变量 secret、AK/SK、token。
- Custom Image 函数先走 `swr-image-readiness.md`，确认镜像和拉取权限。
- 函数日志可能包含业务敏感数据，摘要时要脱敏。

## 常见问题

| 现象 | 常见原因 | 下一步 |
| --- | --- | --- |
| 函数创建失败 | runtime、handler、package、代码来源或 IAM agency 错误 | 输出参数清单和权限缺口，进入权限诊断。 |
| 触发器不触发 | trigger 状态、事件源权限、过滤条件、事件延迟 | 查 `ListFunctionTriggers`，再查源服务事件。 |
| 调用超时 | timeout 太短、VPC 下游不通、冷启动、依赖下载慢 | 查配置、日志、VPC 路径和下游依赖。 |
| 日志为空 | LTS 未启用、函数未执行、日志组/流不匹配 | 查 `ShowLtsLogDetails` 和 LTS playbook。 |
| Custom Image 拉取失败 | SWR 权限、镜像地址、架构或 tag 错误 | 进入 `swr-image-readiness.md`。 |

## 验收

完成 FunctionGraph readiness 时，应能说明：

- 函数是否存在，runtime/handler/memory/timeout 是否符合目标。
- 代码来源和依赖是否清楚。
- 触发器是否存在、状态是否符合预期。
- 日志路径是否可用。
- 是否存在 IAM、VPC、SWR、OBS/APIG/LTS 等外部依赖缺口。
- 如果要真实创建/更新/调用，下一步需要用户确认参数、费用、下游副作用和回滚方式。
