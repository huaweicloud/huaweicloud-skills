# DevBridge 隧道运行注意事项

## 安装

### Linux / macOS

```bash
curl -fsSL https://res-hd.hc-cdn.cn/sharedata/hdspace/devbridge/install.sh | bash
```

> ⚠️ **headless 环境（无 tty）注意事项：**
> 安装脚本会交互式询问「是否清除旧配置数据」，在无 `/dev/tty` 的 headless 环境（如 CI 容器、AI DevSpace）中会报错：
> ```
> main: line 324: /dev/tty: No such device or address
> main: line 325: response: unbound variable
> ```
> **解决方案**：先手动删除旧配置目录，再通过管道传入 `y` 绕过交互：
> ```bash
> rm -rf /root/.huawei/devbridge 2>/dev/null
> echo "y" | curl -fsSL https://res-hd.hc-cdn.cn/sharedata/hdspace/devbridge/install.sh | bash
> ```
> 若已存在预装的二进制（如 `/root/.huawei/bin/devbridge`），可直接复用，跳过安装。

### Windows (PowerShell 5.1+)

```powershell
irm https://res-hd.hc-cdn.cn/sharedata/hdspace/devbridge/install.ps1 | iex
```

## 登录方式

DevBridge `host` 命令需要 AK/SK 凭证，SSO 登录无法开隧道。

| 登录方式                  | `host` 可用 | 说明                                                            |
| ------------------------- | ----------- | --------------------------------------------------------------- |
| SSO / Non-HuaweiCloud IAM | 否          | 浏览器 SSO 跳转，不存储 AK/SK，`host` 报 `credential not found` |
| AK/SK / Huawei Cloud IAM  | 是          | 凭证存储到 credential store                                     |

## STS 临时凭证：三件套缺一不可

环境中的 AK/SK 常为临时 STS 凭证（带 `securityToken`）。仅传 AK/SK 不传 `securityToken` 会报 `AKSK expired or invalid`。

```bash
# 正确登录方式（STS 临时凭证）
devbridge auth login \
  --access-key "$HW_ACCESS_KEY" \
  --secret-key "$HW_SECRET_KEY" \
  --security-token "$HW_SECURITY_TOKEN"
```

- 若使用永久 AK/SK（非 STS），则不需要 `securityToken`，仅传 AK/SK 即可。
- 三个环境变量 `HW_ACCESS_KEY`、`HW_SECRET_KEY`、`HW_SECURITY_TOKEN` 必须同时存在。

## 验证登录状态

```bash
devbridge auth status
# 应输出: Logged in (Huawei Cloud IAM)
```

若输出 `Non-HuaweiCloud IAM`，说明当前为 SSO 登录，需重新用 AK/SK 登录。

## 开隧道

```bash
devbridge host -p <port> -e 2
```

- `-e 2`：2 小时有效期。
- Host 成功后输出隧道 ID 和访问地址：`https://<tunnelId>-<port>.cn-north-4-bridge.myhuaweicloud.com`
- **`devbridge host` 是前台进程，`Ctrl+C` 会停止隧道。** 自动化场景中需后台运行。
- **⚠️ AI DevSpace 容器时长限制：** 隧道实际有效期受 AI DevSpace 容器剩余有效期限制（取两者较低值），容器超时销毁后需重新拉取仓库并重建隧道。详见 SKILL.md Step 2。

## 常见故障排查

| 错误信息                  | 根因                           | 修复                                                               |
| ------------------------- | ------------------------------ | ------------------------------------------------------------------ |
| `credential not found`    | SSO 登录，无 AK/SK 凭证        | 改用 `devbridge auth login --access-key ... --secret-key ...` 登录 |
| `AKSK expired or invalid` | STS 临时凭证缺 `securityToken` | 补传 `--security-token "$HW_SECURITY_TOKEN"`                       |
| `HD.83700031: Logged in as sub-account. Master-account need to sign latest agreement` | 子账号登录，主账号未签署 DevBridge 最新协议 | ① 主账号签署协议后重试；② 或跳过隧道，置 `envUrl=""` 继续发布（不影响发布，仅无在线访问地址） |
| 隧道进程意外退出          | `Ctrl+C` 或终端关闭            | 重新执行 `devbridge host -p <port> -e 2`                           |
