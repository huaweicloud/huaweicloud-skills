# IAM Policies（IAM 权限策略）

> 本文件说明本 skill 需要的权限范围，以及**如何用官方来源核实**权限名。
> ⚠️ 本文件**不写任何未经核实的 Action 名、系统策略名或 API 路径**：凡是尚未完成官方核实的权限，一律保留 `<...>` 占位并注明「须官方核实后填入」。
> 核实方法见第 3 节；第 5 节给出本文件自身的「零编造」自查命令。

---

## 1. AK/SK 的用途与存放位置

- 本 skill 是外部 `codearts` CLI 的封装：
  - `scripts/setup.sh` / `scripts/setup.ps1` —— 检查并自动安装 CLI、收集并保存 AK/SK、检查权限配置、验证连通性；
  - `scripts/codearts_run.sh` / `scripts/codearts_run.ps1` —— 加载凭据后调用 `codearts`，并强制 stdout/退出码契约。
- AK/SK 由 **`codearts` CLI 自身**用于代表用户调用华为云 CodeArts 代码生成服务与模型服务（MaaS）接口。
- 本 skill 的脚本**只做本地文件与环境变量操作**，不直接调用 IAM 或任何华为云 OpenAPI。因此本文件描述的是「`codearts` 运行时需要什么权限」，而不是「本 skill 的脚本需要什么权限」。
- 凭据存放位置（明文，已在 SKILL.md 的安全提醒中向用户明示）：
  - Linux / macOS：`~/.bashrc` 中的 `export CODEARTS_CLI_AK=...` / `export CODEARTS_CLI_SK=...`；
  - Windows：当前用户的**用户级环境变量** `CODEARTS_CLI_AK` / `CODEARTS_CLI_SK`（`scripts/setup.ps1` 默认 `User` 作用域）。
- 清理命令（用户同意后由 Agent 执行）：

  ```bash
  bash scripts/setup.sh --clear-aksk
  ```

  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -ClearAksk
  ```

  两者都输出 `{"status":"cleared","code":0,"message":"AK/SK removed from ~/.bashrc"}` 并退出 `0`。
- ⚠️ AK/SK 属于敏感凭据：不得写入任务描述、脚本、文档或仓库文件；本 skill 全部脚本均不含硬编码凭据。

---

## 2. 最小权限原则

1. **够用即可**：只授予调用 `codearts` 所需的权限，不授予 `*:*`，不使用资源级通配 `*`。
2. **读写分开**：查询类操作（列出模型、校验连通性）与生成类操作分别列明，避免用一份高权限策略覆盖两类用途。
3. **优先系统策略、再自定义**：系统策略能满足时不要另建；必须自定义身份策略时，范围限定到实际调用的服务。
4. **凭据最小化**：建议使用专用 IAM 用户或临时安全凭证；按需授权、定期轮换、用完后用上面的清理命令删除。
5. **不落盘**：AK/SK 只保存在用户本机的环境变量 / `~/.bashrc`，不上传任何外部服务（对应 SKILL.md 的 Security Notice / Note）。

---

## 3. 官方核实流程（强制，禁止推断）

本节列出的命令**仅供人工/CI 在带凭据的环境下做官方核实**，本 skill 自身不执行它们，也不需要 `hcloud` 已安装。

必须通过以下**官方来源**至少其一取得权限名，**严禁凭命名规律推断、严禁改写大小写**：

| # | 官方来源 | 命令 / 入口 | 必须逐字抄下来的内容 |
|---|---------|------------|--------------------|
| ① | KooCLI 授权项 Schema 查询 | `hcloud IAM GetAuthorizationSchemaV5 --cli-region=cn-north-4 --service_code=<service_code>` | 响应中该服务真实的 `name` 与 `urn_template`，**逐字复制，不要重新大小写化或规范化** |
| ② | 官方《权限及授权项说明》 | 华为云支持中心 → 目标服务 → 《权限及授权项说明》（服务列表见下） | 标准的 `服务:资源类型:操作` 三元组写法 |
| ③ | 系统策略查询 | `hcloud IAM ListPoliciesV5 --cli-region=cn-north-4`，随后 `hcloud IAM GetPolicyVersionV5 --cli-region=cn-north-4 --policy_id=<policy_id> --version_id=<version_id>` | 真实存在的系统策略名，以及 `document` 字段中的真实 JSON 语法 |

参数占位符的取值必须来自上一步的真实响应或控制台，**不得猜测**：

- `<service_code>` —— 目标服务的服务代码，来自官方服务列表 / Schema 响应；
- `<policy_id>` / `<version_id>` —— 来自 `ListPoliciesV5` 的真实响应。

官方入口（仅使用下列已存在的入口，不要拼接深链）：

- 华为云 API Explorer：https://console.huaweicloud.com/apiexplorer/#/openapi
- IAM 访问密钥用户指南：https://support.huaweicloud.com/usermanual-iam/iam_02_0003.html
- IAM 控制台「我的凭证 → 访问密钥」：https://console.huaweicloud.com/iam/?#/mine/accessKey

### 核实记录表（由执行核实的人填写；未填写的行视为**未核实**）

| 用途 | 官方来源（①/②/③） | 抄录到的 Action（逐字） | 核实人 / 日期 |
|------|------------------|----------------------|--------------|
| 列出当前账号与区域可用的模型（`codearts models`） | 待填写 | `<须官方核实后填入>` | — |
| 提交代码生成任务（`codearts run --format json`） | 待填写 | `<须官方核实后填入>` | — |
| 附件随任务描述提交（wrapper 的 `-f`） | 待填写 | `<须官方核实后填入>` | — |

> 说明：`codearts` 是运行时从华为云 OBS 下载安装的**外部二进制**，其内部调用路径不在本仓库内。上面三行必须由核实人用本节的官方来源实测后填写；**在核实完成之前，本文件不会出现任何看起来像 Action 的字符串**。

---

## 4. IAM 5.0 身份策略骨架

**版本（Version）规则**（对齐华为云官方策略规范）：

- IAM 5.0 身份策略使用 `"Version": "5.0"`（系统策略与现代自定义策略的标准）；
- 仅当需要兼容传统 IAM v3 模板时才使用 `"Version": "1.1"`；
- **禁止书写未经官方验证的版本号**（例如 `"1.0"`）。

**骨架**（`Action` 处为占位，**须经第 3 节官方来源核实后填入**）：

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "<SERVICE_CODE>:<RESOURCE_TYPE>:<ACTION>"
      ]
    }
  ]
}
```

**若直接引用系统策略**，策略名同样必须来自 `ListPoliciesV5` 的真实响应，此处保留占位：

```text
<系统策略名——须经 ListPoliciesV5 官方核实后填入>
```

**读写分离模板**（占位保留；核实后把只读 Action 放进第一条 Statement，写类 Action 放进第二条）：

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Sid": "ReadOnlyForConnectivityCheck",
      "Effect": "Allow",
      "Action": [
        "<READ_ONLY_ACTION——须官方核实后填入>"
      ]
    },
    {
      "Sid": "WriteForCodeGeneration",
      "Effect": "Allow",
      "Action": [
        "<WRITE_ACTION——须官方核实后填入>"
      ]
    }
  ]
}
```

---

## 5. 本文件的「零编造」自查

```bash
# 1) 不应出现任何被引号包裹的具体 Action 字面量（形如 服务:资源类型:操作 的三段式）
grep -nE '"[a-z0-9_-]+:[a-z0-9_-]+:[a-z0-9_*]+"' references/iam-policies.md \
  && echo "FAIL: concrete Action literal found" || echo "OK: no concrete Action literal"

# 2) 不应出现具体的系统策略名（形如 <服务名> 加 FullAccess / ReadOnlyAccess）
grep -nE '"[A-Za-z0-9]+ [A-Za-z]+Access"' references/iam-policies.md \
  && echo "FAIL: system-policy name literal found" || echo "OK: no system-policy name literal"

# 3) 本文件出现的 http(s) 链接必须只有第 3 节列出的 3 个官方入口
grep -noE 'https?://[^ )]+' references/iam-policies.md | sort -u
```

预期：前两条都输出 `OK...`（本文件只保留 `<...>` 占位，所有具体名称等待官方核实后由核实人填入）；第 3 条恰好列出 3 个链接，分别是 API Explorer、IAM 访问密钥用户指南、IAM 控制台访问密钥。
