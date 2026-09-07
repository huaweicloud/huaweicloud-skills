# Huawei CLI Local Meta Discovery

## 目标

在 live help 不稳定、`APIE_ERROR` 常出现的环境里，尽量利用本地 `~/.hcloud/metaRepo` 做 discovery。

当前 skill 还内置了从 hcloud metaRepo 生成的 catalog。运行时默认读取 `references/hcloud-service-catalog.index.json`，再按需加载 `references/hcloud-service-catalog/<service>.json`；full catalog 不再提交到仓库，只在维护期需要完整 diff 时临时生成。准确覆盖规模以 `hcloud_catalog_audit.py --pretty` 的 `catalog` 字段和 `references/hcloud-service-catalog.fingerprint.json` 的 `source` 字段为准。源 metaRepo 只在重新生成 catalog 或排查 metadata drift 时使用。

## 为什么需要这一步

当前环境已经验证到：

- `hcloud ECS --help` 可以列出 operation
- 但很多 `hcloud <service> --help` 或 `hcloud <service> <operation> --help` 会因为 API Explorer 元数据失败而拿不到完整信息

因此，必须把“本地 meta cache discovery”作为正式流程的一部分。

## 推荐脚本

```bash
python3 scripts/hcloud_meta_lookup.py --service=ECS --pretty
```

## 脚本能做什么

### 1. 列本地已知服务

```bash
python3 scripts/hcloud_meta_lookup.py --list-services --limit=20 --pretty
```

返回：

- `services_en.json` 里的服务名
- 服务描述
- 分类
- 是否全局服务
- 是否已在本地缓存出 template 目录

### 2. 看某个 service 的本地缓存情况

```bash
python3 scripts/hcloud_meta_lookup.py --service=ECS --pretty
```

返回：

- 本地是否缓存了该 service
- 缓存了多少 operation 摘要
- 哪些 operation 有详细元数据
- endpoint / region 信息

### 3. 看某个 operation 的本地细节

```bash
python3 scripts/hcloud_meta_lookup.py \
  --service=ECS \
  --operation=ListFlavors \
  --region=cn-north-4 \
  --pretty
```

返回：

- 请求方法
- 请求路径
- 参数位置
- 参数类型
- 是否必填

## `--allow-help-fallback`

当本地没有 cache 时，可以尝试：

```bash
python3 scripts/hcloud_meta_lookup.py --service=IMS --allow-help-fallback --pretty
```

用途：

- 至少拿到 `Usage` 和 service 级失败信息

但当前环境下，它通常只能拿到：

- service 名
- `Usage`
- `APIE_ERROR`

也就是说，这一步不是万能补救，只是把失败上下文结构化。

## 生成 catalog

如果 hcloud 升级或本地 metaRepo 更新，需要先重新生成并审计 skill 自带 catalog：

```bash
python3 scripts/build_hcloud_catalog.py \
  --source-meta-repo <path-to-hcloud-metaRepo> \
  --fingerprint-output references/hcloud-service-catalog.fingerprint.json \
  --index-output references/hcloud-service-catalog.index.json \
  --service-output-dir references/hcloud-service-catalog

python3 scripts/hcloud_catalog_audit.py --fail-on-drift --pretty
```

规则：

- 生成 catalog 可以读取本地 metaRepo 作为一次性输入。
- `huawei-cloud-solution-ops` 运行时不依赖源 metaRepo 目录，也不依赖外部数据项目。
- 生成后的 JSON 会被 `hcloud_resource_discovery.py`、`hcloud_resource_query.py` 和 `hcloud_service_change_plan.py` 作为 registry 外服务的 metadata-backed 兜底。
- `hcloud-service-catalog.index.json` 和 `hcloud-service-catalog/` 是运行时懒加载入口；不要把 per-service JSON 当成 curated coverage。
- `hcloud-service-catalog.fingerprint.json` 是小体积升级审查文件，用于快速比较服务、operation 和 required 参数漂移。
- 如果维护期确实需要 operation 级完整 diff，可额外传 `--output <temporary-full-catalog-json>` 生成本地 full catalog；该文件不要提交。
- `hcloud-service-confidence.json` 用于记录 live smoke、confidence 和 dry-run 支持性，不属于纯 metadata 生成结果。
- audit 需要保持 `success=true`；如果 registry operation 在 catalog 中消失，应先修 registry 或确认服务是否改名。

## 当前覆盖情况

- curated registry：以 `hcloud_catalog_audit.py --pretty` 的 `registry` 字段和 `references/service-registry.json` 为准，其中 OBS 走 `hcloud obs`/obsutil 专用 runner。
- generated catalog：以 `hcloud_catalog_audit.py --pretty` 的 `catalog` 字段和 `references/hcloud-service-catalog.fingerprint.json` 的 `source` 字段为准。
- metadata-backed 服务：以 `hcloud_catalog_audit.py --pretty` 的 `metadata_backed` 字段为准；这些 registry 外服务可用于保守发现、显式参数只读查询和 planner-only 变更计划。
- 自动 discovery 只选择无必填业务参数的只读 `List` / `Count` / `Search` / `Query` / `Check` 操作。
- `Show*`、目标型 `List*`、`Get*` 等带必填参数的只读操作必须通过 `hcloud_resource_query.py --param KEY=VALUE` 显式传参。
- mutating operation 只进入 `hcloud_service_change_plan.py` 的 planner-only 路径，不自动 submit；metadata-backed mutation 的 dry-run 支持默认为 `unknown`。
- metadata-backed planner 会把 service `category` 作为风险下限；安全合规、身份、密钥和治理类 mutation 会进入 hard guard，通用 guarded flow 不能自动 submit。
- metadata-backed 只读实测可用 `hcloud_catalog_readonly_smoke.py`，执行结果应按命令形态、账号权限、服务开通、region/project、参数和网络等原因分桶。

## 如何在 workflow 里使用

推荐顺序：

1. `hcloud_context_inspect.py`
2. `hcloud_meta_lookup.py`
3. `hcloud_catalog_audit.py`（metadata 升级后或怀疑 registry drift 时）
4. `hcloud --help`
5. `hcloud <service> --help`
6. `hcloud_safe_exec.py`

含义：

- 先看本地缓存里有什么
- 再决定是否继续依赖 live help

## 不要做的事

- 不要看到 service 在 `services_en.json` 里，就假设本地一定有 operation 详情
- 不要把没有本地 detail cache 的 operation 参数直接写死
- 不要忽略 `detail_cached=false` 这一信号
- 不要把 metadata-backed 误说成 curated playbook 覆盖；它只是更广的保守兜底层
