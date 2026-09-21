# hcloud CLI 安装与认证指南

## 安装

> **不在运行时 curl 或下载外部脚本。** KooCLI 官方为每个平台提供独立安装包及 SHA256 校验文件，请按下方步骤下载、校验、解压后使用。若运行环境已内置 hcloud（执行 `hcloud version` 有输出），可跳过本节。
>
> **每个步骤独立执行，不要用 `&&` / `;` 串联。** 解压、赋权、移动到系统 PATH 是三个独立操作，各步骤之间请人工确认结果后再继续，避免一次性串联执行将文件写入错误路径。

### 步骤一：下载对应平台的安装包

从 [KooCLI 下载页](https://support.huaweicloud.com/qs-hcli/hcli_02_003.html) 获取适配目标系统的安装包与校验文件。官方提供的包如下（以 Linux ARM 64 位为例，其余平台同理）：

| 平台 | 安装包 | 校验文件 |
|------|--------|----------|
| Linux AMD 64 位 | `KooCLI-linux-amd64.tar.gz` | `KooCLI-linux-amd64.tar.gz_sha256` |
| Linux ARM 64 位 | `KooCLI-linux-arm64.tar.gz` | `KooCLI-linux-arm64.tar.gz_sha256` |
| macOS ARM 64 位 | `KooCLI-mac-arm64.tar.gz` | `KooCLI-mac-arm64.tar.gz_sha256` |
| Windows 64 位 | `KooCLI-windows-amd64.zip` | `KooCLI-windows-amd64.zip_sha256` |

将安装包与同名的 `_sha256` 校验文件下载到同一目录。

### 步骤二：校验 SHA256

下载完成后，务必校验安装包完整性，哈希不匹配则**停止安装**：

```bash
# 1. 读取官方校验文件中的预期哈希
cat KooCLI-linux-arm64.tar.gz_sha256
# 输出示例: <64位十六进制哈希>  KooCLI-linux-arm64.tar.gz
```

```bash
# 2. 计算本地安装包的实际哈希
# Linux:
sha256sum KooCLI-linux-arm64.tar.gz
# macOS（系统自带 shasum，无 sha256sum）:
# shasum -a 256 KooCLI-mac-arm64.tar.gz
# 人工确认：上一步读取的预期哈希与本步计算结果必须完全一致，不一致则停止
```

### 步骤三：解压

```bash
# 仅解压，不执行任何后续操作
tar -xzf KooCLI-linux-arm64.tar.gz
```

确认当前目录生成了 `hcloud` 可执行文件后再进入下一步。

### 步骤四：赋权

```bash
# 为解压出的 hcloud 添加执行权限
chmod +x hcloud
```

### 步骤五：移动到 PATH（人工确认）

> ⚠️ 此步骤将文件写入系统目录，请人工确认目标路径无冲突后再执行。

```bash
# 单独执行，确认目标路径可写、无同名文件后移动
mv hcloud /usr/local/bin/   # 或其他 PATH 内目录
```

### 验证

```bash
hcloud version
# 预期输出: 当前KooCLI版本:7.x.x
```

## 认证配置

> **凭据配置属用户职责域。** 本工具与本文档不代为执行 `hcloud configure set` 写入 AK/SK，仅在运行前做存在性检查；无可用 profile 时提示用户自行初始化。

### 步骤一：存在性检查（工具自动执行）

```bash
# 列出已配置的 profile，确认是否已有可用凭据
hcloud configure list
```

- 若输出中存在 profile（如 `default`）且后续只读调用能正常返回 → 认证就绪，跳到 [验证认证](#验证认证)。
- 若无 profile，或只读调用报认证失败 → 进入步骤二。

### 步骤二：用户自行初始化凭据（由用户执行）

```bash
# 交互式初始化 default profile，按提示输入 AK / SK
hcloud configure init
```

> 此命令由用户本人执行并自行输入凭据；工具与文档不代写、不接触 AK/SK 明文。
> 多 profile 管理等进阶用法请参考 [KooCLI 官方文档](https://support.huaweicloud.com/qs-hcli/hcli_02_003.html)，同样由用户自行配置。

### 环境变量（仅用于脚本建议性检查，非 hcloud 认证方式）

> ⚠️ **KooCLI 不通过环境变量认证**。hcloud 的认证只能通过上述 profile（`hcloud configure init`）或命令行参数（`--cli-access-key`/`--cli-secret-key`）完成。以下环境变量仅被 `scripts/prepare.py` 用于检查"AK/SK 是否已配置"的建议性检查项，不影响 hcloud 的实际认证。

```bash
# 以下环境变量被脚本用于建议性检查（设置其中任意一组即可）
export HUAWEICLOUD_SDK_AK="你的AK"
export HUAWEICLOUD_SDK_SK="你的SK"
```

## 验证认证

```bash
# 列出 RDS 实例，验证认证是否成功
hcloud RDS ListInstances --cli-region=cn-north-1
```

## 常见问题

### Q: hcloud 命令未找到？

确保 `hcloud` 所在目录在 PATH 中：

```bash
export PATH="$PATH:/path/to/hcloud"
```

### Q: 认证失败，提示 AK/SK 无效？

- 检查 AK/SK 是否正确（无多余空格）
- 确认 AK/SK 对应的 IAM 用户拥有 RDS 操作权限
- 重新执行 `hcloud configure init` 自行配置凭据

### Q: 区域 ID 如何获取？

参考 [华为云区域列表](https://support.huaweicloud.com/regionendpoints/index.html)，常用区域：

| 区域 | ID |
|------|-----|
| 华北-北京一 | cn-north-1 |
| 华北-北京四 | cn-north-4 |
| 华东-上海一 | cn-east-3 |
| 华南-广州 | cn-south-1 |
