# CLI安装指南 - 华为云OBS对象存储管理

本skill需要两个CLI工具：hcloud（KooCLI）和obsutil。

## 目录

- [hcloud (KooCLI) 安装](#hcloud-kocli-安装)
- [obsutil 安装](#obsutil-安装)
- [凭证配置](#凭证配置)
- [验证安装](#验证安装)
- [故障排除](#故障排除)

---

## hcloud (KooCLI) 安装

### macOS

```bash
# 使用Homebrew安装
brew install hcloudcli

# 或直接下载
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-macos-amd64.tar.gz
tar -xzf hcloudcli-macos-amd64.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/
```

### Linux (x86_64)

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-linux-amd64.tar.gz
tar -xzf hcloudcli-linux-amd64.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/
```

### Linux (ARM64)

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-linux-arm64.tar.gz
tar -xzf hcloudcli-linux-arm64.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/
```

### Windows

```powershell
# 下载并解压
Invoke-WebRequest -Uri "https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-windows-amd64.zip" -OutFile "hcloudcli.zip"
Expand-Archive hcloudcli.zip
# 将hcloud.exe添加到PATH
```

---

## obsutil 安装

### macOS

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_darwin_amd64.tar.gz
tar -xzf obsutil_darwin_amd64.tar.gz
chmod +x obsutil_darwin_amd64_*
sudo mv obsutil_darwin_amd64_*/obsutil /usr/local/bin/
```

### Linux (x86_64)

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_linux_amd64.tar.gz
tar -xzf obsutil_linux_amd64.tar.gz
chmod +x obsutil_linux_amd64_*
sudo mv obsutil_linux_amd64_*/obsutil /usr/local/bin/
```

### Linux (ARM64)

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_linux_arm64.tar.gz
tar -xzf obsutil_linux_arm64.tar.gz
chmod +x obsutil_linux_arm64_*
sudo mv obsutil_linux_arm64_*/obsutil /usr/local/bin/
```

### Windows

```powershell
Invoke-WebRequest -Uri "https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_windows_amd64.zip" -OutFile "obsutil.zip"
Expand-Archive obsutil.zip
# 将obsutil.exe添加到PATH
```

---

## 凭证配置

### hcloud 凭证配置

#### 方式一：交互式配置（推荐）

```bash
hcloud configure
# 按提示输入：
# - 区域（如cn-south-1）
# - AK（Access Key ID）
# - SK（Access Key Secret）
```

#### 方式二：环境变量

```bash
export HUAWEICLOUD_SDK_AK=<your-access-key-id>
export HUAWEICLOUD_SDK_SK=<your-access-key-secret>
```

#### 方式三：非交互式配置

```bash
hcloud configure set --cli-profile=default --region=cn-south-1 --access-key-id=<AK> --secret-access-key=<SK>
```

> **⚠️ 安全警告**：方式三会在命令历史中暴露AK/SK，仅在安全环境中使用。

### obsutil 凭证配置

```bash
obsutil config -ak=<AK> -sk=<SK> -e=obs.cn-south-1.myhuaweicloud.com
```

> **⚠️ obsutil的Endpoint格式**
>
> OBS Endpoint格式：`obs.<region-id>.myhuaweicloud.com`
>
> 常见Endpoint：
>
> | 区域 | Endpoint |
> |------|----------|
> | cn-north-1 | obs.cn-north-1.myhuaweicloud.com |
> | cn-north-4 | obs.cn-north-4.myhuaweicloud.com |
> | cn-east-2 | obs.cn-east-2.myhuaweicloud.com |
> | cn-east-3 | obs.cn-east-3.myhuaweicloud.com |
> | cn-south-1 | obs.cn-south-1.myhuaweicloud.com |
> | ap-southeast-1 | obs.ap-southeast-1.myhuaweicloud.com |

---

## 验证安装

### 验证hcloud

```bash
# 检查版本
hcloud version
# 预期：>= 3.2.0

# 测试认证
hcloud OBS ListAllMyBucketsType --region=cn-south-1 --limit=1
```

### 验证obsutil

```bash
# 检查版本
obsutil version
# 预期：>= 5.5.0

# 测试认证（列出桶，限制1个）
obsutil ls -limit=1
```

---

## 故障排除

### hcloud 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `hcloud: command not found` | 未安装或不在PATH中 | 安装hcloud或将路径添加到PATH |
| `authentication failed` | 凭证无效或过期 | 重新配置凭证 |
| `insufficient permissions` | IAM权限不足 | 添加所需IAM策略 |
| `region not found` | 区域ID错误 | 使用正确的区域ID |

### obsutil 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `obsutil: command not found` | 未安装或不在PATH中 | 安装obsutil或将路径添加到PATH |
| `Status code: 403` | AK/SK错误或权限不足 | 重新运行 `obsutil config` 配置凭证 |
| `Status code: 404` | 桶不存在 | 确认桶名正确 |
| `connection timeout` | 网络问题或Endpoint错误 | 检查网络连接和Endpoint配置 |

---

## 安全最佳实践

1. **禁止在对话中直接提供AK/SK** - 始终通过交互式配置或环境变量
2. **定期轮换AK/SK** - 建议每90天更换一次
3. **使用IAM临时凭证** - 优先使用IAM代理委托或临时凭证
4. **最小权限原则** - 只授予所需最小权限
5. **审计日志** - 开启OBS桶日志记录访问请求
6. **obsutil凭证文件权限** - 确保obsutil配置文件权限为600

---

## 官方文档

- [hcloud安装指南](https://support.huaweicloud.com/cli/cli_hcloud_install.html)
- [obsutil安装指南](https://support.huaweicloud.com/utiltg-obs/obs_11_0003.html)
- [obsutil配置指南](https://support.huaweicloud.com/utiltg-obs/obs_11_0005.html)
- [OBS区域与Endpoint](https://support.huaweicloud.com/devg-obs/obs_03_0110.html)
