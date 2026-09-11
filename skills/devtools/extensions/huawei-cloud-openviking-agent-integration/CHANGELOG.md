# Changelog

## [1.2.1] — 2026-09-09

- 合并 CodeArts + 本地两个瘦身版本，各取所长；openclaw.sh 同步上游更新
- 脚本：lib/ 和入口脚本取 CodeArts 深度瘦身版（registry.sh 142→84, common.sh 26→9, ui.sh 70→55 等）；agent 脚本取两者中更小版本
- 文档：SKILL.md 保留 YAML frontmatter + 本地精简正文结构；guardrails.md 吸收 iam-policies 权限表；agent-configs.md 保留表格结构 + CodeArts 小代码块示例；verification.md 表格格式 + agent-specific 细节
- 瘦身：合并 verification-method + acceptance-criteria → verification.md；删除 iam-policies.md（信息已在 SKILL.md）、demo/example-input.json（内容已被参数表覆盖）
- CodeArts/OpenCode 改用 `@openviking/opencode-plugin` + 共享插件缓存（TTL 24h）；TUI 启动慢修复（注入 package-lock.json + offline 配置 + 预填缓存）
- WorkSwarm 双通道 + 运行时补丁（code-mode 主动召回、top_k→limit、account 默认值修复）
- base.sh 新增宿主机软件检测、共享缓存框架、运行时补丁框架、集中常量
- opencode.sh 重构：删除无效步骤、合并冗余逻辑、修复 unbind 遗漏与 status 检测
- 总体积 332K→284K（−14.5%），总行数 5786→~4700（−18.7%），所有脚本 bash -n 通过

## [1.2.0] — initial release

- 8 agent 集成/解绑全生命周期
- 插件依赖缓存（TTL 1 天）
