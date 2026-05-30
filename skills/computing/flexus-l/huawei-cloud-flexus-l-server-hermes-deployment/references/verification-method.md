# 技能验证方法

本文档描述了 Hermes 一键部署技能的验证方法和测试步骤。

## 验证流程

### 阶段一：环境准备验证

**验证项：**
- [ ] Python 版本 >= 3.8
- [ ] 依赖包已安装 (`pip install -r requirements.txt`)
- [ ] 华为云 AK/SK 准备就绪
- [ ] 网络连通性正常

**验证命令：**
```bash
# 检查 Python 版本
python --version

# 检查依赖安装
python -c "from huaweicloudsdkcore.signer.signer import Signer; print('SDK OK')"

# 检查命令行参数支持
python scripts/caller.py deploy --help
```

### 阶段二：部署功能验证

**验证项：**
- [ ] 实例创建成功
- [ ] 实例状态正常
- [ ] 实例规格符合预期

**验证命令：**
```bash
# 部署实例（测试环境建议使用较小规格）
python scripts/caller.py deploy --ak <your_ak> --sk <your_sk> --name test-hermes --region cn-north-4

# 验证实例状态（通过华为云控制台或API）
```

**预期结果：**
- 实例创建成功，状态为 "running"
- 实例规格符合预期配置

### 阶段三：模型配置验证

**验证项：**
- [ ] UniAgent 状态为 ONLINE
- [ ] 模型配置成功
- [ ] 模型可正常调用

**验证命令：**
```bash
# 配置模型
python scripts/caller.py maas --ak <your_ak> --sk <your_sk> --resource-id <instance_id> --region-id cn-north-4 --api-key <your_api_key> --model-name deepseek-v3.2 --non-interactive
```

**预期结果：**
- UniAgent 状态检查通过
- 模型配置任务执行成功

### 阶段四：通道配置验证

**验证项：**
- [ ] 通道配置成功
- [ ] 通道状态正常
- [ ] 消息收发正常

**验证命令：**
```bash
# 配置通道（飞书）
python scripts/caller.py channel --ak <your_ak> --sk <your_sk> --resource-id <instance_id> --region-id cn-north-4 --bot-platform feishu --feishu-app-id <app_id> --feishu-app-secret <app_secret> --non-interactive
```

**预期结果：**
- 通道配置任务执行成功
- 通道显示在 Hermes 通道列表中

## 常见问题排查

### 问题 1：AK/SK 验证失败

**现象：**
```
错误：AK/SK 验证失败，请检查凭证是否正确
```

**排查步骤：**
1. 确认 `--ak` 和 `--sk` 参数已正确传递
2. 确认 AK/SK 未过期
3. 确认 AK/SK 具有足够的权限

### 问题 2：UniAgent 状态异常

**现象：**
```
UniAgent状态: OFFLINE
请确保UniAgent已启动并在线
```

**排查步骤：**
1. 等待实例完全启动（通常需要 5-10 分钟）
2. 通过华为云控制台检查 UniAgent 状态
3. 尝试重启 UniAgent 服务

### 问题 3：模型配置超时

**现象：**
```
错误：执行超时，请检查网络连接或增加超时时间
```

**排查步骤：**
1. 增加超时时间参数 `--timeout 1200`
2. 检查实例网络连接
3. 确认模型参数正确

## 自动化测试脚本

可以创建以下测试脚本来自动化验证流程：

```bash
#!/bin/bash
echo "=== Hermes Deployment Verification ==="

echo ""
echo "1. Checking Python version..."
python --version

echo ""
echo "2. Checking SDK installation..."
python -c "from huaweicloudsdkcore.signer.signer import Signer; print('SDK OK')"

echo ""
echo "3. Checking command line parameters..."
python scripts/caller.py deploy --help | grep -E "(ak|sk)"

echo ""
echo "=== Verification completed ==="
echo ""
echo "Note: AK/SK credentials are passed via --ak and --sk command line parameters"
```

## 验证矩阵

| 验证项 | 成功标准 | 失败处理 |
|--------|----------|----------|
| 环境准备 | Python >= 3.8, 依赖安装成功 | 检查 Python 版本，重新安装依赖 |
| 凭证配置 | `--ak` 和 `--sk` 参数已正确传递 | 确认 AK/SK 参数正确 |
| 实例部署 | 实例创建成功，状态 running | 检查权限和网络 |
| 模型配置 | 模型配置成功，可正常调用 | 检查 UniAgent 状态和模型参数 |
| 通道配置 | 通道配置成功，可收发消息 | 检查通道配置参数 |