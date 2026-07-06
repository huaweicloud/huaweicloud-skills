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
pip install huaweicloudsdkcore huaweicloudsdkecs huaweicloudsdkvpc huaweicloudsdkeip huaweicloudsdkcoc requests
```

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

**方式一：命令行参数（推荐）**

✅ **正确示例**：
```bash
python3 deploy_sqlbot.py \
  --ak AKEXAMPLE123456 \
  --sk SKEXAMPLE789012 \
  --project-id PROJECT123456 \
  --region cn-north-4
```

**方式二：环境变量**

✅ **正确示例**：
```bash
export HW_ACCESS_KEY="AKEXAMPLE123456"
export HW_SECRET_KEY="SKEXAMPLE789012"
```

❌ **错误示例**：
```python
# Do NOT hardcode credentials in source code
AK = "AKEXAMPLE123456"  # Security risk!
SK = "SKEXAMPLE789012"  # Security risk!
```

## 5. 常见问题

### Q: pip install 失败？

✅ **解决方案**：
```bash
# Try with --user flag
pip install --user huaweicloudsdkcore

# Or use mirror
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple huaweicloudsdkcore
```

### Q: 权限不足？

✅ **解决方案**：
```bash
# Check file permissions
ls -la ~/.config/hcloud/

# Fix permissions
chmod 600 ~/.config/hcloud/config.json
```
