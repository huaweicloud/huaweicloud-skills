# 验证方法 - huawei-cloud-architecture-resource-archive

## 概述

本文档定义本技能的验证方法，覆盖**每个执行步骤**的成功/失败判断标准。验证分为三个层级：安装验证、配置验证、功能验证；功能验证进一步覆盖流水线各步骤（查询、转换、标记表生成）及最终产物。

验证按顺序执行，前一层级通过后才进入下一层级：

```
安装验证 → 配置验证 → 功能验证（查询 → 转换 → 标记表生成 → 产物核验）
```

---

## 1. 安装验证

验证 KooCLI 与 Python 依赖是否正确安装。

| 检查项 | 验证命令 | 成功标准 |
|--------|---------|---------|
| KooCLI 已安装 | `hcloud version` | 返回版本号 ≥ 7.2.2 |
| Python 版本 | `python3 --version` | ≥ 3.8 |
| openpyxl | `python3 -c "import openpyxl; print(openpyxl.__version__)"` | 无报错，打印版本号 |
| kubernetes | `python3 -c "import kubernetes; print(kubernetes.__version__)"` | 无报错，打印版本号 |

```bash
# 一键验证（推荐）：Step 1 环境检查脚本
python scripts/check_koocli.py
```

**✅ 成功**：所有检查项通过，输出显示依赖已就绪。

**❌ 失败**：某项检查未通过。处理方式：按脚本提示安装对应依赖后重新执行。

---

## 2. 配置验证

验证 AK/SK 凭证是否正确配置。

| 检查项 | 验证命令 | 成功标准 |
|--------|---------|---------|
| 环境变量 AK | `test -n "$HW_ACCESS_KEY"` | 非空（不打印值） |
| 环境变量 SK | `test -n "$HW_SECRET_KEY"` | 非空（不打印值） |
| KooCLI 配置 | `hcloud configure list` | 显示有效的 AK/SK 和 region 配置 |

> ⚠️ 安全规则：禁止用 `echo` 或任何命令输出 AK/SK 明文值。使用 `test -n` 仅检查存在性，不暴露值。

**✅ 成功**：凭证已配置且有效。

**❌ 失败**：凭证未配置或无效。处理方式：参考 [CLI 安装指南](cli-installation-guide.md) 配置 AK/SK 后重新验证。

---

## 3. 功能验证

### 3.1 单服务查询验证

验证 KooCLI 能正常调用云服务 API。

| 检查项 | 验证命令 | 成功标准 |
|--------|---------|---------|
| ECS 查询 | `hcloud ECS ListServersDetails --cli-region=cn-north-4` | 返回 HTTP 200 和实例列表 |
| VPC 查询 | `hcloud VPC ListVpcs --cli-region=cn-north-4` | 返回 VPC 列表 |
| RDS 查询 | `hcloud RDS ListInstances --cli-region=cn-north-4` | 返回实例列表 |
| CCE 查询 | `hcloud CCE ListClusters --cli-region=cn-north-4` | 返回集群列表（代理环境下自动解析 project_id） |
| SFS 查询 | `hcloud SFSTurbo ListShares --cli-region=cn-north-4` | 返回文件系统列表 |

**✅ 成功**：命令返回有效 JSON（资源列表或空列表），无 USE_ERROR/OPENAPI_ERROR。

**❌ 失败**：命令报错。处理方式：
- `USE_ERROR` → 检查服务名/操作名/参数是否正确（用 `hcloud --help` 确认）
- `OPENAPI_ERROR` / 权限错误 → 检查 IAM 权限，参考 [IAM 权限策略](iam-policies.md)
- 网络超时 → 检查代理配置

### 3.2 流水线查询步骤验证（Step 2）

验证全量查询能发现资源并正确保存，**不依赖外部参照**（无需人工对照控制台）。

```bash
python scripts/run_pipeline.py --account test --services ecs,vpc --regions cn-north-4
```

**✅ 成功**（全部满足）：
- 每个服务打印 `saved ... (N rows)`，N 为可解析的非负整数
- 保存的 JSON 文件内容为有效 JSON（非 `USE_ERROR`/`OPENAPI_ERROR`/错误文本）
- **冒烟服务计数 > 0**：VPC、ECS、子网等任何账号都必然有资源的基础服务，计数必须 ≥ 1
- 无 FATAL 错误

**❌ 失败**：
- 冒烟服务（VPC/ECS/子网）计数为 0 → 查询链路故障，检查服务名/操作名/凭证/代理
- 某服务保存的 JSON 是错误文本（`USE_ERROR` 等）→ 该服务调用失败，用 `hcloud --help` 核对服务名/操作名/参数
- 查询报 FATAL 错误 → 查看错误日志定位原因

### 3.3 转换步骤验证（Step 3）

验证 raw JSON 正确转换为标记表兼容格式。

**✅ 成功**：
- 日志显示 `converted` 输出，行数与查询计数一致
- `converted/<SVC>/temp/*.json` 中存在资源行（`rows` 非空）

**❌ 失败**：
- 转换行数为 0 但查询有数据 → 转换器字段映射错误（如 id/name 不匹配）
- 提示 `no KooCLI query results found` → raw 目录缺失或文件格式错误

### 3.4 标记表生成步骤验证（Step 4）

验证标记表 Excel 和 store JSON 正确生成。

**✅ 成功**：
- 生成 `关键资源标记表.xlsx` 和 `_resource_store.json`
- store 中 `rows` 数量与转换行数一致

**❌ 失败**：提示 `no resource rows found` → 转换输出为空，回溯 Step 3。

### 3.5 产物内容核验

验证标记表内容完整正确。

| 检查项 | 验证方式 | 成功标准 |
|--------|---------|---------|
| 资源行 | 读取 `_resource_store.json` 的 `rows` | 每条资源出现一次，`resource_id` 无重复 |
| 类型覆盖 | 统计 `resource_type` 去重数 | 覆盖本次查询的全部服务（查询阶段有数据的服务在标记表中都有对应类型） |
| 规格列 | 检查数据库/CCE/CloudTable/Workspace 行的 `spec` | 非空，含服务特定键（如 规格/vCPU/内存/版本/节点规格） |
| 下游推断 | 检查 VPC/CCE/ER 行的 `downstream_inferred` | 有关联的资源非空 |

**✅ 成功**：行数、规格、下游推断完整准确，且与查询阶段（3.2）的计数一致。

**❌ 失败**：
- 某服务在查询阶段（3.2）计数 > 0，但标记表中该类型为 0 行 → 转换器字段映射错误（常见：SFS→SFSTurbo、CSS→ListClustersDetails、DMS→Kafka 等命名差异）
- 同一 `resource_id` 出现多次 → 转换去重逻辑问题

---

## 4. 端到端验证（完整流水线）

```bash
# 小范围验证（单服务单区域，推荐首次使用）
python scripts/run_pipeline.py --account test --services ecs --regions cn-north-4

# 全量验证（所有服务所有区域）
python scripts/run_pipeline.py --account test
```

**✅ 成功**：
1. Step 1-4 全部完成，无 FATAL 错误
2. 生成 `resource-output/<account>-<timestamp>/marker/关键资源标记表.xlsx`
3. 生成 `resource-output/<account>-<timestamp>/marker/_resource_store.json`
4. 标记表内容核验通过（见 3.5）

**❌ 失败**：某步骤报错。处理方式：按对应步骤的失败处理流程排查（见 3.2-3.4）。

---

## 5. 验证流程汇总

```
安装验证 → 失败？ → 安装依赖 → 重新验证
    ↓ 通过
配置验证 → 失败？ → 配置 AK/SK → 重新验证
    ↓ 通过
功能验证（3.1 单服务查询） → 失败？ → 检查服务名/权限/网络 → 重新验证
    ↓ 通过
流水线验证（3.2 查询 → 3.3 转换 → 3.4 标记表） → 失败？ → 按步骤排查 → 重新运行
    ↓ 通过
产物核验（3.5） → 失败？ → 检查转换器映射 → 重新转换
    ↓ 通过
端到端验证 → 完成
```
