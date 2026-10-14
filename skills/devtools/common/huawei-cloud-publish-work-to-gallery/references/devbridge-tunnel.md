# DevBridge 隧道运行要点（Linux 走内置 skill）

## 平台分工

| 平台 | 隧道 |
|------|------|
| **Linux（目标环境）** | 加载内置 skill **`huawei-cloud-devbridge-tunnel`**，按其说明完成开隧道并取得 `envUrl`；不臆造/不自行拼 devbridge 命令 |
| **Windows** | **不使用 DevBridge**（无内置隧道能力），直接 `envUrl=""` |

> 2026-09-20 起：本发布 skill 不再内置 devbridge 下载/登录/spawn 脚本。隧道逻辑完全由仓库技能 `huawei-cloud-devbridge-tunnel` 承载（该 skill 位于本仓库 `skills/devtools/devbridge/huawei-cloud-devbridge-tunnel/`），仓库内只声明委托与降级出口，避免与技能本体双源漂移。

## Linux：开隧道（委托内置 skill）

1. **加载内置 skill** `huawei-cloud-devbridge-tunnel`，按其操作说明执行（典型流程：创建隧道 → 配置端口 → 启动 host → 从日志解析公网 URL）。
2. 取到 `envUrl`（形如 `https://<tunnelId>-<port>.<region>-bridge.myhuaweicloud.com`）后继续 Step 3。
3. **降级出口**：内置 skill 不可用 / 隧道失败 / 无公网访问地址 → **`envUrl=""` 照常发布**（作品仍可提交，仅无在线访问地址）。

## 清理

**禁止在发布流程结束后自动清理隧道**：不停 host、不删隧道，除非用户明确要求。隧道可能被后续发布 / 409 改名重试复用，发布结束 ≠ 隧道生命周期结束；未开隧道则无清理动作。

## 注意

- 隧道为联调/演示用途，非生产对外服务；公开分享内容才开匿名访问，含敏感数据的服务勿开。
- `envUrl` 为**可选**字段（平台接受空串占位），隧道开不起绝不阻塞发布。