# CLI Installation Guide — huawei-cloud-ecs-query

本技能的核心查询能力通过 Python 脚本（`scripts/ecs_query.py`）实现，同时也提供 hcloud CLI（KooCLI）等价命令供已安装 CLI 的环境使用。

## 1. Python 环境（脚本必需）

### 安装依赖

```bash
pip install requests pyyaml
```

### 验证

```bash
python3 -c "import requests, yaml; print('OK')"
```

## 2. hcloud CLI（KooCLI，可选）

如使用 hcloud CLI 等价命令查询，需安装并配置 KooCLI。

### 安装

通过官方一键脚本安装（推荐）：

```bash
curl -o hcloud_install.sh https://hwcloudcli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh
bash hcloud_install.sh
```

更多安装方式参见 [KooCLI 官方文档](https://support.huaweicloud.com/usermanual-hcli/hcli_01_001.html)。

### 配置认证

```bash
hcloud configure
# 按提示输入 AK/SK 与区域
```

### 验证

```bash
hcloud version
hcloud ECS ListServersDetails --cli-region=cn-north-4 --limit=1
```

## 3. 认证模式说明

| 模式 | 适用范围 |
|------|----------|
| 脚本 AK/SK | `config.yaml` 中 `auth_method: aksk`，Python 脚本直连 API |
| 脚本 Token | `config.yaml` 中 `auth_method: token`，先获取 Token 再查询 |
| hcloud CLI | `hcloud configure` 后使用等价命令 |

> **安全提示**：`config.yaml` 含有 AK/SK 或密码等敏感信息，严禁提交到版本控制系统；建议将配置文件放在 `~/.huawei-ecs/config.yaml` 并加入 `.gitignore`。