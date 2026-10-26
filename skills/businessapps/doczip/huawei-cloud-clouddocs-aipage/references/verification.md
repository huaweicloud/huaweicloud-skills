# 验收标准 — huawei-cloud-clouddocs-aipage

## 前置条件

- Windows 环境（clouddocs-cli 仅提供 Windows 安装包）
- clouddocs-cli 已安装并加入 PATH（`command -v clouddocs-cli` 能定位）
- clouddocs-cli 已登录（`clouddocs-cli auth status` 显示 ready）
- 服务地址已配置（`~/.clouddocs/config.json` 的 `base_url` 非空）
- Python 3.8+ 标准库可用

## 验收用例

### A1. 安装链路

| 步骤 | 操作 | 预期 |
|------|------|------|
| 1 | `powershell -ExecutionPolicy Bypass -File bin/windows/install-windows.ps1` | 安装成功，`clouddocs-cli --help` 可执行 |
| 2 | 同目录存在 SHA256SUMS 时安装 | 输出「✔ 安装包校验和匹配」 |
| 3 | 同目录无安装包时安装 | 报错并指引到 cli-installation-guide.md 获取渠道，退出码 1 |

### A2. 鉴权探测（--probe-auth）

| 步骤 | 操作 | 预期 |
|------|------|------|
| 1 | CLI 已安装且已登录：`python3 scripts/create_page.py --probe-auth` | 输出 JSON，`auth_ready=true`，退出码 0 |
| 2 | CLI 未安装：`python3 scripts/create_page.py --probe-auth` | 输出友好错误信息，退出码 2（不抛 Traceback） |

### A3. 创建在线 page 文档

| 步骤 | 操作 | 预期 |
|------|------|------|
| 1 | 准备 `drafts/page.md`，运行 `create_page.py --title '测试文档'` | 退出码 0，stdout 含 `doc_id` / `doc_url` |
| 2 | 重跑同一命令（幂等） | 退出码 0，`reused=true`，不重复建文档 |
| 3 | 缺 `--title` | 退出码 1，提示缺少 --title |
| 4 | 缺 `drafts/page.md` 且无 `--content` | 退出码 1，提示缺少内容 |

### A4. 导出 docx

| 步骤 | 操作 | 预期 |
|------|------|------|
| 1 | 创建成功后执行 `clouddocs-cli file +export --document_id <id> --export_type word --output <dir>` | 导出 docx 到指定目录 |
| 2 | 导出失败重试 | 最多重试 1 次，仍失败则放弃导出，只交付链接 |

### A5. 文档一致性

| 检查项 | 预期 |
|--------|------|
| SKILL.md 与 _hws_cli.py docstring 关于 organization_id/wiki_id 的表述 | 统一为「脚本自动解析，模型无需手动前置」 |
| install-windows.ps1 末尾文档引用 | 指向 `cli-installation-guide.md`，不引用不存在的 INSTALL-GUIDE.md |
| bin/windows/SHA256SUMS | 存在且与 zip 包哈希匹配 |
