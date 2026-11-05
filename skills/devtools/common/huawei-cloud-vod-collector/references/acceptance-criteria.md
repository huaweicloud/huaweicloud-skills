# huawei-cloud-vod-collector 验收标准

本文档列出了 VoD Collector 技能达到生产就绪状态的客观验收标准。

## 功能

- 反馈捕获：可以通过 `md_io.py write-feedback` 创建反馈，并保存到 `.vod/feedbacks/`，文件名格式为 `VOD-YYYYMMDD-NNNN.md`。
- 敏感信息清理：在捕获时自动或通过 `vod_sanitize.py` 清理敏感字段（令牌、密码、密钥）。
- 去重：会话内去重时增加 `recurrence_count`；跨会话去重通过 `vod_deliver.py dedup-scan` 扫描最近反馈（`--lookback`，默认 10 条）得到候选清单，再由 Agent 判定，命中重复则不交付。
- 提取：LLM 丰富会填充关键字段（`error_stack`、`user_intent`、`scenario`、`expected_behavior`、`environment`、`dialog_context`）。
- 交付：`vod_deliver.py deliver` 会将问题提交到配置的 `delivery.channels.gitcode.repo_url`，并更新反馈状态；未加 `--force` 时如发现跨会话强重复候选，返回 `duplicate_suspected` 且不创建 issue。
- 通知渠道：`vod_deliver.py notify --channel webhook|email|auto` 按 `delivery.channels.notification` 配置发送；无待发送反馈时返回 `{"success": true, "pending": 0, "sent": []}`，且不解析 token、不触发登录。
- 自动登录流程：当返回 `need_login` 时，使用 AtomGit-GO 完成安装/登录序列，并将令牌存储在 `${ATOMCODE_HOME:-$HOME/.atomcode}/auth.toml`（权限 0600）下。

## 非功能

- 日志：脚本应提供有意义的错误信息和非敏感调试日志。
- 安全：令牌只能写入 `$ATOMCODE_HOME/auth.toml`（默认 `~/.atomcode/auth.toml`），绝不写入其他位置；设置 `VOD_ATOMGIT_TOKEN` 时优先使用该环境变量且不落盘（注意：POSIX 下同 uid 的进程仍可从 `/proc/<pid>/environ` 读到该变量，更高安全要求请使用短时效 token）。POSIX 下读取前收紧为 0600（无法收紧则拒绝读取），Windows 下由目录 ACL 保护。
- 限制：遵守 `storage.max_feedbacks_per_session` 和其他配置限制。

## 测试用例（示例）

- 创建反馈，运行清理，验证已红线处理。
- 使用有效 `repo_url` 交付反馈，并验证问题已创建。
- 触发 `need_login` 路径并完成登录流程；验证令牌文件存在且权限正确。

## 文档

- `SKILL.md` 包含用法、核心命令、参数列表，以及指向 `references/` 的引用。

## 上线

- 向后兼容：已有 `.vod/` 反馈不会被覆盖。

