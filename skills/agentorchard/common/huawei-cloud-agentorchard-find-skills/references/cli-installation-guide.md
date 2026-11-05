# 环境要求与安装指南

## 运行环境

| 依赖 | 版本要求 | 说明 |
|------|---------|------|
| Python | 3.6+ | 脚本仅使用标准库，无第三方依赖 |
| 网络 | 可达 `devdata.huaweicloud.com` | 通过 HTTPS 访问华为云 AI Gallery API |

## 安装步骤

> 脚本使用标准库即可运行，不依赖第三方库。以下命令使用 `python3`；若环境仅提供 `python`（且同时有 python3），可用 `python` 等价执行。

### 1. 确认 Python 版本

```bash
python3 --version
```

需确保版本 >= 3.6。

### 2. 验证网络连通性

```bash
curl -s -o /dev/null -w "%{http_code}" "https://devdata.huaweicloud.com/rest/aiasset/user_system/v1/aihub/contents?content_type=skills&limit=1"
```

返回 `200` 表示网络可达。

> 注：连通性检查地址与脚本内 `DEFAULT_API_BASE`（`/rest/aiasset/user_system`）保持一致。

### 3. 获取脚本

将 `scripts/search_skills.py` 放置到本地任意目录即可使用。

## 常见问题

### Q: 网络不通怎么办？

1. 确认是否可以访问公网
2. 检查防火墙规则是否放行 `devdata.huaweicloud.com`
3. 尝试通过代理访问

### Q: 提示 `python3: command not found`？

1. 确认已安装 Python 3.6+（如 `apt install python3` / `yum install python3`）
2. 若系统仅提供 `python`，将命令中的 `python3` 替换为 `python`

### Q: 如何在本地运行搜索脚本？

```bash
cd <技能目录>
PYTHONIOENCODING=utf-8 python3 scripts/search_skills.py -k "银行"
```
