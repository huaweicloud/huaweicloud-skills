# OBS hcloud obs Boundary

## 当前结论

`data-by-changping/data.xlsx` 的人工 E2E 数据里包含 OBS 桶和生命周期规则任务。OBS 不出现在普通 KooCLI service metadata 中，因此不能用 `hcloud OBS ListBuckets` 这类 OpenAPI-style 命令。

KooCLI 集成了 obsutil，可通过 `hcloud obs` 管理 OBS 桶和对象数据。本 skill 因此把 OBS 桶/对象操作作为专用 runner：

- 只读查询：`scripts/hcloud_obs_readonly.py`
- planner-only 变更：`scripts/hcloud_obs_change_plan.py`

## 处理原则

- 不要生成 `hcloud OBS <Operation>` 命令。
- bucket list 用 `hcloud obs ls`，通过 `hcloud_obs_readonly.py --operation ListBuckets` 生成。
- bucket 级查询必须显式传 `--bucket`，例如 `--operation GetBucketLifecycle --bucket <bucket>`。
- OBS 输出是 obsutil 文本，不是标准 OpenAPI JSON；最终回复只摘要关键信息，不展开 bucket policy、生命周期细节或认证参数。
- bucket、lifecycle、policy 写类操作只生成 planner-only 命令；真实 submit 需要单独确认。

OBS 用量、请求数和流量统计不是 `hcloud obs` 文本命令的同一执行面。默认按下面区分：

| 问题 | 推荐数据源 | 关键点 |
| --- | --- | --- |
| 列桶、桶属性、生命周期、policy | `hcloud obs` / obsutil | 输出是文本，适合桶/对象管理证据 |
| 桶容量趋势、流量、请求数、告警 | CES `SYS.OBS` / `ShowMetricData` | 输出是监控指标，适合趋势、成本治理和告警 |
| 精确对象数和桶大小 | OBS `GetBucketStorageInfo` 或 obsutil stat | 精确但批量慢，适合单桶核对 |
| 多桶容量排名 | CES `capacity_total` | 采集有延迟，但适合批量排名和治理 |

## 已支持能力

- `ListBuckets` -> `hcloud obs ls`
- `StatBucket` -> `hcloud obs stat obs://bucket`
- `GetBucketLifecycle` -> `hcloud obs lifecycle obs://bucket -method=get`
- `GetBucketPolicy` -> `hcloud obs bucketpolicy obs://bucket -method=get`
- `CreateBucket` planner -> `hcloud obs mb obs://bucket`
- `DeleteBucket` planner -> `hcloud obs rm obs://bucket`
- `PutBucketLifecycle` / `DeleteBucketLifecycle` planner
- `PutBucketPolicy` / `DeleteBucketPolicy` planner

## 验证注意

- `hcloud obs` 会写 obsutil 日志；受限沙箱里可能出现 `.obsutil_log` 写入权限警告。
- 如果 live 查询失败，优先检查 obsutil endpoint、AK/SK/token、`.obsutilconfig` 和网络。
- 不要把 OBS 写类 planner 的 submit 命令当成已经执行。

## OBS CES 统计注意

- CES namespace 使用 `SYS.OBS`，常见 dimension 是 `bucket_name,<bucket>`。
- CES `ShowMetricData` 的 dimension 参数按 KooCLI 形态写成 `--dim.0=bucket_name,<bucket>`，不要用 SDK JSON dimensions 形态。
- 流量统计要使用 traffic metrics，例如 `download_traffic_extranet`、`download_traffic_intranet`、`upload_traffic_extranet`、`upload_traffic_intranet`。这些是 Bytes，可按 `sum` 汇总。
- 不要用 bandwidth metrics，例如 `download_bytes`、`download_bytes_extranet`、`upload_bytes` 去直接代表总流量；它们是 Bytes/s，必须按周期换算，容易算错。
- OBS 没有单个 `request_count` 指标。总请求数需要汇总：
  - `get_request_count`
  - `put_request_count`
  - `post_request_count`
  - `head_request_count`
  - `delete_request_count`
- 容量指标如 `capacity_total` 适合 `average` 并取最新 datapoint；不要对容量快照使用 `sum`。
- CES 统计有采集延迟。容量类指标适合趋势和排名，不能替代单桶精确核算。
