# 环境要求与安装指南

## 运行环境

| 依赖 | 版本要求 | 说明 |
|------|---------|------|
| Python | 3.6+ | 脚本仅使用标准库，无第三方依赖 |
| 网络 | 可达 `devdata.huaweicloud.com` | 通过 HTTPS 访问华为云 AI Gallery API |

## 安装步骤

### 1. 确认 Python 版本

```bash
python --version
# 或
python3 --version
```

需确保版本 >= 3.6。

### 2. 验证网络连通性

```bash
curl -s -o /dev/null -w "%{http_code}" "https://devdata.huaweicloud.com/rest/modelarts/user_system/v1/aihub/contents?content_type=skills&limit=1"
```

返回 `200` 表示网络可达。

### 3. 获取脚本

将 `scripts/search_skills.py` 放置到本地任意目录即可使用。

## 常见问题

### Q: 网络不通怎么办？

1. 确认是否可以访问公网
2. 检查防火墙规则是否放行 `devdata.huaweicloud.com`
3. 尝试通过代理访问
