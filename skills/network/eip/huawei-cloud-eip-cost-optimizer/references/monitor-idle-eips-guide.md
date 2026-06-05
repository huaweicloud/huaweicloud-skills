# 闲置 EIP 监控工具使用指南

## 功能概述

`monitor_idle_eips.py` 是一个基于华为云 Python SDK v2 的闲置 EIP 监控工具，支持：

- ✅ 自动扫描闲置 EIP（未绑定的 EIP）
- ✅ 自定义闲置天数阈值
- ✅ 企业微信/钉钉 webhook 通知
- ✅ 邮件告警通知
- ✅ 定时监控任务（cron）
- ✅ 详细的监控报告（包含成本估算）

## 快速开始

### 1. 配置环境变量

```bash
export HUAWEI_CLOUD_AK='your-access-key'
export HUAWEI_CLOUD_SK='your-secret-key'
export HUAWEI_CLOUD_REGION='cn-north-4'  # 可选，默认 cn-north-4
```

### 2. 基本扫描

```bash
# 扫描闲置 EIP（默认阈值：7 天）
python3 scripts/monitor_idle_eips.py --scan

# 自定义闲置天数阈值
python3 scripts/monitor_idle_eips.py --scan --idle-days 3
```

### 3. 发送告警通知

#### 企业微信/钉钉 webhook

```bash
# 企业微信群机器人 webhook
python3 scripts/monitor_idle_eips.py --scan \
  --wechat-webhook "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"

# 钉钉群机器人 webhook
python3 scripts/monitor_idle_eips.py --scan \
  --wechat-webhook "https://oapi.dingtalk.com/robot/send?access_token=xxx"
```

#### 邮件告警

```bash
python3 scripts/monitor_idle_eips.py --scan \
  --email "admin@example.com" \
  --email-user "sender@163.com" \
  --email-pass "your-authorization-code" \
  --email-smtp "smtp.163.com" \
  --email-port 465
```

### 4. 设置定时监控

```bash
# 设置每天 9:00 自动扫描
python3 scripts/monitor_idle_eips.py --setup-cron

# 设置定时任务并配置 webhook
python3 scripts/monitor_idle_eips.py --setup-cron \
  --wechat-webhook "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
```

## 输出示例

### 控制台报告

```
====================================================================================================
⚠️  闲置 EIP 监控报告 (区域：cn-north-4)
====================================================================================================
扫描时间：2026-05-25 02:07:15
发现闲置 EIP 数量：1 个
====================================================================================================
EIP ID                                   IP 地址            带宽         状态         闲置天数       创建时间
----------------------------------------------------------------------------------------------------
9287783b-12c3-4288-bafd-22d91288f99c     120.46.5.112     1 Mbps     DOWN       未知         2026-05-24 17:24:59
----------------------------------------------------------------------------------------------------

💰 估算带宽资源浪费：1 Mbps
⚠️  建议及时释放或绑定这些闲置 EIP 以节省成本
====================================================================================================
```

### 企业微信消息

```
## ⚠️  闲置 EIP 告警 - 发现 1 个闲置 EIP

**扫描时间**: 2026-05-25 02:07:15

### 📊 发现 1 个闲置 EIP

| EIP ID | IP 地址 | 带宽 | 闲置天数 |
|--------|---------|------|----------|
| 9287783b... | 120.46.5.112 | 1 Mbps | 未知 |

建议及时处理闲置 EIP 以节省成本。
```

## 参数说明

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--scan` | 扫描闲置 EIP（必需） | - | `--scan` |
| `--idle-days DAYS` | 闲置天数阈值 | 7 | `--idle-days 3` |
| `--wechat-webhook URL` | 企业微信/钉钉 webhook URL | - | `--wechat-webhook "https://..."` |
| `--email EMAIL` | 告警邮箱地址 | - | `--email "admin@example.com"` |
| `--email-smtp HOST` | SMTP 服务器 | smtp.163.com | `--email-smtp "smtp.qq.com"` |
| `--email-port PORT` | SMTP 端口 | 465 | `--email-port 587` |
| `--email-user USER` | SMTP 登录用户名 | - | `--email-user "sender@163.com"` |
| `--email-pass PASS` | SMTP 登录密码/授权码 | - | `--email-pass "abc123"` |
| `--setup-cron` | 设置定时监控任务 | - | `--setup-cron` |

## 闲置 EIP 判定规则

一个 EIP 被判定为闲置需要满足以下条件：

1. **未绑定资源**: `port_id` 为 `None` 或空字符串
2. **超过闲置阈值**: 创建时间距离当前时间 >= `--idle-days` 指定的天数

**注意**: 如果无法解析 EIP 的创建时间，只要 EIP 未绑定，就会被视为闲置。

## 成本估算

工具会根据闲置 EIP 的带宽大小估算资源浪费：

- **带宽浪费**: 所有闲置 EIP 的带宽总和（Mbps）
- **费用参考**: 华为云 EIP 带宽费用约为 0.8 元/Mbps/天（按量计费）

例如：1 个闲置 EIP，带宽 5 Mbps，每天浪费约 4 元。

## 最佳实践

### 1. 每日定时监控

```bash
# 设置每天早上 9:00 自动扫描并发送微信通知
python3 scripts/monitor_idle_eips.py --setup-cron \
  --wechat-webhook "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx" \
  --idle-days 7
```

### 2. 结合闲置 EIP 释放

```bash
# 先扫描监控
python3 scripts/monitor_idle_eips.py --scan --idle-days 7

# 确认无误后释放闲置 EIP
python3 scripts/find_and_release_idle_eips.py --release
```

### 3. 多区域监控

```bash
# 为不同区域设置独立的监控任务
export HUAWEI_CLOUD_REGION=cn-north-4
python3 scripts/monitor_idle_eips.py --setup-cron --idle-days 7

export HUAWEI_CLOUD_REGION=cn-east-3
python3 scripts/monitor_idle_eips.py --setup-cron --idle-days 7
```

## 故障排查

### 问题 1: 认证失败

```
❌ 错误：未检测到认证信息
请设置环境变量 HUAWEI_CLOUD_AK 和 HUAWEI_CLOUD_SK
```

**解决方案**: 确保已正确设置环境变量：
```bash
export HUAWEI_CLOUD_AK='your-ak'
export HUAWEI_CLOUD_SK='your-sk'
```

### 问题 2: webhook 发送失败

```
❌ 发送微信通知失败：HTTP Error 400: Bad Request
```

**解决方案**:
1. 检查 webhook URL 是否正确
2. 确认机器人已添加到群聊
3. 检查 webhook 是否已启用

### 问题 3: 邮件发送失败

```
❌ 发送邮件告警失败：(535, b'Authentication Failed')
```

**解决方案**:
1. 使用授权码而非登录密码（163/QQ 邮箱）
2. 确认 SMTP 服务已开启
3. 检查邮箱账号和密码是否正确

## 相关文件

- 脚本路径：`scripts/monitor_idle_eips.py`
- 技能文档：`SKILL.md`
- 参考文档：`references/python-sdk-usage-guide.md`

## 版本历史

- **v1.0.0** (2026-05-25): 初始版本，支持扫描、webhook、邮件、定时任务
