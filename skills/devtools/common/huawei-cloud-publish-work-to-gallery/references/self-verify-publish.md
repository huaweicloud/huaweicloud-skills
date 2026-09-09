# 自委托发布：最小权限 STS 凭证生成与调用方身份识别

> 发布前，调用方（技能）通过 hcloud 自委托 `SELF_VERIFY` 生成**最小权限临时凭证**，把临时 AK/SK + SecurityToken 传给接口；网关用该凭证解析调用方身份（账号 ID）并注入已验证的 `X-Domain-Id`/`X-Domain-Hash` 头域，服务端（gallery）直接使用。展示时优先使用旧署名，否则取作者昵称。两个 `open-api-public` 接口（`/camps`、`/works`）均要求通过头域 `X-Tmp-Ak`/`X-Tmp-Sk`/`X-Security-Token` 传递 STS 临时凭证。作品发布成功后服务端即时领取成长积分，结果随发布响应 `data.reward` 返回。

## 一、前置条件

| 条件 | 说明 |
|------|------|
| hcloud（KooCLI）>= 3.2.0 | 华为云 CLI 工具 |
| 调用方永久/临时凭证 | 创建委托、AssumeAgency 时使用（环境变量 `HUAWEICLOUD_SDK_AK/SK`，临时凭证再配 `HUAWEICLOUD_SDK_SECURITY_TOKEN`） |
| 委托配额 | 每账号最多 192 个委托，需有空余名额 |

## 二、一次性配置：幂等创建自委托 `SELF_VERIFY`

已有同名委托则跳过，否则创建（委托方与被委托方均填调用方账号 ID = 自委托）：

```bash
REGION=cn-north-4
ACCOUNT_ID=<调用方账号ID>

# 已存在则跳过
hcloud IAM ListAgencies --cli-region=$REGION --domain_id=$ACCOUNT_ID

# 不存在才创建
hcloud IAM CreateAgency --cli-region=$REGION \
  --agency.name=SELF_VERIFY \
  --agency.domain_id=$ACCOUNT_ID \
  --agency.trust_domain_id=$ACCOUNT_ID \
  --agency.description='自委托，用于生成最小权限STS凭证以验证OpenAPI调用者身份'
```

## 三、每次发布：生成最小权限临时凭证

AssumeAgency 时传入**最小权限允许策略**（Version 必须 `"5.0"`）。策略需放行服务端做身份识别与账号名解析所需的两个只读动作：`STS.GetCallerIdentity`（返回 `account_id`，即账号 ID）与 `IAM.listAuthDomains`（返回账号名，用于身份解析；在 deny-all 下该项会被 403 拒绝）。

> **`_refresh` 元数据（重要）**：凭证落盘时同时写入 `_refresh` 字段（`accountId`、`agencyUrn`、`region`），使 `api.mjs --auto-refresh` 在收到 401 `GALLERY.AUTH.UNAUTHORIZED`（凭证过期）时能自动调 `hcloud STS AssumeAgency` 重新生成凭证并重试，无需 agent 手动干预。完整发布流程（字体安装 + Chromium 下载 + 截图 + 封面 + 图表）可能超过 900s，`_refresh` 元数据是自动刷新的前提。

> **统一用脚本生成（Python `subprocess` 直传，不经 shell，Linux/Windows 一致）**：

```bash
# Linux/macOS：hcloud 在默认路径可自检出
python <skill>/scripts/gen_sts.py --account <账号ID>
# Windows / hcloud 不在默认路径：显式指定
python <skill>/scripts/gen_sts.py --account <账号ID> --hcloud <hcloud.exe绝对路径>
```

脚本自动完成：`hcloud STS AssumeAgency`（`agency_urn=iam::<账号ID>:agency:SELF_VERIFY`，900s，最小策略）→ 落盘 `sts-creds.json`（camelCase，`api.mjs --creds-file` 直接可用）与 `sts-creds.sh`（`STS_AK/STS_SK/STS_TOKEN`）→ 写入 `_refresh` 元数据 `{accountId, agencyUrn, region, hcloudExe}`（供 401 自动刷新）。AK/SK 由 hcloud 读取（`HUAWEICLOUD_SDK_AK/SK[/SECURITY_TOKEN]` 或 hcloud 已配置）。

> **Windows**：路径用 `tempfile.gettempdir()`（`%TEMP%`）；脚本不经 PowerShell 引号/编码问题，无需再手工抄写内联 JSON/PS 模板。

> 💡 **凭证传递（核心）**：`security_token` 是超长 base64（数百~上千字符），**禁止**作为 shell 命令行参数传给 `api.mjs`/`publish-work.mjs`（Windows 命令行 8191 字符上限/转义易截断）。统一用落盘文件：
> - `api.mjs --creds-file /tmp/sts-creds.json`（自动注入 X-Tmp-Ak/X-Tmp-Sk/X-Security-Token）
> - 或 `source /tmp/sts-creds.sh` 后经环境变量 `STS_AK/STS_SK/STS_TOKEN`
> - `publish-work.mjs` 的 params JSON 已含凭证，脚本内部不经过 shell 传参。

> ⚠️ 策略使用说明：若采用严格 deny-all（仅允许 `GetCallerIdentity`），身份解析只能得到账号 ID，无法得到账号名。建议按 allow-list 同时放行账号名读取，保证身份解析完整。

## 四、网关身份识别

网关收到临时凭证后：

1. 用临时 AK/SK + SecurityToken 构建 `GlobalCredentials`（STS 与 IAM 均为 Global 级服务）。
2. `STS.GetCallerIdentity` → `account_id`（账号 / Domain ID），校验失败返回 `401 GALLERY.AUTH.UNAUTHORIZED`。
3. 用 HMAC-SHA256 派生 `domain_hash`，与 `X-Domain-Id` 一同注入头域。
4. 校验通过后**剥除** `X-Tmp-*` 临时凭证头，注入已验证的 `X-Domain-Id`/`X-Domain-Hash` 头域；gallery 按 `X-Domain-Id` fail-closed（缺失即 400）。

## 五、安全要点

- 调用方仅发送临时凭证，永久 AK/SK 始终留在本地；临时凭证由网关消费后不再下行传递。
- 临时凭证默认 900s 有效期，Session policy 最小化，网关仅可做只读身份识别。
- 无法伪造：临时凭证由 STS 签发，`GetCallerIdentity` 由网关验证真实性，应用侧只信任网关注入的身份头域。

## 六、401 自动刷新机制

完整发布流程（字体安装 + Chromium 下载 + 截图 + 封面合成 + 图表生成 + 文章撰写 + zip 打包）可能超过 STS 凭证 900s 有效期。`api.mjs --auto-refresh` 提供自动刷新：

1. `api.mjs` 收到 401 `GALLERY.AUTH.UNAUTHORIZED` 响应。
2. 读取 `--creds-file` JSON 中的 `_refresh` 元数据（`accountId`、`agencyUrn`、`region`）。
3. 调 `hcloud STS AssumeAgency` 重新生成临时凭证（`execFileSync`，不经 shell）。
4. 更新 creds 文件（保留 `_refresh` 元数据），用新凭证重试请求（仅重试一次）。
5. 若无 `_refresh` 元数据或刷新失败，原样返回 401（向后兼容）。

`publish-work.mjs` 在 params JSON 含 `_refresh` 字段时自动启用 `--auto-refresh`。agent 在 Step 1 生成 STS 凭证时写入 `_refresh` 元数据（见上方命令），后续 `--creds-file` 调用和 `publish-work.mjs` params 均自动获得刷新能力，无需 agent 手动处理过期。
