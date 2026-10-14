# IAM Policies

本 skill 按**最小权限**原则运行：执行 AK/SK **仅需 2 项 IAM 权限**——查询 Domain ID（`iam:listAuthDomains`）与自委托 `SELF_VERIFY` 换取 STS 临时凭证（`sts:agencies:assumeRole`）。作品陈列馆平台 API、DevBridge 隧道、GitCode 授权均**不属于** IAM 资源权限，详见下文说明。

## Minimum Required Permissions

| 权限 | IAM Action | 用途 | 对应脚本 / 命令 |
|------|-----------|------|-----------------|
| 查询账号 / Domain ID | `iam:listAuthDomains` | Step 1 解析 `domain_id`（`hcloud IAM KeystoneListAuthDomains`） | `node $SKILL_DIR/scripts/resolve-domain.mjs` |
| 自委托代入 `SELF_VERIFY` 委托方 | `sts:agencies:assumeRole` | Step 1 生成 900s STS 临时凭证；Step 8 发布 401 时自动刷新（仅重试一次） | `python $SKILL_DIR/scripts/gen_sts.py`、`node $SKILL_DIR/scripts/api.mjs`（`--auto-refresh`） |

> `sts:agencies:assumeRole` 的 Resource 仅限**本账号自委托** `SELF_VERIFY`（`gen_sts.py` 固定拼装 `iam::<account_id>:agency:SELF_VERIFY`），不涉及跨账号委托，无需额外授权。

### 推荐策略 JSON

将以下策略附加到执行 AK/SK 对应的 IAM 用户（或用户组）：

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:listAuthDomains"
      ],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "sts:agencies:assumeRole"
      ],
      "Resource": ["iam::*:agency:SELF_VERIFY"]
    }
  ]
}
```

## SELF_VERIFY 自委托（临时凭证会话策略）

`gen_sts.py` 通过 `hcloud STS AssumeAgency` 代入本账号自委托：

```bash
hcloud STS AssumeAgency \
  --cli-region=cn-north-4 \
  --agency_urn=iam::<account_id>:agency:SELF_VERIFY \
  --agency_session_name=publish-<ts> \
  --duration_seconds=900 \
  --policy='{"Version":"5.0","Statement":[{"Effect":"Allow","Action":["sts::GetCallerIdentity","iam::listAuthDomains"],"Resource":["*"]}]}'
```

- 会话策略（`--policy`）与托管策略**取交集**，进一步收敛临时凭证权限（仅 `sts::GetCallerIdentity` + `iam::listAuthDomains`）。
- 临时凭证写入 `--creds-out` 指定路径（SKILL.md 约定 `./sts-creds.json` 相对路径；缺省 `tmpdir/sts-creds.json`），内容为 `accessKeyId` / `secretAccessKey` / `securityToken` + `_refresh` 元数据；sh 文件（`sts-creds.sh`）为 `STS_AK` / `STS_SK` / `STS_TOKEN`。
- 发布流程中平台 API（`gallery.developer.huaweicloud.com`）通过请求头 `X-Tmp-Ak` / `X-Tmp-Sk` / `X-Security-Token` 携带临时凭证认证。

## 无需 IAM 权限的部分

| 能力 | 认证方式 | 说明 |
|------|----------|------|
| 作品陈列馆 / 训练营平台 API（`/v1/gallery/*`） | STS 临时凭证请求头 | 非 IAM 资源 API，权限由平台侧按 SELF_VERIFY 委托校验 |
| DevBridge 隧道 / 登录 | DevBridge 账户 API Key / 登录态 | 外部 SaaS，与华为云 IAM 无关（Linux 走内置 `huawei-cloud-devbridge-tunnel` skill） |
| GitCode 仓库凭证 / OAuth | 用户浏览器 OAuth 2.0 授权 | `gitcode-oauth.ensure.mjs` 本地起回调服务器，token 落盘 `~/.gitcode/auth.toml` |
| 本地工具（git / zip / 截图 / 字体） | 本地能力 | 无云上权限 |

## Security Notes

- 永久 AK/SK **仅留在本机**（环境变量或 hcloud 已配置），**绝不上传**；上传到平台的只有 900s 过期的 STS 临时凭证。
- 临时凭证文件（`sts-creds.json` / `sts-creds.sh`）在发布完成后清理（Step 8 成功路径）。
- 401 自动刷新仅重试一次；刷新失败原样返回 401，不无限重试。
- 遵循最小权限原则：不要为执行用户授予 `iam:*` / `sts:*` 等通配写权限。