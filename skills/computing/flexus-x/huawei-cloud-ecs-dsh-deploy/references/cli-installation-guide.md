# CLI 安装指南

## 概述

本文档说明如何安装和配置华为云命令行工具（KooCLI）以及本技能所需的依赖。

## 1. Python 环境安装

### Linux/macOS
```bash
# Check Python version
python3 --version

# If not installed, use package manager
# Ubuntu/Debian
sudo apt update && sudo apt install python3 python3-pip -y

# CentOS/RHEL
sudo yum install python3 python3-pip -y

# macOS (with Homebrew)
brew install python3
```

### 验证安装
```bash
python3 --version
# Expected output: Python 3.8.x or higher
```

## 2. 依赖包安装

```bash
pip install requests huaweicloudsdkcore huaweicloudsdkecs huaweicloudsdkcoc
```

> 💡 国内环境可指定华为云 pip 镜像源加速安装。注意：`pip` 不读取 `pyproject.toml` 中的镜像配置，需显式传入：
> ```bash
> pip install -i https://repo.huaweicloud.com/repository/pypi/simple requests huaweicloudsdkcore huaweicloudsdkecs huaweicloudsdkcoc
> ```
> 也可持久化配置：
> ```bash
> pip config set global.index-url https://repo.huaweicloud.com/repository/pypi/simple
> ```
>
> 注：直接运行 `deploy_dsh.py` 时会自动安装缺失依赖，且已内置华为云镜像（`-i` 参数），无需手动配置。

### 验证安装
```bash
python3 -c "import huaweicloudsdkcore; print('SDK installed successfully')"
```

## 3. 华为云 KooCLI 安装（可选）

如果需要使用 KooCLI 进行调试：

### Linux
```bash
curl -l https://hwcloudcli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o hcloud_install.sh
bash hcloud_install.sh
```

### macOS
```bash
curl -l https://hwcloudcli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o hcloud_install.sh
bash hcloud_install.sh
```

### 验证安装
```bash
hcloud version
# Expected output: KooCLI version: x.x.x
```

## 4. AK/SK 配置

### 获取 AK/SK

1. 登录华为云控制台：https://console.huaweicloud.com/
2. 点击右上角头像 → 我的凭证
3. 左侧选择访问密钥
4. 点击新增访问密钥
5. 下载 CSV 文件（包含 AK 和 SK）

### 配置方式

凭证统一在**运行时**通过 `os.environ.get()` 从环境变量注入，代码中不出现任何明文密钥。

**方式一：环境变量注入（首选，强烈推荐）**

✅ **正确示例**：
```python
import os

# 运行时从环境变量注入凭证，避免硬编码
ak = os.environ.get("HW_ACCESS_KEY")
sk = os.environ.get("HW_SECRET_KEY")
security_token = os.environ.get("HW_SECURITY_TOKEN")  # 临时凭证（可选）
```

在运行前通过环境变量提供凭证：
```bash
# 永久凭证
export HW_ACCESS_KEY="<AK>"
export HW_SECRET_KEY="<SK>"

# 临时凭证（更高安全性）
export HW_ACCESS_KEY="<AK>"
export HW_SECRET_KEY="<SK>"
export HW_SECURITY_TOKEN="<TOKEN>"
```

**方式二：命令行参数注入（次选，可接受但不推荐）**

✅ **正确示例**（`deploy_dsh.py` 已内置 `os.environ.get()` 作为默认值，命令行参数仅为覆盖）：
```bash
# 永久凭证
python3 deploy_dsh.py \
  --ak <AK> \
  --sk <SK> \
  --region cn-north-4 \
  --flavor x1.2u.4g

# 临时凭证
python3 deploy_dsh.py \
  --ak <AK> \
  --sk <SK> \
  --security-token <TOKEN> \
  --region cn-north-4 \
  --flavor x1.2u.4g
```

❌ **错误示例**（严禁在源码中硬编码密钥）：
```python
# 禁止：将凭证明文硬编码到源码中，存在泄露风险
AK = "HARDCODED_AK"  # ❌ 硬编码，禁止
SK = "HARDCODED_SK"  # ❌ 硬编码，禁止
```

## 5. 常见问题

### Q: pip install 失败？

✅ **解决方案**：
```bash
# Try with --user flag
pip install --user huaweicloudsdkcore

# Or use mirror
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple huaweicloudsdkcore

# Or use Huawei Cloud mirror (recommended in China)
pip install -i https://repo.huaweicloud.com/repository/pypi/simple huaweicloudsdkcore
```

### Q: 权限不足？

✅ **解决方案**：
```bash
# Check file permissions
ls -la ~/.config/hcloud/

# Fix permissions
chmod 600 ~/.config/hcloud/config.json
```
