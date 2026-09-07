# SDK 后端与便捷只读 Runner

`hcloud` 仍是默认优先的 Agent 接口；华为云 Python SDK 是受支持的程序化后端。SDK 可用于补充
hcloud 证据，也可在类型化请求、复杂 body、分页/并发、结构化异常或 hcloud 实际覆盖/解析障碍时
直接承担当前任务。

## 定位

- **默认优先接口**：`hcloud` / KooCLI。
- **程序化后端**：已安装的官方 `huaweicloudsdk*` Python package。
- **便捷只读 runner**：`hcloud_sdk_readonly.py`，只覆盖小型 curated registry。
- **SDK 源码参考**：维护者可通过 `--sdk-root <sdk-source-root>` 显式传入 `huaweicloud-sdk-python-v3` checkout，用于测试和离线比对；默认不会搜索 Skill 外部目录。
- **IaC 面**：Terraform 是由 IaC 意图触发的独立 plan/validate/apply/verify 链路，不由 SDK runner 替代。

## 参考快照

当前维护快照来自上游 `huaweicloud/huaweicloud-sdk-python-v3`：

- 本地 `VERSION`：`3.1.199`
- 本地 changelog 日期：`2026-06-11`
- 运行时要求：用户机器不需要 SDK 源码，只需要按需安装 pip package
- Python 要求：本 Skill 统一要求 Python 3.12+；上游 SDK 的兼容范围以其官方文档为准

注意：这只是本仓库维护期快照。真实用户环境应以已安装 package 版本和当前 PyPI/SDK 中心为准；agent 不应假设用户机器存在源码 checkout。

## 运行时认证与 region 线索

SDK 路径读取或调用已安装的 `huaweicloudsdk*` package。典型安装方式：

```bash
pip install huaweicloudsdkecs
pip install huaweicloudsdkvpc
```

`huaweicloudsdkall` 会安装集合包，但不建议 agent 默认要求用户安装全量集合；只有当任务确实跨多个服务且用户接受依赖体积时才提示。

SDK 常见环境变量：

| 变量 | 用途 |
| --- | --- |
| `HUAWEICLOUD_SDK_AK` | SDK Access Key |
| `HUAWEICLOUD_SDK_SK` | SDK Secret Key |
| `HUAWEICLOUD_SDK_SECURITY_TOKEN` | 临时凭证 token |
| `HUAWEICLOUD_SDK_PROJECT_ID` | 区域级服务 project ID |
| `HUAWEICLOUD_SDK_DOMAIN_ID` | 全局级服务 domain ID |

认证选择：

- 区域级服务优先使用 `BasicCredentials`，通常需要 project ID；新版 SDK 在使用永久 AK/SK 且 `with_region()` 时可自动查询 project ID。
- 全局级服务使用 `GlobalCredentials`，通常需要 domain ID。
- SDK 支持环境变量、profile、metadata、Pod Identity 等凭证来源；CCE Pod Identity 能减少明文 AK/SK 暴露，但只能在对应集群/身份配置完成后使用。

Region/endpoint 选择：

- 优先用 SDK 内置 region，例如 `{Service}Region.value_of("cn-north-4")`。
- 显式 endpoint 可用于专属云、特殊网络或内置 region 不完整的场景，但通常需要显式 project/domain ID。
- SDK 的 region 查找顺序包括环境变量、配置文件和内置 region；找不到时可能抛出 `KeyError`。
- 自定义 endpoint 可通过形如 `HUAWEICLOUD_SDK_REGION_{SERVICE_NAME}_{REGION_ID}` 的环境变量补充；多 endpoint 需要确认 SDK 版本支持。

异常处理：

- `ClientRequestException` 通常包含 `status_code`、`request_id`、`error_code`、`error_msg`。
- Agent 应保存这些字段用于错误归因。SDK 如果已被选为当前任务后端，可以依据这些结构修正、重试
  或报告；不要把 SDK 错误强行翻译成 hcloud 错误。

## 什么时候用 SDK

适合选择 SDK 的场景：

1. hcloud metadata/help 缺少参数类型、query/path/body 位置或 region/endpoint 线索。
2. 请求 body 嵌套复杂、需要类型化模型，或者需要稳定分页、并发和结果转换。
3. hcloud 当前版本缺少服务/operation metadata，或输出混杂导致无法可靠判定业务结果，而官方 SDK
   package 覆盖该 API。
4. 需要 SDK 的 `openapi_types`、`attribute_map`、`sensitive_list` 或异常结构作为规划和诊断证据。
5. 当前 operation 已被 curated runner 覆盖，直接复用比临时写代码更快。

不优先使用 SDK 的场景：

1. 为了“支持 SDK”而支持 SDK。
2. hcloud 已能稳定、简洁完成，SDK 不能提供额外可靠性或处理优势。
3. 需要跨大量服务自动生成一套平行 SDK runner。
4. 用户明确要求 Terraform/IaC、import、drift 或长期 state 管理。

Agent 编写任务专用 SDK 代码时，可以调用官方 SDK 的查询或变更 API，不受该 registry 限制；但仍要
核对安装包、client/version、request model、region/endpoint、凭据类型、错误结构和完成证据。写操作
继续遵守与 hcloud 相同的风险披露、用户授权、幂等、副作用收敛和回读要求。

## 运行时规则

- 默认探测已安装 package，例如 `huaweicloudsdkecs`。
- 如果用户机器没有对应 package，优先按任务安装单个服务 package；不能安装时再选择可用 hcloud、
  Terraform 或如实报告依赖缺口。
- `scripts/hcloud_sdk_catalog.py` 可以从已安装 package 或维护期源码 fallback 读取 SDK metadata。
- `references/sdk-supplement-registry.json` 只控制 `hcloud_sdk_readonly.py` 的便捷执行范围。每个条目说明
  hcloud 对照计划、SDK 价值、风险、证据和是否允许该 runner execute；它不是 Skill 的全局 SDK 白名单。
- `scripts/hcloud_sdk_supplement_audit.py` 校验 registry 结构、边界、fallback 和 SDK metadata。
- `scripts/hcloud_sdk_readonly.py` 默认只生成计划；只有显式 `--execute` 才会调用 SDK。
- `scripts/hcloud_sdk_readonly.py` 只执行 registry 内 read-only operation。非 registry 操作不能通过这个
  runner 执行；Agent 可以回到 hcloud，或在核验官方 API 后编写任务专用 SDK 代码。

## 推荐使用顺序

1. 根据 `backend-selection.md` 判断 SDK 是证据辅助、当前任务后端，还是不需要使用。
2. 只需要 SDK metadata 时调用：

```bash
python3 scripts/hcloud_sdk_catalog.py --service ECS --operation ListFlavors --pretty
```

3. 如果明确需要 SDK 便捷只读 runner，并且 operation 已登记：

```bash
python3 scripts/hcloud_sdk_readonly.py \
  --service ECS \
  --operation ListFlavors \
  --region cn-north-4 \
  --pretty
```

4. 需要 runner 未覆盖的 API 时，先确认官方 package 和 request model，再编写最小任务代码；不要为了
   一个调用扩展通用 runner。
5. 真实 SDK 执行前确认对应 package、region/endpoint、BasicCredentials/GlobalCredentials 和凭证来源。

## 便捷 runner 准入流程

新增 SDK supplement 时按顺序执行：

1. 只有一个调用在不同任务中反复出现、接口稳定且封装能明显减少错误时，才考虑加入 registry。
2. 在 `references/sdk-supplement-registry.json` 增加条目，说明 SDK runner 的价值。
3. 确认 `fallback.runner` 指向可比较的 hcloud 路径，例如 `scripts/hcloud_resource_query.py`。
4. 默认 `execute_allowed=false`；只有低风险、只读、稳定、已有测试和人工 smoke 计划的操作才允许打开。
5. 运行：

```bash
python3 scripts/hcloud_sdk_supplement_audit.py --pretty
```

6. 若维护者机器有 SDK package 或源码 fallback，可加：

```bash
python3 scripts/hcloud_sdk_supplement_audit.py --require-metadata --pretty
```

7. 为 runner 行为补单测。真实 `--execute` 前补人工 smoke 记录。

## 候选池规则

从 SDK reference 继续吸收新能力时，优先考虑下面这类只读补充：

- CBR vault/policy 等备份姿态查询。
- RFS stack、execution plan 等 IaC 状态元数据。
- DCS instance、session、background task 等缓存可见性查询。
- HSS、SecMaster、CFW 等安全姿态 list/show 查询，但默认 `execute_allowed=false`，先用于参数和证据规划。

不要把这些能力自动变成公共 SDK 入口。只有重复需求明确、SDK package 可维护、operation 只读且经过
smoke/test 后，才进入 `sdk-supplement-registry.json`；数据库操作、密码重置、升级、kill session、
删除、启停、扩缩容等 action/mutation 不进入这个便捷 runner，但这不禁止 Agent 在用户已授权、
语义已核验且具备回读方案时使用官方 SDK 完成具体变更任务。
