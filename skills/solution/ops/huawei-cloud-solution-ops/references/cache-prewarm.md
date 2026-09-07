# Cache Prewarm

## 目标

在真正让 agent 处理华为云真实业务前，先把 `hcloud` 依赖的本地元数据和帮助信息尽量热起来，降低第一次执行时卡在 `APIE_ERROR`、参数校验不全、region 列表不全的概率。

这个预热流程主要覆盖两类缓存：

- `~/.hcloud/metaOrigin`
  - 由 `hcloud meta download` 下载的离线元数据包
- `~/.hcloud/metaRepo`
  - `hcloud` 在解析 service / operation 时实际使用和写入的本地缓存

## 脚本入口

```bash
python3 scripts/hcloud_prewarm_cache.py --pretty
```

默认行为：

- 先尝试执行 `hcloud meta download`
- 再预热 `ECS`、`IAM`、`VPC`、`IMS`、`KPS`
- 对 `ECS` 额外预热一组高价值 operation
- 对其他 service，优先根据 `hcloud <service> --help` 动态发现 operation
- 运行中默认把进度信息打印到 `stderr`
- 运行中持续写检查点文件，便于中断后续跑
- 输出结构化 JSON summary

## 推荐用法

### 1. 先跑一轮默认重点预热

```bash
python3 scripts/hcloud_prewarm_cache.py \
  --pretty \
  --summary-file=./hcloud-prewarm-summary.json
```

适合：

- 先把高频路径热起来
- 先看当前网络和缓存边界

### 2. 网络稳定时，尽量把发现到的 operation 也拉一遍

```bash
python3 scripts/hcloud_prewarm_cache.py \
  --discovered-operations=all \
  --pretty \
  --summary-file=./hcloud-prewarm-full.json
```

适合：

- 你想尽量把当前 service 的 operation 详情提前缓存在本地
- 你接受这会比默认模式更慢

### 2.1 中断后续跑

如果你已经指定了 `--summary-file`，脚本会默认在旁边生成一个检查点文件。

例如：

- summary: `./hcloud-prewarm-full.json`
- checkpoint: `./hcloud-prewarm-full.checkpoint.json`

中断后直接用同一条命令重跑即可，脚本会自动：

- 读取检查点
- 跳过已完成的 `meta download`
- 跳过已完成的 `service help`
- 跳过已完成的 `operation help`

### 2.2 保留检查点做多次复跑

```bash
python3 scripts/hcloud_prewarm_cache.py \
  --discovered-operations=all \
  --summary-file=./hcloud-prewarm-full.json \
  --keep-checkpoint \
  --pretty
```

适合：

- 你想保留检查点观察续跑行为
- 你想分多次慢慢把长任务跑完

### 3. 只预热单个 service

```bash
python3 scripts/hcloud_prewarm_cache.py \
  --service=ECS \
  --discovered-operations=all \
  --pretty
```

### 4. 只精确预热几个 operation

```bash
python3 scripts/hcloud_prewarm_cache.py \
  --service=ECS \
  --skip-priority-operations \
  --discovered-operations=none \
  --operation=ECS:ListFlavors \
  --operation=ECS:CreateServers \
  --pretty
```

适合：

- 你明确知道接下来要做哪些业务
- 不想预热太多无关 operation

## 常用参数

- `--skip-meta-download`
  - 跳过 `hcloud meta download`
  - 只做 service / operation help 预热
- `--profile`
  - 为所有命令显式指定 `cli-profile`
- `--region`
  - 为 help 发现显式指定 `cli-region`
- `--discovered-operations`
  - `none`: 不使用动态发现到的 operation
  - `sample`: 只预热部分动态发现的 operation
  - `all`: 预热全部动态发现的 operation
- `--max-discovered-operations`
  - 当 `discovered-operations=sample` 时，每个 service 最多预热多少个动态发现 operation
- `--summary-file`
  - 把完整预热结果写到 JSON 文件，方便后续交给 agent 分析
- `--checkpoint-file`
  - 显式指定检查点文件路径
- `--no-resume`
  - 忽略已有检查点，强制从头开始
- `--keep-checkpoint`
  - 即使成功也保留检查点文件
- `--no-progress`
  - 关闭运行中的实时进度输出
  - 默认不建议关，这样更容易判断脚本是否还在运行

## 进度输出说明

脚本运行中默认会打印类似下面的进度信息：

```text
[hcloud-prewarm] step 1/4 inspect context before prewarm
[hcloud-prewarm] step 2/4 download offline metadata package
[hcloud-prewarm] step 3/4 service 1/5: discover ECS
[hcloud-prewarm] start service help ECS
[hcloud-prewarm] done  service help ECS -> ok in 0.06s
```

这些进度信息会打印到 `stderr`，不是 `stdout`。

这样做的好处是：

- 你在终端里能确认脚本仍在运行
- 如果把 `stdout` 重定向到文件，最终 JSON 结果仍然是干净的
- 后续 agent 或脚本仍可以稳定解析 `stdout`

## 检查点行为

默认规则：

- 运行中会持续更新检查点文件
- 脚本异常中断后，检查点会保留
- 下次重跑同一组参数时，会自动续跑
- 如果本次成功完成，默认会删除检查点文件

如果你想手动控制：

- 用 `--keep-checkpoint` 保留成功后的检查点
- 用 `--no-resume` 忽略已有检查点并重头跑
- 用 `--checkpoint-file=...` 改检查点位置

## 如何看结果

重点关注这些字段：

- `meta_download.success`
  - 离线元数据包下载是否成功
- `context_before.meta_origin`
  - 预热前是否已有离线包目录
- `context_after.meta_origin`
  - 预热后离线包目录是否出现、文件数是否增加
- `context_after.meta_repo`
  - 预热后本地 cache service 和 template 文件数是否增加
- `services[].service_help.success`
  - 该 service 的帮助信息能否正常拉取
- `services[].target_operations`
  - 本轮实际尝试预热了哪些 operation
- `services[].operations[].help.success`
  - 每个 operation help 是否拉取成功
- `services[].operations[].help.error_type`
  - 失败时是 `APIE_ERROR`、`NETWORK_ERROR` 还是其他类型

## 建议判断规则

### 可以认为“预热基本可用”的情况

- `meta download` 成功
- `ECS` 的 service help 成功
- `ECS` 的 `ListFlavors`、`ListServerAzInfo`、`CreateServers` 至少有一部分 operation help 成功
- `IAM/VPC/IMS/KPS` 中至少有若干 service help 成功

### 需要继续补救的情况

- `meta download` 失败
- 大多数 service help 都是 `APIE_ERROR`
- operation help 基本全失败
- `metaOrigin` 和 `metaRepo` 在预热前后几乎没有变化

## 与在线/离线模式的关系

这个脚本默认不会帮你切换 `cli-offline`。

原因：

- 预热缓存是一件事
- 改变 KooCLI 的全局运行模式是另一件事

如果你已经成功下载离线元数据包，并且后续希望脚本化命令长期稳定复用，再考虑手动切到离线模式：

```bash
hcloud configure set --cli-offline=true
```

如果你更看重新 service / 新 operation 的即时发现，则保持在线模式更合适。

## 当前版本的现实边界

- 当前机器已经验证过：`ECS` 的帮助和部分缓存最好用
- `IAM`、`VPC`、`IMS`、`KPS` 在受限网络下容易卡在 `APIE_ERROR`
- 这不是预热脚本本身的逻辑问题，而是 `hcloud` 获取 API Explorer 元数据时依赖网络

因此，预热脚本的价值不只是“尝试拉缓存”，还包括：

- 帮你记录真实可用边界
- 告诉后续 agent 哪些 service 已经能稳定发现，哪些还不行
