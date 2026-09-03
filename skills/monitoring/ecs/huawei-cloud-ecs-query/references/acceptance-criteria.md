# Acceptance Criteria — huawei-cloud-ecs-query

技能验收标准。全部通过视为本次交付合格。

## 功能验收

- [ ] `python3 scripts/ecs_query.py list-servers --config config.yaml` 可列出 ECS 实例（表格与 `--output json` 两种格式）
- [ ] `list-servers` 支持 `--status` / `--name` / `--flavor` 过滤参数
- [ ] `python3 scripts/ecs_query.py show-server --server-id <id>` 返回实例详情
- [ ] `python3 scripts/ecs_query.py server-status --server-id <id>` 返回状态及中文说明
- [ ] AK/SK 与 Token 两种认证方式均可完成查询
- [ ] `--region` 参数可切换区域查询

## 健壮性验收

- [ ] server-id 缺失时给出明确提示并退出（exit 1）
- [ ] 配置文件缺失时给出创建指引
- [ ] API 失败时输出 HTTP 状态与错误正文，而非裸异常

## 安全验收

- [ ] 代码中无 AK/SK/密码硬编码（配置仅从 config.yaml / 参数读取）
- [ ] 文档示例均使用占位符（your-access-key-id 等）
- [ ] 配置文件路径建议置于 `~/.huawei-ecs/`，不随仓库提交

## 文档验收

- [ ] SKILL.md 含工作流、核心命令、注意事项章节
- [ ] references/ 含 cli-installation-guide / iam-policies / verification-method / api-reference
- [ ] 所有 references 链接在 SKILL.md 中可访问