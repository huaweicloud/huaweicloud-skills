# IMS Image Discovery Playbook

## 目标

在创建 ECS 或排查镜像选择问题时，先把 IMS 侧镜像发现路径讲清楚。

## 适用场景

- 创建 ECS 前选择镜像
- 用户想找某类系统盘镜像
- 用户想确认某个 image id 是否存在

## 当前环境约束

当前机器已经验证到：

- `IMS` 在 `services_en.json` 中存在
- 当前机器没有 `IMS` 的本地 template cache
- `hcloud IMS --help` 在当前网络环境下会卡在 `APIE_ERROR`

因此：

- 本 playbook 当前主要提供 discovery 方法和检查顺序
- 不宣称已经有稳定的 operation 级本地缓存

## 标准步骤

### 1. 先看上下文

```bash
python3 scripts/hcloud_context_inspect.py --pretty
```

### 2. 看本地是否有 IMS cache

```bash
python3 scripts/hcloud_meta_lookup.py --service=IMS --allow-help-fallback --pretty
```

重点看：

- `cached_locally`
- `cached_operations_count`
- `service_help_fallback`

### 3. 再决定下一步

#### 如果未来拿到了 IMS 本地 cache

优先走：

- `hcloud_meta_lookup.py --service=IMS`
- `hcloud IMS --help`
- `hcloud IMS <operation> --help`

#### 如果当前仍没有 cache，且 live help 也失败

就不要直接猜 operation 和 body。

应改为：

- 先向用户说明当前 discovery 受环境限制
- 先继续完成 ECS readiness 里其他已知部分

## 大输出处理

`ListImages` 默认按高风险大输出 API 处理。公共镜像、共享镜像和跨平台查询可能返回大量镜像元数据，不要默认把完整 JSON 带回对话。

推荐做法：

1. 先用小 `limit` 或明确过滤条件确认返回结构。
2. 查询公共系统镜像时优先考虑 `visibility`、`status`、`name`、`architecture`、`__platform`、`__imagetype` 等过滤参数，真实参数以当前 operation help 为准。
3. 如果需要全量核验镜像范围，把完整结果写入 `--result-file` / `--parsed-json-file`，对话里只返回总数、候选样本、关键字段和文件位置。
4. 后续筛选镜像时读取落盘文件做字段投影，不要直接 `cat` 全量结果。

## 在 ECS 创建里的作用

IMS 侧至少需要回答：

- 用哪个镜像
- 这个镜像是公共镜像、私有镜像还是共享镜像
- 镜像和目标 region 是否匹配

如果这些问题没有答案，就不适合进入真实创建。
