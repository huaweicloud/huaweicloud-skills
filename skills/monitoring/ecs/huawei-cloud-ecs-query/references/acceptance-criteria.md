# Acceptance Criteria — huawei-cloud-ecs-query

技能验收标准。全部通过视为本次交付合格。

## 功能验收

- [ ] `python3 scripts/ecs_query.py list-servers --config config.yaml` 可列出 ECS 实例（表格与 `--output json` 两种格式）
- [ ] `list-servers` 支持 `--status` / `--name` / `--flavor` 过滤参数
- [ ] `python3 scripts/ecs_query.py show-server --server-id <id>` 返回实例详情
- [ ] `python3 scripts/ecs_query.py server-status --server-id <id>` 返回状态及中文说明
- [ ] `show-server` 输出包含挂载云硬盘字段（API 返回时）
- [ ] `server-status` 状态输出与列表/详情复用统一格式化模块（无重复实现）
- [ ] AK/SK 与 Token 两种认证方式均可完成查询
- [ ] `--region` 参数可切换区域查询（需配置 `regions` 映射或 `--project-id`），切换后不报 Common.0018
- [ ] `--project-id` 参数可临时指定目标区域项目ID

## 健壮性验收

- [ ] server-id 缺失时给出明确提示并退出（exit 1）
- [ ] 配置文件缺失时给出创建指引
- [ ] API 失败时输出 HTTP 状态与错误正文，而非裸异常
- [ ] Token 认证失败（获取 Token 401 等）时输出「认证失败」友好提示而非 traceback
- [ ] 查询参数含特殊字符（空格/&/=/中文）时请求不报 400/签名错误
- [ ] 表格输出 ID 截断时给出「使用 --output json 获取完整 ID」提示

## 安全验收

- [ ] 代码中无 AK/SK/密码硬编码（配置仅从 config.yaml / 参数读取）
- [ ] 文档示例均使用占位符（your-access-key-id 等）
- [ ] 配置文件路径建议置于 `~/.huawei-ecs/`，不随仓库提交
- [ ] SKILL.md 声明「不支持查看/重置云服务器登录密码、密钥等敏感凭据」
- [ ] SKILL.md 声明「不支持账单/费用/配额等 BSS 类查询」
- [ ] SKILL.md 提供写操作（创建/删除/启停/规格变更/迁移）统一拒绝话术

## 文档验收

- [ ] SKILL.md 含工作流、核心命令、注意事项章节
- [ ] references/ 含 cli-installation-guide / iam-policies / verification-method / api-reference
- [ ] 所有 references 链接在 SKILL.md 中可访问