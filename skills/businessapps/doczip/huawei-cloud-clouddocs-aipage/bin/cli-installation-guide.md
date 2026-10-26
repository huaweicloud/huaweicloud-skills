---
name: clouddocs-cli-install
version: 1.0.0
description: "clouddocs-cli 安装子技能（仅支持 Windows）：检测本机是否已安装 clouddocs-cli，未安装则执行本目录 windows/install-windows.ps1 一键安装（解压安装包 → 装到 %USERPROFILE%\\bin → 加入用户 PATH → 自检 --help）。宿主在运行依赖 clouddocs-cli 的主技能前先检测，未安装则按本技能完成安装。"
triggers:
  - 安装clouddocs-cli
  - clouddocs-cli 未安装
  - 部署clouddocs-cli
  - 初始化云文档环境
  - 主技能前置检查发现找不到 clouddocs-cli
not_for:
  - macOS / Linux 上的 clouddocs-cli 安装（本技能仅覆盖 Windows）
  - clouddocs-cli 登录认证（auth login）
  - 配置服务地址（config init --host）
metadata:
  requires:
    bins: ["powershell"]
---

# clouddocs-cli 安装（Windows 一键安装子技能）

把 `clouddocs-cli` 装到本机并加入 PATH，供依赖它的主技能使用。**仅支持 Windows**；macOS / Linux 暂不支持，直接向用户说明「当前仅支持 Windows 安装」。

## 安装包位置与获取渠道 ★

安装包与脚本在**本技能目录**下：

| 文件                                                               | 说明                             |
| ------------------------------------------------------------------ | -------------------------------- |
| `<技能基目录>/bin/windows/clouddocs-cli-v<版本>-windows-amd64.zip` | 安装包（内含 clouddocs-cli.exe） |
| `<技能基目录>/bin/windows/install-windows.ps1`                     | 一键安装脚本（免管理员权限）     |

`install-windows.ps1` 会自动在**脚本同目录**查找 `clouddocs-cli*.zip`（优先）或 `clouddocs-cli.exe`，无需手动指定 `-Package`。

### 安装包获取渠道

安装包**不随技能仓库/PR 分发**（clouddocs-cli 为内部工具，其二进制安装包由维护方独立发布）。如脚本同目录未找到安装包，按以下渠道获取：

| 渠道                                         | 说明                                                                                       |
| -------------------------------------------- | ------------------------------------------------------------------------------------------ |
| 内部软件分发仓（OBS / 内部制品仓）           | 向 clouddocs-cli 维护团队申请访问权限后检索下载                                           |
| 包名规范                                     | `clouddocs-cli-<版本>[-<环境>]-windows-amd64.zip`（环境后缀：`-m3sdv` 测试 / `-m3prod` 生产） |
| 版本示例                                     | `0.5.7`                                                                                    |
| 下载后放置位置                               | `<技能基目录>/bin/windows/`（与 `install-windows.ps1` 同目录）                             |

## 步骤 1. 检测是否已安装

```bash
command -v clouddocs-cli     # Windows cmd/PowerShell 用: where clouddocs-cli / Get-Command clouddocs-cli
```

- **能找到** → 已安装，跳过安装直接结束（可顺手 `clouddocs-cli --help` 确认可执行）。
- **找不到** → 走步骤 2 安装。
- 兜底再查安装目录：`%USERPROFILE%\bin\clouddocs-cli.exe` 存在也可视为已安装（PATH 可能尚未刷新，见步骤 4）。

## 步骤 2. 执行安装

在任一 shell 中运行（`<技能基目录>` = 本技能所在目录，即 `bin/` 的上一级）：

```bash
powershell -ExecutionPolicy Bypass -File "<技能基目录>/bin/windows/install-windows.ps1"
```

脚本自动完成：解压 zip → 复制 `clouddocs-cli.exe` 到 `%USERPROFILE%\bin\` → 加入用户 PATH（`-SkipPath` 可跳过）→ 自检 `--help`。

> 可选：脚本支持 `-ServiceHost <内部服务地址>`，装完顺手执行 `clouddocs-cli config init --host <地址>`（若不传，需在后续步骤自行配置服务地址）。

## 步骤 3. 验证

```bash
clouddocs-cli --help        # 能输出帮助即安装成功
```

## 步骤 4. PATH 刷新注意事项 ★

**PATH 在进程启动时读取**，安装脚本写入的是用户级 PATH，**当前已打开的终端/shell 会话可能仍提示找不到命令**。三种处理方式任选：

1. **新开终端/shell 窗口**再验证（最稳妥）；
2. 当前会话重新读取用户 PATH 后使用（bash：`export PATH="$USERPROFILE/bin:$PATH"`）；
3. 直接用全路径调用：`"$USERPROFILE/bin/clouddocs-cli.exe" --help`。

## 安装后的必做配置（由主技能前置检查接续）

安装只解决「命令存在」，使用前还需：

```bash
clouddocs-cli config init --host <服务地址>              # 服务地址已配置可跳过
clouddocs-cli auth login --no-wait --json                # 立即返回验证 URL + device_code（禁止直接 auth login——阻塞式会挂起）
powershell.exe -NoProfile -Command "Start-Process '<verification_url>'"  # 自动打开浏览器授权页（Windows），URL 同时交给用户
clouddocs-cli auth login --device-code <device_code>     # 后台运行续接轮询（默认最多 240s），用户授权成功即自动完成，无需人工通知
clouddocs-cli auth status                                # 显示 ready 即就绪
```

## 约束

- **只允许通过 `install-windows.ps1` 安装**，禁止手动解压复制替代（脚本同时负责 PATH 与自检）。
- 安装是**一次性操作**：检测到已安装即跳过，不重复执行安装脚本。
- 安装过程向用户输出简洁进度（如「正在安装 clouddocs-cli...」/「clouddocs-cli 安装完成」），细节静默。
