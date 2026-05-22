# 镜像源配置参考

## 华为云镜像源

华为云提供了 Terraform Provider 的镜像服务，可加速国内下载。

### Provider 镜像

**基础 URL**: `https://mirrors.huaweicloud.com/terraform/registry.terraform.io/`

**HuaweiCloud Provider**:
- 版本列表: `https://mirrors.huaweicloud.com/terraform/registry.terraform.io/huaweicloud/huaweicloud/`
- 版本 JSON: `https://mirrors.huaweicloud.com/terraform/registry.terraform.io/huaweicloud/huaweicloud/{version}.json`
- 下载文件: `https://mirrors.huaweicloud.com/terraform/registry.terraform.io/huaweicloud/huaweicloud/terraform-provider-huaweicloud_{version}_{os}_{arch}.zip`

### 版本 JSON 格式

```json
{
  "archives": {
    "linux_amd64": {
      "hashes": ["h1:xxx"],
      "url": "terraform-provider-huaweicloud_1.90.0_linux_amd64.zip"
    },
    "darwin_arm64": {
      "hashes": ["h1:xxx"],
      "url": "terraform-provider-huaweicloud_1.90.0_darwin_arm64.zip"
    }
  }
}
```

## 官方源

### Terraform 本体

**Releases URL**: `https://releases.hashicorp.com/terraform/`

**下载格式**: `https://releases.hashicorp.com/terraform/{version}/terraform_{version}_{os}_{arch}.zip`

**版本 API**: `https://releases.hashicorp.com/terraform/index.json`

### Provider Registry

**Registry API**: `https://registry.terraform.io/v1/providers/huaweicloud/huaweicloud`

**下载 API**: `https://registry.terraform.io/v1/providers/huaweicloud/huaweicloud/{version}/download/{os}/{arch}`

**下载源**: GitHub Releases (`https://github.com/huaweicloud/terraform-provider-huaweicloud/releases/`)

## CLI 配置

### ~/.terraformrc

```hcl
plugin_cache_dir = "$HOME/.terraform.d/plugin-cache"

provider_installation {
  filesystem_mirror {
    path    = "$HOME/.terraform.d/plugins"
    include = ["registry.terraform.io/huaweicloud/*"]
  }
  direct {
    include = ["*/*"]
  }
}
```

### 环境变量

```bash
# 禁用远程获取（离线模式）
export TF_PLUGIN_CACHE_DIR="$HOME/.terraform.d/plugin-cache"

# 使用本地镜像
export TF_CLI_CONFIG_FILE="$HOME/.terraformrc"
```

## 离线安装

### 预下载文件

1. **Terraform 本体**: 从官方 releases 下载 zip 文件
2. **Provider**: 从华为云镜像或 GitHub releases 下载 zip 文件

### 手动安装步骤

```bash
# 1. 解压 Terraform
unzip terraform_1.9.8_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# 2. 创建 Provider 目录
mkdir -p ~/.terraform.d/plugins/registry.terraform.io/huaweicloud/huaweicloud/1.90.0/linux_amd64

# 3. 解压 Provider
unzip terraform-provider-huaweicloud_1.90.0_linux_amd64.zip \
  -d ~/.terraform.d/plugins/registry.terraform.io/huaweicloud/huaweicloud/1.90.0/linux_amd64/

# 4. 配置 CLI
# (参考上面的 ~/.terraformrc 配置)
```

## 镜像源优先级

| 资源 | 优先 | 备用 |
|------|------|------|
| Terraform 本体 | 官方 releases | - |
| Provider | 华为云镜像 | GitHub releases |
